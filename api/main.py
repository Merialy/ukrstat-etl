"""
Проєкт «Дані» | REST API 
FastAPI + SQLAlchemy (async)
"""

from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query
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

# ------ Хелпери ------
def _get_region_col(record: dict) -> str:
    for key in ("Регіон", "region", "Region"):
        if key in record:
            return record[key]
    return "Невідомо"


def _flatten_to_stats(data: list[dict], years: list[str]) -> list[dict]:
    """Перетворює широкий формат (регіон × роки) у довгий (одна дата = один запис)."""
    result = []
    for row in data:
        region = _get_region_col(row)
        for year in years:
            val = row.get(year)
            result.append({
                "region": region,
                "year": int(year),
                "value": float(val) if val is not None else None,
                "unit": "грн",
            })
    return result


# ------ Ендпоінти ------
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Перевірка стану API """
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/stats", tags=["Statistics"])
def get_stats(
    region: Optional[str] = Query(None, description="Фільтр за назвою регіону (частковий збіг)"),
    year: Optional[int] = Query(None, description="Фільтр за роком (2020-2024)"),
    page: int = Query(1,    ge=1, description="Номер сторінки"),
    per_page: int = Query(20,   ge=1, le=100, description="Записів на сторінці"),
):
    """
    Повертає статистичні дані (середня ЗП по регіонах).

    **Параметри:**
    - `region` — частковий збіг у назві регіону
    - `year` — рік спостереження
    - `page`, `per_page` — пагінація
    """
    stats = _flatten_to_stats(MOCK_DATA, YEAR_COLUMNS)

    # Фільтрація
    if region:
        stats = [s for s in stats if region.lower() in (s["region"] or "").lower()]
    if year:
        stats = [s for s in stats if s["year"] == year]

    total = len(stats)
    start = (page - 1) * per_page
    end   = start + per_page

    return {"total": total,
            "page": page,
            "per_page": per_page,
            "data": stats[start:end],
    }


@app.get("/api/v1/stats/regions", tags=["Statistics"])
def list_regions():
    """Повертає список унікальних регіонів у датасеті."""
    regions = sorted({_get_region_col(r) for r in MOCK_DATA})
    return {"count": len(regions), "regions": regions}


@app.get("/api/v1/stats/summary", tags=["Statistics"])
def get_summary(year: int = Query(2024, description="Рік для підсумкової статистики")):
    """ Зведена статистика за вказаний рік: 
            мін, макс, середнє значення по всіх регіонах """
    year_key = str(year)
    if year_key not in YEAR_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Рік {year} відсутній у датасеті. Доступні: {YEAR_COLUMNS}")

    values = [
        float(r[year_key])
        for r in MOCK_DATA
        if r.get(year_key) is not None
    ]

    if not values:
        raise HTTPException(status_code=404, detail="Немає даних за вказаний рік")

    return {"year": year,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "average": round(sum(values) / len(values), 2),
    }


@app.get("/api/v1/stats/region/{region_name}", tags=["Statistics"])
def get_region_timeseries(region_name: str):
    """ Повертає часовий ряд (2020-2024) для конкретного регіону """
    matches = [r for r in MOCK_DATA if region_name.lower() in _get_region_col(r).lower()]
    if not matches:
        raise HTTPException(status_code=404, detail=f"Регіон '{region_name}' не знайдено")

    row = matches[0]
    timeseries = []
    for year in YEAR_COLUMNS:
        val = row.get(year)
        timeseries.append({
            "year": int(year),
            "value": float(val) if val is not None else None,
        })

    return {"region": _get_region_col(row),
            "indicator": "Середня заробітна плата",
            "unit": "грн",
            "timeseries": timeseries,
    }
