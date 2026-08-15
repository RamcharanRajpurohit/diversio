"""Parsing and identity-validation tests.

These import nothing from Django. They exercise the analysis directly, which
keeps them fast and means a failure points at the logic rather than the view.
"""

import io
import unittest

from preview.core.models import CSVFormatError
from preview.core.parsing import parse_employees

HEADER = "employee_id,employee_name,email,manager_id,manager_email,department\n"


def parse(body: str, *, header: str = HEADER, bom: bool = False):
    raw = (header + body).encode("utf-8")
    if bom:
        raw = b"\xef\xbb\xbf" + raw
    return parse_employees(io.BytesIO(raw))


class DuplicateIdentityTests(unittest.TestCase):
    def test_every_row_in_a_duplicate_id_group_is_rejected(self):
        """The contract rejects the whole group, not just the later row.

        This is why duplicate detection needs a counting pass before any row
        can be judged: row 2 is only invalid because of row 3.
        """
        result = parse(
            "DIV-1,Ada,ada@x.com,,,Eng\n"
            "DIV-1,Grace,grace@x.com,,,Eng\n"
            "DIV-2,Alan,alan@x.com,,,Eng\n"
        )

        self.assertEqual(result.total_rows, 3)
        self.assertEqual([e.employee_id for e in result.employees], ["DIV-2"])
        self.assertEqual([e.line_number for e in result.errors], [2, 3])

    def test_duplicate_email_is_detected_after_case_folding(self):
        """Two rows differing only by email case are still the same identity."""
        result = parse(
            "DIV-1,Ada,ada@x.com,,,Eng\n"
            "DIV-2,Grace,ADA@X.COM,,,Eng\n"
        )

        self.assertEqual(result.employees, [])
        self.assertEqual(len(result.errors), 2)


class NormalizationTests(unittest.TestCase):
    def test_values_are_trimmed_emails_lowercased_and_ids_left_alone(self):
        result = parse(
            "  div-1  ,  Ada Lovelace  ,  ADA@X.COM  ,,  BOSS@X.COM  ,  Eng  \n"
            "BOSS,Boss,boss@x.com,,,Eng\n"
        )

        employee = result.employees[0]
        self.assertEqual(employee.employee_id, "div-1")  # case preserved
        self.assertEqual(employee.employee_name, "Ada Lovelace")
        self.assertEqual(employee.email, "ada@x.com")
        self.assertEqual(employee.manager_email, "boss@x.com")
        self.assertEqual(employee.department, "Eng")

    def test_quoted_commas_and_a_byte_order_mark_are_handled(self):
        """Proves real CSV parsing rather than a naive split(',')."""
        result = parse('DIV-1,"Alvarez, Renée",r@x.com,,,Eng\n', bom=True)

        self.assertEqual(result.errors, [])
        self.assertEqual(result.employees[0].employee_name, "Alvarez, Renée")


class RowRejectionTests(unittest.TestCase):
    def test_blank_required_field_is_reported_against_its_source_line(self):
        result = parse(
            "DIV-1,Ada,ada@x.com,,,Eng\n"
            "DIV-2,Grace,,,,Eng\n"
        )

        self.assertEqual([e.employee_id for e in result.employees], ["DIV-1"])
        self.assertEqual(result.errors[0].line_number, 3)
        self.assertIn("email is required", result.errors[0].message)

    def test_line_numbers_survive_a_newline_inside_a_quoted_field(self):
        """csv reports a record's last line, so the start line is tracked instead."""
        result = parse(
            'DIV-1,"Ada\nLovelace",ada@x.com,,,Eng\n'
            "DIV-2,Grace,,,,Eng\n"
        )

        # The second record starts on line 4: header, then a two-line record.
        self.assertEqual(result.errors[0].line_number, 4)

    def test_unquoted_comma_shifts_the_row_and_is_rejected(self):
        """The commonest real-world CSV defect. Reading the shifted values as
        though they were correct would import a department into the email
        column, so the row is refused instead."""
        result = parse("DIV-1,Alvarez, Renee,r@x.com,,,Eng\n")

        self.assertEqual(result.employees, [])
        self.assertIn("unquoted comma", result.errors[0].message)


class UnreadableFileTests(unittest.TestCase):
    def test_missing_column_names_the_column(self):
        with self.assertRaises(CSVFormatError) as caught:
            parse("DIV-1,Ada,ada@x.com\n", header="employee_id,employee_name,email\n")

        self.assertIn("manager_id", str(caught.exception))

    def test_non_utf8_bytes_raise_a_format_error_not_a_traceback(self):
        raw = HEADER.encode() + b"DIV-1,Jos\xe9,j@x.com,,,Eng\n"

        with self.assertRaises(CSVFormatError):
            parse_employees(io.BytesIO(raw))

    def test_empty_file_is_rejected(self):
        with self.assertRaises(CSVFormatError):
            parse_employees(io.BytesIO(b""))


if __name__ == "__main__":
    unittest.main()
