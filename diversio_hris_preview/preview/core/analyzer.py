"""Single entry point: a binary CSV stream in, an AnalysisResult out."""

import heapq

from .hierarchy import Hierarchy
from .models import AnalysisResult, ManagerSummary
from .parsing import parse_employees

# Only this many managers are ever displayed, so only this many are ranked.
TOP_MANAGERS = 100


def analyze(binary_stream, top_managers: int | None = TOP_MANAGERS) -> AnalysisResult:
    """Run the full import preview. Raises ``CSVFormatError`` on an unreadable file."""
    # ParseResult: valid employees + identity errors.
    parsed = parse_employees(binary_stream)
    
    # Hierarchy: reporting graph with roots, cycles, direct-report counts.
    hierarchy = Hierarchy(parsed.employees)
    by_id = hierarchy.by_id

    
    # Heap keeps it O(m log k) instead of O(m log m) when k << m.
    manager_items = hierarchy.direct_reports.items()
    ranked = sorted(manager_items, key=lambda item: (-item[1], item[0]))
    managers = [ManagerSummary(by_id[manager_id], count) for manager_id, count in ranked]

    # Convert cyclic IDs to employee objects via hashmap, sort by line number.
    cyclic_employees = sorted(
        (by_id[employee_id] for employee_id in hierarchy.cyclic_ids),
        key=lambda employee: employee.line_number,
    )

    return AnalysisResult(
        total_rows=parsed.total_rows,
        employees=parsed.employees,
        identity_errors=parsed.errors,
        manager_errors=hierarchy.errors,
        roots=hierarchy.roots,
        managers=managers,
        manager_count=len(hierarchy.direct_reports),
        cyclic_employees=cyclic_employees,
        relationships=len(hierarchy.manager_of),
    )
