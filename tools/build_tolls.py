#!/usr/bin/env python3
"""建立隧道收費資料檔（data/tolls.json）。

來源：
  - 運輸署「道路網絡（第二代）」開放數據
      TUN_BRIDGE_TOLL.csv    固定收費隧道及橋樑
      TUN_BRIDGE_TV_TOLL.csv 分時段收費（過海隧道、大欖隧道）
  - 1823 香港公眾假期（判斷分時段收費的「星期日及公眾假期」日別）

用法：python3 tools/build_tolls.py
"""
import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXED_URL = "https://static.data.gov.hk/td/road-network-v2/TUN_BRIDGE_TOLL.csv"
TV_URL = "https://static.data.gov.hk/td/road-network-v2/TUN_BRIDGE_TV_TOLL.csv"
HOL_URL = "https://www.1823.gov.hk/common/ical/tc.json"

CLASSES = {
    "MC": "電單車／機動三輪車",
    "PC": "私家車",
    "TA": "的士",
    "OTH": "其他車輛",
    "LB": "小巴",
    "LGV": "輕型貨車",
    "MGV": "中型貨車",
    "HGV": "重型貨車",
    "SD": "單層巴士",
    "DD": "雙層巴士",
    "AV": "特別用途車輛",
    "VT": "鄉村車輛",
    "VTT": "鄉村車輛（拖車）",
    "AAX": "其他車輛",
}
TV_CLASSES = ["MC", "PC", "TA", "OTH"]


def get(url, enc="utf-8-sig"):
    req = urllib.request.Request(url, headers={"User-Agent": "park-easy/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode(enc, "ignore")


def parse_rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def build_fixed(rows):
    out = {}
    for r in rows:
        name = r["TUNNEL_BRIDGE_CHINESE_NAME"].strip()
        cls = r["VEHICLE_CLASS_DESCRIPTION"].strip()
        toll = r["CONCESS_TOLL"].strip() or r["GAZETTED_TOLL"].strip()
        if not name or not cls:
            continue
        out.setdefault(name, {})[cls] = float(toll)
    return [{"name": n, "tolls": t} for n, t in out.items()]


def build_tv(rows):
    tv = {}
    for r in rows:
        name = r["TUNNEL_BRIDGE_CHINESE_NAME"].strip()
        if "備用" in name:
            continue                      # 備用收費點不是實際行車隧道
        dow = r["DAY_OF_WEEK"].strip()     # A = 星期一至六（不含公眾假期），B = 星期日及公眾假期
        cls = r["VEHICLE_CLASS_DESCRIPTION"].strip()
        if cls not in TV_CLASSES:
            continue
        band = tv.setdefault(name, {}).setdefault(dow, {})
        key = (r["START_TIME"].strip(), r["END_TIME"].strip())
        band.setdefault(key, {})[cls] = float(r["GAZETTED_TOLL"])
    out = []
    for name, days in tv.items():
        obj = {"name": name}
        for dow, bands in days.items():
            arr = []
            for (s, e), tolls in sorted(bands.items()):
                arr.append([s, e] + [tolls.get(c) for c in TV_CLASSES])
            obj[dow] = arr
        out.append(obj)
    return out


def build_holidays():
    """由 1823 的 iCal JSON 抽出公眾假期日期（YYYY-MM-DD）。"""
    text = get(HOL_URL)
    dates = set()
    for m in re.finditer(r'"dtstart"\s*:\s*\[\s*"(\d{8})"', text):
        d = m.group(1)
        dates.add(f"{d[:4]}-{d[4:6]}-{d[6:]}")
    return sorted(dates)


def main():
    try:
        fixed_rows = parse_rows(get(FIXED_URL))
        tv_rows = parse_rows(get(TV_URL))
    except Exception as e:
        print("下載失敗：", e, file=sys.stderr)
        return 1
    holidays = []
    try:
        holidays = build_holidays()
    except Exception as e:
        print("公眾假期下載失敗，改用空清單：", e, file=sys.stderr)

    out = {
        "v": 1,
        "generated": date.today().isoformat(),
        "source": "運輸署 道路網絡（第二代）開放數據 TUN_BRIDGE_TOLL.csv / TUN_BRIDGE_TV_TOLL.csv；公眾假期來自 1823",
        "note": "分時段收費：A = 星期一至六（不包括公眾假期），B = 星期日及公眾假期",
        "classes": CLASSES,
        "tvClasses": TV_CLASSES,
        "holidays": holidays,
        "tv": build_tv(tv_rows),
        "fixed": build_fixed(fixed_rows),
    }
    path = os.path.join(BASE, "data", "tolls.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"寫入 {path}：{len(out['tv'])} 條分時段隧道、{len(out['fixed'])} 條固定收費隧道、"
          f"{len(holidays)} 個公眾假期")
    return 0


if __name__ == "__main__":
    sys.exit(main())
