FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu -r requirements.txt
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "main.py"]
