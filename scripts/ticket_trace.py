#!/usr/bin/env python3
"""單據追溯視圖 — 把「一張服務請求」從開單到關單的證據鏈渲染成一頁 HTML。

治理後台(governance_console)是「全部單據的鳥瞰」;這支是「單一單據的鑽取(drill-down)」:
跟著 serviceRequest 號,把它的變更單 / 供應鏈交接 / 簽章 / 驗章閘門 / 執行 / CMDB / 換版 / 關單
串成一條垂直證據鏈,每一格標來源檔 + 串接鍵(serviceRequest / digest),這就是稽核的「可追溯」。

用法:scripts/ticket_trace.py --issue 34 [--app supply-chain-backend] [--output docs/ticket-34.html]
gh 可選(取 issue 開/關時間與標籤;無 gh 則略過)。
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
    sys.exit("✗ 需要 PyYAML")

ENV_ORDER = ["openliberty-sandbox", "test", "uat", "prod"]


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def load(p):
    try:
        return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def gh_json(args):
    try:
        o = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
        return json.loads(o.stdout) if o.returncode == 0 and o.stdout.strip() else None
    except Exception:
        return None


def collect(issue_no, app_hint):
    ref = f"#{issue_no}"
    # 變更單:serviceRequest == #N
    changes = []
    for f in sorted(glob.glob("deployments/*/*.yaml")):
        d = load(f)
        if d.get("kind") == "DeploymentRequest" and str(
                (d.get("metadata", {}) or {}).get("serviceRequest", "")) == ref:
            changes.append((f, d))
    app = app_hint or (changes[0][1]["metadata"]["app"] if changes else None)
    # CMDB CI:provenance.serviceRequest == #N
    cis = {}
    for f in sorted(glob.glob("cmdb/*/*.yaml")):
        d = load(f)
        prov = (d.get("spec", {}) or {}).get("provenance", {}) or {}
        if d.get("kind") == "ConfigurationItem" and str(prov.get("serviceRequest", "")) == ref:
            cis[d["metadata"]["environment"]] = (f, d)
    # 執行證據
    records = {}
    for f in sorted(glob.glob("deployments/*/last-deploy.json")):
        try:
            r = json.loads(Path(f).read_text(encoding="utf-8"))
            records[r.get("environment")] = (f, r)
        except Exception:
            pass
    # 交接 manifest
    handoff = None
    for f in glob.glob("integration/inbox/*.handoff.yaml"):
        d = load(f)
        if not app or d.get("app") == app:
            handoff = (f, d)
    # issue(gh 可選)
    issue = gh_json(["issue", "view", str(issue_no), "--json",
                     "number,title,state,labels,createdAt,closedAt"])
    return ref, app, changes, cis, records, handoff, issue


def card(stage, title, src, key, rows_html):
    keyhtml = f'<span class="key">串接鍵: {esc(key)}</span>' if key else ""
    srchtml = f'<span class="src">{esc(src)}</span>' if src else ""
    return f"""
    <div class="card">
      <div class="stage">{esc(stage)}</div>
      <div class="body">
        <div class="ttl">{title} {keyhtml}</div>
        {rows_html}
        {srchtml}
      </div>
    </div>
    <div class="arrow">▼</div>"""


def kv(label, val, cls=""):
    return f'<div class="kv"><span class="k">{esc(label)}</span><span class="v {cls}">{esc(val)}</span></div>'


def build(data):
    ref, app, changes, cis, records, handoff, issue = data
    digest = ""
    if changes:
        digest = (changes[0][1].get("spec", {}).get("source", {}) or {}).get("digest", "")
    cards = []

    # ① 需求單
    if issue:
        labels = ", ".join(l["name"] for l in issue.get("labels", []))
        rows = (kv("狀態", issue["state"], "ok" if issue["state"] == "CLOSED" else "")
                + kv("標籤", labels) + kv("開單", issue.get("createdAt", "—"))
                + kv("關單", issue.get("closedAt", "—") or "(未關)"))
        cards.append(card("①", f'需求單 Issue {ref}<br><span class="sub">{esc(issue["title"])}</span>',
                          f"GitHub Issue {ref}", None, rows))
    else:
        cards.append(card("①", f"需求單 {ref}", "GitHub Issue(無 gh,略)", None,
                          kv("提出方式", "service-request Issue Form")))

    # ② 變更單(取 sandbox / 第一個)
    if changes:
        f, d = changes[0]
        m, s = d["metadata"], d.get("spec", {})
        src = s.get("source", {})
        rows = (kv("app / 環境", f'{m.get("app")} / {m.get("environment")}')
                + kv("變更型別", m.get("changeType"), "ok")
                + kv("優先級", m.get("priority")) + kv("資料分級", s.get("dataClassification"))
                + kv("產物 digest", src.get("digest"), "mono")
                + kv("測試證據", f'{src.get("testCount")} 筆 / {str(src.get("testReport",""))[:18]}…'))
        cards.append(card("②", "變更單 DeploymentRequest", f, f"serviceRequest = {ref}", rows))

    # ⑨ 供應鏈交接
    if handoff:
        f, d = handoff
        src = d.get("source", {})
        rows = (kv("建置方", d.get("provenance", {}).get("builtBy"))
                + kv("digest", src.get("digest"), "mono")
                + kv("測試", f'{src.get("testCount")} 筆 / {str(src.get("testReport",""))[:18]}…')
                + kv("簽章檔", d.get("signature")))
        cards.append(card("⑨", "供應鏈交接 handoff(build→test→sign)", f,
                          f"digest = {str(digest)[:18]}…", rows))

    # ③ 簽章
    sigp = f"deployments/{changes[0][1]['metadata']['environment']}/sig/{app}.sig" if changes else None
    if sigp and Path(sigp).is_file():
        sig = Path(sigp).read_text(encoding="utf-8").strip()
        cards.append(card("③", "簽章物證 cosign", sigp, f"簽 digest = {str(digest)[:18]}…",
                          kv("signature", sig[:46] + "…", "mono")))

    # ④ 部署前驗章閘門 + 執行
    env0 = changes[0][1]["metadata"]["environment"] if changes else None
    if env0 in records:
        f, r = records[env0]
        rows = (kv("部署前驗章閘門", r.get("gate"), "ok")
                + kv("完整性閉環", r.get("integrityCheck"))
                + kv("結果", r.get("result"), "ok" if r.get("result") == "success" else "warn")
                + kv("時間", r.get("deployedAt")))
        cards.append(card("④", "部署前驗章閘門 + 執行", f, None, rows))

    # ⑤ CMDB CI
    if env0 in cis:
        f, d = cis[env0]
        prov = d["spec"]["provenance"]
        rels = ", ".join(r["type"] for r in d["spec"].get("relationships", []))
        rows = (kv("requestedBy", prov.get("requestedBy"))
                + kv("gate / result", f'{prov.get("gate")} / {prov.get("result")}', "ok")
                + kv("關係", rels))
        cards.append(card("⑤", "組態項 CI(CMDB-as-code)", f, f"provenance.serviceRequest = {ref}", rows))

    # ⑥ 換版軌跡
    trail = []
    for e in ENV_ORDER:
        dg = ""
        if e in cis:
            dg = (cis[e][1]["spec"]["source"].get("digest") or "")
        elif e in records:
            dg = (records[e][1].get("digest") or "")
        deployed = e in records and records[e][1].get("result") == "success"
        mark = "✅" if deployed else "○"
        trail.append(f'<span class="env">{mark} {esc(e)} <span class="mono small">'
                     f'{esc(dg[:15])}…</span></span>')
    cards.append(card("⑥", "換版軌跡(build once, promote same digest)", "cmdb/*/ + deployments/*/",
                      f"全程同一 digest = {str(digest)[:18]}…",
                      '<div class="trail">' + " → ".join(trail) + "</div>"))

    # ⑦ 關單
    if issue and issue["state"] == "CLOSED":
        cards.append(card("⑦", "關單 Closure", f"GitHub Issue {ref} (closed)", None,
                          kv("狀態", "CLOSED — ITIL 請求閉環完成", "ok")
                          + kv("關單時間", issue.get("closedAt", "—"))))

    body = "".join(cards)
    if body.endswith('<div class="arrow">▼</div>'):
        body = body[:-len('<div class="arrow">▼</div>')]

    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>單據追溯 {esc(ref)} — {esc(app)}</title>
<style>
body {{ margin:0; background:#0f1419; color:#e6edf3; font:15px/1.6 -apple-system,"Noto Sans CJK TC",sans-serif; padding:24px; }}
h1 {{ font-size:22px; margin:0 0 4px; }}
.lead {{ color:#8b98a5; margin:0 0 20px; }}
.card {{ display:flex; background:#1a2230; border:1px solid #2d3748; border-radius:10px; overflow:hidden; max-width:760px; }}
.stage {{ background:#1f3a5f; min-width:54px; display:flex; align-items:center; justify-content:center; font-size:22px; font-weight:700; }}
.body {{ padding:12px 16px; flex:1; }}
.ttl {{ font-weight:600; margin-bottom:8px; }}
.sub {{ color:#8b98a5; font-weight:400; font-size:13px; }}
.kv {{ display:flex; gap:8px; font-size:13.5px; padding:1px 0; }}
.kv .k {{ color:#8b98a5; min-width:120px; }}
.kv .v.ok {{ color:#3fb950; }} .kv .v.warn {{ color:#d29922; }}
.mono {{ font-family:ui-monospace,monospace; }} .small {{ font-size:12px; }}
.key {{ background:#3d2f5f; color:#d2b8ff; font-size:11px; padding:1px 8px; border-radius:10px; margin-left:6px; }}
.src {{ display:block; margin-top:8px; color:#6b7681; font-size:11.5px; font-family:ui-monospace,monospace; }}
.arrow {{ color:#388bfd; font-size:18px; margin:2px 0 2px 24px; }}
.trail {{ display:flex; flex-wrap:wrap; gap:4px; }} .env {{ background:#22343f; padding:2px 8px; border-radius:8px; font-size:12.5px; }}
footer {{ color:#6b7681; font-size:12px; margin-top:20px; max-width:760px; }}
</style></head><body>
<p><a href="governance-console.html" style="color:#a371f7;text-decoration:none;font-size:13px;">← 回治理後台</a></p>
<h1>🔎 單據追溯 {esc(ref)} — {esc(app)}</h1>
<p class="lead">跟著 serviceRequest 號,把一張服務請求從開單到關單的證據鏈鑽取出來。
每格的「串接鍵」(紫)就是稽核追溯靠的線:serviceRequest 串前段、digest 串後段。</p>
{body}
<footer>由 scripts/ticket_trace.py 從版控記錄生成 · 全部記錄皆版控檔,可開原檔對照 ·
這是 governance-console(鳥瞰)的單據鑽取(drill-down)版。</footer>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True)
    ap.add_argument("--app", default=None)
    ap.add_argument("--output", default=None)
    a = ap.parse_args()
    out = Path(a.output or f"docs/ticket-{a.issue}.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(collect(a.issue, a.app)), encoding="utf-8")
    print(f"✅ 單據追溯視圖:{out}")
    print(f"   開啟:firefox {out.resolve()}")


if __name__ == "__main__":
    main()
