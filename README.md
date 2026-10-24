# AVL, Red-Black, and Splay Tree Benchmarks

Python implementations comparing tree construction, search patterns, rotations,
and operations on prebuilt trees. Keys are unique integers or strings; the
experiments use alphanumeric strings of length 10-24.

## Setup

Run from the project root. The recorded experiments used Python 3.12.15 on
Windows 11 with 64 GB RAM.

```sh
conda create -n cosc520_a2 python=3.12.15 -y
conda activate cosc520_a2
python -m pip install -r requirements.txt
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

```sh
python main.py test
python main.py generate --output data/generated/sample --count 1000 --missing-count 1000
python main.py workloads --dataset data/generated/sample --trials 2 --output results/example_workloads
python main.py operations --dataset data/generated/sample --sizes 100 1000 --trials 2 --output results/example_operations
python main.py plot --results results/example_workloads --operations results/example_operations --output results/example_plots
```

Dataset and benchmark output directories must be new. Choose another output
name when repeating a command. Small examples verify execution, not performance.

## Reproduce the full experiment

The large key files are excluded from Git. Generate them locally with:

```sh
python main.py generate --output data/generated/10m --count 10000000 --missing-count 10000000 --seed 520
```

Run the two experiments in new directories:

```sh
python main.py workloads --dataset data/generated/10m --sizes 3200 16000 80000 400000 2000000 10000000 --trials 5 --seed 520 --output results/scaling_repeat --skip-validation
python main.py operations --dataset data/generated/10m --sizes 3200 16000 80000 400000 2000000 10000000 --trials 5 --seed 520 --output results/operations_repeat --skip-validation
python main.py plot --results results/scaling_repeat --operations results/operations_repeat --output results/repeat_plots
```

These are long-running experiments, not installation checks. Both key files are
loaded into memory.
workload definitions, validation, and progress reporting.

## Recreate figures from saved results

No large dataset or benchmark rerun is needed:

```sh
python main.py plot --results results/scaling --operations results/operations --output results/scaling/plots
```

The committed results have their actual trial counts recorded in metadata.
A command requesting five trials does not change previously collected results.
The generator instructions support reproduction;
