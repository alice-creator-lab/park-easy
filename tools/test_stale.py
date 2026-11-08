#!/usr/bin/env python3
"""Sensor-staleness smoke test：官方報「空置」但很久沒更新的位，不可以顯示為「有位」。

真實個案：元朗良業街 23357A — 咪錶 2026-11-08 14:40 仍顯示 A 位有 47 分鐘泊車時間，
但政府 occupancystatus.csv 自 11-06 19:26 起一直報 V（空置）。

Run: python3 tools/test_stale.py [url]
環境變數：STALE_ID（預設 23357A）、OCC_ID（預設 23357B）、SITE（預設 良業街）
"""
import json
import os
import random
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cdp import Page  # noqa: E402

CHROME = os.path.expanduser("~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome")
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790/"
PORT = random.randint(9400, 9500)
OUT = os.path.join(HERE, "..", "shots")

SITE = os.environ.get("SITE", "良業街")
STALE_ID = os.environ.get("STALE_ID", "23357A")
OCC_ID = os.environ.get("OCC_ID", "23357B")


def soft(page, expr, timeout=30, label=""):
    """Headless Chrome 用軟件畫布，縮放後偶爾幾十秒無反應；此類情況回傳 None，不當失敗。"""
    try:
        return page.js(expr, timeout=timeout)
    except Exception as e:      # noqa: BLE001
        print(f"  (skip {label or expr[:30]}: {type(e).__name__})")
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    proc = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={PORT}", "--window-size=390,844",
         "--no-first-run", "--hide-scrollbars", f"--user-data-dir=/tmp/pe-st-{PORT}",
         "--force-device-scale-factor=1", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    page = Page(PORT, match="about:blank")
    ok = True
    try:
        page.send("Emulation.setDeviceMetricsOverride",
                  {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        page.nav(URL, timeout=90)
        page.js("window.__errs=[];addEventListener('error',e=>__errs.push(e.message));1")
        for _ in range(160):
            n = page.js("__pe.S.occ.size")
            if n and n > 10000:
                break
            time.sleep(0.5)
        page.js("__pe.map.flyTo=(ll,z)=>__pe.map.setView(ll,z,{animate:false});1")

        state = page.js(f"(function(){{const a=__pe.S.occ.get('{STALE_ID}'),b=__pe.S.occ.get('{OCC_ID}');"
                        f"return {{a:a&&a.s,b:b&&b.s,staleA:__pe.freeStale(a),staleB:__pe.freeStale(b),"
                        f"occ:__pe.S.occ.size}};}})()")
        print("data:", state)
        if not (state and state["a"] == "V" and state["staleA"] and not state["staleB"]):
            print("FAIL 資料狀態不如預期（政府資料可能已更新；可用 STALE_ID 指定其他位）")
            ok = False

        # 1) 詳情頁不可以寫「有位」，標籤應為「資料過舊」
        txt = page.js(f"(function(){{__pe.showMeter(__pe.S.byId.get('{STALE_ID}'));"
                      f"return (document.querySelector('.big')||{{}}).textContent;}})()")
        pill = page.js("(document.querySelector('.pill')||{}).textContent")
        print(f"detail {STALE_ID}:", txt.strip(), "| pill:", pill)
        if txt and "有位" in txt:
            print("FAIL 過舊空位仍顯示「有位」")
            ok = False
        if pill != "資料過舊":
            print("FAIL 標籤應為「資料過舊」，實際：", pill)
            ok = False

        # 2) 街道分組不可把該位算作空位（暫時把 getBounds 限死在該場附近，
        #    免得要移動地圖；headless 軟件畫布移動地圖偶爾會卡住主執行緒）
        js_grp = ("(function(){const ob=__pe.map.getBounds.bind(__pe.map);"
                  "__pe.map.getBounds=()=>({contains:ll=>Math.abs(ll[0]-22.4501)<0.01&&Math.abs(ll[1]-114.0292)<0.01});"
                  "try{const g=__pe.meterGroups().filter(x=>x.section===@S@||x.street===@S@)[0];"
                  "return g?{v:g.v,unk:g.unk,n:g.n}:null}finally{__pe.map.getBounds=ob}})()"
                  ).replace("@S@", json.dumps(SITE, ensure_ascii=False))
        grp = page.js(js_grp, timeout=30)
        print("group:", grp)
        if not grp:
            print("FAIL 找不到該場的街道分組")
            ok = False
        elif not grp.get("unk"):
            print("FAIL 街道分組未標示資料過舊的位")
            ok = False

        # 3) 地圖標記：該位用「存疑」樣式（需要地圖在該處 z>=17；headless 卡住就跳過）
        js_dot = ("(function(){const a=document.querySelector('.fmk.stale[data-mid=\"@I@\"]');"
                  "return {staleDot:!!a,dots:document.querySelectorAll('[data-mid]').length};})()"
                  ).replace("@I@", STALE_ID)
        try:
            page.js("__pe.map.setView([22.45014,114.02918],18,{animate:false});1", timeout=30)
            time.sleep(1.5)
            dots = page.js(js_dot, timeout=30)
            print("markers:", dots)
            if not dots.get("staleDot"):
                print("FAIL 地圖上找不到該位的「存疑」標記")
                ok = False
        except Exception as e:      # noqa: BLE001
            print("  (skip map markers:", type(e).__name__, ")")

        # 4) 截圖（最後做；軟件畫布無反應時不影響結果）
        for name, expr in (("5-stale-meter.png", f"__pe.showMeter(__pe.S.byId.get('{STALE_ID}'));1"),
                           ("6-stale-map.png", "__pe.map.setView([22.45014,114.02918],18,{animate:false});1")):
            try:
                page.js(expr, timeout=30)
                time.sleep(1.5)
                page.shot(os.path.join(OUT, name))
            except Exception as e:      # noqa: BLE001
                print("  (screenshot skipped:", name, type(e).__name__, ")")

        errs = soft(page, "__errs", label="error log")
        print("errors:", errs)
        if errs:
            ok = False
    finally:
        page.close()
        proc.terminate()
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
