import os
import random
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import Page  # noqa: E402

CH = "/home/admin/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome"
PORT = random.randint(9400, 9500)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shots")

proc = subprocess.Popen([CH, "--headless=new", f"--remote-debugging-port={PORT}",
                         "--window-size=390,844", f"--user-data-dir=/tmp/pe-shot-{PORT}",
                         "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(80):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
        break
    except Exception:
        time.sleep(0.2)

pg = Page(PORT, match="about:blank")
try:
    pg.send("Emulation.setDeviceMetricsOverride",
            {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
    pg.nav(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790/", timeout=90)
    for _ in range(160):
        if pg.js("__pe.S.occ.size") > 10000:
            break
        time.sleep(0.5)
    pg.js("__pe.map.flyTo=(ll,z)=>__pe.map.setView(ll,z,{animate:false});1")
    pg.js("__pe.showMeter(__pe.S.byId.get('23357A'));1")
    time.sleep(1.5)
    pg.shot(os.path.join(OUT, "5-stale-meter.png"))
    print("detail shot ok")
    pg.js("__pe.showMeter(__pe.S.byId.get('23357B'));1")
    time.sleep(1.2)
    pg.shot(os.path.join(OUT, "5b-occupied-meter.png"))
    print("occupied shot ok")
    pg.js("(function(){const b=document.querySelector('#back');if(b)b.click();"
          "if(__pe.S.sel)__pe.S.sel=null;return 1})()")
    pg.js("__pe.map.setView([22.45014,114.02918],18,{animate:false});1")
    time.sleep(2.5)
    q = ("(function(){const a=document.querySelector('.fmk.stale[data-mid=\"23357A\"]');"
         "return {stale:!!a,total:document.querySelectorAll('[data-mid]').length}})()")
    print("dots", pg.js(q, timeout=60))
    pg.shot(os.path.join(OUT, "6-stale-map.png"))
    print("map shot ok")
finally:
    pg.close()
    proc.terminate()
