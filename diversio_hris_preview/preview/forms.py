from django import forms

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class UploadForm(forms.Form):
    csv_file = forms.FileField(label="HRIS CSV export")

    def clean_csv_file(self):
        """Reject an oversized file before the view spends any time parsing it.

        Parsing is CPU-bound and holds the worker for its whole duration, so
        the cheapest protection is refusing work that is too big to start.
        """
        uploaded = self.cleaned_data["csv_file"]
        if uploaded.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError(
                f"This file is {uploaded.size / 1_048_576:.1f} MB. "
                f"The limit is {MAX_UPLOAD_BYTES // 1_048_576} MB — "
                "split the export and upload it in parts."
            )
        return uploaded
