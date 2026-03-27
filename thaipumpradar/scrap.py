import asyncio
import re
import logging
from fastapi import HTTPException
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from cache import cache_get, cache_set

# Mapping ชื่อภาษาไทยบนหน้าเว็บ → key ที่ใช้ใน Response
FUEL_TYPE_MAP = {
    "ดีเซล": "diesel",
    "แก๊สโซฮอล์ 95": "benzineG95",
    "แก๊สโซฮอล์ 91": "benzineG91",
    "E20": "benzineE20",
    "E85": "benzineE85",
}

def _compute_severity(diesel_out_pct: float) -> str:
    if diesel_out_pct >= 60:
        return "critical"
    elif diesel_out_pct >= 30:
        return "warning"
    return "normal"


async def _scrape_province(province: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()

        logging.info(f"[Scrap] Opening browser for: {province}")
        await page.goto("https://www.thaipumpradar.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        for attempt in range(5):  # กดได้สูงสุด 5 รอบ ป้องกัน infinite loop
            try:
                close_btn = page.locator("button:has(svg path[d*='M6 18'])").first
                await close_btn.wait_for(state="visible", timeout=2000)
                await close_btn.click()
                logging.info(f"[Scrap] Dismissed panel #{attempt + 1}")
                await page.wait_for_timeout(500)
            except Exception:
                logging.info(f"[Scrap] No more panels to dismiss (cleared {attempt})")
                break

        # Step 1: กดปุ่ม filter "จังหวัด"
        await page.locator("button", has_text="จังหวัด").first.click()
        await page.wait_for_timeout(500)

        # Step 2: พิมพ์ชื่อจังหวัด
        search_input = page.get_by_placeholder("พิมพ์ชื่อจังหวัด...")
        await search_input.fill(province)
        await page.wait_for_timeout(1000)

        # Step 3: กดเลือกจังหวัดแรกในลิสต์
        province_btn = page.locator("button.w-full.text-left.text-sm").first
        try:
            await province_btn.wait_for(state="visible", timeout=3000)
        except Exception:
            await browser.close()
            raise HTTPException(
                status_code=404,
                detail=f"ไม่พบข้อมูลจังหวัด '{province}' กรุณาตรวจสอบชื่อจังหวัด ต้องเป็นภาษาไทย"
            )

        selected = await province_btn.inner_text()
        logging.info(f"[Scrap] Clicking province: {selected.strip()}")
        await province_btn.click()
        await page.wait_for_timeout(1500)

        # Step 4: กดแท็บ "ภาพรวม" เพื่อดูสรุป
        # <button class="rounded-lg px-4 py-1.5 text-xs font-semibold ...">ภาพรวม</button>
        await page.get_by_role("button", name="ภาพรวม").click()
        await page.wait_for_timeout(1000)

        # ---- Step 5: Scrape ข้อมูล ----

        # 5.1 สถิติ 3 กล่องบนสุด (ปั๊มทั้งหมด / มีรายงาน / ดีเซลหมด%)
        total_stations = 0
        reported_stations = 0
        diesel_out_pct = 0.0

        stat_panels = page.locator(".grid.grid-cols-3.gap-2 > div")
        for i in range(await stat_panels.count()):
            label = await stat_panels.nth(i).locator("p").nth(0).inner_text()
            value = await stat_panels.nth(i).locator("p").nth(1).inner_text()
            value = value.strip()
            if "ปั๊มทั้งหมด" in label:
                total_stations = int(value)
            elif "มีรายงาน" in label:
                reported_stations = int(value)
            elif "ดีเซลหมด" in label:
                diesel_out_pct = float(value.replace("%", ""))

        # Validate: ถ้าไม่มีข้อมูลเลย = ชื่อจังหวัดผิด
        if total_stations == 0 and reported_stations == 0:
            await browser.close()
            raise HTTPException(
                status_code=404,
                detail=f"ไม่พบข้อมูลจังหวัด '{province}' กรุณาตรวจสอบชื่อจังหวัด ต้องเป็นภาษาไทย"
            )

        # 5.2 สถานะน้ำมันแยกชนิด
        # "8 มี / 35 หมด" → available=8, out=35
        fuel_summary = {}
        fuel_rows = page.locator(".space-y-3 > .space-y-1")
        for i in range(await fuel_rows.count()):
            row = fuel_rows.nth(i)
            fuel_name = (await row.locator("span.text-xs.font-semibold").inner_text()).strip()
            stat_text = (await row.locator("span.text-slate-500").inner_text()).strip()
            m = re.match(r"(\d+)\s*มี\s*/\s*(\d+)\s*หมด", stat_text)
            available = int(m.group(1)) if m else 0
            out = int(m.group(2)) if m else 0
            fuel_key = FUEL_TYPE_MAP.get(fuel_name, fuel_name)
            fuel_summary[fuel_key] = {"available": available, "limited": 0, "out": out, "total": available + out}

        # 5.3 แยกตามแบรนด์
        # "OTHER  42 สาขา  หมด 3"  /  "BANGCHAK  23 สาขา  หมด 11  มี 2"
        brands = []
        brand_rows = page.locator("div.flex.items-center.gap-2")
        for i in range(await brand_rows.count()):
            row = brand_rows.nth(i)

            # brand name มาจาก span ที่มี class w-20 truncate
            name_els = row.locator("span.w-20.truncate")
            if await name_els.count() == 0:
                continue
            brand_id = (await name_els.inner_text()).strip()

            # total สาขา
            total_text = (await row.locator("span.text-slate-500").inner_text()).strip()
            total_m = re.match(r"(\d+)\s*สาขา", total_text)
            total = int(total_m.group(1)) if total_m else 0

            # diesel หมด (text-red-400)
            diesel_out = 0
            out_els = row.locator("span.text-red-400")
            if await out_els.count() > 0:
                out_m = re.match(r"หมด\s*(\d+)", (await out_els.inner_text()).strip())
                diesel_out = int(out_m.group(1)) if out_m else 0

            # diesel มี (text-emerald-400) — optional
            diesel_ok = 0
            ok_els = row.locator("span.text-emerald-400")
            if await ok_els.count() > 0:
                ok_m = re.match(r"มี\s*(\d+)", (await ok_els.inner_text()).strip())
                diesel_ok = int(ok_m.group(1)) if ok_m else 0

            brands.append({
                "brandId": brand_id,
                "total": total,
                "dieselOut": diesel_out,
                "dieselOk": diesel_ok,
            })


        await browser.close()

        return {
            "totalStations": total_stations,
            "reportedStations": reported_stations,
            "dieselOutPct": diesel_out_pct,
            "severity": _compute_severity(diesel_out_pct),
            "fuelSummary": fuel_summary,
            "brands": brands,
        }


def fetch_from_scrap(province: str) -> dict:
    """Entry point สำหรับ main.py (sync wrapper บน async playwright)"""
    cache_key = f"thaipumpradar:scrap:{province}"

    # 1. เช็ค Cache ก่อน
    cached = cache_get(cache_key)
    if cached:
        return cached

    # 2. รัน Playwright
    try:
        data = asyncio.run(_scrape_province(province))
    except HTTPException:
        raise
    except PlaywrightTimeout:
        raise HTTPException(status_code=504, detail="Scraper timeout — ไม่สามารถโหลดหน้าเว็บได้")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraper error: {e}")

    # 3. บันทึกลง Cache 60 วินาที
    cache_set(cache_key, data, ttl=60)
    return data
