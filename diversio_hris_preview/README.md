# Diversio HRIS Import Preview

A small Django app for previewing a client HRIS CSV before any employee or
reporting data is imported. It reports source row counts, accepted employees,
row-level validation errors, roots, manager direct-report counts, and employees
inside reporting cycles.

No employee data is written to a database.

## Setup

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

Open <http://127.0.0.1:8000/> and upload `data/sample_hris.csv`.

## Tests

```bash
python manage.py test
```

The core parsing and hierarchy tests can also run without Django:

```bash
python -m unittest discover -s preview/tests -t .
```

## Project Structure

```text
config/          Django project settings, URL routing, and WSGI entry point
preview/         Upload form, view, templates, tests, and HRIS analysis code
preview/core/    Pure Python parsing and hierarchy logic
data/            Sample CSV files for manual testing
```

The `preview/core` package deliberately has no Django imports, so the HRIS
rules can be tested directly without driving a browser.

## How It Works

1. The upload view validates the file and passes the binary stream to
   `preview.core.analyzer.analyze`.
2. `parsing.py` reads the CSV with Python's `csv` module, supports UTF-8 with or
   without a byte-order mark, trims values, lowercases emails, validates
   required identity fields, and rejects duplicate employee IDs or emails.
3. `hierarchy.py` builds lookup indexes for accepted employees, resolves manager
   references by ID and/or email, records manager errors, roots, and direct
   report counts.
4. Cycle detection follows each employee's single manager pointer using an
   iterative path walk. When the walk re-enters the current path, only that path
   suffix is marked cyclic, so employees that merely report into a cycle are not
   incorrectly flagged.
5. The result page renders the summary and paginates long tables.

## Complexity

The analysis is O(n) time and O(n) space for n source rows.
(if we ignore the sorting of managers whihc is mlogm where m is the number of managers)

The implementation uses hash maps for duplicate checks and manager lookup.
Cycle detection is also linear because each employee is settled once. The walk
is iterative rather than recursive so a deep reporting chain does not hit
Python's recursion limit.

## Error Handling

File-level problems stop the upload with a clear message:

- empty file
- missing required columns
- unreadable/non-UTF-8 file
- malformed CSV that cannot continue being read

Row-level problems are collected and displayed with source row numbers, while
valid rows continue through analysis:

- blank `employee_id` or `email`
- duplicate employee ID or email
- shifted/ragged rows such as an unquoted comma
- missing manager
- conflicting `manager_id` and `manager_email`
- self-management

## Pagination Trade-Off

The exercise says employee data does not need to be persisted. To support
pagination after upload without adding a database, the app stores preview
results in a short-lived in-memory cache. This is acceptable for a local
exercise. In production, I would move this to a real cache or background job
store with expiry.

## Assumptions

- "Total source rows" means data rows, excluding the header.
- Manager errors do not reject employees. They remain accepted, produce no
  reporting relationship, and are not counted as roots.
- Invalid identity rows are excluded from manager lookup.
- Header names are matched after trimming whitespace.
- Extra unknown columns are ignored.
- Rows with the wrong number of columns are rejected because field positions may
  have shifted.
- A header-only file is valid and reports zero source rows.

## Known Limitations

- The analysis runs synchronously in the web request. For larger production
  uploads, I would use a background job and poll for status.
- The result is held in memory for pagination and expires from the process-local
  cache.
- Only UTF-8 files are supported.
- The UI is intentionally plain HTML.
- Cycle detection identifies employees in cycles. Future improvement: show
  the manager-report chains (manager_id column) so cycle relationships are
  visible without referencing the source CSV.

## Data Files

- `data/sample_hris.csv`: supplied sample file.
- `data/edge_cases.csv`: additional edge cases for manual testing.
- `data/large_hris_100k.csv`: generated local stress-test file, ignored for
  submission.

## Time Spent

Approximately 100 minutes excluding the recording.

I worked in three focused passes: about 40 minutes for the core implementation,
20 minutes for review, testing, and optimization discussion, and 10 minutes for
final cleanup, verification, and small UI/submission polish.
30 minute for slef optimization for code(modulrization/reduce extra loops)

## AI Tools Used

I used Claude Code heavily for the main implementation. I started in plan mode,
then iterated through multiple runs while steering the approach myself. I have
been practicing DSA recently, so I pushed for the hash-map based lookup,
iterative cycle detection, and complexity analysis instead of treating the task
as only a Django form exercise.

I also used AI help to discuss optimization ideas, cross-language benchmarking,
and patterns from ML/data pipelines that looked similar, such as dictionary
encoding and exact-match hashing. I accepted the suggestion to keep the core
parsing and hierarchy logic separate from Django because it made the tests much
cleaner. I rejected adding heavier dependencies such as pandas, polars, or numpy
because the app needs row-level CSV errors and the standard library handled that
more directly for this exercise.

At the end I used Codex for final touch-ups, small UI changes, README cleanup,
and verification.
