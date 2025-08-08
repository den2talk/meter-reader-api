from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import re
import tempfile
from pathlib import Path
import shutil
import os
import yaml
from dotenv import load_dotenv

from gemini_client import recognize_meter_reading

# Загрузка переменных окружения
load_dotenv()

# Загрузка клиентов и ключей из YAML
with open("clients.yaml", "r", encoding="utf-8") as f:
    CLIENT_KEYS = yaml.safe_load(f)["clients"]

def get_client_by_key(api_key: str) -> Optional[str]:
    for client, key in CLIENT_KEYS.items():
        if api_key == key:
            return client
    return None

app = FastAPI(title="Сервис распознавания счетчиков")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_IMAGE_SIZE_MB = 10

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Сервис распознавания работает. Откройте /docs для API-интерфейса."}

@app.post("/recognize")
async def recognize(
    phone_number: str = Form(..., description="Номер телефона клиента"),
    image: UploadFile = File(..., description="Фотография счетчика"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    client_name = get_client_by_key(x_api_key)
    if not client_name:
        raise HTTPException(status_code=401, detail="Неверный API-ключ")

    if not re.match(r"^\+[1-9]\d{1,14}$", phone_number):
        raise HTTPException(status_code=400, detail="Неверный формат номера телефона")

    ext = Path(image.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Недопустимый формат изображения")

    content = await image.read()
    if len(content) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл изображения слишком большой")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        meter_reading = recognize_meter_reading(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка распознавания: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    result = {
        "client": client_name,
        "phone_number": phone_number,
        "meter_reading": meter_reading,
        "timestamp": datetime.utcnow().isoformat()
    }

    return JSONResponse(content=result)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)