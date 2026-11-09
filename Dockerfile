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

# Вшиваем модель Qwen2.5-1.5B прямо в Docker-образ для мгновенного старта и автономной работы
RUN mkdir -p /app/models && \
    curl -L -o /app/models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
    https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

COPY . .

CMD ["python", "main.py"]
