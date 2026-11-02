#!/usr/bin/env python3
"""Build data/meters.json from the TD metered-parking-spaces CSV.

The upstream CSV is ~4.8 MB (uncompressed, no gzip), too heavy to load on a
phone every visit. This script keeps only what the map needs.

Usage: python3 tools/build_meters.py
"""
import csv
import io
import json
import os
import urllib.request

SRC = "https://resource.data.one.gov.hk/td/psiparkingspaces/spaceinfo/parkingspaces.csv"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "meters.json")

FIELDS = ["id", "lat", "lng", "street", "section", "district", "region", "vt", "lpp", "unit", "price", "op"]


def main():
    req = urllib.request.Request(SRC, headers={"User-Agent": "park-easy/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        text = r.read().decode("utf-8-sig")

    lines = text.splitlines()
    # line 0 = file generation date, line 1 = blank/padding, line 2 = header
    header_idx = next(i for i, ln in enumerate(lines) if ln.startswith("PoleId,"))
    reader = csv.DictReader(io.StringIO("\n".join(lines[header_idx:])))

    rows = []
    seen = set()
    for r in reader:
        sid = (r.get("ParkingSpaceId") or "").strip()
        if not sid or sid in seen:
            continue
        try:
            lat = round(float(r["Latitude"]), 6)
            lng = round(float(r["Longitude"]), 6)
        except (TypeError, ValueError, KeyError):
            continue
        # skip internal-test / not-yet-commissioned meters (ids >= 90000 per spec)
        try:
            if int(sid.rstrip("ABCD")) >= 90000:
                continue
        except ValueError:
            pass
        seen.add(sid)
        rows.append([
            sid, lat, lng,
            (r.get("Street_tc") or "").strip(),
            (r.get("SectionOfStreet_tc") or "").strip(),
            (r.get("District_tc") or "").strip(),
            (r.get("Region_tc") or "").strip(),
            (r.get("VehicleType") or "A").strip(),
            int(float(r["LPP"])) if r.get("LPP") else None,
            int(float(r["TimeUnit"])) if r.get("TimeUnit") else None,
            float(r["PaymentUnit"]) if r.get("PaymentUnit") else None,
            (r.get("OperatingPeriod") or "").strip(),
        ])

    rows.sort(key=lambda x: x[0])
    payload = {
        "v": 1,
        "generated": lines[0].strip(),
        "source": SRC,
        "fields": FIELDS,
        "count": len(rows),
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {len(rows)} meters -> {os.path.abspath(OUT)} ({os.path.getsize(OUT)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
