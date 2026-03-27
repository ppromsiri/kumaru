# Thai Pump Radar API for AI Agents ⛽🤖

บริการดึงข้อมูลสถานะปั๊มน้ำมันรายจังหวัดจากเว็บ [ThaiPumpRadar.com](https://www.thaipumpradar.com/) ออกแบบมาเพื่อส่งต่อให้ AI Agent (LLM) นำไปวิเคราะห์ต่อ โดยรองรับทั้งรูปแบบ JSON และ Markdown

## ✨ คุณสมบัติหลัก (Features)
- **แหล่งข้อมูล 2 ทาง (Dual Source):** ดึงข้อมูลรวดเร็วผ่าน `API` (ข้อมูลละเอียด รวมถึงมีข้อมูล B95) หรือเปลี่ยนไปใช้ระบบ `Scrap` ผ่านเบราว์เซอร์จริง (ข้อมูลเฉพาะดีเซลรายแบรนด์) หาก API ถูกบล็อก
- **ระบบ Caching ความเร็วสูง:** เชื่อมต่อกับ Redis เพื่อ Cache ข้อมูล 60 วินาที ช่วยลดภาระเซิร์ฟเวอร์และได้คำตอบทันที
- **Smart Ranking & Filtering:** คัดเลือกและเรียงลำดับสถานีที่ยังมีน้ำมันพร้อมจำหน่าย (Available) โดยเน้นตามเวลาที่รายงานล่าสุด และจำนวนชนิดน้ำมันที่มี
- **สรุปรายงานพร้อมใช้สำหรับ AI:** สามารถสั่งให้ API ตอบกลับเป็น `Markdown` พร้อมตารางสรุปปั๊มที่ยังมีน้ำมัน เพื่อให้ตั้งค่า Prompt ส่งต่อให้ LLM ได้ทันที
- **Security:** ผูก API Key (Header `X-API-KEY`) สำหรับป้องกันการยิง API มั่วซั่ว

---

## 🚀 โครงสร้างโปรเจกต์
- `main.py`: ไฟล์ FastAPI Router หลัก
- `api.py`: ระบบยิง Request ไปหา Endpoint ของ ThaiPumpRadar ตรงๆ
- `scrap.py`: ระบบ Scraper สำรอง (Playwright Parse HTML) ใช้งานเมื่อ API ล่ม
- `cache.py`: จัดการการต่อ Redis Shared Instance ระหว่าง api และ scrap
- `Dockerfile` / `docker-compose.yml`: สำหรับรันบน Production

---

## 🛠 ติดตั้งและรันบนเครื่องเซิร์ฟเวอร์ (Docker)
วิธีที่ง่ายที่สุด แนะนำให้รันผ่าน Docker Compose เพราะระบบจะจัดการลง Playwright และ Redis ให้ครบถ้วน

1. สร้างไฟล์ `.env` :
```env
PORT=8000
API_KEY=my-super-secret-key  # เปลี่ยนเป็น key ของคุณ

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

2. สั่งรัน Docker Compose:
```bash
docker compose up -d --build
```
ระบบจะเปิดให้บริการที่พอร์ต `8000`

---

## 💻รันแบบ Local สำหรับการพัฒนา 

ติดตั้งโปรแกรมจัดการแพ็คเกจ `uv` ก่อนรัน

1. ติดตั้ง Dependencies และ Playwright
```bash
uv sync
uv run playwright install chromium --with-deps
```

2. ตั้งค่าไฟล์ `.env` (ให้ Redis ชี้มาที่ localhost หรือแก้ไขให้ตรงกับที่คุณมี)

3. รัน FastAPI
```bash
uv run uvicorn main:app --reload
```

---

## 📝 วิธีการใช้งาน (API Usage)

**Endpoint:** `POST /fuel-status`  
**Headers:**
- `X-API-KEY`: ค่า API_KEY ที่ตั้งไว้ใน `.env`
- `Content-Type`: `application/json`

**Body Params:**
| Parameter | Type | Description |
|---|---|---|
| `source_type` | string | `"api"` (เร็วกว่า) หรือ `"scrap"` (วิธีสำรอง) |
| `province` | string | ชื่อจังหวัดภาษาไทย เช่น `"กระบี่"` |
| `markdown` | boolean | `true` จะได้คำตอบเป็นข้อความ Markdown, `false` เป็น JSON ดิบ |

### ตัวอย่างการส่ง Request
```bash
curl -X 'POST' \
  'http://localhost:8000/fuel-status' \
  -H 'X-API-KEY: .................' \
  -H 'Content-Type: application/json' \
  -d '{
  "source_type": "api",
  "province": "กระบี่",
  "markdown": true
}'
```

### ตัวอย่าง Response แบบ Markdown (`markdown: true`)
```json
{
  "markdown_content": "## ⛽ อัปเดตสถานการณ์น้ำมัน: จังหวัดกระบี่\n\n- **สถานีทั้งหมดในจังหวัด:** 151 แห่ง\n- **สถานีที่ได้รับการรีพอร์ตแล้ว:** 77 แห่ง\n- **สัดส่วนที่ปั๊มดีเซลหมด:** 46.8%\n- **ระดับความรุนแรง (Severity):** warning\n\n### 📊 สรุปแต่ละประเภทน้ำมัน\n- **D**: มี 12 | ขาดแคลน 11 | หมด 36\n- **G95**: มี 13 | ขาดแคลน 3 | หมด 3\n...\n\n### 🏪 สรุปแยกแต่ละแบรนด์ปั๊มน้ำมัน\n- **PTT**: รวม 19 แห่ง | ดีเซลหมด 11 แห่ง | ดีเซลมี 4 แห่ง\n...\n\n### ⛽ ปั๊มน้ำมันที่ยังมีน้ำมัน 5 แห่ง\n| # | ชื่อปั๊ม | แบรนด์ | เชื้อเพลิงพร้อมจำหน่าย | รายงานล่าสุด |\n|:---:|:---|:---:|:---:|:---:|\n| 1 | สหกรณ์ นิคมอ่าวลึก จำกัด | BANGCHAK | D | 26/03 14:52 |\n| 2 | สหกรณ์อิสลามษะกอฟะฮ จำกัด | SHELL | G95 | 26/03 09:37 |\n..."
}
```

### ตัวอย่าง Response แบบ JSON ธรรมดา (`markdown: false`)
```json
{
  "totalStations": 109,
  "reportedStations": 67,
  "dieselOutPct": 55.2,
  "severity": "warning",
  "fuelSummary": {
    "diesel": {
      "available": 8,
      "limited": 0,
      "out": 35,
      "total": 43
    },
    ...
  },
  "brands": [
    ...
  ],
  "stations": [
    {
      "id": "...",
      "name": "สหกรณ์ นิคมอ่าวลึก จำกัด",
      "brandId": "BANGCHAK",
      "latestReport": {
        "fuelStatuses": { "D": "available" },
        "createdAt": "2026-03-26T07:52:19.423Z"
      },
      "reportTime": "2026-03-26T07:52:19.423Z"
    },
    ...
  ]
}
```


### ตัวอย่าง Response แบบ Markdown ที่จัดรูปแล้ว

```md
## ⛽ อัปเดตสถานการณ์น้ำมัน: จังหวัดกระบี่

- **สถานีทั้งหมดในจังหวัด:** 109 แห่ง
- **สถานีที่ได้รับการรีพอร์ตแล้ว:** 67 แห่ง
- **สัดส่วนที่ปั๊มดีเซลหมด:** 55.2%
- **ระดับความรุนแรง (Severity):** warning

### 📊 สรุปแต่ละประเภทน้ำมัน
- **diesel**: มี 8 | ขาดแคลน 0 | หมด 35
- **benzineG95**: มี 11 | ขาดแคลน 0 | หมด 5

### 🏪 สรุปแยกแต่ละแบรนด์ปั๊มน้ำมัน
- **PTT**: รวม 19 แห่ง | ดีเซลหมด 11 แห่ง | ดีเซลมี 4 แห่ง | B95 หมด 0 แห่ง
- **BANGCHAK**: รวม 24 แห่ง | ดีเซลหมด 10 แห่ง | ดีเซลมี 3 แห่ง | B95 หมด 1 แห่ง

### ⛽ ปั๊มน้ำมันที่ยังมีน้ำมัน 5 แห่ง
| # | ชื่อปั๊ม | แบรนด์ | เชื้อเพลิงพร้อมจำหน่าย | รายงานล่าสุด |
|:---:|:---|:---:|:---:|:---:|
| 1 | สหกรณ์ นิคมอ่าวลึก จำกัด | BANGCHAK | D | 26/03 14:52 |
| 2 | สหกรณ์อิสลามษะกอฟะฮ จำกัด | SHELL | G95 | 26/03 09:37 |
| 3 | ห้างหุ้นส่วนจำกัด ศรีเฟื่องฟู | SHELL | D, G95, G91, E20 | 26/03 08:26 |
| 4 | สถานีบริการ สาขาสนามบินกระบี่ | PTT | D | 26/03 01:04 |
| 5 | นอบเซอร์วิส | OTHER | D, G95 | 25/03 18:36 |
```

---

## 🧪 การทดสอบ (Testing)

โปรเจกต์นี้ใช้ `pytest` ร่วมกับ `pytest-mock` และ `httpx` (ผ่าน FastAPI TestClient) ในการทดสอบระบบ โดยการทดสอบถูกออกแบบมาให้รันได้ทันทีแม้ไม่ได้ติดตั้ง Redis (ใช้การ Mocking ระบบ Cache)

### 1. เครื่องมือที่ใช้ทดสอบ
หากยังไม่ได้ติดตั้งเครื่องมือสำหรับ Test ให้รันคำสั่ง:
```bash
uv add pytest pytest-mock httpx pytest-asyncio --dev
```

### 2. วิธีการรัน Test
ใช้คำสั่งผ่าน `uv` เพื่อรันการทดสอบทั้งหมดในโฟลเดอร์ `test/`:
```bash
uv run pytest test/
```

### 3. รายละเอียดชุดการทดสอบ
- **`test_main.py`**: ทดสอบ API Endpoints ของ FastAPI
  - Health Check (`GET /`)
  - Authentication (ตรวจสอบการส่ง Header `X-API-KEY`)
  - Integration (จำลองการดึงข้อมูลจาก Source ต่างๆ)
  - Layout (ตรวจสอบการตอบกลับทั้งแบบ JSON และ Markdown)
- **`test_api.py`**: ทดสอบ Logic การเชื่อมต่อ External API
  - ตรวจสอบการจัดการ Response เมื่อได้ค่าว่าง (จังหวัดผิด)
  - ตรวจสอบการจัดการ HTTP Error (เช่น 404 Not Found)
- **`test_scrap.py`**: ทดสอบ Logic ชุดคำสั่ง Scraper
  - ตรวจสอบชุดคำสั่งจำลองการรัน Browser
  - ตรวจสอบการจัดการกรณี Timeout หรือ Error อื่นๆ จาก Playwright

> [NOTE]
> ระบบ Test ในปัจจุบันจะมีการ **Mock Cache** ไว้โดยอัตโนมัติ (ผ่าน `test/conftest.py`) เพื่อให้สามารถรันทดสอบ Logic หลักของแอปพลิเคชันได้โดยไม่ต้องต่อ Redis ตัวจริง
