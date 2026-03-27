FROM python:3.13-slim

# ติดตั้ง uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files ก่อน (ใช้ layer cache)
COPY pyproject.toml uv.lock ./

# ติดตั้ง Python dependencies
RUN uv sync --frozen --no-dev --no-cache

# ติดตั้ง Playwright พร้อม Chromium และ system dependencies
RUN uv run playwright install chromium --with-deps

# Copy source code
COPY main.py api.py cache.py scrap.py ./

# Expose port
EXPOSE 8000

# รัน FastAPI ผ่าน uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
