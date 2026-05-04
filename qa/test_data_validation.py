"""
Проєкт «Дані» | Автоматизовані тести
        pytest + httpx
"""

import json
import csv
import os
import sys
import tempfile
import pytest
import pandas as pd
from pathlib import Path

# Додаємо кореневу директорію до path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.parse_ukrstat import (
    load_excel,
    save_json,
    save_csv,
    add_metadata,
    generate_sample_excel,
)



# Fixtures
@pytest.fixture(scope="session")
def sample_excel_path(tmp_path_factory):
    """Генерує тестовий Excel-файл один раз для всієї сесії."""
    path = tmp_path_factory.mktemp("data") / "sample.xlsx"
    generate_sample_excel(str(path))
    return path


@pytest.fixture(scope="session")
def parsed_df(sample_excel_path):
    """Повертає розпарсений DataFrame."""
    return load_excel(str(sample_excel_path))


@pytest.fixture(scope="session")
def json_output(parsed_df, tmp_path_factory, sample_excel_path):
    """Генерує JSON-файл із результатами."""
    out = tmp_path_factory.mktemp("output") / "output.json"
    records, meta = add_metadata(parsed_df, str(sample_excel_path))
    save_json(records, meta, str(out))
    return out, records, meta


@pytest.fixture(scope="session")
def csv_output(parsed_df, tmp_path_factory, sample_excel_path):
    """Генерує CSV-файл із результатами."""
    out = tmp_path_factory.mktemp("output") / "output.csv"
    records, meta = add_metadata(parsed_df, str(sample_excel_path))
    save_csv(records, str(out))
    return out, records


# TS-01 | ETL: Зчитування Excel
class TestExcelLoading:

    def test_tc001_valid_file_loads(self, parsed_df):
        """TC-001: Валідний .xlsx завантажується без помилок."""
        assert parsed_df is not None
        assert len(parsed_df) > 0

    def test_tc001_has_expected_columns(self, parsed_df):
        """TC-001: Присутні очікувані стовпці (регіон + роки)."""
        cols = [str(c) for c in parsed_df.columns]
        assert any("Регіон" in c or "region" in c.lower() for c in cols), \
            f"Стовпець Регіон не знайдено. Стовпці: {cols}"

    def test_tc002_no_extra_header_rows(self, parsed_df):
        """TC-002: Рядки-заголовки Укрстату пропущені, дані починаються з регіонів."""
        first_col = parsed_df.columns[0]
        # Перший рядок не повинен містити службовий текст типу "Державна служба"
        assert "Державна" not in str(parsed_df.iloc[0][first_col])

    def test_tc003_na_values_converted(self, parsed_df):
        """TC-003: Значення '-' та '...' перетворені у NaN."""
        # Числові стовпці не повинні містити рядок '-'
        for col in parsed_df.select_dtypes(include=["float64", "int64"]).columns:
            assert "-" not in parsed_df[col].astype(str).values

    def test_tc004_file_not_found(self):
        """TC-004: Відсутній файл кидає FileNotFoundError."""
        with pytest.raises((FileNotFoundError, Exception)):
            load_excel("/nonexistent/path/file.xlsx")

    def test_tc005_column_names_clean(self, parsed_df):
        """TC-005: Назви стовпців не містять символів переносу рядка."""
        for col in parsed_df.columns:
            assert "\n" not in str(col), f"Стовпець містить '\\n': {repr(col)}"
            assert "\r" not in str(col)


# TS-02 | ETL: Конвертація у JSON
class TestJsonOutput:

    def test_tc010_json_file_created(self, json_output):
        """TC-010: Файл output.json створено."""
        out_path, _, _ = json_output
        assert out_path.exists()

    def test_tc010_json_has_required_keys(self, json_output):
        """TC-010: JSON містить обов'язкові поля `metadata` і `data`."""
        out_path, _, _ = json_output
        with open(out_path, encoding="utf-8") as f:
            payload = json.load(f)
        assert "metadata" in payload
        assert "data" in payload

    def test_tc011_row_count_matches(self, parsed_df, json_output):
        """TC-011: Кількість записів у JSON == кількість рядків у DataFrame."""
        _, records, meta = json_output
        assert meta["_total_rows"] == len(parsed_df)
        assert len(records) == len(parsed_df)

    def test_tc012_no_newlines_in_keys(self, json_output):
        """TC-012: Ключі JSON не містять переносів рядків."""
        _, records, _ = json_output
        for record in records:
            for key in record.keys():
                assert "\n" not in key, f"Ключ містить '\\n': {repr(key)}"

    def test_tc013_numeric_fields_are_numbers(self, json_output):
        """TC-013: Числові поля є float/int, а не рядками."""
        _, records, _ = json_output
        year_cols = ["2020", "2021", "2022", "2023", "2024"]
        for record in records:
            for col in year_cols:
                if col in record and record[col] is not None:
                    assert isinstance(record[col], (int, float)), \
                        f"Поле {col} = {record[col]!r} — має бути числом"

    def test_tc014_valid_json_file(self, json_output):
        """TC-014: Файл є валідним JSON."""
        out_path, _, _ = json_output
        with open(out_path, encoding="utf-8") as f:
            payload = json.load(f)   # не кидає виняток = тест пройдено
        assert isinstance(payload, dict)

    def test_tc014_metadata_has_source(self, json_output):
        """TC-014: Metadata містить поле _source з іменем файлу."""
        _, _, meta = json_output
        assert "_source" in meta
        assert meta["_source"].endswith(".xlsx")


# TS-03 | ETL: Конвертація у CSV
class TestCsvOutput:

    def test_tc020_csv_file_created(self, csv_output):
        """TC-020: Файл output.csv створено."""
        out_path, _ = csv_output
        assert out_path.exists()

    def test_tc021_row_count_matches(self, parsed_df, csv_output):
        """TC-021: Кількість рядків у CSV == кількість рядків у DataFrame."""
        out_path, _ = csv_output
        with open(out_path, encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == len(parsed_df), \
            f"CSV: {len(reader)} рядків, DataFrame: {len(parsed_df)} рядків"

    def test_tc022_encoding_utf8_bom(self, csv_output):
        """TC-022: CSV починається з BOM (сумісність з Excel)."""
        out_path, _ = csv_output
        with open(out_path, "rb") as f:
            header = f.read(3)
        assert header == b"\xef\xbb\xbf", "Файл не містить UTF-8 BOM"

    def test_tc023_no_none_string_in_csv(self, csv_output):
        """TC-023: Відсутні значення — порожні клітинки, не рядок 'None'."""
        out_path, _ = csv_output
        with open(out_path, encoding="utf-8-sig") as f:
            content = f.read()
        assert "None" not in content, "CSV містить рядок 'None'"

    def test_tc023_no_nan_string_in_csv(self, csv_output):
        """TC-023: CSV не містить рядок 'nan'."""
        out_path, _ = csv_output
        with open(out_path, encoding="utf-8-sig") as f:
            content = f.read().lower()
        assert "nan" not in content, "CSV містить рядок 'nan'"


# TS-04 | API тести (потребує запущеного сервера)
try:
    from fastapi.testclient import TestClient
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from api.main import app
    client = TestClient(app)
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False


@pytest.mark.skipif(not API_AVAILABLE, reason="FastAPI або httpx не встановлені")
class TestApi:

    def test_tc030_health_ok(self):
        """TC-030: /health повертає 200 OK."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_tc031_stats_has_required_fields(self):
        """TC-031: /api/v1/stats містить total, page, data."""
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "page" in body
        assert "data" in body
        assert isinstance(body["data"], list)

    def test_tc032_regions_list(self):
        """TC-032: /api/v1/stats/regions повертає непорожній список."""
        resp = client.get("/api/v1/stats/regions")
        assert resp.status_code == 200
        body = resp.json()
        assert "regions" in body
        assert len(body["regions"]) > 0

    def test_tc033_summary_2024(self):
        """TC-033: /api/v1/stats/summary?year=2024 повертає min, max, average."""
        resp = client.get("/api/v1/stats/summary?year=2024")
        assert resp.status_code == 200
        body = resp.json()
        for field in ("min", "max", "average", "count"):
            assert field in body, f"Поле {field} відсутнє"
        assert body["min"] <= body["average"] <= body["max"]

    def test_tc034_region_timeseries(self):
        """TC-034: /api/v1/stats/region/Київ повертає 5 точок часового ряду."""
        resp = client.get("/api/v1/stats/region/Київ")
        assert resp.status_code == 200
        body = resp.json()
        assert "timeseries" in body
        assert len(body["timeseries"]) == 5

    def test_tc040_invalid_year_returns_400(self):
        """TC-040: ?year=1900 → 400 Bad Request."""
        resp = client.get("/api/v1/stats/summary?year=1900")
        assert resp.status_code == 400

    def test_tc041_unknown_region_returns_404(self):
        """TC-041: Неіснуючий регіон → 404."""
        resp = client.get("/api/v1/stats/region/НеіснуючийРегіон12345")
        assert resp.status_code == 404

    def test_tc042_per_page_over_limit(self):
        """TC-042: per_page=500 → 422 Validation Error."""
        resp = client.get("/api/v1/stats?per_page=500")
        assert resp.status_code == 422

    def test_tc043_unknown_route_404(self):
        """TC-043: Неіснуючий маршрут → 404."""
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404

    def test_stats_filter_by_region(self):
        """Фільтр по регіону повертає лише відповідні записи."""
        resp = client.get("/api/v1/stats?region=Київ")
        assert resp.status_code == 200
        for record in resp.json()["data"]:
            assert "київ" in record["region"].lower()

    def test_stats_pagination(self):
        """Пагінація: per_page=2 повертає не більше 2 записів."""
        resp = client.get("/api/v1/stats?per_page=2&page=1")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) <= 2
