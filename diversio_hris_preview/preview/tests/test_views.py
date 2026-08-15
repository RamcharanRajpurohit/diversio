"""View-level smoke tests for the upload and preview flow."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase


HEADER = b"employee_id,employee_name,email,manager_id,manager_email,department\n"


class ImportPreviewViewTests(SimpleTestCase):
    def test_valid_upload_redirects_to_preview_result(self):
        upload = SimpleUploadedFile(
            "hris.csv",
            HEADER + b"ROOT,Root,root@example.com,,,Executive\n",
            content_type="text/csv",
        )

        response = self.client.post("/", {"csv_file": upload}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[0][1], 302)
        self.assertContains(response, "Diversio import preview")
        self.assertContains(response, "source rows")

    def test_missing_required_header_returns_clear_upload_error(self):
        upload = SimpleUploadedFile(
            "bad.csv",
            b"employee_id,email\nROOT,root@example.com\n",
            content_type="text/csv",
        )

        response = self.client.post("/", {"csv_file": upload})

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "missing required columns", status_code=400)
        self.assertContains(response, "manager_id", status_code=400)

    def test_long_result_sections_are_paginated(self):
        rows = [
            f"E{i},Person {i},e{i}@example.com,,,Dept\n".encode()
            for i in range(105)
        ]
        upload = SimpleUploadedFile("many.csv", HEADER + b"".join(rows))

        response = self.client.post("/", {"csv_file": upload}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "roots_page=2")
