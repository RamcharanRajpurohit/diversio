"""CSV reading and header validation utilities."""

import csv
import io

from .models import REQUIRED_HEADERS, CSVFormatError


def setup_csv_reader(binary_stream):
    """Open CSV stream and read + validate headers, return reader and column info.

    Raises CSVFormatError if file is unreadable or headers are missing.
    """
    text_stream = io.TextIOWrapper(binary_stream, encoding="utf-8-sig", newline="")
    reader = csv.reader(text_stream)

    try:
        header_row = next(reader)
    except StopIteration:
        raise CSVFormatError("The file is empty. Upload a CSV that has a header row.")
    except (csv.Error, UnicodeDecodeError) as exc:
        raise CSVFormatError(f"The header row could not be read: {exc}") from exc

    headers = [h.strip() for h in header_row]
    missing = [n for n in REQUIRED_HEADERS if n not in headers]
    if missing:
        raise CSVFormatError("The file is missing required columns: " + ", ".join(missing))

    i_id, i_name, i_email, i_mid, i_memail, i_dept = (headers.index(c) for c in REQUIRED_HEADERS)
    width = len(headers)

    return reader, i_id, i_name, i_email, i_mid, i_memail, i_dept, width
