#!/usr/bin/env bash
# setup-itop.sh — 一鍵把 iTop(Combodo)在本機站起來 + 啟用 REST API,給 itop_sync.py 用。
#
# 把原本零散的手動步驟固化成可重現腳本(冪等;重跑安全)。涵蓋:
#   1. 跑 vbkunin/itop 容器(內含 MariaDB)
#   2. 無人值守安裝「完整 ITIL 資料模型」(itop-install.xml — 真實模組名,非 extension_code)
#   3. 修正權限/DB 帳號(install 以 root CLI 跑,檔案/連線會對不上 www-data → 必修)
#   4. 啟用 REST:給 admin「REST Services User」profile,並建 least-privilege 服務帳號
#
# ⚠️ 機敏資訊一律走環境變數,別寫進腳本、別 commit:
#     ITOP_ADMIN_PWD  iTop admin 密碼(未設則自動產生)
#     ITOP_DB_PWD     itop_db 專用 DB 帳號密碼(未設則自動產生)
#     ITOP_SVC_PWD    svc_itops_sync REST 服務帳號密碼(未設則自動產生)
#   產生的密碼會寫到 ./.itop-secrets(已被 .gitignore 忽略),給 itop_sync.py 取用。
#
# 用法:  bash integration/itop/setup-itop.sh
#         source .itop-secrets   # 然後 ITOP_PWD=$ITOP_SVC_PWD python3 scripts/itop_sync.py ...
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
CTR="${ITOP_CONTAINER:-itop}"
PORT="${ITOP_PORT:-8000}"
IMAGE="docker.io/vbkunin/itop:latest"
SECRETS="$REPO/.itop-secrets"
say() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }

gen() { openssl rand -hex "${1:-6}"; }
ITOP_ADMIN_PWD="${ITOP_ADMIN_PWD:-ItopAdmin_$(gen 4)}"
ITOP_DB_PWD="${ITOP_DB_PWD:-itopdb_$(gen 4)}"
ITOP_SVC_PWD="${ITOP_SVC_PWD:-SvcItops_$(gen 6)}"

# ── 1. 容器 ────────────────────────────────────────────────
say "[1/4] 啟動 iTop 容器($CTR,:$PORT)"
if ! podman ps --format '{{.Names}}' | grep -qx "$CTR"; then
  podman rm -f "$CTR" >/dev/null 2>&1 || true
  podman run -d -p "${PORT}:80" --name "$CTR" "$IMAGE" >/dev/null
fi
say "等待 MariaDB ready"
for _ in $(seq 1 30); do
  podman exec "$CTR" sh -c 'mysqladmin -uroot ping 2>/dev/null' | grep -q alive && break
  sleep 2
done

# ── 2. 無人值守安裝(完整 ITIL 模組)──────────────────────────
say "[2/4] 無人值守安裝(datamodel 3.2.1,完整 ITIL 模組)"
podman exec "$CTR" sh -c 'rm -f /var/www/html/data/.maintenance; \
  mysql -uroot -e "DROP DATABASE IF EXISTS itop_db; CREATE DATABASE itop_db CHARACTER SET utf8mb4;"'
sed "s/__SET_YOUR_ADMIN_PWD__/${ITOP_ADMIN_PWD}/" "$HERE/itop-install.xml" > /tmp/itop-install-filled.xml
podman cp /tmp/itop-install-filled.xml "$CTR":/tmp/itop-install.xml
rm -f /tmp/itop-install-filled.xml
podman exec "$CTR" sh -c 'cd /var/www/html/setup/unattended-install && \
  php unattended-install.php --param-file=/tmp/itop-install.xml' | tail -3
podman exec "$CTR" sh -c 'rm -f /tmp/itop-install.xml'

# ── 3. 修權限 + DB 帳號 + 授 REST profile(install 以 root CLI 跑造成的落差)──────
#   雷:config 與 data/log 被建成 root:root → www-data(apache)讀不到 → REST 報
#       "Could not find configuration file";root 又只能 unix_socket 登入 → www-data 連 DB 被拒。
#   REST 閘門:3.2.x 是 secure_rest_services + 硬編碼 HasProfile('REST Services User'),
#   舊 README 寫的 allowed_rest_profiles 對 3.2.x 無效 → 改成「給 admin 這個 profile」。
say "[3/4] 修正權限 + DB 帳號 + 授 admin REST profile"
podman exec "$CTR" sh -c "mysql -uroot -e \"
  CREATE USER IF NOT EXISTS 'itop'@'localhost' IDENTIFIED BY '${ITOP_DB_PWD}';
  GRANT ALL PRIVILEGES ON itop_db.* TO 'itop'@'localhost'; FLUSH PRIVILEGES;\""
podman exec "$CTR" sh -c "
  chown -R www-data:www-data /var/www/html/conf /var/www/html/data /var/www/html/log /var/www/html/env-production 2>/dev/null
  chmod 640 /var/www/html/conf/production/config-itop.php
  sed -i \"s/'db_user' => 'root'/'db_user' => 'itop'/\" /var/www/html/conf/production/config-itop.php
  sed -i \"s/'db_pwd' => ''/'db_pwd' => '${ITOP_DB_PWD}'/\" /var/www/html/conf/production/config-itop.php"
REST_ID=$(podman exec "$CTR" sh -c "mysql -uitop -p'${ITOP_DB_PWD}' -N itop_db -e \
  \"SELECT id FROM priv_urp_profiles WHERE name='REST Services User';\"")
podman exec "$CTR" sh -c "mysql -uitop -p'${ITOP_DB_PWD}' itop_db -e \
  \"INSERT INTO priv_urp_userprofile (userid, profileid, description)
    SELECT 1, ${REST_ID}, 'Bootstrap REST for admin'
    WHERE NOT EXISTS (SELECT 1 FROM priv_urp_userprofile WHERE userid=1 AND profileid=${REST_ID});\""

# 乾淨重啟一次(由 runit 重起 apache+mysql),讓 config 改動 + profile 生效。
# 不用 apachectl -k graceful——那在 runit 容器會另起一隻 rogue apache。
say "重啟容器讓設定生效"
podman restart "$CTR" >/dev/null
for _ in $(seq 1 30); do
  podman exec "$CTR" sh -c 'mysqladmin -uroot ping 2>/dev/null' | grep -q alive && break; sleep 2
done
REST="http://localhost:${PORT}/webservices/rest.php?version=1.3"
for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${PORT}/" || true)
  [ "$code" = "302" ] || [ "$code" = "200" ] && break; sleep 1
done

# ── 4. 建 least-privilege 服務帳號(經 REST,iTop 自己雜湊密碼)──
say "[4/4] 建服務帳號 svc_itops_sync(least-privilege)"
# 建服務帳號(若不存在):REST Services User(1024)+ Configuration Manager(3)+ Change Supervisor(8)+ Service Desk Agent(4)
EXIST=$(curl -s "$REST" --data-urlencode auth_user=admin --data-urlencode auth_pwd="$ITOP_ADMIN_PWD" \
  --data-urlencode 'json_data={"operation":"core/get","class":"UserLocal","key":"SELECT UserLocal WHERE login=\"svc_itops_sync\"","output_fields":"id"}' \
  | python3 -c 'import sys,json;print(len(json.load(sys.stdin).get("objects") or {}))')
if [ "$EXIST" = "0" ]; then
  curl -s "$REST" --data-urlencode auth_user=admin --data-urlencode auth_pwd="$ITOP_ADMIN_PWD" \
    --data-urlencode "json_data={\"operation\":\"core/create\",\"class\":\"UserLocal\",\"comment\":\"itops_sync service account\",\"output_fields\":\"id,login\",\"fields\":{\"login\":\"svc_itops_sync\",\"password\":\"${ITOP_SVC_PWD}\",\"language\":\"EN US\",\"profile_list\":[{\"profileid\":\"1024\"},{\"profileid\":\"3\"},{\"profileid\":\"8\"},{\"profileid\":\"4\"}]}}" \
    | python3 -c 'import sys,json;d=json.load(sys.stdin);print("  服務帳號:",d.get("message") or list(d.get("objects",{}).values())[0]["message"])'
else
  echo "  服務帳號 svc_itops_sync 已存在(略過建立;密碼沿用既有)"
fi

# ── 寫 secrets(供 itop_sync.py / 之後 source 用)──────────────
umask 077
cat > "$SECRETS" <<EOF
# iTop 本機開發密碼 — 由 setup-itop.sh 產生。請勿 commit(已在 .gitignore)。
export ITOP_URL="http://localhost:${PORT}"
export ITOP_USER="svc_itops_sync"
export ITOP_ADMIN_PWD="${ITOP_ADMIN_PWD}"
export ITOP_DB_PWD="${ITOP_DB_PWD}"
export ITOP_SVC_PWD="${ITOP_SVC_PWD}"
export ITOP_PWD="${ITOP_SVC_PWD}"   # itop_sync.py 預設讀這個
EOF

echo
echo "✅ iTop 就緒:http://localhost:${PORT}  (admin / 見 .itop-secrets)"
echo "   REST 服務帳號:svc_itops_sync(least-privilege)"
echo "   下一步:source .itop-secrets && python3 scripts/itop_sync.py --env vm-openliberty"
