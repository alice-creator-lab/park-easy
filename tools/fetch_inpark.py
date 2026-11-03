#!/usr/bin/env python3
"""Fetch live vacancy for the supplementary car parks from InPark AI.

Sino's malls (荃新天地, 屯門市廣場, 奧海城, 中港城, 黃金海岸, 朗壹廣場) have real
barrier-counted vacancy but do NOT publish it to data.gov.hk. Their S+ system
feeds aggregators such as InPark AI, whose car-park pages embed the current
reading in a `liveVacancy` object:

    {"vacancy":121,"observed_max":135,"data_state":"live",
     "source_system":"sino_splus","updated_minutes_ago":2,...}

We read that object for every park listed in data/parks_extra.json that has an
`inpark` id and write data/live_extra.json — a thin snapshot the static app
loads. Nothing else on the page is used.

Usage: python3 tools/fetch_inpark.py
Exit code 0 even when some parks fail (partial data is still useful); the
snapshot keeps `ok` per park so the UI can fall back to "no live data".
"""
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "data", "parks_extra.json")
OUT = os.path.join(ROOT, "data", "live_extra.json")
BASE = "https://inpark.com.hk/en/carpark/"
UA = "park-easy/1.0 (+https://github.com/alice-creator-lab/park-easy)"
HKT = timezone(timedelta(hours=8))


def fetch(slug):
    req = urllib.request.Request(BASE + slug, headers={"User-Agent": UA, "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def live_vacancy(html):
    """Pull the balanced {...} that follows "liveVacancy": in the page payload."""
    s = html.replace('\\"', '"')
    m = re.search(r'"liveVacancy"\s*:\s*(\{)', s)
    if not m:
        return None
    start, depth = m.start(1), 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start:i + 1])
                except ValueError:
                    return None
    return None


def main():
    with open(SRC, encoding="utf-8") as f:
        extra = json.load(f)
    rows, ok = {}, 0
    for p in extra.get("rows", []):
        slug = p.get("inpark")
        if not slug:
            continue
        entry = {"ok": False}
        try:
            v = live_vacancy(fetch(slug))
            if v and v.get("data_state") == "live" and v.get("vacancy") is not None:
                entry = {
                    "ok": True,
                    "n": int(v["vacancy"]),
                    "cap": v.get("observed_max"),
                    "state": v.get("data_state"),
                    "mins": v.get("updated_minutes_ago"),
                    "at": v.get("gov_lastupdate") or "",
                    "sys": v.get("source_system") or "",
                }
                ok += 1
            elif v:
                entry["state"] = v.get("data_state")
        except Exception as e:  # network / parse — keep the park, drop the number
            entry["err"] = type(e).__name__
        rows[p["id"]] = entry
        time.sleep(0.3)

    payload = {
        "v": 1,
        "generated": datetime.now(HKT).replace(microsecond=0).isoformat(),
        "source": "InPark AI car-park pages (liveVacancy), data from Sino S+ car park system",
        "note": "第三方聚合，非政府開放數據；只抽取 liveVacancy 物件。",
        "count": ok,
        "rows": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"live {ok}/{len(rows)} -> {OUT} ({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
