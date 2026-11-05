# 泊車易

香港泊車空位地圖：一頁看清全港 593 個停車場的即時空位，以及 20,000 多個咪錶位的佔用狀況。

## 功能

- **停車場**：data.gov.hk 每分鐘更新的空位數字，並以顏色標示（綠色＝有空位、黃色＝車位緊張、紅色＝已滿、灰色＝無資料）；縮小地圖時按區域聚合成「N 車位 / N 個停車場」
- **遠景空位提示**：縮小地圖時，有空位的咪錶以綠色圓點聚合顯示（圓點越大＝該區空位越多），並置於所有圖層最上；16 級以上逐個顯示綠色空位點
- **精細點選**：地圖可放大至 20 級；在 17 級以上點按地圖空白處，會自動選中最接近（22 像素內）的咪錶位
- **咪錶位**：運輸署 PSI 咪錶佔用資料，街道層面逐個顯示空置／已泊；已泊的位在街景級以紅色小球顯示剩餘分鐘（以佔用開始時間＋錶位上限推算），列表按街道分組並以距離排序
- **詳情頁**：空位、總車位、開放時間、時租、高度限制、電動車充電／傷健車位、電話、導航連結
- **搜尋**：停車場名稱、地址、地區、街道；輸入兩個字以上會自動調整地圖至結果範圍
- **畫面範圍統計**：停車場／咪錶位數目及下方列表只計算目前地圖可見範圍；縮小至全港時顯示全部
- **收藏**：以星號收藏常用停車場，可只顯示收藏
- **隧道收費**：右上角隧道圖示開啟收費面板；過海隧道及大欖隧道按香港時間即時顯示現時收費、有效至幾點、下一段收費，並可展開當日各時段；獅子山、城門、香港仔、大老山、青沙管制區顯示固定收費
- **定位**：於 iOS／Android 瀏覽器定位後，列表自動按距離排序
- **離線**：空位快照及停車場靜態資料會存於 localStorage；離線或 API 故障時顯示上一次資料，並標示「資料舊」

## 資料來源

| 用途 | 來源 |
| --- | --- |
| 停車場靜態資料＋即時空位 | `https://api.data.gov.hk/v1/carpark-info-vacancy` |
| 咪錶位置、收費、時限 | 運輸署 metered parking spaces CSV（經 `tools/build_meters.py` 精簡） |
| 咪錶佔用狀況 | 運輸署 `occupancystatus.csv` |
| 補充停車場（無實時空位） | `data/parks_extra.json`（逐個查核官網）＋ `data/parks_osm.json`（OpenStreetMap，ODbL） |
| 隧道收費 | 運輸署「道路網絡（第二代）」`TUN_BRIDGE_TOLL.csv`（固定收費）及 `TUN_BRIDGE_TV_TOLL.csv`（分時段收費），經 `tools/build_tolls.py` 整理成 `data/tolls.json` |
| 公眾假期 | 1823 香港公眾假期（同日別 B 收費） |
| 底圖 | OpenStreetMap |

## 檔案

```
index.html             單檔應用（HTML + CSS + JS，無建置步驟，除 Leaflet 外無第三方依賴）
data/meters.json       20,699 個咪錶位（id, 座標, 街道, 地區, 車種, 時限, 收費, 營運時段）
data/parks_extra.json  政府數據未收錄的停車場（`inpark` 欄目指向 InPark AI 的停車場 id）
data/live_extra.json   上述停車場的實時空位快照（由 GitHub Actions 每 10 分鐘更新）
data/parks_osm.json    OpenStreetMap 有名稱的停車場（608 個，無實時空位）
data/tolls.json        隧道及橋樑收費（分時段 A／B 別、固定收費、公眾假期日期）
tools/build_meters.py  由運輸署 CSV 重建 data/meters.json
tools/build_osm_parks.py 由 Overpass 重建 data/parks_osm.json
tools/fetch_inpark.py  由 InPark AI 停車場頁面抽取 liveVacancy，寫入 data/live_extra.json
tools/build_tolls.py   由運輸署兩個收費 CSV 及 1823 公眾假期建立 data/tolls.json
.github/workflows/live.yml  每 10 分鐘執行 fetch_inpark.py，並在有變動時提交快照
.github/workflows/tolls.yml 每月重建 data/tolls.json（收費或假期有變動才提交）
tools/shot.py          headless Chrome 截圖及煙霧測試（需要本機 http server）
```

## 為何部分停車場搜尋不到？

政府 vacancy API 只收錄自願上報即時空位的停車場（政府場地、領展、港鐵、部分商場），私人商場如荃新天地、海港城、朗豪坊均不在名單內。因此本應用分為兩層：

1. **有實時空位**：593 個停車場，以綠色／黃色／紅色標記
2. **無實時空位**（空心圈）：`parks_extra.json` 人手查核的停車場，加上 OpenStreetMap 有名稱的停車場；只提供位置、收費、電話、官網，不會顯示空位數字

### 實時空位（補充停車場）

信和系商場（荃新天地、屯門市廣場、奧海城、中港城、黃金海岸、朗壹廣場）設有實時車位數，但只透過商場 S+ 系統／第三方聚合應用程式發佈。`tools/fetch_inpark.py` 讀取 InPark AI 停車場頁面內嵌的 `liveVacancy` 物件（`data_state: live`、`source_system: sino_splus`），寫成 `data/live_extra.json`；`.github/workflows/live.yml` 每 10 分鐘執行一次，有變動才提交，Pages 隨即自動更新。沒有實時數字的停車場仍會顯示位置及收費，介面不會假裝有數據。

### 節省數據用量（只更新畫面可見範圍）

| 資料 | 大小 | 更新時機 |
| --- | --- | --- |
| 停車場空位（API） | ~100 KB（無 ETag，無法回 304） | 畫面有停車場才下載；有互動時每 60 秒，靜態超過 2 分鐘改為每 3 分鐘 |
| 咪錶佔用 CSV | ~719 KB（有 ETag → 內容未變回 304） | 只在咪錶分頁、z ≥ 16、畫面有咪錶位，或開啟咪錶詳情時，才每 5 分鐘下載 |
| 補充停車場實時（InPark） | ~1.5 KB | 每 10 分鐘，只在畫面有信和停車場或開啟其詳情時下載 |
| `data/meters.json` | ~2 MB | 開頁時載入一次（之後依靠 localStorage／HTTP cache） |

移動地圖時，若新區域有停車場而資料已超過 60 秒，才會補充下載一次；切換至其他應用程式再返回時，亦只會在必要時更新。

新增停車場：於 `data/parks_extra.json` 加入一筆資料（`id, name, lat, lng, addr, tel, fee, site, ev, source`）。座標可於香港政府地址資料庫 <https://www.als.gov.hk/lookup?q=地址> 查詢；`source` 填寫所查核的官網，`checked` 更新為查核日期。

## 本機執行

```bash
python3 -m http.server 8802 --bind 127.0.0.1
# 開啟 http://127.0.0.1:8802/
python3 tools/shot.py http://127.0.0.1:8802/
```

## 更新咪錶資料

```bash
python3 tools/build_meters.py      # 重新下載 CSV 並輸出 data/meters.json
```
