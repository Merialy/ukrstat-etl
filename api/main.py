"""
Проєкт «Дані» | REST API 
FastAPI + SQLAlchemy (async)
"""

from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# ------ Ініціалізація ------
app = FastAPI(
    title="Укрстат Data API",
    description="Прототип API для доступу до статистичних даних України",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # У продакшені — обмежити конкретними доменами
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
