#!/usr/bin/env python3
"""itop_sync — 把 itops 的 CMDB-as-code 推進「真 iTop（Combodo）」當系統 of record。

定位:itops 的 git 版控 CMDB(`cmdb/<env>/*.yaml`)是「左側護欄 + 政策即程式碼」的產物;
合規通過、成功部署的東西,才由本工具經 iTop REST API 登錄到真正的 ITSM/CMDB 工具,
成為正式組態紀錄與服務台 / 變更單。不合規的東西在 itops 閘門就被擋下,根本不會 sync 進來。

對映(已用真 API 驗證,選 WebServer 串接是為了得到 iTop 原生的影響分析圖 app→ws→host):

  itops CI(cmdb/<env>/)          iTop class       關係(FK)
  ─────────────────────────────  ───────────────  ────────────────────────────
  host(VM)                       VirtualMachine   —
  host(容器宿主 podman)          Server           —
  middleware(OpenLiberty)        WebServer        system_id  → host
  software(已部署 app)           WebApplication   webserver_id → middleware
  software.provenance.request    UserRequest      functionalcis_list → app
  一次部署(過版)                RoutineChange    functionalcis_list → app
                                                  (護欄預先授權 → 例行變更)

冪等:以「name(host/mw/sw 用 ciId)」或「title(工單/變更)」為自然鍵,
存在則 core/update、不存在則 core/create。重跑只會更新,不會重複。

連線(機敏資訊一律走環境變數,不進版控、不上 CLI):
  ITOP_URL   iTop base URL(預設 http://localhost:8000)
  ITOP_USER  REST 帳號(預設 svc_itops_sync;應為 least-privilege 服務帳號,非 admin)
  ITOP_PWD   REST 密碼(必填)

對應治理控制項:
  ISO 20000 組態管理 / 變更管理;ISO 27001 A.8.9 組態管理、A.5.23 雲端服務使用。

用法:
  ITOP_PWD=... scripts/itop_sync.py --env vm-openliberty [--org Demo] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML(pip install pyyaml)")

REST_VERSION = "1.3"


def oql_str(value: str) -> str:
    """把字串安全地包成 OQL 字面值(單引號 + 跳脫)。"""
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


class ItopError(RuntimeError):
    pass


class ItopClient:
    """極簡 iTop REST 客戶端(只用標準庫 urllib,無外部相依)。"""

    def __init__(self, url: str, user: str, pwd: str, dry_run: bool = False):
        self.endpoint = url.rstrip("/") + "/webservices/rest.php?version=" + REST_VERSION
        self.user = user
        self.pwd = pwd
        self.dry_run = dry_run

    def call(self, operation: str, **payload) -> dict:
        payload["operation"] = operation
        data = urllib.parse.urlencode({
            "auth_user": self.user,
            "auth_pwd": self.pwd,
            "json_data": json.dumps(payload),
        }).encode()
        req = urllib.request.Request(self.endpoint, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.URLError as exc:  # noqa: F821 (urllib.error 隨 urllib.request 載入)
            raise ItopError(f"連不上 iTop({self.endpoint}):{exc}") from exc
        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ItopError(f"iTop 回傳非 JSON(可能 PHP error,看容器 error.log):{body[:200]}") from exc
        if result.get("code") != 0:
            raise ItopError(f"iTop REST 錯誤 [{operation}] code={result.get('code')}: {result.get('message')}")
        return result

    def get_id(self, klass: str, oql: str) -> str | None:
        result = self.call("core/get", **{"class": klass}, key=oql, output_fields="id")
        objs = result.get("objects") or {}
        if not objs:
            return None
        return next(iter(objs.values()))["fields"]["id"]

    def upsert(self, klass: str, key_field: str, key_value: str, fields: dict, comment: str) -> str:
        """以 key_field=key_value 為自然鍵 upsert,回傳 iTop 物件 id。"""
        if self.dry_run:
            print(f"   [dry-run] 會 upsert {klass}({key_field}={key_value})")
            return "DRYRUN"
        oql = f"SELECT {klass} WHERE {key_field} = {oql_str(key_value)}"
        existing = self.get_id(klass, oql)
        full = dict(fields)
        full[key_field] = key_value
        verb = "更新" if existing else "建立"
        if existing:
            self.call("core/update", **{"class": klass}, key=int(existing),
                      fields=full, comment=comment, output_fields="id")
            print(f"   ↻ {verb} {klass}:{key_value}(id={existing})")
            return existing
        result = self.call("core/create", **{"class": klass},
                           fields=full, comment=comment, output_fields="id")
        new_id = next(iter(result["objects"].values()))["fields"]["id"]
        print(f"   ＋ {verb} {klass}:{key_value}(id={new_id})")
        return new_id


def load_cis(cmdb_dir: Path, env: str) -> dict[str, dict]:
    """讀 cmdb/<env>/*.yaml,回傳 {ciId: ci_dict}。"""
    env_dir = cmdb_dir / env
    if not env_dir.is_dir():
        sys.exit(f"✗ 找不到 CMDB 環境目錄:{env_dir}")
    cis: dict[str, dict] = {}
    for path in sorted(env_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if doc.get("kind") != "ConfigurationItem":
            continue
        ci_id = (doc.get("metadata") or {}).get("ciId")
        if ci_id:
            cis[ci_id] = doc
    if not cis:
        sys.exit(f"✗ {env_dir} 沒有任何 ConfigurationItem")
    return cis


def rel_target(ci: dict, rel_type: str) -> str | None:
    """從 CI 的 relationships 取某類型關係的 target(ciId)。"""
    for rel in (ci.get("spec", {}).get("relationships") or []):
        if rel.get("type") == rel_type:
            return rel.get("target")
    return None


def short(digest: str) -> str:
    return (digest or "").replace("sha256:", "")[:12]


def main() -> int:
    ap = argparse.ArgumentParser(description="把 itops CMDB-as-code 推進真 iTop")
    ap.add_argument("--env", required=True, help="CMDB 環境(cmdb/<env>/),如 vm-openliberty")
    ap.add_argument("--cmdb-dir", default="cmdb", help="CMDB 根目錄(預設 cmdb)")
    ap.add_argument("--org", default="Demo", help="iTop Organization 名稱(預設 Demo)")
    ap.add_argument("--dry-run", action="store_true", help="只印出將執行的動作,不寫入 iTop")
    args = ap.parse_args()

    url = os.environ.get("ITOP_URL", "http://localhost:8000")
    user = os.environ.get("ITOP_USER", "svc_itops_sync")
    pwd = os.environ.get("ITOP_PWD")
    if not pwd and not args.dry_run:
        sys.exit("✗ 缺少環境變數 ITOP_PWD(REST 密碼)。機敏資訊不走 CLI;請 export 後再跑。")

    client = ItopClient(url, user, pwd or "", dry_run=args.dry_run)
    cmdb_dir = Path(args.cmdb_dir)
    cis = load_cis(cmdb_dir, args.env)

    # 解析 org_id
    if args.dry_run and not pwd:
        org_id = "DRYRUN"
        print(f"[dry-run] 略過連線;假設 Organization '{args.org}'")
    else:
        org_id = client.get_id("Organization", f"SELECT Organization WHERE name = {oql_str(args.org)}")
        if not org_id:
            sys.exit(f"✗ iTop 找不到 Organization '{args.org}'(用 --org 指定既有組織)")

    comment = f"itops_sync:{args.env}"
    id_map: dict[str, str] = {}  # ciId -> iTop id

    by_type = lambda t: [c for c in cis.values() if (c.get("metadata") or {}).get("type") == t]

    # ── Pass 1:host(libvirt VM / 容器宿主)→ Server ──
    #   註:iTop 的 VirtualMachine 強制要 virtualhost_id(必須掛在 Hypervisor/Farm 下),
    #   但 itops 不建模虛擬化平台層,故一律登錄為 Server(對 app 而言就是一台主機),
    #   是 VM 還是容器宿主寫進 description。
    print(f"▶ 同步 host CI → iTop Server({url},org={args.org})")
    for ci in by_type("host"):
        meta, attrs = ci["metadata"], ci["spec"].get("attributes", {})
        ci_id = meta["ciId"]
        fields = {
            "org_id": org_id,
            "status": "production",
            "description": (f"itops CMDB-as-code（{meta.get('app')} / {meta.get('environment')}）\n"
                            f"kind={attrs.get('kind')}; provisionedBy={attrs.get('provisionedBy')}; "
                            f"iac={attrs.get('iac')}"),
        }
        addr = attrs.get("address")
        if addr and addr != "127.0.0.1":
            fields["managementip"] = addr
        id_map[ci_id] = client.upsert("Server", "name", ci_id, fields, comment)

    # ── Pass 2:middleware(OpenLiberty)→ WebServer(system_id → host)──
    print("▶ 同步 middleware CI → iTop WebServer")
    for ci in by_type("middleware"):
        meta, attrs = ci["metadata"], ci["spec"].get("attributes", {})
        ci_id = meta["ciId"]
        host_ci = rel_target(ci, "hosted-on")
        fields = {
            "org_id": org_id,
            "description": (f"itops middleware CI — {attrs.get('product')}（instance={attrs.get('instance')}）\n"
                            f"url={attrs.get('url')}; httpPort={attrs.get('httpPort')}"),
        }
        if host_ci and host_ci in id_map and not args.dry_run:
            fields["system_id"] = id_map[host_ci]
        id_map[ci_id] = client.upsert("WebServer", "name", ci_id, fields, comment)

    # ── Pass 3:software(已部署 app)→ WebApplication(webserver_id → middleware)──
    #            + UserRequest(服務請求)+ RoutineChange(過版變更),皆連回此 app CI ──
    print("▶ 同步 software CI → iTop WebApplication（+ 服務請求/變更單）")
    for ci in by_type("deployed-application"):
        meta = ci["metadata"]
        spec = ci["spec"]
        src = spec.get("source", {})
        runtime = spec.get("runtime", {})
        prov = spec.get("provenance", {})
        ci_id = meta["ciId"]
        app = meta.get("app")
        env = meta.get("environment")
        mw_ci = rel_target(ci, "runs-on")

        desc = (f"itops 已部署應用 — {app} @ {env}\n"
                f"digest={src.get('digest')}\nversion={src.get('version')}; "
                f"gitCommit={src.get('gitCommit')}; gitTag={src.get('gitTag')}\n"
                f"signature={src.get('signature')}; testCount={src.get('testCount')}\n"
                f"gate={prov.get('gate')}; result={prov.get('result')}; deployedAt={prov.get('deployedAt')}\n"
                f"dataClassification={spec.get('dataClassification')}")
        fields = {"org_id": org_id, "description": desc}
        if runtime.get("url"):
            fields["url"] = runtime["url"]
        if mw_ci and mw_ci in id_map and not args.dry_run:
            fields["webserver_id"] = id_map[mw_ci]
        app_id = client.upsert("WebApplication", "name", ci_id, fields, comment)
        id_map[ci_id] = app_id

        ci_link = [] if args.dry_run else [{"functionalci_id": int(app_id)}]

        # 服務請求 → UserRequest(以標題為自然鍵)
        svc_req = prov.get("serviceRequest")
        if svc_req:
            title = f"[itops] 部署 {app} 至 {env}（需求 {svc_req}）"
            ur_fields = {
                "org_id": org_id,
                "description": (f"來源:itops 服務請求 {svc_req}，由 {prov.get('requestedBy') or 'developer'} 發起。\n"
                                f"目標:{app} @ {env}（{runtime.get('url')}）。\n"
                                f"護欄閘門:{prov.get('gate')};結果:{prov.get('result')}。"),
                "functionalcis_list": ci_link,
            }
            client.upsert("UserRequest", "title", title, ur_fields, comment)

        # 過版 → RoutineChange(護欄預先授權的例行變更)
        chg_title = f"[itops] 部署 {app} {short(src.get('digest'))} 至 {env}"
        chg_fields = {
            "org_id": org_id,
            "description": (f"護欄預先授權的例行部署(build-once-promote)。\n"
                            f"digest={src.get('digest')}\n"
                            f"gitCommit={src.get('gitCommit')}; signature={src.get('signature')}\n"
                            f"gate={prov.get('gate')}; result={prov.get('result')}; "
                            f"deployedAt={prov.get('deployedAt')}"),
            "functionalcis_list": ci_link,
        }
        client.upsert("RoutineChange", "title", chg_title, chg_fields, comment)

    n = len(id_map)
    if args.dry_run:
        print(f"\n[dry-run] 完成試跑:會同步 {n} 個 CI(host→middleware→software)+ 服務請求/變更單。")
    else:
        print(f"\n✅ 已同步進 iTop:{n} 個 CI(host→middleware→software)+ 服務請求/變更單。"
              f"\n   去 {url} 看 Configuration Management → 影響分析圖(app → web server → host)。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
