import json

def main(http_response) -> dict:
    prices = []
    
    raw_body = http_response
    if isinstance(http_response, dict) and "body" in http_response:
        raw_body = http_response["body"]
    
    data = []
    if isinstance(raw_body, str):
        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError:
            data = []
    elif isinstance(raw_body, list):
        data = raw_body

    summary_date = ""
    if isinstance(data, list) and len(data) > 0:
        entry = data[0]
        
        summary_date = entry.get("OilRemark2", "") 
        if not summary_date:
            summary_date = entry.get("OilPriceDate", "") 
        
        oil_list_raw = entry.get("OilList", "[]")
        
        oil_items = []
        if isinstance(oil_list_raw, str):
            try:
                oil_items = json.loads(oil_list_raw)
            except json.JSONDecodeError:
                oil_items = []
        else:
            oil_items = oil_list_raw if isinstance(oil_list_raw, list) else []
            
        for item in oil_items:
            prices.append({
                "name": str(item.get("OilName", "")),
                "yesterday": str(item.get("PriceYesterday", "0")),
                "today": str(item.get("PriceToday", "0")),
                "tomorrow": str(item.get("PriceTomorrow", "0")),
                "unit": "บาท"
            })
            
    text_summary = f"{summary_date}:\n" if summary_date else "ราคาน้ำมันบางจากฉบับล่าสุด:\n"
    if not prices:
        text_summary += "ไม่พบข้อมูลราคาน้ำมัน"
    else:
        for p in prices:
            text_summary += f"- {p['name']}:\n  เมื่อวาน: {p['yesterday']} | วันนี้: {p['today']} | พรุ่งนี้: {p['tomorrow']} ({p['unit']})\n"
    
    return {
        "text_result": text_summary,
        "date_info": summary_date
    }