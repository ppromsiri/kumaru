import urllib.request
import urllib.parse
import json
import logging
from fastapi import HTTPException
from cache import cache_get, cache_set

def fetch_from_api(province: str) -> dict:
    cache_key = f"thaipumpradar:api:{province}"

    # 1. เช็ค Cache ก่อน
    cached = cache_get(cache_key)
    if cached:
        return cached

    # 2. ไม่มี Cache → ยิง API จริง
    logging.info(f"[API] Fetching fresh data for '{province}'")
    url = f"https://www.thaipumpradar.com/api/provinces/{urllib.parse.quote(province)}/stations"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))

            # Validate: ถ้า totalInProvince และ totalStations เป็น 0 ทั้งคู่ หมายความว่าชื่อจังหวัดน่าจะผิด (API คืน 200 แต่ข้อมูลว่าง)
            if data.get("totalInProvince", 0) == 0 and data.get("totalStations", 0) == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"ไม่พบข้อมูลจังหวัด '{province}' กรุณาตรวจสอบชื่อจังหวัด ต้องเป็นภาษาไทย"
                )

            # --- ดึงข้อมูลจริง จัดเรียงปั๊มน้ำมันที่มีน้ำมันพร้อมจำหน่าย 5 แห่ง ---
            stations = data.get("stations", [])
            available_stations = []
            
            for st in stations:
                latest_report = st.get("latestReport", {})
                fuel_statuses = latest_report.get("fuelStatuses", {})
                
                # นับจำนวนเชื้อเพลิงที่มีสถานะ available
                available_count = sum(1 for status in fuel_statuses.values() if status == "available")
                
                if available_count > 0:
                    available_stations.append((available_count, st))
                    
            # เรียงลำดับ: 1. reportTime หรือ createdAt ล่าสุด (มากไปน้อย), 2. จำนวนเชื้อเพลิงพร้อมจำหน่าย (มากไปน้อย)
            available_stations.sort(key=lambda x: (x[1].get("reportTime") or "", x[0]), reverse=True)
            
            # เลือกมาแค่ 5 อันดับแรก
            data["stations"] = [st for count, st in available_stations[:5]]
            # ----------------------------------------

            # 3. บันทึกลง Cache 60 วินาที
            cache_set(cache_key, data, ttl=60)
            return data

    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูลจังหวัดนี้")
        raise HTTPException(status_code=500, detail=f"API Request Error: {e.code}")
    except HTTPException:
        # Re-raise HTTPException to avoid catching it as generic Exception
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
