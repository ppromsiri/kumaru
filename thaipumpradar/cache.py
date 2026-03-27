import os
import json
import logging
import redis
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

# --- Redis Client (ใช้ร่วมกันทุก module) ---
redis_client = None
try:
    temp_client = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        db=int(os.getenv("REDIS_DB")),
        decode_responses=True,
        socket_timeout=1,
        socket_connect_timeout=1
    )
    temp_client.ping()
    redis_client = temp_client
    logging.info("Redis connected successfully.")
except Exception as e:
    logging.warning(f"Redis not available, bypassing cache. Reason: {e}")
    redis_client = None

# --- Helper: ดึงข้อมูลจาก Cache ---
def cache_get(key: str) -> dict | None:
    if not redis_client:
        return None
    try:
        cached = redis_client.get(key)
        if cached:
            logging.info(f"[Cache HIT] {key}")
            return json.loads(cached)
    except Exception as e:
        logging.warning(f"Redis GET error: {e}")
    return None

# --- Helper: บันทึกข้อมูลลง Cache (TTL หน่วยเป็นวินาที, default 60 วิ) ---
def cache_set(key: str, data: dict, ttl: int = 60) -> None:
    if not redis_client:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(data, ensure_ascii=False))
        logging.info(f"[Cache SET] {key} (TTL={ttl}s)")
    except Exception as e:
        logging.warning(f"Redis SET error: {e}")
