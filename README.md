# Проєкт «Дані» — Прототип

Перетворення статистичних таблиць Укрстату (Excel/PDF) у машинночитний формат + REST API.

---

## Структура репозиторію

```
ukrstat-data/
├── scripts/
│   └── parse_ukrstat.py      # ETL: Excel → JSON + CSV
├── db/
│   └── schema.sql            # Схема PostgreSQL
├── api/
│   └── main.py               # REST API (FastAPI)
├── qa/
│   ├── test_plan.md          # Тест-план
│   └── test_data_validation.py  # pytest-тести
├── data/                     # Генерується автоматично
│   ├── sample_ukrstat.xlsx
│   ├── output.json
│   └── output.csv
└── README.md
```
---

## Швидкий старт

### 1. Встановлення залежностей
```bash
pip install pandas openpyxl fastapi uvicorn httpx pytest
```

### 2. Запуск ETL-скрипту (генерує демо-дані)
```bash
python scripts/parse_ukrstat.py
# → data/output.json та data/output.csv
```

### 3. Запуск API
```bash
python -m venv venv
.\venv\Scripts\activate
pip install fastapi uvicorn sqlalchemy asyncpg
uvicorn api.main:app --reload
# Документація: http://localhost:8000/docs
```

### 4. Запуск тестів
```bash
pip install pytest httpx pandas openpyxl fastapi
pytest qa/test_data_validation.py -v
```
---

## API Ендпоінти

| Метод | Маршрут | Опис |
|-------|---------|------|
| GET | `/health` | Стан сервісу |
| GET | `/api/v1/stats` | Всі значення (пагінація, фільтр) |
| GET | `/api/v1/stats/regions` | Список регіонів |
| GET | `/api/v1/stats/summary?year=2024` | Мін/макс/середнє за рік |
| GET | `/api/v1/stats/region/{name}` | Часовий ряд регіону |
---

## Схема бази даних

```
regions ──────────┐
                  ▼
indicators ──→ stat_values ←── import_logs
    ▲               ▲
indicator_categories  units
```
---

## Наступні кроки

- [ ] Підключити реальну PostgreSQL замість mock-даних
- [ ] Додати парсер PDF-таблиць (pdfplumber)
- [ ] Реалізувати автоматичне завантаження нових файлів з ukrstat.gov.ua
- [ ] Інтеграція з дашбордом (Grafana або власний frontend)
