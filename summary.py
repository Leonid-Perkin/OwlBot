import os
import gc
import urllib.request
import asyncio
from datetime import datetime

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILENAME)
MODEL_PATH = os.environ.get("LLM_MODEL_PATH", DEFAULT_MODEL_PATH)
MODEL_DOWNLOAD_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
)

def ensure_model_exists():
    if os.path.exists(MODEL_PATH):
        return True
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    print(f"Загрузка модели LLM с {MODEL_DOWNLOAD_URL}...")
    urllib.request.urlretrieve(MODEL_DOWNLOAD_URL, MODEL_PATH)
    print("Модель успешно загружена!")
    return True

def generate_summary_sync(messages: list[tuple[str, str]], date_str: str) -> str:
    if not messages or len(messages) < 3:
        return "В чате за сегодня недостаточно сообщений для составления выжимки (нужно хотя бы 3 сообщения)."

    try:
        ensure_model_exists()
    except Exception as e:
        return f"❌ Ошибка при загрузке модели: {e}"

    # Build dialogue transcript
    transcript_lines = []
    total_chars = 0
    # Take up to the last 80 messages if chat is huge
    selected_messages = messages[-80:]
    for user_name, text in selected_messages:
        line = f"{user_name}: {text}"
        transcript_lines.append(line)
        total_chars += len(line)
        if total_chars > 3500:
            break

    dialogue = "\n".join(transcript_lines)

    try:
        from llama_cpp import Llama
    except ImportError:
        return "❌ Ошибка: пакет llama-cpp-python не установлен."

    try:
        threads = min(4, os.cpu_count() or 2)
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=2048,
            n_threads=threads,
            verbose=False
        )

        chat_messages = [
            {
                "role": "system",
                "content": (
                    "Ты — русскоязычный аналитик чата. Твоя задача — составить краткую выжимку переписки за день.\n"
                    "ПРАВИЛА:\n"
                    "1. Перескажи суть обсуждений СВОИМИ СЛОВАМИ. Категорически ЗАПРЕЩЕНО цитировать или копировать сообщения!\n"
                    "2. Опиши главные темы, договорённости, вопросы и выводы участников.\n"
                    "3. Формат: 2-5 кратких пунктов, каждый с новой строки, начиная с подходящего эмодзи (💬, 📌, 🤝, ⏰).\n"
                    "4. Отвечай кратко и только по фактам из диалога."
                )
            },
            {
                "role": "user",
                "content": f"Вот переписка в чате:\n{dialogue}\n\nСделай краткую выжимку своими словами:"
            }
        ]

        response = llm.create_chat_completion(
            messages=chat_messages,
            max_tokens=250,
            temperature=0.3,
            stop=["<|im_end|>", "<|im_start|>"]
        )

        summary_text = response["choices"][0]["message"]["content"].strip()

        # Free memory immediately
        del llm
        gc.collect()

        try:
            formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
        except ValueError:
            formatted_date = date_str

        return (
            f"📝 **Краткая выжимка дня ({formatted_date})**\n"
            f"────────────────────\n"
            f"{summary_text}\n"
            f"────────────────────\n"
            f"🤖 _Сгенерировано локальной моделью Qwen2.5-1.5B_"
        )

    except Exception as e:
        return f"❌ Ошибка генерации выжимки: {e}"

async def generate_summary(messages: list[tuple[str, str]], date_str: str) -> str:
    return await asyncio.to_thread(generate_summary_sync, messages, date_str)
