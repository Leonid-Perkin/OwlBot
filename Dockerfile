FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    build-essential \
    cmake \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Собираем llama-cpp-python с архитектурой x86-64-v2 + AVX + F16C (без AVX2 и без BMI2),
# что гарантирует 100% совместимость с процессорами AMD A10/FX, Intel Celeron и старыми серверами.
ARG TARGETPLATFORM
RUN if [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
        pip install --no-cache-dir --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu -r requirements.txt; \
    else \
        CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_AVX2=OFF -DGGML_BMI2=OFF -DGGML_AVX=ON -DCMAKE_C_FLAGS='-march=x86-64-v2 -mavx -mf16c -mno-bmi2 -mno-avx2' -DCMAKE_CXX_FLAGS='-march=x86-64-v2 -mavx -mf16c -mno-bmi2 -mno-avx2'" \
        CMAKE_BUILD_PARALLEL_LEVEL=4 \
        pip install --no-cache-dir -r requirements.txt; \
    fi

RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Вшиваем модель Google Gemma 2 2B (Q3_K_M) прямо в Docker-образ для мгновенного старта и автономной работы
RUN mkdir -p /app/models && \
    curl -L -o /app/models/gemma-2-2b-it.Q3_K_M.gguf \
    https://huggingface.co/MaziyarPanahi/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it.Q3_K_M.gguf

RUN apt-get purge -y build-essential cmake \
    && apt-get install -y --no-install-recommends libgomp1 \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "main.py"]
