FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ai_worker ./ai_worker
COPY core ./core
COPY scripts ./scripts
COPY storage ./storage

CMD ["python", "scripts/cameras/run_worker.py"]
