import requests
import base64
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Загрузка конфигурации
CONFIG_PATH = Path(__file__).parent / "gemini_config.yaml"
config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
gconf = config["gemini"]

# Подставляем API-ключ из окружения
gconf["api_key"] = os.getenv("GEMINI_API_KEY")

def read_image_as_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def recognize_meter_reading(image_path: str) -> str:
    base64_image = read_image_as_base64(image_path)
    url = gconf["endpoint"].replace("{model}", gconf["model"])
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": gconf["api_key"]
    }

    body = {
        "contents": [
            {
                "parts": [
                    {"text": gconf["prompt_template"]},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"Ошибка Gemini API: {response.status_code} - {response.text}")

    result = response.json()
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise Exception("Ошибка в ответе Gemini API: Невозможно извлечь показание счетчика.")