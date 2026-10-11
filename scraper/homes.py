#!/usr/bin/env python3
"""Find homes for sale within N miles of any synagogue in each community.

Steps:
 1. Geocode synagogue/school addresses with the free US Census geocoder (cached in
    data/geocode_cache.json, no API key). Entries with vague addresses are skipped.
 2. For each geocoded synagogue, query a licensed listings API for active for-sale
    listings within home_radius_miles (default 2).
 3. Merge, dedupe, record the nearest synagogue and distance, write data/homes/<slug>.json.

Why not Zillow: Zillow has no public listings API for this use and its terms prohibit
scraping, so we use RentCast (set RENTCAST_API_KEY; free tier available). Swap in another
provider by editing fetch_listings().
"""
import json, math, os, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "geocode_cache.json"


def haversine(lat1, lon1, lat2, lon2):
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def geocode(address, cache):
    if address in cache:
        return cache[address]
    q = urllib.parse.urlencode({"address": address, "benchmark": "Public_AR_Current", "format": "json"})
    url = f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?{q}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            m = json.load(r)["result"]["addressMatches"]
        cache[address] = {"lat": m[0]["coordinates"]["y"], "lon": m[0]["coordinates"]["x"]} if m else None
    except Exception as ex:
        print(f"  geocode failed for {address!r}: {ex}", file=sys.stderr)
        return None
    return cache[address]


def fetch_listings(lat, lon, radius):
    key = (os.environ.get("RENTCAST_API_KEY") or "").strip()
    if not key:
        print("  no RENTCAST_API_KEY set, skipping", file=sys.stderr)
        return None
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "radius": radius,
                                "status": "Active", "limit": 500})
    req = urllib.request.Request(f"https://api.rentcast.io/v1/listings/sale?{q}",
                                 headers={"X-Api-Key": key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as ex:
        body = ex.read().decode("utf-8", "replace")[:300]
        hint = " (key rejected: check the RENTCAST_API_KEY secret)" if ex.code in (401, 403) else ""
        print(f"  RentCast error {ex.code}{hint}: {body}", file=sys.stderr)
        return None  # treated as "skipped": existing data is kept
    except urllib.error.URLError as ex:
        print(f"  RentCast network error: {ex}", file=sys.stderr)
        return None


def main():
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    for path in sorted((ROOT / "data" / "communities").glob("*.json")):
        c = json.loads(path.read_text())
        radius = c.get("home_radius_miles", 2)
        shuls = []
        for s in c["synagogues"]:
            pt = geocode(s["address"], cache)
            if pt:
                s.update(pt)
                shuls.append(s)
            else:
                print(f"  skipping {s['name']}: address not geocodable ({s['address']!r})")
        if not shuls:
            print(f"{c['name']}: no geocodable synagogues, keeping existing data/homes file")
            continue
        homes = {}
        skipped = False
        for s in shuls:
            listings = fetch_listings(s["lat"], s["lon"], radius)
            if listings is None:
                skipped = True
                break
            for h in listings:
                if h.get("latitude") is None:
                    continue
                best = min(shuls, key=lambda x: haversine(h["latitude"], h["longitude"], x["lat"], x["lon"]))
                d = haversine(h["latitude"], h["longitude"], best["lat"], best["lon"])
                if d > radius:
                    continue
                homes[h.get("id") or h.get("formattedAddress")] = {
                    "address": h.get("formattedAddress", ""), "price": h.get("price"),
                    "beds": h.get("bedrooms"), "baths": h.get("bathrooms"), "sqft": h.get("squareFootage"),
                    "type": h.get("propertyType", ""), "listed": (h.get("listedDate") or "")[:10],
                    "nearest_synagogue": best["name"], "miles": round(d, 2),
                    "url": h.get("listingUrl", ""), "source": "RentCast",
                }
        if skipped:
            print(f"{c['name']}: no key, keeping existing data/homes file")
            continue
        out = sorted(homes.values(), key=lambda h: h["miles"])
        (ROOT / "data" / "homes").mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / "homes" / f"{c['slug']}.json").write_text(json.dumps(out, indent=2))
        print(f"{c['name']}: {len(out)} homes within {radius} mi of {len(shuls)} synagogues")
    CACHE.write_text(json.dumps(cache, indent=2))


if __name__ == "__main__":
    main()
