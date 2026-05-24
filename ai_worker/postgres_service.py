import json
from pathlib import Path
from typing import Any

from config import EMPLOYEES_TABLE, POSTGRES_EXPORT_PATH


class PostgresExportService:
    def __init__(self, export_path: Path = POSTGRES_EXPORT_PATH) -> None:
        self.export_path = export_path
        self.tables = self._load_tables()

    def _load_tables(self) -> dict[str, dict[str, Any]]:
        data = json.loads(self.export_path.read_text(encoding="utf-8"))
        return {table["name"]: table for table in data["tables"]}

    def get_employee_by_id(self, employee_id: int) -> dict[str, Any] | None:
        table = self.tables[EMPLOYEES_TABLE]
        for row in table["rows"]:
            if row["id"] == employee_id:
                return row
        return None
