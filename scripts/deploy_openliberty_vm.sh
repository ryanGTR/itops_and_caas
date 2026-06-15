#!/usr/bin/env bash
# deploy_openliberty_vm.sh — 治理化部署到「真 QEMU/libvirt VM」上的 OpenLiberty。
#
# D6 的 VM 版:部署目標從 podman 容器升級為 OpenTofu 開的 libvirt VM。
#   D5 部署前驗章閘門(fail-closed) ──放行──▶ tofu apply(開 VM,取 NAT IP)
#     ──▶ scp WAR+server.xml ──▶ 在 VM 內裝 Java21+OpenLiberty+部署 ──▶ 煙霧測試
#
# 對應:ISO 20000 發布與部署管理、ISO 27001 A.8.28 完整性。
# 前置:libvirt(qemu:///system,default NAT 網路)、tofu、sshpass、cdrtools(mkisofs)。
set -euo pipefail
cd "$(dirname "$0")/.." || exit 2
export PATH="$HOME/.local/bin:$PATH"

REQUEST="${REQUEST:-deployments/openliberty-sandbox/supply-chain-backend.yaml}"
SIGNATURE="${SIGNATURE:-deployments/openliberty-sandbox/sig/supply-chain-backend.sig}"
ENV_DIR="iac/environments/vm-openliberty"
BACKEND="${BACKEND:-$HOME/Documents/supply-chain/github/app/backend}"
SSHU=debian
SSHPW="${VM_PASSWORD:-itops}"
SSHO=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10)
say() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }

# ── 階段⑤:部署前驗章閘門(治理 — 與容器版同一道 fail-closed 閘門)──
say "[1/5] D5 部署前驗章閘門(fail-closed)"
python3 scripts/verify_deploy_gate.py --request "$REQUEST" --signature "$SIGNATURE" \
  || { echo "✗ 驗章閘門拒絕,中止(VM 不會被開)。" >&2; exit 1; }

# ── 階段④:OpenTofu 開 VM,取 NAT IP ──
say "[2/5] OpenTofu apply(開 QEMU/libvirt VM)"
tofu -chdir="$ENV_DIR" init -input=false >/dev/null
tofu -chdir="$ENV_DIR" apply -auto-approve >/dev/null
IP="$(tofu -chdir="$ENV_DIR" output -raw vm_ip)"
echo "  VM IP:$IP"

# ── 等 SSH 起來 ──
for i in $(seq 1 30); do
  sshpass -p "$SSHPW" ssh "${SSHO[@]}" "$SSHU@$IP" true 2>/dev/null && break
  sleep 3
done

# ── 階段⑥:推 app 產物 + 在 VM 內裝 OpenLiberty 部署 ──
say "[3/5] 推送 WAR + server.xml,VM 內部署 OpenLiberty"
[ -f "$BACKEND/target/liberty-backend.war" ] || (cd "$BACKEND" && mvn -B -q clean package -DskipTests)
sshpass -p "$SSHPW" scp -O "${SSHO[@]}" \
  "$BACKEND/target/liberty-backend.war" \
  "$BACKEND/src/main/liberty/config/server.xml" \
  "$ENV_DIR/provision-app.sh" "$SSHU@$IP:/tmp/" >/dev/null
sshpass -p "$SSHPW" ssh "${SSHO[@]}" "$SSHU@$IP" 'sudo bash /tmp/provision-app.sh' | tail -3

# ── 煙霧測試(host 直連 VM:9080)──
say "[4/5] 煙霧測試(host → VM:9080)"
SMOKE_OK=true
for path in /health /api/products; do
  ok=false
  for i in $(seq 1 30); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://$IP:9080$path")" = "200" ] && { ok=true; break; }
    sleep 3
  done
  $ok && echo "  ✅ GET $path → 200" || { echo "  ✗ GET $path 未回 200"; SMOKE_OK=false; }
done

# ── 留痕 ──
say "[5/5] 記錄部署結果"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RESULT=$([ "$SMOKE_OK" = true ] && echo success || echo failed)
mkdir -p deployments/vm-openliberty
cat > deployments/vm-openliberty/last-deploy.json <<JSON
{
  "app": "supply-chain-backend",
  "environment": "vm-openliberty",
  "target": "qemu/libvirt VM (OpenTofu)",
  "vmIp": "${IP}",
  "url": "http://${IP}:9080",
  "deployedAt": "${TS}",
  "gate": "passed",
  "smokeTest": { "health": "GET /health", "business": "GET /api/products" },
  "result": "${RESULT}"
}
JSON
echo "  → deployments/vm-openliberty/last-deploy.json (result=${RESULT})"
[ "$SMOKE_OK" = true ] && echo -e "\n▶ 部署成功 ✅  supply-chain-backend 在真 VM 的 OpenLiberty 上可服務(http://${IP}:9080)" || exit 1
