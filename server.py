from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from datetime import datetime
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def fetch_infobulletin(client: httpx.AsyncClient, place_rid: int, location_rid: int, placetime_rid: int, date: str):
    target_url = "https://tpbusker.gov.taipei/tpbuskerfrontserver/api/Front/VenueApplication/GetBulletinInfoList"
    params = {
        "locationRid": location_rid,
        "placeTimeRid": placetime_rid,
        "date": date
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://tpbusker.gov.taipei/"
    }
    try:
        res = await client.get(target_url, params=params, headers=headers, timeout=10.0)
        if res.status_code == 200:
            json_data = res.json()
            if json_data.get("isSuccess"):
                loc_name = f"點位 #{location_rid}"
                if place_rid == 104:
                    loc_names_104 = {
                        299: "點位 #299 (A場地)", 301: "點位 #301 (C場地)",
                        302: "點位 #302 (D場地)", 303: "點位 #303 (E場地)",
                        304: "點位 #304 (F場地)", 308: "點位 #308 (G場地)",
                        311: "點位 #311 (H場地)", 313: "點位 #313 (I場地)",
                        315: "點位 #315 (J場地)", 318: "點位 #318 (K場地)",
                        319: "點位 #319 (L場地)", 320: "點位 #320 (L場地)",
                        323: "點位 #323 (M場地)", 326: "點位 #326 (N場地)",
                        329: "點位 #329 (O場地)"
                    }
                    loc_name = loc_names_104.get(location_rid, f"點位 #{location_rid}")
                elif place_rid == 102:
                    loc_names_102 = {
                        291: "點位 #291 (102場地)"
                    }
                    loc_name = loc_names_102.get(location_rid, f"點位 #{location_rid}")

                slot_names = {
                    165: "全天 / 標準時段",
                    171: "下午 13:30-17:30", 
                    172: "晚上 18:00-22:00", 
                    173: "平日晚上 18:00-22:00"
                }
                slot_name = slot_names.get(placetime_rid, f"時段 #{placetime_rid}")

                items = json_data.get("data", [])
                formatted_items = []
                for item in items:
                    head_shot = item.get("headShot")
                    if head_shot:
                        item["headShotUrl"] = f"https://tpbusker.gov.taipei/tpbusker/upfiles/{head_shot}"
                    else:
                        busker_rid = item.get("bulletinBuskerrid")
                        item["headShotUrl"] = f"https://tpbusker.gov.taipei/tpbusker/upfiles/bkr{busker_rid}_6.jpg" if busker_rid else ""

                    item["buskerName"] = item.get("buskerName") or item.get("buskerinfdataName")
                    item["bulletinBuskerno"] = item.get("bulletinBuskerno") or item.get("buskerNo")
                    item["_locationName"] = loc_name
                    item["_timeSlotName"] = slot_name
                    formatted_items.append(item)

                    group_list = item.get("isGroup")
                    if isinstance(group_list, list):
                        for sub in group_list:
                            sub_head = sub.get("headShot")
                            sub["headShotUrl"] = f"https://tpbusker.gov.taipei/tpbusker/upfiles/{sub_head}" if sub_head else ""
                            sub["buskerName"] = sub.get("buskerName")
                            sub["bulletinBuskerno"] = sub.get("bulletinBuskerno") or sub.get("buskerNo")
                            sub["_locationName"] = loc_name
                            sub["_timeSlotName"] = slot_name
                            formatted_items.append(sub)

                return formatted_items
    except Exception as e:
        print(f"場地 {place_rid} 點位 {location_rid} 抓取失敗: {e}")
    return []

@app.get("/api/buskers")
async def get_buskers(date: str, placeRid: int = 104):
    if placeRid == 104:
        locations = [299, 301, 302, 303, 304, 308, 311, 313, 315, 318, 320, 323, 326, 329]
        placetime_ids = [171, 172, 173]
    elif placeRid == 102:
        locations = [291]
        placetime_ids = [165, 171, 172]  # 將 165 加入 102 場地的查詢時段
    else:
        locations = []
        placetime_ids = []

    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        tasks = []
        for loc in locations:
            for time_id in placetime_ids:
                tasks.append(fetch_infobulletin(client, placeRid, loc, time_id, date))
        
        results = await asyncio.gather(*tasks)
        combined_data = [item for sublist in results for item in sublist]
        
        return {
            "isSuccess": True,
            "message": None,
            "data": combined_data,
            "summary": "場地動態切換結果"
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
