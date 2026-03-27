import json
import re

def clean_intent(intent: str) -> str:
    intent = intent.strip('"\'#')
    return intent.strip()

def extract_json(s: str) -> dict:
    s = s.strip()
    if not s:
        raise ValueError("empty")
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        pass
    m = re.search(r'\{.*\}', s, re.DOTALL)
    if m:
        return json.loads(m.group())
    raise ValueError("no JSON found")

def main(llm_output: str, llm_reasoning: str) -> dict:
    for src in [llm_output, llm_reasoning]:
        try:
            data = extract_json(src)
            break
        except (json.JSONDecodeError, ValueError):
            continue
    else:
        data = {"agents": ["cultivation_agent"], "intent": ""}
    agents = data.get("agents", []) or ["cultivation_agent"]

    return {
        "intent":            clean_intent(data.get("intent", "")),
        "run_price":         "price_agent"         in agents,
        "run_cultivation":   "cultivation_agent"   in agents,
        "run_geo_weather":   "geo_weather_agent"   in agents,
        "run_cost":          "cost_profit_agent"   in agents,
        "run_news":          "news_agent"          in agents,
        "run_baac_market":   "baac_market_agent"   in agents,
        "run_baac_forecast": "baac_forecast_agent" in agents,
        "run_pumpradar": "pumpradar_agent" in agents,
        "run_oil_price": "oil_price_agent" in agents,

    }