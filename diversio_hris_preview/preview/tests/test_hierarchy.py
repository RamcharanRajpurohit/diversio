"""Manager resolution and reporting-cycle tests."""

import io
import unittest

from preview.core.analyzer import analyze

HEADER = "employee_id,employee_name,email,manager_id,manager_email,department\n"


def run(body: str):
    return analyze(io.BytesIO((HEADER + body).encode("utf-8")))


class ManagerResolutionTests(unittest.TestCase):
    def test_manager_found_by_email_regardless_of_case(self):
        result = run(
            "BOSS,Boss,boss@x.com,,,Eng\n"
            "DIV-1,Ada,ada@x.com,,BOSS@X.COM,Eng\n"
        )

        self.assertEqual(result.manager_errors, [])
        self.assertEqual(result.relationships, 1)
        self.assertEqual(result.managers[0].employee.employee_id, "BOSS")

    def test_manager_may_be_defined_after_the_employee_who_reports_to_them(self):
        """Both indexes are built before any reference is resolved."""
        result = run(
            "DIV-1,Ada,ada@x.com,BOSS,,Eng\n"
            "BOSS,Boss,boss@x.com,,,Eng\n"
        )

        self.assertEqual(result.manager_errors, [])
        self.assertEqual(result.relationships, 1)

    def test_conflicting_references_keep_the_employee_but_drop_the_edge(self):
        """A manager error is not the same as a rejected employee, and it is
        not a root either — all three states have to be checked."""
        result = run(
            "A,Alpha,a@x.com,,,Eng\n"
            "B,Beta,b@x.com,,,Eng\n"
            "DIV-1,Ada,ada@x.com,A,b@x.com,Eng\n"
        )

        self.assertEqual(len(result.employees), 3)          # still accepted
        self.assertEqual(len(result.manager_errors), 1)
        self.assertEqual(result.relationships, 0)           # no edge produced
        self.assertNotIn("DIV-1", [e.employee_id for e in result.roots])
        # The error names both candidates so a reviewer can see the disagreement.
        message = result.manager_errors[0].message
        self.assertIn("A", message)
        self.assertIn("B", message)

    def test_reference_to_an_identity_rejected_row_is_not_found(self):
        """Duplicated rows are excluded from the lookup indexes, so pointing at
        one must fail rather than silently binding to an arbitrary duplicate."""
        result = run(
            "DUP,First,first@x.com,,,Eng\n"
            "DUP,Second,second@x.com,,,Eng\n"
            "DIV-1,Ada,ada@x.com,DUP,,Eng\n"
        )

        self.assertEqual(len(result.identity_errors), 2)
        self.assertEqual(len(result.manager_errors), 1)
        self.assertIn("does not match", result.manager_errors[0].message)

    def test_self_management_is_an_error_and_not_a_root(self):
        result = run("DIV-1,Ada,ada@x.com,DIV-1,,Eng\n")

        self.assertEqual(result.roots, [])
        self.assertEqual(len(result.manager_errors), 1)
        self.assertEqual(result.cyclic_employees, [])

    def test_blank_manager_fields_make_a_root(self):
        result = run("DIV-1,Ada,ada@x.com,   ,   ,Eng\n")

        self.assertEqual([e.employee_id for e in result.roots], ["DIV-1"])


class CycleDetectionTests(unittest.TestCase):
    def test_only_cycle_members_are_flagged_not_the_tail_reporting_into_it(self):
        """The behaviour the spec calls out explicitly.

        T1 -> T2 -> C1 -> C2 -> C3 -> C1. Only C1..C3 are members; the tail
        reaches the cycle but is not part of it.
        """
        result = run(
            "T1,Tail One,t1@x.com,T2,,Eng\n"
            "T2,Tail Two,t2@x.com,C1,,Eng\n"
            "C1,Cycle One,c1@x.com,C2,,Eng\n"
            "C2,Cycle Two,c2@x.com,C3,,Eng\n"
            "C3,Cycle Three,c3@x.com,C1,,Eng\n"
        )

        self.assertEqual(
            sorted(e.employee_id for e in result.cyclic_employees), ["C1", "C2", "C3"]
        )
        self.assertEqual(result.roots, [])

    def test_two_independent_cycles_are_both_found(self):
        result = run(
            "A1,A One,a1@x.com,A2,,Eng\n"
            "A2,A Two,a2@x.com,A1,,Eng\n"
            "B1,B One,b1@x.com,B2,,Eng\n"
            "B2,B Two,b2@x.com,B3,,Eng\n"
            "B3,B Three,b3@x.com,B1,,Eng\n"
        )

        self.assertEqual(
            sorted(e.employee_id for e in result.cyclic_employees),
            ["A1", "A2", "B1", "B2", "B3"],
        )

    def test_a_clean_tree_reports_no_cycles(self):
        result = run(
            "ROOT,Root,root@x.com,,,Exec\n"
            "MID,Mid,mid@x.com,ROOT,,Eng\n"
            "LEAF,Leaf,leaf@x.com,MID,,Eng\n"
        )

        self.assertEqual(result.cyclic_employees, [])
        self.assertEqual([e.employee_id for e in result.roots], ["ROOT"])
        self.assertEqual(result.relationships, 2)

    def test_deep_chain_does_not_hit_the_recursion_limit(self):
        """A recursive walk would raise RecursionError well before 5,000."""
        rows = "ROOT,Root,root@x.com,,,Eng\n" + "".join(
            f"E{i},Person {i},e{i}@x.com,{'ROOT' if i == 0 else f'E{i - 1}'},,Eng\n"
            for i in range(5000)
        )
        result = run(rows)

        self.assertEqual(result.cyclic_employees, [])
        self.assertEqual(result.relationships, 5000)


if __name__ == "__main__":
    unittest.main()
