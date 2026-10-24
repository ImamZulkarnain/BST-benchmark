"""Measure insertion, deletion, and search sequences on prebuilt trees."""

import random

from benchmarks.workload_runner import run_benchmarks


def make_operation_workloads(keys, misses, seed, queries):
    """Create reproducible batches shared by all trees in one trial.

    Updates use max(1, n // 100) distinct keys. Searches sample existing keys
    with replacement max(10000, n // 100) times. Changes persist within a batch.
    """
    count = max(1, len(keys) // 100)
    if len(keys) < 2 or len(misses) < count:
        raise ValueError('Need at least two stored keys and enough new insertion keys')
    rng = random.Random(seed)
    baseline = list(keys)
    rng.shuffle(baseline)
    return baseline, [
        ('insert_existing', 'insert', rng.sample(misses, count), True),
        ('delete_existing', 'delete', rng.sample(keys, count), True),
        ('search_existing', 'search',
         [rng.choice(keys) for _ in range(max(10000, len(keys) // 100))], True),
    ]


def run_operations(dataset, output, trials=5, seed=520, sizes=None,
                   validate=True, progress=True):
    """Run only prebuilt-tree workloads using the shared measurement machinery."""
    return run_benchmarks(dataset, output, trials=trials, seed=seed, sizes=sizes,
                          validate=validate, progress=progress,
                          workload_factory=make_operation_workloads)
