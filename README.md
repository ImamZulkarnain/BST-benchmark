# AVL, Red-Black, and Splay Tree Benchmarks

Python implementations comparing tree construction, search patterns, rotations,
and operations on prebuilt trees. Keys are unique integers or strings; the
experiments use alphanumeric strings of length 10-24.

- Repository: https://github.com/ImamZulkarnain/BST-benchmark
- Dataset: https://drive.google.com/drive/folders/1v9EoVmyP67thq8u0aKmhtoB83GSOLj77?usp=sharing

## Get the project

Install Git and Miniconda or Anaconda, then clone the repository:

```sh
git clone https://github.com/ImamZulkarnain/BST-benchmark.git
cd BST-benchmark
```

Alternatively, download the GitHub ZIP, extract it, and open a terminal in the
folder containing `main.py`. Run all commands below from that folder. On Windows,
use Anaconda Prompt or a PowerShell terminal where `conda` is available.

## Setup

Run from the project root. The recorded experiments used Python 3.12.15 on
Windows 11 with 64 GB RAM.

```sh
conda create -n cosc520_a2 python=3.12.15 -y
conda activate cosc520_a2
python -m pip install -r requirements.txt
```

Create the environment once. In each new terminal, return to the project folder
and run `conda activate cosc520_a2` before using the project. `tqdm` provides
progress reporting and Matplotlib produces figures; neither implements the trees.

All project tasks run through `main.py`. List commands and their options with:

```sh
python main.py --help
python main.py generate --help
python main.py workloads --help
python main.py operations --help
python main.py plot --help
```

## Layout

- `methods/`: shared interface and the three tree implementations.
- `data/generate.py`: reproducible unique/disjoint dataset generator.
- `benchmarks/workload_runner.py`: construction, search patterns, full deletion.
- `benchmarks/operation_runner.py`: insertion/deletion batches and searches on prebuilt trees.
- `benchmarks/plot.py`: PNG figures from saved measurements.
- `tests/`: correctness, runner, and plotting tests.
- `results/`: saved measurements and report figures; see its README.

## Tests and a small example

No downloaded dataset is needed for the tests. The verified suite contains 75
tests and a successful run ends with `OK`. The following commands then generate
a small dataset, run both experiments, and create the four PNG figures:

```sh
python main.py test
python main.py generate --output data/generated/sample --count 1000 --missing-count 1000
python main.py workloads --dataset data/generated/sample --trials 2 --output results/example_workloads
python main.py operations --dataset data/generated/sample --sizes 100 1000 --trials 2 --output results/example_operations
python main.py plot --results results/example_workloads --operations results/example_operations --output results/example_plots
```

Dataset and benchmark output directories must be new. Choose another output
name when repeating a command. Small examples verify execution, not performance.

Expected outputs from this example:

- `data/generated/sample/`: `insert_keys.txt`, `missing_keys.txt`, and `manifest.json`.
- `results/example_workloads/`: `raw.csv` with 48 measurements
  (8 workloads x 3 trees x 2 trials), `summary.csv`, and `metadata.json`.
- `results/example_operations/100/` and `1000/`: each contains 18 raw measurements
  (3 workloads x 3 trees x 2 trials), a summary, and metadata.
- `results/example_plots/`: `insertion_order.png`, `rotations_per_operation.png`,
  `search_patterns.png`, and `operation_times.png`.

Plots are PNG only and do not open graphical windows. Plotting again replaces
same-named PNGs; it does not modify the source measurements.

## Download the report dataset

Download all three files from the dataset link above. If Drive creates a ZIP,
extract the files into this structure (avoid an extra nested dataset folder):

```text
data/generated/10m/
    insert_keys.txt
    missing_keys.txt
    manifest.json
```

The two text files contain ten million keys each and are disjoint. The manifest
is required by the loader. Pass the containing directory to `--dataset`, not an
individual text file. These large files are excluded from Git; keep their original
order and contents when reproducing the saved experiments.

## Reproduce the full experiment

Instead of downloading, generate the dataset locally with the original seed and
default 10-24 character lengths:

```sh
python main.py generate --output data/generated/10m --count 10000000 --missing-count 10000000 --seed 520
```

Both runners use these sizes: 3,200; 16,000; 80,000; 400,000; 2,000,000; and
10,000,000. Each uses the first n keys from each source file, with identical
workload sequences across trees within a trial.

| Setting | Workload experiment | Prebuilt-tree experiment |
| --- | --- | --- |
| Workloads per tree | 8 | 3 |
| Construction/deletion | Insert all n keys / delete all n keys | Fresh n-key setup; update max(1, n // 100) keys |
| Searches per phase | n | max(10000, n // 100) |
| Trials in commands below | 5 | 5 |
| Base seed | 520 | 520 |

Run the two experiments in new directories:

```sh
python main.py workloads --dataset data/generated/10m --sizes 3200 16000 80000 400000 2000000 10000000 --trials 5 --seed 520 --output results/scaling_repeat --skip-validation
python main.py operations --dataset data/generated/10m --sizes 3200 16000 80000 400000 2000000 10000000 --trials 5 --seed 520 --output results/operations_repeat --skip-validation
python main.py plot --results results/scaling_repeat --operations results/operations_repeat --output results/repeat_plots
```

These are long-running experiments, not installation checks. Both key files are
loaded into memory. See the measurement and troubleshooting sections below for timing, validation,
and progress reporting.

## Recreate figures from saved results

No large dataset or benchmark rerun is needed:

```sh
python main.py plot --results results/scaling --operations results/operations --output results/scaling/plots
```

`results/scaling` contains five trials per size. The saved `results/operations`
contains four trials per size, combined from two two-trial runs with seeds 520-521
and 522-523. Its metadata retains the source-run information. The commands above
request a new five-trial experiment; they do not change the saved results. To
repeat the saved operation workload's four seeds in one run, use `--trials 4 --seed 520` with a new output directory. Separate executions can differ in timing
and tree execution order even when their workload seeds match.

Use only `scaling` and the combined `operations` as plotting inputs. If the original
source-run folders are present, do not include them again: that duplicates sizes.
See [saved-result details](results/README.md).


## Understand the measurements

- Each raw CSV row describes one tree, workload, size, and trial. It includes
  total seconds, nanoseconds per operation, operation count, rotations, and
  initial/final sizes and heights. `summary.csv` aggregates trials;
  `metadata.json` records settings, source data information, and run status.
- Construction timing starts from an empty tree. Other phases build their initial
  tree outside timing. Dataset loading, query preparation, validation, height
  inspection, and result writing are excluded from timing.
- Timing includes Python loop/method-call overhead, rotation counters, and
  accumulation of successful results. Garbage collection is disabled during
  timing and restored afterward. No separate warm-up is performed.
- Every workload gets a fresh tree. Changes persist within a sequence, including
  splay restructuring. Tree execution order rotates between trials.
- Plots show medians and min-max ranges, not confidence intervals. Operation-time
  panels use microseconds per operation, a logarithmic x-axis, and a linear y-axis.
  The other three figures use the largest workload size unless `--size` is supplied.
- Rotations are counted only during the workload: each left or right rotation is
  one, double rotations are two, and recoloring is excluded. Heights count edges:
  an empty tree has height -1 and a leaf has height 0.
- Validation is enabled by default. `--skip-validation` skips full structural and
  exact-key checks, but still checks success totals and final sizes. Small tests
  use full validation. Memory usage and comparison counts are not measured.

Exact timings will differ between machines and runs. Preserve raw measurements,
metadata, code revision, and dependency versions. The requirements file lists
packages without pinning versions; the existing metadata is not a package lockfile.
For a new experiment, record these alongside its results:

```sh
python -m pip freeze > results/packages.txt
git rev-parse HEAD > results/commit.txt
```

ZIP users should record the downloaded revision separately. A captured package
list can later be installed with `python -m pip install -r results/packages.txt`.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `conda` or `python` not found | Use Anaconda Prompt or a terminal configured for Conda; activate `cosc520_a2`. |
| Missing Python package | Run `python -m pip install -r requirements.txt` in the active environment. |
| Command required / unrecognized arguments | Use `python main.py generate`, `workloads`, `operations`, `plot`, or `test`. Old module-entry commands have been removed. |
| Dataset or manifest not found | Check that `--dataset` points to a directory containing all three extracted files. |
| Invalid counts, duplicate keys, or overlap | Use the original complete files or regenerate a new dataset; do not edit the manifest to bypass validation. |
| Output directory already exists | Choose a new generator/benchmark output directory; existing data is protected. |
| Multiple runs for the same size | Select one result set per experiment. Do not mix combined and source runs. |
| Missing or incomplete results | Inspect run metadata and terminal errors. Failed runs may have `partial.csv`; do not relabel them complete. |
| Progress bar appears stationary | Updates happen after a whole phase, including setup. Large tree builds can take minutes. |
| Plain messages instead of a bar | Redirected output uses plain messages; `--no-progress` requests them explicitly. |
| High RAM use | Both source files stay in memory; full validation and generation use additional memory. Start with the small example. |
| Plot cannot overwrite a file | Close the image viewer or select a new output directory. |

There is no automatic resume. Completed size folders are retained if a later size
fails. A rerun with fewer sizes is a partial experiment and should be reported as
such. Long benchmarks should be run explicitly, not as a setup check.
