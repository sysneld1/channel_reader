#!/usr/bin/env python3
"""
Скрипт для проверки конфигурации приложения
Запустите этот скрипт перед основным запуском для проверки настроек
"""
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_config():
    """Проверяет конфигурацию и выводит статус"""
    print("=== Проверка конфигурации Channel Reader ===")
    print("=" * 50)
    
    errors = []
    warnings = []
    
    # Проверка обязательных переменных
    bot_token = os.getenv("BOT_TOKEN", "")
    api_id = os.getenv("API_ID", "")
    api_hash = os.getenv("API_HASH", "")
    
    if not bot_token or bot_token == "your_telegram_bot_token_here":
        errors.append("[ERROR] BOT_TOKEN не настроен или содержит значение по умолчанию")
    else:
        print(f"[OK] BOT_TOKEN настроен: {bot_token[:10]}...")
    
    if not api_id or api_id == "your_api_id_here":
        errors.append("[ERROR] API_ID не настроен или содержит значение по умолчанию")
    else:
        try:
            api_id_int = int(api_id)
            if api_id_int <= 0:
                errors.append("[ERROR] API_ID должен быть положительным числом")
            else:
                print(f"[OK] API_ID настроен: {api_id_int}")
        except ValueError:
            errors.append("[ERROR] API_ID должен быть числом")
    
    if not api_hash or api_hash == "your_api_hash_here":
        errors.append("[ERROR] API_HASH не настроен или содержит значение по умолчанию")
    else:
        print(f"[OK] API_HASH настроен: {api_hash[:10]}...")
    
    # Проверка дополнительных настроек
    summarization_type = os.getenv("SUMMARIZATION_TYPE", "short")
    print(f"[OK] Тип суммаризации: {summarization_type}")
    
    if summarization_type == "api":
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key:
            warnings.append("[WARNING] SUMMARIZATION_TYPE=api, но OPENAI_API_KEY не настроен")
        else:
            print(f"[OK] OpenAI API ключ настроен: {openai_key[:10]}...")
    
    check_interval = os.getenv("CHECK_INTERVAL_SECONDS", "10")
    try:
        interval_int = int(check_interval)
        if interval_int < 30:
            warnings.append(f"[WARNING] CHECK_INTERVAL_SECONDS={interval_int} слишком малый (рекомендуется >= 30)")
        else:
            print(f"[OK] Интервал проверки: {interval_int} секунд")
    except ValueError:
        errors.append("[ERROR] CHECK_INTERVAL_SECONDS должен быть числом")
    
    # Проверка llama_cpp настроек
    if summarization_type == "llama_cpp":
        model_path = os.getenv("LLAMA_CPP_MODEL_PATH", "")
        if not model_path:
            warnings.append("[WARNING] SUMMARIZATION_TYPE=llama_cpp, но LLAMA_CPP_MODEL_PATH не настроен")
        else:
            print(f"[OK] Путь к модели llama_cpp: {model_path}")
    
    # Вывод результатов
    print("\n" + "=" * 50)
    
    if errors:
        print("НАЙДЕНЫ ОШИБКИ:")
        for error in errors:
            print(f"  {error}")
        print("\nИсправьте ошибки перед запуском приложения")
        return False
    
    if warnings:
        print("ПРЕДУПРЕЖДЕНИЯ:")
        for warning in warnings:
            print(f"  {warning}")
        print("\nПриложение может работать, но рекомендуется исправить предупреждения")
    
    print("Конфигурация готова к использованию!")
    print("\nСледующие шаги:")
    print("  1. Установите зависимости: pip install -r requirements.txt")
    print("  2. Запустите приложение: python main.py")
    print("  3. При первом запуске потребуется авторизация в Telegram")
    
    return True

if __name__ == "__main__":
    success = check_config()
    sys.exit(0 if success else 1)