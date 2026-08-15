"""Data shapes shared across the import preview.

This module (and every other module in ``core``) deliberately imports nothing
from Django, so the analysis logic can be tested and reused without a request.
"""

from dataclasses import dataclass, field

# The headers the CSV contract requires. Order in the file does not matter.
REQUIRED_HEADERS = (
    "employee_id",
    "employee_name",
    "email",
    "manager_id",
    "manager_email",
    "department",
)


class CSVFormatError(Exception):
    """The upload could not be read at all, so no rows can be reported."""


@dataclass(slots=True)
class EmployeeRow:
    """One normalized data row, tagged with the line it came from.

    ``slots=True`` removes the per-instance ``__dict__``; at 100k rows that is
    a meaningful chunk of memory for a one-word change.
    """

    line_number: int
    employee_id: str
    employee_name: str
    email: str
    manager_id: str
    manager_email: str
    department: str


@dataclass(slots=True)
class RowError:
    """A problem attributable to a single source row."""

    line_number: int
    employee_id: str
    message: str


@dataclass(slots=True)
class ManagerSummary:
    employee: EmployeeRow
    direct_reports: int


@dataclass(slots=True)
class ParseResult:
    total_rows: int
    employees: list[EmployeeRow] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


@dataclass(slots=True)
class AnalysisResult:
    """Everything the template needs, with no further computation required."""

    total_rows: int
    employees: list[EmployeeRow]
    identity_errors: list[RowError]
    manager_errors: list[RowError]
    roots: list[EmployeeRow]
    managers: list[ManagerSummary]   # the top N only; see manager_count
    manager_count: int
    cyclic_employees: list[EmployeeRow]
    relationships: int
