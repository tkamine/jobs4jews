#!/usr/bin/env python3
"""Fetch jobs within N miles of each community and write data/jobs/<slug>.json.

Sources are pluggable. Start with the Adzuna API (legit, free tier, no HTML scraping
of sites whose terms forbid it). Set ADZUNA_APP_ID and ADZUNA_APP_KEY.
Add more sources by writing a function that returns a list of job dicts and
registering it in SOURCES.

Job dict: title, company, location, lat, lon, url, posted, source, summary
"""
import json, math, os, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def haversine(lat1, lon1, lat2, lon2):
    r = 3958.8  # miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def adzuna(community, pages=3):
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        print("  adzuna: no ADZUNA_APP_ID/ADZUNA_APP_KEY set, skipping", file=sys.stderr)
        return None
    out = []
    for page in range(1, pages + 1):
        q = urllib.parse.urlencode({
            "app_id": app_id, "app_key": app_key, "results_per_page": 50,
            "where": community["name"], "distance": int(community["radius_miles"] * 1.609),  # km
            "sort_by": "date",
        })
        url = f"https://api.adzuna.com/v1/api/jobs/us/search/{page}?{q}"
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r)
        for j in data.get("results", []):
            out.append({
                "title": j.get("title", "").strip(),
                "company": (j.get("company") or {}).get("display_name", ""),
                "location": (j.get("location") or {}).get("display_name", ""),
                "lat": j.get("latitude"), "lon": j.get("longitude"),
                "url": j.get("redirect_url", ""),
                "posted": (j.get("created") or "")[:10],
                "summary": (j.get("description") or "")[:240],
                "source": "Adzuna",
            })
    return out


SOURCES = [adzuna]


def main():
    for path in sorted((ROOT / "data" / "communities").glob("*.json")):
        c = json.loads(path.read_text())
        print(f"{c['name']}:")
        jobs, seen = [], set()
        ran = False
        for src in SOURCES:
            results = src(c)
            if results is None:  # source skipped (e.g. no API key)
                continue
            ran = True
            for j in results:
                key = (j["title"].lower(), j["company"].lower(), j["location"].lower())
                if key in seen:
                    continue
                seen.add(key)
                if j["lat"] is not None and j["lon"] is not None:
                    j["miles"] = round(haversine(c["lat"], c["lon"], j["lat"], j["lon"]), 1)
                    if j["miles"] > c["radius_miles"]:
                        continue
                jobs.append(j)
        if not ran:
            print("  no sources ran; keeping existing data/jobs file")
            continue
        jobs.sort(key=lambda j: j.get("posted", ""), reverse=True)
        outdir = ROOT / "data" / "jobs"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / f"{c['slug']}.json").write_text(json.dumps(jobs, indent=2))
        print(f"  wrote {len(jobs)} jobs")


if __name__ == "__main__":
    main()
