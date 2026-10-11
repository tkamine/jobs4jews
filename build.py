#!/usr/bin/env python3
"""Build a static site: dist/index.html plus dist/<slug>.html per community."""
import html, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
e = html.escape

CSS = """
:root{--bg:#faf8f3;--ink:#1d2433;--mut:#5d6679;--card:#fff;--line:#e3dfd3;--acc:#1f4e8c;--acc2:#c9a227}
@media(prefers-color-scheme:dark){:root{--bg:#14171f;--ink:#eceff5;--mut:#9aa3b5;--card:#1c2030;--line:#2c3247;--acc:#7fb0ee;--acc2:#e0bf4f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 Georgia,'Times New Roman',serif}
header{padding:28px 16px 20px;border-bottom:3px solid var(--acc2);text-align:center}
h1{margin:0;font-size:1.9rem;letter-spacing:.3px}header p{margin:6px auto 0;max-width:640px;color:var(--mut)}
main{max-width:1100px;margin:0 auto;padding:20px 16px;display:grid;gap:20px;grid-template-columns:1fr}
@media(min-width:860px){main{grid-template-columns:340px 1fr}}
section.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
h2{font-size:1.15rem;margin:0 0 8px;color:var(--acc)}h3{font-size:1rem;margin:14px 0 4px}
.sub{color:var(--mut);font-size:.9rem}ul{padding-left:18px;margin:6px 0}a{color:var(--acc)}
.job{border-top:1px solid var(--line);padding:12px 0}.job:first-of-type{border-top:0}
.job b{font-size:1.05rem}.tag{display:inline-block;font-size:.75rem;border:1px solid var(--line);border-radius:99px;padding:0 8px;margin-left:6px;color:var(--mut)}
input{width:100%;padding:9px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit;margin-bottom:10px}
.note{font-size:.85rem;color:var(--mut);border-left:3px solid var(--acc2);padding-left:10px;margin-top:12px}
.stats{max-width:1100px;margin:16px auto 0;padding:0 16px;display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;text-align:center}
.stat .n{font-size:1.7rem;color:var(--acc);font-weight:bold;line-height:1.2}
footer{text-align:center;color:var(--mut);font-size:.85rem;padding:20px}
"""

JS = """
const q=document.getElementById('q'),jobs=[...document.querySelectorAll('.job')],cnt=document.getElementById('cnt');
q.addEventListener('input',()=>{const t=q.value.toLowerCase();let n=0;
jobs.forEach(j=>{const ok=j.textContent.toLowerCase().includes(t);j.style.display=ok?'':'none';if(ok)n++});cnt.textContent=n});
"""


def link(name, url):
    return f'<a href="{e(url)}" rel="noopener">{e(name)}</a>' if url else e(name)


def real_count(items):
    n = sum(1 for i in items if i.get("source") != "sample")
    return n if n or not items else "sample"


def stat(num, label, note=""):
    return (f"<div class='stat'><div class='n'>{e(str(num))}</div><div>{e(label)}</div>"
            f"<div class='sub'>{e(note)}</div></div>")


def homes_html(c, homes):
    r = c.get("home_radius_miles", 2)
    rows = "".join(
        f"<div class='job'><b>{e(h['address'])}</b><span class='tag'>{e(str(h['miles']))} mi from {e(h['nearest_synagogue'])}</span><br>"
        f"${h['price']:,} · {e(str(h.get('beds','?')))} bd · {e(str(h.get('baths','?')))} ba"
        f"{' · ' + format(h['sqft'], ',') + ' sqft' if h.get('sqft') else ''}"
        f" <span class='sub'>· {e(h.get('type',''))} · listed {e(h.get('listed',''))} · via {e(h['source'])}</span>"
        f"{' · ' + link('View listing', h['url']) if h.get('url') else ''}</div>"
        for h in homes)
    return (f"<section class='card' style='grid-column:1/-1'><h2>Homes for sale within {r} miles of a synagogue ({len(homes)})</h2>"
            f"{rows or '<p>No listings yet.</p>'}</section>")


def page(c, jobs, homes):
    pop = c.get("jewish_population")
    stats = "".join([
        stat(len(c["schools"]), "Jewish day schools"),
        stat(len(c["synagogues"]), "Synagogues", "list may be incomplete"),
        stat(len(c["organizations"]), "Community organizations"),
        stat(f"~{pop['value']:,}", "Jewish residents", pop["source"]) if pop else "",
        stat(real_count(jobs), f"Jobs within {c['radius_miles']} mi"),
        stat(real_count(homes), f"Homes near a synagogue", f"within {c.get('home_radius_miles', 2)} mi"),
    ])
    schools = "".join(
        f"<li>{link(s['name'], s.get('website',''))} <span class='sub'>({e(s['grades'])})</span><br>"
        f"<span class='sub'>{e(s['address'])}. {e(s['note'])}</span></li>" for s in c["schools"])
    shuls = "".join(
        f"<li>{link(s['name'], s.get('website',''))} <span class='sub'>· {e(s['movement'])} · {e(s['address'])}</span></li>"
        for s in c["synagogues"])
    orgs = "".join(f"<li>{link(o['name'], o.get('website',''))}</li>" for o in c["organizations"])
    jhtml = "".join(
        f"<div class='job'><b>{link(j['title'], j['url'] if j['url'] != '#' else '')}</b>"
        f"<span class='tag'>{e(str(j.get('miles','?')))} mi</span><br>"
        f"{e(j['company'])} · {e(j['location'])} <span class='sub'>· posted {e(j['posted'])} · via {e(j['source'])}</span>"
        f"<div class='sub'>{e(j.get('summary',''))}</div></div>" for j in jobs)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jobs for Jews · {e(c['name'])}</title><style>{CSS}</style></head><body>
<header><p style="margin:0 0 6px"><a href="index.html">&larr; All communities</a></p><h1>Jobs for Jews · {e(c['name'])}</h1><p>{e(c['tagline'])}</p></header>
<div class="stats">{stats}</div>
<main>
<aside><section class="card"><h2>About the community</h2><p>{e(c['about'])}</p>
<h3>Jewish day schools</h3><ul>{schools}</ul>
<h3>Synagogues</h3><ul>{shuls}</ul>
<h3>Community organizations</h3><ul>{orgs}</ul>
<p class="note">{e(c.get('todo_verify',''))}</p></section></aside>
<section class="card"><h2>Jobs within {c['radius_miles']} miles (<span id="cnt">{len(jobs)}</span>)</h2>
<input id="q" placeholder="Filter by title, employer or town" aria-label="Filter jobs">
{jhtml or "<p>No jobs yet.</p>"}</section>
{homes_html(c, homes)}</main>
<footer>Job listings are gathered automatically from third-party sources and may be out of date.</footer>
<script>{JS}</script></body></html>"""


HOME_CSS = """
.map{max-width:1100px;margin:16px auto;padding:0 8px}
.map svg{width:100%;height:auto;display:block}
.land{fill:var(--land);stroke:none}.bord{fill:none;stroke:var(--bg);stroke-width:1}
.star{fill:#1f6fd1;stroke:#fff;stroke-width:1.5;stroke-linejoin:round;paint-order:stroke}
.pt .lbl{font:15px Georgia,serif;fill:var(--ink);paint-order:stroke;stroke:var(--bg);stroke-width:4px}
.pt:hover .star,.pt:focus .star{fill:#0b4ea8}.pt{cursor:pointer;outline:none}
.pt:focus .hit{stroke:var(--acc);stroke-width:2}
.list{max-width:1100px;margin:0 auto;padding:0 16px 8px}
.list a{display:inline-block;margin:4px 14px 4px 0}
"""
HOME_LAND = "--land:#d9d4c3;"
HOME_LAND_DARK = "--land:#2a3045;"


def star_defs(r=20):
    """Hexagram as ONE 12-point outline so the outline doesn't cut across the fill."""
    import math
    pts = []
    for k in range(6):
        for rad, off in ((r, -90), (r / math.sqrt(3), -60)):
            ang = math.radians(off + 60 * k)
            pts.append(f"{rad * math.cos(ang):.1f},{rad * math.sin(ang):.1f}")
    return f'<polygon id="star" class="star" points="{" ".join(pts)}"/>'


def home_page(communities, m):
    pts = ""
    for p in m["points"]:
        short = p["name"].split(",")[0]
        label = next((c.get("map_label") for c in communities if c["slug"] == p["slug"]), None) or short
        pts += (f'<a class="pt" href="{e(p["slug"])}.html" aria-label="{e(p["name"])} community page">'
                f'<title>{e(p["name"])}</title>'
                f'<circle class="hit" cx="{p["x"]}" cy="{p["y"]}" r="26" fill="transparent"/>'
                f'<use href="#star" x="{p["x"]}" y="{p["y"]}"/>'
                f'<text class="lbl" x="{p["x"] - 24}" y="{p["y"] + 5}" text-anchor="end">{e(label)}</text></a>')
    lst = "".join(f'<a href="{e(c["slug"])}.html">{e(c["name"])}</a>' for c in communities)
    n = len(communities)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jobs for Jews</title>
<style>{CSS}:root{{{HOME_LAND}}}@media(prefers-color-scheme:dark){{:root{{{HOME_LAND_DARK}}}}}{HOME_CSS}</style></head><body>
<header><h1>Jobs for Jews</h1>
<p>Jobs, homes and community information for small Jewish communities with day schools. Click a Star of David to explore a community.</p></header>
<div class="map"><svg viewBox="0 0 {m['width']} {m['height']}" role="img" aria-label="Map of the United States with a Star of David on each available community">
<defs>{star_defs()}</defs>
<path class="land" d="{m['states']}"/><path class="bord" d="{m['borders']}"/>{pts}</svg></div>
<div class="list"><b>{n} communit{'y' if n == 1 else 'ies'}:</b> {lst}</div>
<footer>More communities coming soon.</footer></body></html>"""


def main():
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    subprocess.run(["node", str(ROOT / "scripts" / "make_map.mjs")], check=True, cwd=ROOT)
    m = json.loads((ROOT / "data" / "map.json").read_text())
    communities = []
    for p in sorted((ROOT / "data" / "communities").glob("*.json")):
        c = json.loads(p.read_text())
        communities.append(c)
        jp = ROOT / "data" / "jobs" / f"{c['slug']}.json"
        jobs = json.loads(jp.read_text()) if jp.exists() else []
        hp = ROOT / "data" / "homes" / f"{c['slug']}.json"
        homes = json.loads(hp.read_text()) if hp.exists() else []
        (dist / f"{c['slug']}.html").write_text(page(c, jobs, homes))
    (dist / "index.html").write_text(home_page(communities, m))
    print("built", sorted(f.name for f in dist.iterdir()))


if __name__ == "__main__":
    main()
