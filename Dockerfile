FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH="/root/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY . .

EXPOSE 10000

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --loop uvloop --http httptools --workers ${WEB_CONCURRENCY:-1}"]
