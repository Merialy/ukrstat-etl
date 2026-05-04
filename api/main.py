"""
Проєкт «Дані» | REST API 
FastAPI + SQLAlchemy (async)
"""

from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json

# ------ Ініціалізація ------
app = FastAPI(
    title="Укрстат Data API",
    description="Прототип API для доступу до статистичних даних України",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ------ Схеми відповідей ------
class StatRecord(BaseModel):
    region: Optional[str]
    year: int
    value: Optional[float]
    unit: Optional[str]

class IndicatorMeta(BaseModel):
    id: int
    name: str
    category: str
    source_table: Optional[str]

class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    data: list

class HealthResponse(BaseModel):
    status: str
    version: str


# ------ Заглушка-сховище (замініти на БД у продакшені) ------
# Завантажуємо JSON, згенерований parse_ukrstat.py
def _load_mock_data() -> list[dict]:
    json_path = Path(__file__).parent.parent / "data" / "output.json"
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            payload = json.load(f)
            return payload.get("data", [])
    # Вбудована заглушка якщо файл ще не згенерований
    return [
        {"Регіон": "м. Київ",                "2020": 22000, "2021": 26500, "2022": 30100, "2023": 36200, "2024": 42000},
        {"Регіон": "Львівська",              "2020": 11200, "2021": 13600, "2022": 15500, "2023": 18700, "2024": 21300},
        {"Регіон": "Вінницька",              "2020": 10234, "2021": 12456, "2022": 14100, "2023": 16890, "2024": 19200},
        {"Регіон": "Харківська",             "2020": 11800, "2021": 14200, "2022": None,  "2023": 15100, "2024": 18400},
        {"Регіон": "Дніпропетровська",       "2020": 12000, "2021": 14500, "2022": 16200, "2023": 19500, "2024": 22100},
        {"Регіон": "Івано-Франківська",      "2020": 9800,  "2021": 11900, "2022": 13700, "2023": 16200, "2024": 18500},
    ]

MOCK_DATA = _load_mock_data()
YEAR_COLUMNS = ["2020", "2021", "2022", "2023", "2024"]