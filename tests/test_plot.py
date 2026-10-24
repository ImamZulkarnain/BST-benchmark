"""Check plotting calculations, input handling, and figure export."""

import contextlib
import csv
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.plot import TREES, WORKLOADS, OPERATIONS, create_plots, load_results, statistics_for


def make_results(directory, size=10, workloads=WORKLOADS):
    """Write a small complete result set with known trial measurements."""
    directory.mkdir()
    (directory / 'metadata.json').write_text(json.dumps({'status': 'complete', 'python': 'test'}))
    rows = []
    for tree in TREES:
        for workload in workloads:
            for trial, seconds in enumerate((1, 3, 2), 1):
                rows.append(dict(tree=tree, workload=workload, trial=trial,
                                 key_count=size, operation_count=(max(10000, size // 100) if workload == 'search_existing'
                                     else max(1, size // 100) if workload in OPERATIONS else size), seconds=seconds,
                                 rotations=trial, height_before=2,
                                 height_after=-1 if workload == 'delete_random' else 3))
    with (directory / 'raw.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


class TestPlots(unittest.TestCase):
    """Verify that figures use real trial statistics and comparable inputs."""

    def test_units_and_ranges(self):
        """Time and rotation rates are calculated per operation before aggregation."""
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / 'run'
            make_results(directory)
            groups, metadata = load_results([directory])
            self.assertEqual(len(groups), 24)
            self.assertEqual(statistics_for(groups, 10, 'AVLTree', 'insert_random', 'seconds'), (2, 1, 3))
            self.assertEqual(statistics_for(groups, 10, 'AVLTree', 'insert_random', 'microseconds'),
                             (200000, 100000, 300000))
            self.assertEqual(statistics_for(groups, 10, 'AVLTree', 'insert_random', 'rotations_per_operation'),
                             (0.2, 0.1, 0.3))

    def test_repeated_sizes_and_incomplete_runs_are_rejected(self):
        """Do not combine duplicate runs or present unfinished results as complete."""
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / 'first', Path(folder) / 'second'
            make_results(first)
            make_results(second)
            with self.assertRaisesRegex(ValueError, 'Multiple runs'):
                load_results([first, second])
            (second / 'metadata.json').write_text(json.dumps({'status': 'running'}))
            with self.assertRaisesRegex(ValueError, 'not complete'):
                load_results([second])

    def test_missing_workloads_are_rejected(self):
        """Missing measurements should not become zero-height bars."""
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / 'run'
            make_results(directory)
            path = directory / 'raw.csv'
            lines = path.read_text().splitlines()
            path.write_text('\n'.join(lines[:-3]) + '\n')
            with self.assertRaisesRegex(ValueError, 'Missing'):
                load_results([directory])

    @unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'Matplotlib is needed for figure export')
    def test_exports_all_figures_with_one_size(self):
        """A one-size run exports four PNGs and removes the retired growth figure."""
        with tempfile.TemporaryDirectory() as folder:
            directory, output = Path(folder) / 'run', Path(folder) / 'plots'
            make_results(directory)
            operations = Path(folder) / 'operations'
            make_results(operations, workloads=OPERATIONS)
            output.mkdir()
            (output / 'runtime_growth.png').write_text('obsolete')
            (output / 'runtime_growth.pdf').write_text('obsolete')
            with contextlib.redirect_stdout(io.StringIO()) as messages:
                paths = create_plots([directory], output, operation_directories=[operations])
            self.assertFalse((output / 'runtime_growth.png').exists())
            self.assertFalse((output / 'runtime_growth.pdf').exists())
            self.assertEqual(len(paths), 4)
            self.assertIn('preliminary', messages.getvalue())
            for path in paths:
                self.assertTrue(path.read_bytes().startswith(b'\x89PNG'))
                self.assertFalse(path.with_suffix('.pdf').exists())
