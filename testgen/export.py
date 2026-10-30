"""Export a test suite to CSV or a formatted Excel sheet (the format QA teams actually use)."""
import csv
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from testgen.schema import TestSuite

COLUMNS = [
    "ID", "Title", "Requirement", "Type", "Priority",
    "Preconditions", "Steps", "Test Data", "Expected Result", "Status",
]
WIDTHS = [9, 32, 28, 11, 10, 26, 48, 24, 38, 10]


def to_rows(suite: TestSuite) -> list[list[str]]:
    rows = []
    for c in suite.test_cases:
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(c.steps, start=1))
        rows.append([
            c.id, c.title, c.requirement, c.type, c.priority,
            c.preconditions, steps, c.test_data, c.expected_result, "Not Run",
        ])
    return rows


def to_csv_bytes(suite: TestSuite) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS)
    writer.writerows(to_rows(suite))
    return buffer.getvalue().encode("utf-8-sig")  # BOM so Excel opens it correctly


def to_excel_bytes(suite: TestSuite) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Test Cases"
    ws.append(COLUMNS)
    for row in to_rows(suite):
        ws.append(row)

    header_fill = PatternFill("solid", fgColor="0B2E59")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for i, width in enumerate(WIDTHS):
        ws.column_dimensions[chr(ord("A") + i)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
