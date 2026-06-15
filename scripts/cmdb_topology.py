#!/usr/bin/env python3
"""CMDB 拓樸視圖 — 把多層 CI(host → middleware → software)的關係圖渲染成一頁 HTML。

真 CMDB 的核心是「CI + 關係拓樸」(硬體 → 中介軟體 → 軟體)。這支把 cmdb/ 裡的
三層 CI 依關係畫成每個環境的拓樸鏈,讓「組態關係圖」看得見。

用法:scripts/cmdb_topology.py [--cmdb-dir cmdb] [--output docs/cmdb-topology.html]
"""
from __future__ import annotations

import argparse
import glob
import html
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML")


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def load(p):
    try:
        return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def attr_rows(d: dict) -> str:
    out = []
    for k, v in (d or {}).items():
        out.append(f'<div class="kv"><span class="k">{esc(k)}</span>'
                   f'<span class="v">{esc(v)}</span></div>')
    return "".join(out)


def node(ci: dict, cls: str, layer: str) -> str:
    m, s = ci.get("metadata", {}), ci.get("spec", {})
    attrs = s.get("attributes") or {}
    # software 層用 source/runtime 當屬性
    if not attrs and m.get("type") == "deployed-application":
        src = s.get("source", {}) or {}
        rt = s.get("runtime", {}) or {}
        attrs = {"digest": str(src.get("digest", ""))[:19] + "…", "version": src.get("version"),
                 "url": rt.get("url"), "testCount": src.get("testCount")}
    rels = " · ".join(f'{r.get("type")}→{r.get("target")}'.replace("ci-", "")
                      for r in (s.get("relationships") or []))
    return f"""
    <div class="node {cls}">
      <div class="layer">{esc(layer)}</div>
      <div class="cid">{esc(m.get("ciId"))}</div>
      {attr_rows(attrs)}
      <div class="rels">{esc(rels)}</div>
    </div>"""


def build(cmdb_dir: str) -> str:
    envs: dict[str, dict[str, dict]] = {}
    for f in sorted(glob.glob(f"{cmdb_dir}/*/*.yaml")):
        ci = load(f)
        if ci.get("kind") != "ConfigurationItem":
            continue
        m = ci.get("metadata", {})
        envs.setdefault(m.get("environment"), {})[m.get("type")] = ci

    blocks = []
    for env, layers in envs.items():
        host = layers.get("host")
        mw = layers.get("middleware")
        sw = layers.get("deployed-application")
        chain = []
        if host:
            chain.append(node(host, "host", "① host(硬體)"))
        if mw:
            chain.append('<div class="link">⇅ hosts</div>')
            chain.append(node(mw, "mw", "② middleware(中介軟體)"))
        if sw:
            chain.append('<div class="link">⇅ runs-on</div>')
            chain.append(node(sw, "sw", "③ software(軟體)"))
        blocks.append(f'<section><h2>{esc(env)}</h2><div class="chain">{"".join(chain)}</div></section>')

    n_ci = sum(len(v) for v in envs.values())
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CMDB 拓樸 — host → middleware → software</title>
<style>
body {{ margin:0; background:#0f1419; color:#e6edf3; font:14px/1.55 -apple-system,"Noto Sans CJK TC",sans-serif; padding:24px; }}
h1 {{ font-size:22px; margin:0 0 4px; }}
.lead {{ color:#8b98a5; margin:0 0 18px; max-width:780px; }}
section {{ background:#1a2230; border:1px solid #2d3748; border-radius:10px; padding:14px 18px; margin:14px 0; }}
h2 {{ font-size:16px; margin:0 0 10px; color:#a371f7; }}
.chain {{ display:flex; flex-direction:column; gap:0; max-width:620px; }}
.node {{ border:1px solid #2d3748; border-radius:8px; padding:10px 14px; }}
.node.host {{ background:#102a26; border-color:#1f5f50; }}
.node.mw {{ background:#22343f; border-color:#2f5f6f; }}
.node.sw {{ background:#1f2a3f; border-color:#388bfd; }}
.layer {{ font-size:11px; color:#8b98a5; }}
.cid {{ font-family:ui-monospace,monospace; font-weight:600; margin:2px 0 6px; }}
.kv {{ display:flex; gap:8px; font-size:12.5px; }}
.kv .k {{ color:#8b98a5; min-width:96px; }} .kv .v {{ font-family:ui-monospace,monospace; }}
.rels {{ margin-top:6px; font-size:11px; color:#6b7681; }}
.link {{ text-align:center; color:#388bfd; font-size:13px; padding:3px 0; }}
footer {{ color:#6b7681; font-size:12px; margin-top:18px; }}
</style></head><body>
<h1>🗺️ CMDB 拓樸 — host → middleware → software</h1>
<p class="lead">真 CMDB 的核心:Configuration Item(CI)+ 關係拓樸。這裡每個環境畫成三層鏈——
host(VM/容器宿主)→ middleware(OpenLiberty)→ software(app),以 ciId 互連。
共 {n_ci} 個 CI、{len(envs)} 個環境。</p>
{"".join(blocks)}
<footer>由 scripts/cmdb_topology.py 從 cmdb/ 的多層 CI 生成 · 對應 ISO 20000 組態管理 / ISO 27001 A.8.9。</footer>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmdb-dir", default="cmdb")
    ap.add_argument("--output", default="docs/cmdb-topology.html")
    a = ap.parse_args()
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(a.cmdb_dir), encoding="utf-8")
    print(f"✅ CMDB 拓樸視圖:{out}")
    print(f"   開啟:firefox {out.resolve()}")


if __name__ == "__main__":
    main()
