#!/usr/bin/env python3
"""治理後台生成器 — 把 itops 的單據生命週期渲染成一頁可瀏覽的治理後台(HTML)。

把分散在 repo 各處的治理記錄聚合成「開需求單 → 變更單 → 換版軌跡 → 執行 → 關單」
的單據視圖,每格標 ITIL 階段 + ISO/ISMS/ITSM 控制項,並含 supply-chain 部署整合那條。
這就是 COMPLIANCE_MAP 第五節說的「翻譯層」——讓稽核/主管看得懂的後台。

資料源(皆為版控內的真實記錄,離線可讀):
  - deployments/<env>/<app>.yaml   變更單(DeploymentRequest:changeType/優先級/來源/分級)
  - cmdb/<env>/<app>.yaml          組態項 CI(執行後登錄:digest/證據/關係)
  - deployments/<env>/last-deploy.json  執行記錄(閘門/完整性/煙霧/結果)
  - integration/inbox/<app>.handoff.yaml  supply-chain 交接 manifest(可選)
  - gh(可選):需求單/PIR issues、變更/換版 merged PR(無 gh 則略過,不影響離線)

用法:scripts/governance_console.py [--output docs/governance-console.html]
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML(pip install pyyaml)")

ENV_ORDER = ["openliberty-sandbox", "test", "uat", "prod"]


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def load_yaml(p: Path) -> dict:
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def gh_json(args: list[str]):
    """呼叫 gh 取 JSON;無 gh / 失敗則回 None(離線優雅降級)。"""
    try:
        out = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout or "null")
    except Exception:
        return None


def badge(text: str, cls: str = "") -> str:
    return f'<span class="badge {cls}">{esc(text)}</span>'


def collect():
    root = Path(".")
    deploys = {}   # (env,app) -> request dict
    for f in sorted(glob.glob("deployments/*/*.yaml")):
        d = load_yaml(Path(f))
        if d.get("kind") == "DeploymentRequest":
            m, s = d.get("metadata", {}), d.get("spec", {})
            deploys[(m.get("environment"), m.get("app"))] = {"req": d, "path": f}
    cis = {}
    for f in sorted(glob.glob("cmdb/*/*.yaml")):
        d = load_yaml(Path(f))
        if d.get("kind") == "ConfigurationItem":
            m = d.get("metadata", {})
            cis[(m.get("environment"), m.get("app"))] = {"ci": d, "path": f}
    records = {}
    for f in sorted(glob.glob("deployments/*/last-deploy.json")):
        try:
            r = json.loads(Path(f).read_text(encoding="utf-8"))
            records[(r.get("environment"), r.get("app"))] = r
        except Exception:
            pass
    handoffs = [load_yaml(Path(f)) for f in sorted(glob.glob("integration/inbox/*.handoff.yaml"))]
    issues = gh_json(["issue", "list", "--state", "all", "--limit", "50",
                      "--json", "number,title,state,labels"]) or []
    prs = gh_json(["pr", "list", "--state", "merged", "--limit", "60",
                   "--json", "number,title,mergedAt"]) or []
    return deploys, cis, records, handoffs, issues, prs


def section(title: str, itil: str, iso: str, body: str) -> str:
    return f"""
    <section>
      <h2>{esc(title)}</h2>
      <div class="tags">{badge(itil, 'itil')} {badge(iso, 'iso')}</div>
      {body}
    </section>"""


def build_html(data) -> str:
    deploys, cis, records, handoffs, issues, prs = data
    apps = sorted({a for (_, a) in deploys})

    # 1. 需求單
    sr_rows = []
    for issue in issues:
        labels = ",".join(l["name"] for l in issue.get("labels", []))
        sr_rows.append(f"<tr><td>#{esc(issue['number'])}</td><td>{esc(issue['title'])}</td>"
                       f"<td>{badge(issue['state'], 'state')}</td><td>{esc(labels)}</td></tr>")
    sr_refs = sorted({(v['req'].get('metadata', {}).get('serviceRequest') or '—')
                      for v in deploys.values()})
    sr_body = (
        "<p>需求由服務目錄的 Issue Form 提出(<code>.github/ISSUE_TEMPLATE/service-request.yml</code>),"
        "轉成變更單時以 <code>serviceRequest</code> 連回。</p>"
        + ("<table><tr><th>單號</th><th>標題</th><th>狀態</th><th>標籤</th></tr>"
           + "".join(sr_rows) + "</table>" if sr_rows else
           "<p class='muted'>(目前無 GitHub issue;下方變更單的 serviceRequest 參照:"
           + ", ".join(esc(x) for x in sr_refs) + ")</p>"))

    # 2. 變更單
    ch_rows = []
    for (env, app), v in sorted(deploys.items()):
        m, s = v['req'].get('metadata', {}), v['req'].get('spec', {})
        src = s.get('source', {})
        ct = m.get('changeType', '—')
        ctcls = {'emergency': 'warn', 'retroactive': 'warn', 'normal': 'info'}.get(ct, 'ok')
        ch_rows.append(
            f"<tr><td>{esc(app)}</td><td>{badge(env,'env')}</td>"
            f"<td>{badge(ct, ctcls)}</td><td>{esc(m.get('priority','—'))}</td>"
            f"<td>{esc(m.get('serviceRequest','—'))}</td>"
            f"<td class='mono'>{esc((src.get('digest') or '')[:19])}…</td>"
            f"<td>{esc(s.get('dataClassification','—'))}</td></tr>")
    ch_body = ("<table><tr><th>App</th><th>環境</th><th>變更型別</th><th>優先級</th>"
               "<th>需求單</th><th>產物 digest</th><th>資料分級</th></tr>"
               + "".join(ch_rows) + "</table>")

    # 3. 換版軌跡(每 app 各環境的 digest)
    pt_body = ""
    for app in apps:
        cells = []
        for env in ENV_ORDER:
            ci = cis.get((env, app))
            req = deploys.get((env, app))
            dig = (ci['ci']['spec']['source'].get('digest') if ci else
                   (req['req']['spec']['source'].get('digest') if req else None))
            deployed = (env, app) in records and records[(env, app)].get('result') == 'success'
            if dig:
                state = '✅ 已部署' if deployed else '📋 已定義'
                cells.append(f"<td class='{'ok' if deployed else ''}'>"
                             f"<div>{badge(env,'env')} {state}</div>"
                             f"<div class='mono small'>{esc(dig[:19])}…</div></td>")
            else:
                cells.append(f"<td class='muted'>{badge(env,'env')}<br>—</td>")
        pt_body += (f"<p class='app'>{esc(app)} <span class='muted small'>"
                    f"(build once → 同一 digest 逐區晉級)</span></p>"
                    f"<table class='trail'><tr>{''.join(cells)}</tr></table>")

    # 4. 執行記錄
    ex_rows = []
    for (env, app), r in sorted(records.items()):
        smoke = r.get('smokeTest', {})
        rescls = 'ok' if r.get('result') == 'success' else 'warn'
        ex_rows.append(
            f"<tr><td>{esc(app)}</td><td>{badge(env,'env')}</td>"
            f"<td>{badge(r.get('gate','—'), 'ok' if r.get('gate')=='passed' else 'warn')}</td>"
            f"<td class='small'>{esc(r.get('integrityCheck','—'))}</td>"
            f"<td>{esc(', '.join(smoke.values()))}</td>"
            f"<td>{badge(r.get('result','—'), rescls)}</td>"
            f"<td class='small'>{esc(r.get('deployedAt','—'))}</td></tr>")
    ex_body = ("<table><tr><th>App</th><th>環境</th><th>部署前驗章閘門</th><th>完整性閉環</th>"
               "<th>煙霧測試</th><th>結果</th><th>時間(UTC)</th></tr>"
               + "".join(ex_rows) + "</table>" if ex_rows else
               "<p class='muted'>(尚無執行記錄)</p>")

    # 5. 關單 / 閉環
    pir = [i for i in issues if any(l['name'] == 'pir' for l in i.get('labels', []))]
    drift = [i for i in issues if any(l['name'] == 'drift' for l in i.get('labels', []))]
    cl_pr = "".join(f"<li>#{esc(p['number'])} {esc(p['title'])} "
                    f"<span class='muted small'>{esc(p.get('mergedAt','')[:10])}</span></li>"
                    for p in prs[:15])
    cl_body = (
        f"<p>變更經 PR 合併留痕(共 {len(prs)} 筆已合併變更),最近:</p>"
        f"<ul>{cl_pr}</ul>" if prs else
        "<p class='muted'>(無 gh,略過 PR 軌跡)</p>")
    cl_body += (f"<p>事後檢討(PIR)單:{len(pir)} 筆;漂移單:{len(drift)} 筆"
                f"{'(均已關閉)' if all(i['state']=='CLOSED' for i in drift) and drift else ''}。"
                "漂移對帳由 <code>reconcile.py</code> 比對 CMDB 期望態 vs 線上實際。</p>")

    # 6. supply-chain 整合
    if handoffs:
        ho_rows = []
        for h in handoffs:
            src = h.get('source', {})
            ho_rows.append(
                f"<tr><td>{esc(h.get('app'))}</td>"
                f"<td class='mono small'>{esc((src.get('digest') or '')[:19])}…</td>"
                f"<td>{esc(src.get('testCount'))} 筆 / {esc((src.get('testReport') or '')[:15])}…</td>"
                f"<td>{esc(h.get('signature'))}</td>"
                f"<td>{esc(h.get('provenance',{}).get('builtBy'))}</td></tr>")
        ho_body = ("<p>supply-chain 左側(build→test→sign)交棒給 itops 右側(驗章→部署→CMDB),"
                   "靠 handoff manifest 串接。鏈:</p>"
                   "<div class='chain'>build → mvn test → cosign 簽 → <b>handoff</b> → "
                   "itops 驗章閘門 → 部署 → CMDB</div>"
                   "<table><tr><th>App</th><th>digest</th><th>測試證據</th>"
                   "<th>簽章</th><th>建置方</th></tr>" + "".join(ho_rows) + "</table>")
    else:
        ho_body = ("<p class='muted'>(尚無交接 manifest;執行 "
                   "<code>integration/supplychain_emit.sh</code> 產生)</p>")

    body = "".join([
        section("① 需求單 Service Request", "ITIL 請求實現", "ISO 20000 服務請求管理", sr_body),
        section("② 變更單 Change Record", "ITIL 變更管理", "ISO 27001 A.8.32 / ISMS 變更控制", ch_body),
        section("③ 換版軌跡 Promotion Trail", "ITIL 發布管理", "ISO 27001 A.8.28 完整性(build once)", pt_body),
        section("④ 執行記錄 Execution", "ITIL 部署管理", "ISO 20000 發布與部署 / A.8.28", ex_body),
        section("⑤ 關單 / 閉環 Closure", "ITIL 變更收尾 + PIR", "ISO 27001 A.5.36 合規審查", cl_body),
        section("⑥ supply-chain 部署整合", "供應鏈交棒", "ISO 27001 A.8.29 安全測試 / A.8.28 供應鏈", ho_body),
    ])

    n_change = len(deploys)
    n_exec = sum(1 for r in records.values() if r.get('result') == 'success')
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>itops 治理後台 — 單據生命週期</title>
<style>
:root {{ --bg:#0f1419; --card:#1a2230; --ink:#e6edf3; --muted:#8b98a5; --line:#2d3748;
  --ok:#2ea043; --warn:#d29922; --info:#388bfd; --accent:#a371f7; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.6
  -apple-system,"Noto Sans CJK TC",sans-serif; padding:24px; }}
header h1 {{ margin:0 0 4px; font-size:24px; }}
header p {{ color:var(--muted); margin:0 0 8px; }}
.stat {{ display:inline-block; background:var(--card); border:1px solid var(--line);
  border-radius:8px; padding:8px 14px; margin:4px 8px 16px 0; }}
.stat b {{ font-size:20px; color:var(--accent); }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:16px 20px; margin:16px 0; }}
h2 {{ margin:0 0 6px; font-size:18px; }}
.tags {{ margin-bottom:12px; }}
.badge {{ display:inline-block; font-size:12px; padding:2px 8px; border-radius:10px;
  background:#30363d; color:var(--ink); margin-right:4px; }}
.badge.itil {{ background:#1f3a5f; }} .badge.iso {{ background:#3d2f5f; }}
.badge.env {{ background:#22343f; }} .badge.ok {{ background:var(--ok); }}
.badge.warn {{ background:var(--warn); color:#1a1a1a; }} .badge.info {{ background:var(--info); }}
.badge.state {{ background:#444c56; }}
table {{ width:100%; border-collapse:collapse; margin:8px 0; }}
th,td {{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); font-size:14px; }}
th {{ color:var(--muted); font-weight:600; }}
td.ok {{ background:rgba(46,160,67,.08); }}
.trail td {{ border:1px solid var(--line); vertical-align:top; width:25%; }}
.mono {{ font-family:ui-monospace,monospace; }} .small {{ font-size:12px; }}
.muted {{ color:var(--muted); }} .app {{ margin:14px 0 4px; font-weight:600; }}
.chain {{ background:#0d1117; border:1px solid var(--line); border-radius:8px;
  padding:10px 14px; font-family:ui-monospace,monospace; font-size:13px; margin:8px 0; }}
code {{ background:#0d1117; padding:1px 5px; border-radius:4px; font-size:13px; }}
footer {{ color:var(--muted); font-size:12px; margin-top:24px; }}
</style></head><body>
<header>
  <h1>🏛️ itops 治理後台 — 單據生命週期</h1>
  <p>從服務請求到正式部署的端到端治理記錄,對映 ITIL / ISO 27001 / ISO 20000 / ISMS。
     資料即版控真相(deployments / cmdb / last-deploy / 整合 manifest)。</p>
  <div class="stat"><b>{n_change}</b> 變更單</div>
  <div class="stat"><b>{n_exec}</b> 成功部署</div>
  <div class="stat"><b>{len(prs)}</b> 已合併變更</div>
  <div class="stat"><b>{len(cis)}</b> 組態項(CI)</div>
</header>
{body}
<footer>由 scripts/governance_console.py 從版控記錄生成 · itops_and_caas ·
  這是 COMPLIANCE_MAP 第五節「翻譯層」的具象化。</footer>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="治理後台生成器")
    ap.add_argument("--output", default="docs/governance-console.html")
    args = ap.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(collect()), encoding="utf-8")
    print(f"✅ 治理後台已生成:{out}")
    print(f"   開啟:firefox {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
