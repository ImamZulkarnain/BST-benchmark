"""Check prebuilt-tree batches, timing boundaries, and saved results."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.operation_runner import make_operation_workloads, run_operations
from benchmarks.workload_runner import measure_phase
from benchmarks.plot import OPERATIONS, discover_results, load_results
from data.generate import generate_dataset
from methods import AVLTree, RedBlackTree, SplayTree


class TestOperationRunner(unittest.TestCase):
    """Ensure operations start from n keys and use matching seeded sequences."""

    def test_sequences_and_counts(self):
        """Updates are distinct; successful search queries may repeat."""
        keys, misses = list(range(3200)), list(range(3200, 6400))
        baseline, workloads = make_operation_workloads(keys, misses, 520, None)
        self.assertEqual((baseline, workloads), make_operation_workloads(keys, misses, 520, None))
        self.assertEqual(set(baseline), set(keys))
        insertion, deletion, search = [workload[2] for workload in workloads]
        self.assertEqual(len(insertion), 32)
        self.assertEqual(len(set(insertion)), 32)
        self.assertTrue(set(insertion) <= set(misses))
        self.assertEqual(len(set(deletion)), 32)
        self.assertTrue(set(deletion) <= set(keys))
        self.assertEqual(len(search), 10000)
        self.assertTrue(set(search) <= set(keys))

    def test_prebuilt_sizes_and_rotation_reset(self):
        """All three phases start populated and preserve the expected final keys."""
        baseline, workloads = make_operation_workloads(list(range(200)), list(range(200, 400)), 5, None)
        for tree_class in (AVLTree, RedBlackTree, SplayTree):
            for workload, expected_size in zip(workloads, (202, 198, 200)):
                with self.subTest(tree=tree_class.__name__, workload=workload[0]):
                    row = measure_phase(tree_class, baseline, workload, prebuilt=True)
                    self.assertEqual(row['size_before'], 200)
                    self.assertEqual(row['size_after'], expected_size)
                    self.assertEqual(row['true_results'], len(workload[2]))
                    if workload[1] == 'search' and tree_class is not SplayTree:
                        self.assertEqual(row['rotations'], 0)

    def test_setup_is_outside_timer(self):
        """The timer starts after construction and stops after the update batch."""
        tree = AVLTree()
        snapshots = []

        def clock():
            snapshots.append((len(tree), tree.rotation_count))
            return len(snapshots) * 1000

        with patch('benchmarks.workload_runner.perf_counter_ns', side_effect=clock):
            row = measure_phase(lambda: tree, list(range(100)),
                                ('insert_existing', 'insert', [101], True), prebuilt=True)
        self.assertEqual(snapshots[0], (100, 0))
        self.assertEqual(snapshots[1][0], 101)
        self.assertEqual(row['elapsed_ns'], 1000)

    def test_small_run_outputs_and_plot_loading(self):
        """Small prefix runs produce complete output compatible with the plotter."""
        with tempfile.TemporaryDirectory() as folder:
            dataset, output = Path(folder) / 'data', Path(folder) / 'operations'
            generate_dataset(dataset, 200, 200)
            with contextlib.redirect_stdout(io.StringIO()):
                rows = run_operations(dataset, output, sizes=[100, 200], trials=2, progress=False)
            self.assertEqual(len(rows), 36)
            groups, metadata = load_results(discover_results([output]), OPERATIONS)
            self.assertEqual(len(groups), 18)
            self.assertTrue(all(meta['experiment'] == 'operations' for meta in metadata))
            self.assertTrue(all(meta['queries_per_search_phase'] == 10000 for meta in metadata))
            self.assertEqual(json.loads((output / '100' / 'metadata.json').read_text())['status'], 'complete')
            with self.assertRaises(FileExistsError):
                run_operations(dataset, output)
