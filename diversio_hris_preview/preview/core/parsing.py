"""Parse uploaded CSV files and validate employee identity fields.

This module handles normalization, required fields, and duplicate validation.
CSV reading and header setup are in csv_utils.py. Manager relationships are
resolved later in ``hierarchy.py``.
"""

from collections import Counter

from .csv_utils import setup_csv_reader
from .models import CSVFormatError, EmployeeRow, ParseResult, RowError


def _build_employee_row(row, i_id, i_name, i_email, i_mid, i_memail, i_dept, line_number, departments):
    """Build EmployeeRow from CSV row, normalizing values."""
    department = row[i_dept].strip()
    return EmployeeRow(
        line_number,
        row[i_id].strip(),
        row[i_name].strip(),
        row[i_email].strip().lower(),
        row[i_mid].strip(),
        row[i_memail].strip().lower(),
        departments.setdefault(department, department),
    )


def parse_employees(binary_stream) -> ParseResult:
    """Read a CSV upload and return accepted rows plus row-level errors.

    File-level problems raise ``CSVFormatError``. Row-level problems are added
    to the result so valid rows can still be analyzed.
    """
    reader, i_id, i_name, i_email, i_mid, i_memail, i_dept, width = setup_csv_reader(binary_stream)

    total_rows, pending, errors = 0, [], []
    departments: dict[str, str] = {}  # Interned via setdefault: one per department, not per row.
    seen_ids, seen_emails = set(), set()  # Track seen IDs and emails.
    duplicate_ids, duplicate_emails = set(), set()  # Marked when twin appears later.
    previous_line = reader.line_num  # reader.line_num is where record *ended*; keep previous end for error line numbers.
    try:
        for row in reader:
            total_rows += 1
            line_number = previous_line + 1
            previous_line = reader.line_num

            # Wrong column counts usually mean missing values or an unquoted
            # comma. Do not trust shifted fields.
            if len(row) != width:
                errors.append(RowError(
                    line_number, row[i_id].strip() if len(row) > i_id else "",
                    f"Row has {len(row)} values but the header declares {width}. "
                    "Fields may be shifted; check for an unquoted comma."))
                continue

            employee = _build_employee_row(
                row, i_id, i_name, i_email, i_mid, i_memail, i_dept, line_number, departments
            )
            missing_fields = [n for n, v in (("employee_id", employee.employee_id),
                                             ("email", employee.email)) if not v]
            if missing_fields:
                errors.append(RowError(line_number, employee.employee_id,
                                       f"{' and '.join(missing_fields)} is required and was blank."))
                continue
            if employee.employee_id in seen_ids:
                duplicate_ids.add(employee.employee_id)
            else:
                seen_ids.add(employee.employee_id)
            if employee.email in seen_emails:
                duplicate_emails.add(employee.email)
            else:
                seen_emails.add(employee.email)
            pending.append(employee)
    except (csv.Error, UnicodeDecodeError) as exc:
        raise CSVFormatError(f"The file stopped being readable after line {previous_line}: {exc}") from exc

    accepted = _exclude_duplicates(pending, errors, duplicate_ids, duplicate_emails)
    errors.sort(key=lambda error: error.line_number)
    return ParseResult(total_rows=total_rows, employees=accepted, errors=errors)


def _exclude_duplicates(
    pending: list[EmployeeRow],
    errors: list[RowError],
    duplicate_ids: set[str],
    duplicate_emails: set[str],
) -> list[EmployeeRow]:
    """Reject every row that shares a duplicated employee_id or email.
    """
    if not duplicate_ids and not duplicate_emails:
        return pending

    # Counts make the error messages useful: "used by 2 rows", etc.
    id_counts = Counter(r.employee_id for r in pending if r.employee_id in duplicate_ids)
    email_counts = Counter(r.email for r in pending if r.email in duplicate_emails)

    accepted: list[EmployeeRow] = []
    for row in pending:
        reasons = []
        if row.employee_id in duplicate_ids:
            reasons.append(
                f"employee_id {row.employee_id!r} is used by "
                f"{id_counts[row.employee_id]} rows"
            )
        if row.email in duplicate_emails:
            reasons.append(f"email {row.email!r} is used by {email_counts[row.email]} rows")
        if reasons:
            errors.append(
                RowError(
                    row.line_number,
                    row.employee_id,
                    " and ".join(reasons) + ". Every row in a duplicate group is excluded.",
                )
            )
        else:
            accepted.append(row)
    return accepted
