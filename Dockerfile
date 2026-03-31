FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn httpx

COPY memos_proxy.py .

EXPOSE 11435

CMD ["python", "memos_proxy.py"]
