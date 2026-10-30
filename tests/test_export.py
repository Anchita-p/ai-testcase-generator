import csv
import io

from openpyxl import load_workbook

from testgen.export import COLUMNS, to_csv_bytes, to_excel_bytes, to_rows
from testgen.parsing import parse_suite
from tests.sample_data import VALID_REPLY


def _suite():
    return parse_suite(VALID_REPLY, "User login")


def test_rows_have_one_value_per_column():
    rows = to_rows(_suite())
    assert len(rows) == 3
    assert all(len(r) == len(COLUMNS) for r in rows)


def test_steps_are_numbered_on_separate_lines():
    steps = to_rows(_suite())[0][COLUMNS.index("Steps")]
    assert steps.splitlines() == [
        "1. Open the login page",
        "2. Enter valid email and password",
        "3. Click Login",
    ]


def test_new_cases_start_as_not_run():
    assert {r[COLUMNS.index("Status")] for r in to_rows(_suite())} == {"Not Run"}


def test_csv_has_header_and_all_rows():
    text = to_csv_bytes(_suite()).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == COLUMNS
    assert len(rows) == 4
    assert rows[1][0] == "TC-001"


def test_excel_file_opens_with_formatted_header():
    ws = load_workbook(io.BytesIO(to_excel_bytes(_suite())))["Test Cases"]
    assert [c.value for c in ws[1]] == COLUMNS
    assert ws["A1"].font.bold
    assert ws["A2"].value == "TC-001"
    assert ws.max_row == 4
    assert ws.freeze_panes == "A2"
