"""Resolve manager references and analyse the resulting reporting graph."""

from collections import Counter

from .models import EmployeeRow, RowError


class Hierarchy:
    """The reporting graph built from identity-valid employees.

    Only accepted employees are indexed, so a manager reference pointing at a
    row that failed identity validation correctly resolves to "not found"
    rather than silently picking one of the duplicates.
    """

    def __init__(self, employees: list[EmployeeRow]):
        
        #hashmap/dict by mail and employee id for O(1) lookups
        self.by_id = {employee.employee_id: employee for employee in employees}
        self._by_email = {employee.email: employee for employee in employees}


        #child->parent(manager) relation 
        self.manager_of: dict[str, str] = {}

        #to store the top
        self.roots: list[EmployeeRow] = []

        self.errors: list[RowError] = []

        #keep the count of mangers total reporters
        self.direct_reports: Counter[str] = Counter()

        for employee in employees:
            self._apply_manager_resolution(employee)

        self.cyclic_ids = self._find_cycle_members()

    def _apply_manager_resolution(self, employee: EmployeeRow) -> None:
        """Resolve manager and apply to errors, roots, or manager_of."""
        manager_id, problem = self._resolve_manager(employee)
        if problem:
            self.errors.append(RowError(employee.line_number, employee.employee_id, problem))
        elif manager_id:
            self.manager_of[employee.employee_id] = manager_id
            self.direct_reports[manager_id] += 1
        else:
            self.roots.append(employee)

    def _resolve_manager(self, employee: EmployeeRow) -> tuple[str | None, str | None]:
        """Return ``(manager_employee_id, error)``, both optionally None.

        ``(None, None)`` means the employee is a root. An error means the row
        stays accepted but produces no reporting relationship.
        """
        from_id = from_email = None

        if employee.manager_id:
            manager = self.by_id.get(employee.manager_id)
            if manager is None:
                return None, (
                    f"manager_id {employee.manager_id!r} does not match any "
                    "employee accepted for analysis."
                )
            from_id = manager.employee_id

        if employee.manager_email:
            manager = self._by_email.get(employee.manager_email)
            if manager is None:
                return None, (
                    f"manager_email {employee.manager_email!r} does not match any "
                    "employee accepted for analysis."
                )
            from_email = manager.employee_id

        if from_id is not None and from_email is not None and from_id != from_email:
            return None, (
                f"manager_id points to {from_id} but manager_email points to "
                f"{from_email}. The two references must identify one employee."
            )

        manager_id = from_id if from_id is not None else from_email
        if manager_id is None:
            return None, None
        if manager_id == employee.employee_id:
            return None, "Employee is listed as their own manager."
        return manager_id, None

    def _find_cycle_members(self) -> set[str]:
        """Return the ids of employees that sit *inside* a reporting cycle.

        Every employee has at most one manager, so this is a functional graph:
        each component is a tail feeding into at most one cycle. That removes
        the need for a general SCC algorithm — following the single manager
        pointer is enough.

        The walk is iterative on purpose. A recursive version would raise
        RecursionError on a chain deeper than ~1000, which a 100k-employee org
        can easily produce.

        ``state`` does double duty: while a node is on the current path it
        holds that node's index in the path, and once the node is settled it
        holds -1. Storing the index in the state map rather than a second
        dictionary halves the bookkeeping per node.

        Each node is walked at most once before being settled, so the outer
        loop plus every inner walk together visit each node once: O(n).
        """
        state: dict[str, int] = {}
        cyclic: set[str] = set()

        for start in self.manager_of:
            if start in state:
                continue

            path: list[str] = []
            node = start

            while node is not None and node not in state:
                state[node] = len(path)
                path.append(node)
                node = self.manager_of.get(node)

            # A non-negative state means we re-entered the path we are walking
            # right now, and the stored value is where that node sits in it.
            # The cycle is exactly the path from there on; anything before it
            # merely reports into the cycle and is not itself cyclic.
            if node is not None and state[node] >= 0:
                cyclic.update(path[state[node]:])

            for visited in path:
                state[visited] = -1

        return cyclic
