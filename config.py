"""
Конфигурация приложения
Все настройки загружаются из переменных окружения (.env файла)
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# ============== TELEGRAM BOT ==============
# Токен бота от BotFather
# Получите: https://t.me/BotFather -> /newbot
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")

# ============== TELETHON (MTProto) ==============
# API credentials для прямого доступа к Telegram API
# Получите: https://my.telegram.org/apps -> Create application
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "your_api_hash")

# Имя файла сессии Telethon (сохраняется на диск для повторного использования)
# Сессия содержит авторизованного пользователя
SESSION_NAME = os.getenv("SESSION_NAME", "telegram_aggregator")

# ============== DATABASE ==============
# URL подключения к базе данных
# Формат: dialect+driver://username:password@host:port/database
# SQLite: sqlite:///filename.db (файл создаётся автоматически)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")

# ============== SUMMARIZATION ==============
# Тип суммаризации: "local" (FLAN-T5), "api" (OpenAI/Gemini), "llama_cpp" или "short"
# local: легкая FLAN-T5 модель для CPU, бесплатно, офлайн
# api: требует API ключ, платный, качественная суммаризация
# llama_cpp: локальная модель GGUF, высокая производительность
# short: обрезка текста до 100 символов + "...", самый быстрый режим
SUMMARIZATION_TYPE = os.getenv("SUMMARIZATION_TYPE", "short")

# ============== LLAMA_CPP ==============
# Путь к модели GGUF для llama_cpp
LLAMA_CPP_MODEL_PATH = os.getenv("LLAMA_CPP_MODEL_PATH", r"G:\LLM_models2\Grok-3-reasoning-gemma3-12B-distilled-HF.Q8_0.gguf")

# Формат чата для модели (gemma, chatml, llama-3 и т.д.)
LLAMA_CPP_CHAT_FORMAT = os.getenv("LLAMA_CPP_CHAT_FORMAT", "gemma")

# Максимальное количество токенов в контексте
#LLAMA_CPP_N_CTX = int(os.getenv("LLAMA_CPP_N_CTX", "32768"))
LLAMA_CPP_N_CTX = int(os.getenv("LLAMA_CPP_N_CTX", "4096"))

# Количество потоков CPU
LLAMA_CPP_N_THREADS = int(os.getenv("LLAMA_CPP_N_THREADS", "8"))

# Количество слоёв для загрузки на GPU (0 - только CPU)
LLAMA_CPP_N_GPU_LAYERS = int(os.getenv("LLAMA_CPP_N_GPU_LAYERS", "47"))

# Температура генерации (ниже = более детерминированно)
LLAMA_CPP_TEMPERATURE = float(os.getenv("LLAMA_CPP_TEMPERATURE", "0.1"))

# Максимальное количество токенов в ответе
#LLAMA_CPP_MAX_TOKENS = int(os.getenv("LLAMA_CPP_MAX_TOKENS", "8192"))
LLAMA_CPP_MAX_TOKENS = int(os.getenv("LLAMA_CPP_MAX_TOKENS", "4096"))

# OpenAI API ключ для GPT-суммаризации
# Получите: https://platform.openai.com/api-keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Gemini API ключ (альтернатива OpenAI)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ============== SCHEDULER ==============
# Интервал проверки новых сообщений в секундах
# Рекомендуемое значение: 30-300 секунд
# Слишком частые проверки могут привести к блокировке Telegram
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "10"))

# Список каналов для автоматической подписки при первом запуске
# Разделяйте запятыми: "channel1,channel2,channel3"
DEFAULT_CHANNELS = os.getenv("DEFAULT_CHANNELS", "").split(",")