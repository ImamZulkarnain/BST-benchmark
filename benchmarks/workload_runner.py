"""Benchmark identical string-key workloads with fresh trees for every phase."""

import csv
import gc
import json
import math
import platform
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns

from tqdm import tqdm

from methods import AVLTree, RedBlackTree, SplayTree

TREE_CLASSES = (AVLTree, RedBlackTree, SplayTree)


def load_dataset(directory):
    """Read and verify the generated dataset; return keys, misses, and manifest."""
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    groups = []
    for name in ('insert_keys.txt', 'missing_keys.txt'):
        raw = (directory / name).read_bytes()
        info = manifest['files'][name]

        keys = raw.decode('ascii').splitlines()
        if len(keys) != info['count'] or len(set(keys)) != len(keys):
            raise ValueError(f'Incorrect count or duplicate keys: {name}')
        alphabet = set(manifest['alphabet'])
        if any(not manifest['min_length'] <= len(k) <= manifest['max_length']
               or not set(k) <= alphabet for k in keys):
            raise ValueError(f'Invalid key format: {name}')
        groups.append(keys)
    keys, misses = groups

    # Missing keys must never overlap the keys inserted into a tree.
    if not keys or not misses or not set(keys).isdisjoint(misses):
        raise ValueError('Both key files must be nonempty and disjoint')
    return keys, misses, manifest


def make_workloads(keys, misses, seed, queries):
    """Return baseline insertion order and fixed operation sequences for one trial.

    Hotspot queries draw exactly round(0.9 * queries) accesses from a randomly
    selected ceil(10% of keys) subset, with replacement. The remainder target
    cold keys. Sequential queries cycle over sorted keys if needed.
    """
    if queries < 1 or len(keys) < 2 or not misses:
        raise ValueError('Need at least two stored keys, one miss, and one query')

    # Generate the same operation sequences for every tree in this trial.
    rng = random.Random(seed)
    baseline = list(keys)
    rng.shuffle(baseline)
    ordered = sorted(keys)
    hot_size = min(len(keys) - 1, max(1, math.ceil(len(keys) * 0.1)))
    partition = list(keys)
    rng.shuffle(partition)
    hot, cold = partition[:hot_size], partition[hot_size:]

    # Send 90% of queries to hot keys, then mix in the cold-key queries.
    hot_count = round(0.9 * queries)
    hotspot = [rng.choice(hot) for _ in range(hot_count)]
    hotspot.extend(rng.choice(cold) for _ in range(queries - hot_count))
    rng.shuffle(hotspot)
    deletion = list(keys)
    rng.shuffle(deletion)

    # Each workload records its name, operation, keys, and expected result.
    return baseline, [
        ('insert_random', 'insert', baseline, True),
        ('insert_sorted', 'insert', ordered, True),
        ('insert_reverse', 'insert', list(reversed(ordered)), True),
        ('search_uniform', 'search', [rng.choice(keys) for _ in range(queries)], True),
        ('search_missing', 'search', [rng.choice(misses) for _ in range(queries)], False),
        ('search_sequential', 'search', [ordered[i % len(keys)] for i in range(queries)], True),
        ('search_hotspot', 'search', hotspot, True),
        ('delete_random', 'delete', deletion, True),
    ]


def measure_phase(tree_class, baseline, workload, validate=True, prebuilt=False):
    """Build a fresh tree, time one phase, and return measurements.

    Preparation, garbage collection, shape inspection, and validation are
    outside timing. Timing includes the Python loop, method calls, and counting
    True results. GC is disabled only during timing and its state is restored.
    """
    name, operation, sequence, expected_result = workload
    tree = tree_class()

    # Build the initial tree outside timing for searches and deletions.
    if prebuilt or operation != 'insert':
        for key in baseline:
            tree.insert(key)
    if validate:
        tree.validate()
    size_before, height_before = len(tree), tree.height()

    # Exclude rotations performed while building the initial tree.
    tree.reset_rotation_count()
    method = getattr(tree, operation)

    # Collect old objects before timing and pause collection during the loop.
    gc.collect()
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        # Only the operation loop and result counting are timed.
        started = perf_counter_ns()
        true_results = 0
        for key in sequence:
            true_results += method(key)
        elapsed_ns = perf_counter_ns() - started
    finally:
        if gc_was_enabled:
            gc.enable()
    rotations = tree.rotation_count
    size_after, height_after = len(tree), tree.height()

    # Check result totals even when full validation is disabled.
    expected_true = len(sequence) if expected_result else 0
    expected_size = size_before
    if operation == 'insert':
        expected_size += len(sequence)
    elif operation == 'delete':
        expected_size -= len(sequence)
    if true_results != expected_true or size_after != expected_size:
        raise AssertionError(f'{tree_class.__name__}/{name}: unexpected results or size')
    if validate:
        tree.validate()
        expected_keys = set(baseline)
        if operation == 'insert':
            expected_keys.update(sequence)
        elif operation == 'delete':
            expected_keys.difference_update(sequence)
        if list(tree) != sorted(expected_keys):
            raise AssertionError(f'{tree_class.__name__}/{name}: stored keys changed')
    return {
        'tree': tree_class.__name__, 'workload': name, 'operation': operation,
        'key_count': len(baseline), 'operation_count': len(sequence),
        'elapsed_ns': elapsed_ns, 'seconds': elapsed_ns / 1e9,
        'ns_per_operation': elapsed_ns / len(sequence),
        'rotations': rotations, 'rotations_per_operation': rotations / len(sequence),
        'size_before': size_before, 'size_after': size_after,
        'height_before': height_before, 'height_after': height_after,
        'true_results': true_results,
    }


def write_csv(path, rows):
    """Write measurement dictionaries as a CSV with a header; return None."""
    with Path(path).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows):
    """Group trials and return medians, ranges, and runtime standard deviations."""
    groups = {}

    # Group trials by tree, workload, and dataset size.
    for row in rows:
        groups.setdefault((row['tree'], row['workload'], row['key_count']), []).append(row)
    result = []
    for (tree, workload, count), trials in groups.items():
        times = [r['seconds'] for r in trials]
        result.append({
            'tree': tree, 'workload': workload, 'key_count': count,
            'trials': len(trials), 'operation_count': trials[0]['operation_count'],
            'median_seconds': statistics.median(times),
            'median_ns_per_operation': statistics.median(times) * 1e9 / trials[0]['operation_count'],
            'min_ns_per_operation': min(times) * 1e9 / trials[0]['operation_count'],
            'max_ns_per_operation': max(times) * 1e9 / trials[0]['operation_count'],
            'min_seconds': min(times), 'max_seconds': max(times),
            'stdev_seconds': statistics.stdev(times) if len(times) > 1 else 0.0,
            'median_rotations': statistics.median(r['rotations'] for r in trials),
            'median_height_before': statistics.median(r['height_before'] for r in trials),
            'median_height_after': statistics.median(r['height_after'] for r in trials),
        })
    return result


def run_benchmarks(dataset, output, trials=5, seed=520, queries=None, validate=True,
                   sizes=None, progress=True, workload_factory=None):
    """Load data once and benchmark the full dataset or requested prefix sizes.

    Each requested size uses the first n insertion keys and first n missing
    keys from the source files. Results go into output/n without copying data.
    Without sizes, keep the original single-run output layout.
    """
    if trials < 1 or (queries is not None and queries < 1):
        raise ValueError('trials and queries must be positive')
    if sizes is not None:
        if not sizes or any(size < 2 for size in sizes):
            raise ValueError('sizes must contain integers of at least 2')
        if len(set(sizes)) != len(sizes):
            raise ValueError('sizes must not contain duplicates')

    # Reject an existing output directory before loading the large dataset.
    output = Path(output)
    if output.exists():
        raise FileExistsError(f'Output directory already exists: {output}')
    print(f'Loading dataset from {dataset}...', flush=True)
    keys, misses, manifest = load_dataset(dataset)
    if len(keys) < 2:
        raise ValueError('At least two insertion keys are required')
    if sizes is None:
        return run_size(dataset, output, keys, misses, manifest, trials, seed,
                        queries, validate, 'full dataset', progress, workload_factory)
    if max(sizes) > min(len(keys), len(misses)):
        raise ValueError('Every requested size must fit both insertion and missing-key files')

    # Process nested prefixes in ascending order; slices share the string objects.
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for size in sorted(sizes):
        print(f'Benchmarking {size:,} keys with {trials} trials...', flush=True)
        selected_keys = keys[:size]
        selected_misses = misses[:size]
        rows.extend(run_size(dataset, output / str(size), selected_keys,
                             selected_misses, manifest, trials, seed, queries,
                             validate, 'first n keys from each source file', progress, workload_factory))

        # Release this size before allocating the next size's workload lists.
        del selected_keys, selected_misses
        gc.collect()
    return rows


def run_size(dataset, output, keys, misses, manifest, trials, seed, queries,
             validate, selection, progress=True, workload_factory=None):
    """Benchmark one in-memory selection and save its trials and metadata.

    Trial seeds are seed + trial_index. Search query counts default to this
    selection's size. Setup, selection, and cleanup stay outside timing.
    """
    prebuilt = workload_factory is not None
    queries = max(10000, len(keys) // 100) if prebuilt else (len(keys) if queries is None else queries)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    metadata = {
        'status': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'python_executable': sys.executable,
        'platform': platform.platform(), 'processor': platform.processor(),
        'dataset_directory': str(Path(dataset).resolve()), 'dataset_manifest': manifest,
        'trials': trials, 'seed': seed, 'queries_per_search_phase': queries,
        'selected_key_count': len(keys), 'selected_missing_count': len(misses),
        'dataset_selection': selection,
        'validation_enabled': validate, 'timer': 'perf_counter_ns',
        'gc_disabled_during_timing': True,
        'timing_scope': 'operation loop, method calls, rotation counters, result accumulation',
        'experiment': 'operations' if prebuilt else 'workloads',
        'update_batch_count': max(1, len(keys) // 100) if prebuilt else None,
        'search_count_rule': 'max(10000, n // 100)' if prebuilt else 'queries or n',
        'baseline': 'fresh randomly built n-key tree for every phase' if prebuilt else 'fresh tree per phase; searches and deletion prebuilt',
        'update_count_rule': 'max(1, n // 100)' if prebuilt else 'all n keys',
    }
    metadata_path = output / 'metadata.json'
    metadata_path.write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    rows = []

    # Update once per completed phase, never inside the measured operation loop.
    bar = tqdm(total=trials * (3 if prebuilt else 8) * len(TREE_CLASSES), desc=f'{len(keys):,} keys',
               unit='phase', dynamic_ncols=True,
               disable=not (progress and sys.stderr.isatty()))
    try:
        for trial in range(trials):
            bar.set_postfix_str(f'trial {trial + 1}/{trials}: preparing workloads')
            factory = workload_factory or make_workloads
            baseline, workloads = factory(keys, misses, seed + trial, queries)

            # Rotate which tree runs first to reduce a fixed ordering advantage.
            offset = trial % len(TREE_CLASSES)
            classes = TREE_CLASSES[offset:] + TREE_CLASSES[:offset]
            for workload in workloads:
                for tree_class in classes:
                    bar.set_postfix_str(f'trial {trial + 1}/{trials}: {tree_class.__name__} {workload[0]}')
                    row = measure_phase(tree_class, baseline, workload, validate, prebuilt=prebuilt)
                    row = {'trial': trial + 1, 'workload_seed': seed + trial, **row}
                    rows.append(row)

                    # Parent links can form cycles; free the finished tree before building another.
                    gc.collect()
                    bar.update(1)
                    if bar.disable:
                        print(f'Trial {trial + 1}/{trials}: {row["tree"]} {row["workload"]}: {row["seconds"]:.6f}s', flush=True)

            # Release the old trial's sequences before preparing the next trial.
            del baseline, workloads, workload
            gc.collect()

        # Save individual measurements separately from the combined statistics.
        write_csv(output / 'raw.csv', rows)
        write_csv(output / 'summary.csv', summarize(rows))
        metadata['status'] = 'complete'

    # Keep completed measurements if a later phase fails.
    except Exception as error:
        metadata['status'] = 'failed'
        metadata['error'] = str(error)
        if rows:
            write_csv(output / 'partial.csv', rows)
        raise
    finally:
        bar.close()
        metadata_path.write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    return rows
