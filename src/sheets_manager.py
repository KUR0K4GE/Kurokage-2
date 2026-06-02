"""Google Sheets integration for reading and updating the 30-day content planogram.

Spreadsheet expected column layout (1-indexed, starting at row 2 after header):
  A: Día       — integer 1-30
  B: Título    — post title / main hook
  C: Hook      — slide 1 text (attention-grabber)
  D: Slide_2   — content slide 2
  E: Slide_3   — content slide 3
  F: Slide_4   — content slide 4
  G: Slide_5   — content slide 5
  H: CTA       — call-to-action text for last slide
  I: Estado    — "Sí" when published, empty otherwise

Authentication uses a Google service account JSON key.
Grant the service account email view+edit access to the spreadsheet.
"""

import logging
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_COL = {
    "dia": 0,
    "titulo": 1,
    "slide_1": 2,
    "slide_2": 3,
    "slide_3": 4,
    "slide_4": 5,
    "slide_5": 6,
    "cta": 7,
    "estado": 8,
}

_PUBLISHED_MARKER = "Sí"
_RANGE = "A:I"


class SheetsManager:
    def __init__(self, credentials_path: str, spreadsheet_id: str, tab_name: str):
        self._spreadsheet_id = spreadsheet_id
        self._tab_name = tab_name
        self._service = self._build_service(credentials_path)

    # ── public API ────────────────────────────────────────────────────────────

    def get_day_content(self, day: int) -> Optional[dict]:
        """Return parsed planogram data for *day*, or None if no matching row found.

        Raises RuntimeError if the Sheets API call fails.
        """
        rows = self._fetch_all_rows()
        for sheet_row_index, row in enumerate(rows, start=1):
            try:
                if int(self._cell(row, "dia")) == day:
                    return self._parse_row(row, sheet_row_index)
            except (ValueError, IndexError):
                continue
        log.warning("No planogram row found for day %d", day)
        return None

    def mark_as_published(self, sheet_row: int) -> None:
        """Write the published marker to the Estado column for the given 1-indexed row."""
        col_letter = chr(ord("A") + _COL["estado"])
        range_name = f"{self._tab_name}!{col_letter}{sheet_row}"
        try:
            self._service.spreadsheets().values().update(
                spreadsheetId=self._spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": [[_PUBLISHED_MARKER]]},
            ).execute()
            log.info("Row %d marked as published in Sheets", sheet_row)
        except HttpError as exc:
            raise RuntimeError(f"Failed to update Estado in row {sheet_row}: {exc}") from exc

    # ── private helpers ───────────────────────────────────────────────────────

    def _build_service(self, credentials_path: str):
        try:
            creds = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=_SCOPES
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Service account file not found: {credentials_path}\n"
                "Set GOOGLE_CREDENTIALS_PATH in your .env file."
            ) from exc
        return build("sheets", "v4", credentials=creds, cache_discovery=False)

    def _fetch_all_rows(self) -> list[list[str]]:
        range_name = f"{self._tab_name}!{_RANGE}"
        try:
            result = (
                self._service.spreadsheets()
                .values()
                .get(spreadsheetId=self._spreadsheet_id, range=range_name)
                .execute()
            )
        except HttpError as exc:
            raise RuntimeError(f"Failed to read spreadsheet {self._spreadsheet_id}: {exc}") from exc

        rows: list[list[str]] = result.get("values", [])
        # Skip the header row (first row assumed to contain column labels)
        return rows[1:] if rows else []

    def _parse_row(self, row: list[str], sheet_row: int) -> dict:
        slides = [
            self._cell(row, f"slide_{n}")
            for n in range(1, 6)
            if self._cell(row, f"slide_{n}")
        ]
        estado = self._cell(row, "estado")
        return {
            "dia": int(self._cell(row, "dia")),
            "titulo": self._cell(row, "titulo"),
            "slides": slides,
            "cta": self._cell(row, "cta"),
            "estado": estado,
            "published": estado.lower() in ("sí", "si", "yes", "true", "1"),
            "sheet_row": sheet_row + 1,  # +1 to account for the skipped header row
        }

    @staticmethod
    def _cell(row: list[str], column: str) -> str:
        idx = _COL[column]
        return row[idx].strip() if idx < len(row) else ""
