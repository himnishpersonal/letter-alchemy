FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ALCHEMY_DATA_ROOT=/app

COPY pyproject.toml README.md ./
COPY alchemy ./alchemy
COPY data ./data
COPY bank/puzzles.json ./bank/puzzles.json
RUN pip install --no-cache-dir .

ENV PORT=8080
CMD ["sh", "-c", "uvicorn alchemy.main:app --host 0.0.0.0 --port ${PORT}"]
