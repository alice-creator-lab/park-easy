# 泊車易

香港泊車空位地圖：一版睇清全港 593 個停車場嘅即時空位，同 20,000+ 個咪錶位嘅佔用狀況。

## 功能

- **停車場**：data.gov.hk 每分鐘更新嘅空位數字，有色標記（綠＝有位、黃＝緊張、紅＝滿、灰＝無資料），遠景按區域聚合成「N 位 / N 個場」
- **咪錶位**：運輸署 PSI 咪錶佔用資料，街道層面逐個顯示空置／已泊，列表按街道分組並用距離排序
- **詳情頁**：空位、總車位、開放時間、時租、高度限制、電動車充電／傷健車位、電話、導航連結
- **搜尋**：停車場名、地址、地區、街道；輸入兩個字以上會自動 fit 去結果
- **收藏**：星號收藏常用停車場，可以淨睇收藏
- **定位**：iOS／Android 瀏覽器定位後，列表自動按距離排
- **離線**：空位快照同停車場靜態資料會存 localStorage，離線或 API 掛掉時顯示上次資料並標示「資料舊」

## 資料來源

| 用途 | 來源 |
| --- | --- |
| 停車場靜態資料＋即時空位 | `https://api.data.gov.hk/v1/carpark-info-vacancy` |
| 咪錶位置、收費、時限 | 運輸署 metered parking spaces CSV（經 `tools/build_meters.py` 精簡） |
| 咪錶佔用狀況 | 運輸署 `occupancystatus.csv` |
| 底圖 | OpenStreetMap |

## 檔案

```
index.html            單檔應用（HTML + CSS + JS，無建置步驟，無第三方依賴除 Leaflet）
data/meters.json      20,699 個咪錶位（id, 座標, 街道, 地區, 車種, 時限, 收費, 營運時段）
tools/build_meters.py 由運輸署 CSV 重建 data/meters.json
tools/shot.py         headless Chrome 截圖＋煙霧測試（需要本機 http server）
```

## 本機執行

```bash
python3 -m http.server 8802 --bind 127.0.0.1
# 開 http://127.0.0.1:8802/
python3 tools/shot.py http://127.0.0.1:8802/
```

## 更新咪錶資料

```bash
python3 tools/build_meters.py      # 重新下載 CSV 並輸出 data/meters.json
```
