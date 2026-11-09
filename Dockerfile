FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    cmake \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# На amd64 собираем llama-cpp-python с универсальной поддержкой AVX (AVX2=OFF),
# чтобы бот работал на любых процессорах (AMD A10/FX, Intel Celeron, старых Xeon и современных CPU).
# На arm64 используем готовый wheel от abetlen.
ARG TARGETPLATFORM
RUN if [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        pip install --no-cache-dir --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu -r requirements.txt; \
    else \
        CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_AVX2=OFF -DGGML_AVX=ON" CMAKE_BUILD_PARALLEL_LEVEL=4 \
        pip install --no-cache-dir -r requirements.txt; \
    fi

RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Вшиваем модель Qwen2.5-1.5B прямо в Docker-образ для мгновенного старта и автономной работы
RUN mkdir -p /app/models && \
    curl -L -o /app/models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
    https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

RUN apt-get purge -y build-essential cmake \
    && apt-get install -y --no-install-recommends libgomp1 \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "main.py"]
