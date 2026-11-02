#!/usr/bin/env python3
"""Headless screenshots + smoke checks. Run: python3 tools/shot.py [url]"""
import json, os, random, subprocess, sys, time, urllib.request

CHROME = os.path.expanduser("~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome")
PORT = random.randint(9400, 9500)
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shots")
sys.path.insert(0, os.path.expanduser("~/.hermes/profiles/friend/cache/scratch"))
from cdp import Page  # noqa: E402


def launch(w, h, mobile):
    args = [CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--window-size={w},{h}",
            "--no-first-run", "--hide-scrollbars", f"--user-data-dir=/tmp/pe-{PORT}",
            "--force-device-scale-factor=1", "about:blank"]
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
            return p
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("chrome failed")


def main():
    os.makedirs(OUT, exist_ok=True)
    w, h = 390, 844
    proc = launch(w, h, True)
    page = Page(PORT, match="about:blank")
    try:
        page.send("Emulation.setDeviceMetricsOverride",
                  {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": True})
        page.nav(URL, timeout=90)
        page.js("window.__errs=[];addEventListener('error',e=>__errs.push(e.message));"
                "addEventListener('unhandledrejection',e=>__errs.push('rej:'+e.reason))")
        for _ in range(60):
            n = page.js("document.querySelectorAll('#list .row').length", timeout=15)
            if n and n > 3:
                break
            time.sleep(0.5)
        time.sleep(1.5)
        # headless chrome never finishes Leaflet zoom animations (rAF stalls); use instant moves
        page.js("__pe.map.flyTo=(ll,z)=>__pe.map.setView(ll,z,{animate:false});"
                "__pe.map.fitBounds=(b,o)=>__pe.map.setView(b.getCenter(),15,{animate:false}); 1")
        print("rows", page.js("document.querySelectorAll('#list .row').length"),
              "| hdr:", page.js("document.querySelector('#hdr').textContent"),
              "| stamp:", repr(page.js("document.querySelector('#stamp').textContent")))
        print("parks in state:", page.js("__pe.S.parks.length"),
              "| with total:", page.js("__pe.S.parks.filter(p=>p.total).length"),
              "| vacancy known:", page.js("__pe.S.parks.filter(p=>p.vac!=null).length"),
              "| meters:", page.js("__pe.S.meters.length"),
              "| occ:", page.js("__pe.S.occ.size"))
        page.shot(os.path.join(OUT, "1-list.png"))

        # park detail via a park that has total spaces
        page.js("(function(){const p=__pe.S.parks.find(x=>x.total&&x.vac>0)||__pe.S.parks[0];__pe.showPark(p);})()")
        time.sleep(2)
        print("park detail:", page.js("(document.querySelector('.dtitle')||{}).textContent"),
              "|", page.js("(document.querySelector('.big')||{}).textContent"))
        page.shot(os.path.join(OUT, "2-park-detail.png"))
        page.js("document.querySelector('#back').click()")

        # meters tab
        page.js("document.querySelectorAll('.tab')[1].click()")
        time.sleep(2)
        print("meter rows:", page.js("document.querySelectorAll('#list .row').length"))
        page.shot(os.path.join(OUT, "3-meters.png"))

        # meter detail (occupied one if any)
        page.js("(function(){const m=__pe.S.meters.find(x=>{const o=__pe.S.occ.get(x.id);return o&&o.s==='O'})||__pe.S.meters[0];__pe.showMeter(m);return m.id})()")
        time.sleep(2)
        print("meter detail:", page.js("(document.querySelector('.dtitle')||{}).textContent"),
              "|", page.js("(document.querySelector('.big')||{}).textContent"))
        page.shot(os.path.join(OUT, "4-meter-detail.png"))

        # zoomed map with individual dots
        page.js("document.querySelector('#back').click()")
        page.js("__pe.map.setView([22.3245,114.1690],17,{animate:false}); 1")
        time.sleep(2)
        print("meter markers at z17:", page.js("Object.keys(__pe.map._layers).length"))
        page.shot(os.path.join(OUT, "5-zoom.png"))

        # search
        page.js("document.querySelector('#q').value='旺角';document.querySelector('#q').dispatchEvent(new Event('input'))")
        time.sleep(2.5)
        print("search rows:", page.js("document.querySelectorAll('#list .row').length"))
        page.shot(os.path.join(OUT, "6-search.png"))
        print("errors:", page.js("JSON.stringify(__errs)"))
    finally:
        page.close()
        proc.kill()


if __name__ == "__main__":
    main()
