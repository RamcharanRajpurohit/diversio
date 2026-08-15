# Running the benchmarks

Everything in `benchmarks/` and `verify/` is exploration, not part of the
submission. Delete both folders before sending the exercise.

## Just the application

```bash
pip install -r requirements.txt
python manage.py runserver          # then open http://127.0.0.1:8000/
python manage.py test               # 20 tests
```

Upload `data/sample_hris.csv`. Expect 25 rows, 25 accepted, 1 root,
22 relationships, 2 manager errors, 3 employees in a cycle.

## Everything at once

```bash
bash benchmarks/run_all.sh
```

Runs the tests, the correctness cross-check, generates the 100k fixture if
missing, compiles whichever of C++/Go/Rust you have, and runs the interleaved
cross-language benchmark. Anything without a compiler installed is skipped
cleanly.

Optional compilers:

```bash
sudo apt-get install -y g++ golang-go rustc      # Debian/Ubuntu
brew install gcc go rust                          # macOS
```

Optional Python extras, only for two of the experiments:

```bash
pip install numpy pandas polars
```

## Pieces individually

| Command | What it shows |
|---|---|
| `python benchmarks/make_large_csv.py` | regenerate the 100k fixture (any size: `make_large_csv.py 1000000 out.csv`) |
| `python verify/cross_check.py 5000` | shipped code vs an independent reference on 5,000 random files |
| `python benchmarks/vectorised_cycles.py` | why half-vectorising does not pay (needs numpy) |
| `python benchmarks/fused_experiment.py` | the pass-fusion attempt, frozen at the state it was tried |

## Reading the results

`spread` is slowest minus fastest across rounds. **If a gap is smaller than the
spread, it is not a real difference.** Absolute numbers depend heavily on the
machine and its current load; ratios within one interleaved run are what to
trust.

Full write-up of every approach: `benchmarks/APPROACHES.md`.
