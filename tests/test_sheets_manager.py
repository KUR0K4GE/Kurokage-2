"""Unit tests for SheetsManager — Google API calls are fully mocked."""

import pytest
from unittest.mock import MagicMock, patch, call

from src.sheets_manager import SheetsManager, _PUBLISHED_MARKER


FAKE_CREDENTIALS = "config/fake_service_account.json"
FAKE_SHEET_ID = "fake_sheet_id_1234"
FAKE_TAB = "Planograma"


def _make_manager(mock_service: MagicMock) -> SheetsManager:
    with patch("src.sheets_manager.service_account.Credentials.from_service_account_file"), \
         patch("src.sheets_manager.build", return_value=mock_service):
        return SheetsManager(FAKE_CREDENTIALS, FAKE_SHEET_ID, FAKE_TAB)


def _mock_rows(*rows) -> MagicMock:
    """Build a mock Sheets API response with the given rows (header already excluded)."""
    service = MagicMock()
    values = service.spreadsheets.return_value.values.return_value
    # _fetch_all_rows slices off index 0 (header), so we prepend a dummy header
    values.get.return_value.execute.return_value = {
        "values": [["Día", "Título", "Hook", "S2", "S3", "S4", "S5", "CTA", "Estado"], *rows]
    }
    return service


class TestGetDayContent:
    def test_returns_correct_day(self):
        row = ["3", "Título Test", "Hook aquí", "Slide 2", "Slide 3", "", "", "Síguenos", ""]
        manager = _make_manager(_mock_rows(row))
        content = manager.get_day_content(3)

        assert content is not None
        assert content["dia"] == 3
        assert content["titulo"] == "Título Test"
        assert content["slides"] == ["Hook aquí", "Slide 2", "Slide 3"]
        assert content["cta"] == "Síguenos"
        assert content["published"] is False

    def test_returns_none_for_missing_day(self):
        row = ["1", "Día uno", "Hook", "", "", "", "", "CTA", ""]
        manager = _make_manager(_mock_rows(row))
        assert manager.get_day_content(99) is None

    def test_published_flag_set_for_si(self):
        for marker in ("Sí", "Si", "si", "sí", "yes"):
            row = ["5", "T", "H", "", "", "", "", "C", marker]
            manager = _make_manager(_mock_rows(row))
            content = manager.get_day_content(5)
            assert content["published"] is True, f"Expected published=True for marker '{marker}'"

    def test_skips_non_numeric_rows(self):
        rows = [
            ["Subtítulo", "extra header", "", "", "", "", "", "", ""],
            ["2", "Día dos", "Hook", "", "", "", "", "CTA", ""],
        ]
        manager = _make_manager(_mock_rows(*rows))
        content = manager.get_day_content(2)
        assert content is not None
        assert content["titulo"] == "Día dos"

    def test_sheet_row_accounts_for_header(self):
        row = ["7", "T", "H", "", "", "", "", "C", ""]
        manager = _make_manager(_mock_rows(row))
        content = manager.get_day_content(7)
        # The data row is at position 1 in the raw sheet (after header at position 0 = row 1)
        # _parse_row receives sheet_row_index=1 (enumerate starts at 1), then adds +1 for header
        assert content["sheet_row"] == 2

    def test_raises_on_api_error(self):
        from googleapiclient.errors import HttpError
        from unittest.mock import Mock
        service = MagicMock()
        resp = Mock()
        resp.status = 403
        resp.reason = "Forbidden"
        service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect = HttpError(resp, b"forbidden")
        manager = _make_manager(service)
        with pytest.raises(RuntimeError, match="Failed to read spreadsheet"):
            manager.get_day_content(1)


class TestMarkAsPublished:
    def test_writes_correct_cell(self):
        service = MagicMock()
        service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {"values": []}
        manager = _make_manager(service)

        manager.mark_as_published(sheet_row=5)

        update_mock = service.spreadsheets.return_value.values.return_value.update
        update_mock.assert_called_once()
        call_kwargs = update_mock.call_args.kwargs
        assert call_kwargs["range"] == f"{FAKE_TAB}!I5"
        assert call_kwargs["body"] == {"values": [[_PUBLISHED_MARKER]]}
