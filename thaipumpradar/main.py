from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import os
from api import fetch_from_api
from scrap import fetch_from_scrap
from dotenv import load_dotenv



load_dotenv()

# --- การตั้งค่าเริ่มต้น ---
API_KEY = os.getenv("API_KEY")
PORT = int(os.getenv("PORT"))


app = FastAPI(title="Thai Pump Radar AI Endpoints", description="API สำหรับดึงข้อมูลปั๊มน้ำมันเพื่อไปส่งต่อให้ AI")

# --- การตรวจสอบสิทธิ์ ---
def verify_api_key(x_api_key: str = Header(..., alias="X-API-KEY")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Could not validate API KEY")
    return x_api_key

# --- โครงสร้าง Pydantic ---
class FuelStatusRequest(BaseModel):
    source_type: str = Field(..., description="ระบุ 'api' หรือ 'scrap'")
    province: str = Field(..., description="ชื่อจังหวัดภาษาไทย เช่น 'กรุงเทพมหานคร'")
    markdown: bool = Field(False, description="ถ้า True จะส่งกลับเป็น Markdown String, ถ้า False ส่งกลับเป็น JSON")

# --- โครงสร้าง JSON Response ---
class FuelStatItem(BaseModel):
    available: int = 0
    limited: int = 0
    out: int = 0
    total: int = 0

class BrandItem(BaseModel):
    brandId: str
    total: int
    dieselOut: int
    dieselOk: int
    b95Out: Optional[int] = None

class FuelStatusJsonResponse(BaseModel):
    totalStations: int
    reportedStations: int
    dieselOutPct: float
    severity: str
    fuelSummary: Dict[str, FuelStatItem]
    brands: List[BrandItem]
    stations: Optional[List[Dict]] = []

class FuelStatusMarkdownResponse(BaseModel):
    markdown_content: str

# --- ฟังก์ชันช่วยเหลือ (Markdown) ---
def dict_to_markdown(province: str, data: dict) -> str:
    md = f"## ⛽ อัปเดตสถานการณ์น้ำมัน: จังหวัด{province}\n\n"
    md += f"- **สถานีทั้งหมดในจังหวัด:** {data.get('totalStations', 0)} แห่ง\n"
    md += f"- **สถานีที่ได้รับการรีพอร์ตแล้ว:** {data.get('reportedStations', 0)} แห่ง\n"
    md += f"- **สัดส่วนที่ปั๊มดีเซลหมด:** {data.get('dieselOutPct', 0)}%\n"
    md += f"- **ระดับความรุนแรง (Severity):** {data.get('severity', 'ไม่ระบุ')}\n\n"

    md += "### 📊 สรุปแต่ละประเภทน้ำมัน\n"
    fuel_summary = data.get('fuelSummary', {})
    for fuel_type, stats in fuel_summary.items():
        md += f"- **{fuel_type}**: มี {stats.get('available', 0)} | ขาดแคลน {stats.get('limited', 0)} | หมด {stats.get('out', 0)}\n"

    md += "\n### 🏪 สรุปแยกแต่ละแบรนด์ปั๊มน้ำมัน\n"
    brands = data.get('brands', [])
    for brand in brands:
        line = f"- **{brand.get('brandId')}**: รวม {brand.get('total', 0)} แห่ง | ดีเซลหมด {brand.get('dieselOut', 0)} แห่ง | ดีเซลมี {brand.get('dieselOk', 0)} แห่ง"
        if brand.get('b95Out') is not None:
            line += f" | B95 หมด {brand.get('b95Out')} แห่ง"
        md += line + "\n"
    stations = data.get("stations", [])
    if stations:
        md += f"\n### ⛽ ปั๊มน้ำมันที่ยังมีน้ำมัน {len(stations)} แห่ง\n"
        md += "| # | ชื่อปั๊ม | แบรนด์ | เชื้อเพลิงพร้อมจำหน่าย | รายงานล่าสุด |\n"
        md += "|:---:|:---|:---:|:---:|:---:|\n"
        for idx, st in enumerate(stations):
            rank = str(idx + 1)
            name = st.get("name", "-")
            brand = st.get("brandId", "-")
            
            latest_report = st.get("latestReport", {})
            fuel_statuses = latest_report.get("fuelStatuses", {})
            
            available_fuels = [f for f, s in fuel_statuses.items() if s == "available"]
            fuels_str = ", ".join(available_fuels) if available_fuels else "-"
            
            report_time_str = st.get("reportTime") or latest_report.get("createdAt") or ""
            time_display = "-"
            if report_time_str:
                try:
                    from datetime import datetime, timedelta
                    # ตัด timezone ยิบย่อยออกเหลือแค่ YYYY-MM-DDTHH:MM:SS
                    clean_str = report_time_str.split("+")[0].split("Z")[0][:19]
                    dt = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S")
                    dt_thai = dt + timedelta(hours=7)
                    time_display = dt_thai.strftime("%d/%m %H:%M")
                except Exception:
                    time_display = report_time_str.split("T")[1][:5] if "T" in report_time_str else "-"

            md += f"| {rank} | {name} | {brand} | {fuels_str} | {time_display} |\n"

    return md


@app.get("/", tags=["Health Check"])
def health_check():
    return {"status": "ok"}


# --- Endpoint หลัก (ผูกการเช็คสิทธิ์ `get_api_key`) ---
@app.post("/fuel-status", tags=["Fuel Report"])
def get_fuel_status(req: FuelStatusRequest, api_key: str = Depends(verify_api_key)):
    # 1. รับข้อมูลตาม Data Source
    if req.source_type.lower() == "api":
        raw_data = fetch_from_api(req.province)
    elif req.source_type.lower() == "scrap":
        raw_data = fetch_from_scrap(req.province)
    else:
        raise HTTPException(status_code=400, detail="กรุณาระบุ source_type เป็น 'api' หรือ 'scrap'")

    # 2. คัดแยก Filter ให้ตรงกับ Requirement
    filtered_data = {
        "totalStations": raw_data.get("totalStations", 0),
        "reportedStations": raw_data.get("reportedStations", 0),
        "dieselOutPct": raw_data.get("dieselOutPct", 0.0),
        "severity": raw_data.get("severity", ""),
        "fuelSummary": raw_data.get("fuelSummary", {}),
        "brands": raw_data.get("brands", []),
        "stations": raw_data.get("stations", [])
    }

    # 3. จัด Format การส่งออก
    if req.markdown:
        return {"markdown_content": dict_to_markdown(req.province, filtered_data)}
    else:
        return filtered_data
