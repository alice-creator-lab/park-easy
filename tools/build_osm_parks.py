#!/usr/bin/env python3
"""Build data/parks_osm.json — car parks that exist in OpenStreetMap but are not
in the government vacancy feed.

The vacancy API only carries car parks whose operators volunteer numbers, so
private malls (e.g. 荃新天地) never appear. OSM has many of them with a name,
sometimes website/opening_hours/fee/capacity — no live vacancy, but at least
they can be found, tapped and navigated to.

Usage: python3 tools/build_osm_parks.py
Data © OpenStreetMap contributors, ODbL 1.0.
"""
import json
import os
import urllib.parse
import urllib.request

ENDPOINT = "https://overpass-api.de/api/interpreter"
# HK bounding box (slightly generous: islands + New Territories border)
BBOX = "22.15,113.82,22.60,114.50"
QUERY = """
[out:json][timeout:180];
(
  node["amenity"="parking"]["name"]({bbox});
  way["amenity"="parking"]["name"]({bbox});
  relation["amenity"="parking"]["name"]({bbox});
);
out center tags;
""".format(bbox=BBOX)

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "parks_osm.json")
FIELDS = ["id", "name", "lat", "lng", "site", "hours", "fee", "cap"]


def fetch():
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body,
        headers={"User-Agent": "park-easy/1.0 (+https://github.com/alice-creator-lab/park-easy)"},
    )
    with urllib.request.urlopen(req, timeout=200) as r:
        return json.load(r)


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def main():
    data = fetch()
    rows = {}
    for e in data.get("elements", []):
        tags = e.get("tags") or {}
        name = (tags.get("name:zh-HK") or tags.get("name:zh") or tags.get("name") or "").strip()
        if not name:
            continue
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lng = e.get("lon") or (e.get("center") or {}).get("lon")
        if not lat or not lng:
            continue
        pid = f"osm:{e['type']}/{e['id']}"
        rows[pid] = [
            pid,
            name,
            round(float(lat), 6),
            round(float(lng), 6),
            (tags.get("website") or tags.get("contact:website") or "").strip(),
            (tags.get("opening_hours") or "").strip(),
            (tags.get("fee") or "").strip(),
            num(tags.get("capacity")),
        ]

    out = sorted(rows.values(), key=lambda x: (x[1], x[0]))
    payload = {
        "v": 1,
        "source": ENDPOINT,
        "license": "ODbL 1.0 © OpenStreetMap contributors",
        "query_bbox": BBOX,
        "fields": FIELDS,
        "count": len(out),
        "rows": out,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {len(out)} car parks -> {os.path.abspath(OUT)} ({os.path.getsize(OUT)/1e3:.0f} kB)")


if __name__ == "__main__":
    main()
