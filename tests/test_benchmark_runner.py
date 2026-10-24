"""Benchmark workload, correctness, and output checks."""

import contextlib
import csv
import gc
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from benchmarks.workload_runner import load_dataset, make_workloads, measure_phase, run_benchmarks, summarize
from data.generate import generate_dataset
from methods import AVLTree, RedBlackTree, SplayTree


class TestBenchmarkRunner(unittest.TestCase):
    """Verify comparable workloads and measurement bookkeeping."""

    def test_workload_reproducibility_and_membership(self):
        """Fixed seeds reproduce queries and all intended hits/misses are correct."""
        keys = [f'A{i:09d}' for i in range(100)]
        misses = [f'B{i:09d}' for i in range(20)]
        baseline, workloads = make_workloads(keys, misses, 42, 200)
        self.assertEqual((baseline, workloads), make_workloads(keys, misses, 42, 200))
        self.assertEqual(set(baseline), set(keys))
        self.assertEqual(len(workloads), 8)
        for name, operation, sequence, success in workloads:
            with self.subTest(workload=name):
                if operation == 'search':
                    self.assertEqual(len(sequence), 200)
                    self.assertTrue(all((key in keys) == success for key in sequence))
                else:
                    self.assertEqual(sorted(sequence), sorted(keys))
        self.assertEqual(workloads[1][2], sorted(keys))
        self.assertEqual(workloads[2][2], sorted(keys, reverse=True))
        self.assertEqual(workloads[5][2], sorted(keys) * 2)

    def test_phases_use_expected_sizes_and_preserve_gc_state(self):
        """Each phase starts fresh and counts results without timing setup rotations."""
        baseline, workloads = make_workloads(list(range(20)), [-1, -2], 7, 30)

        # Save the collector setting so the test can restore it afterward.
        original_gc = gc.isenabled()
        try:
            for enabled in (True, False):
                gc.enable() if enabled else gc.disable()
                for cls in (AVLTree, RedBlackTree, SplayTree):
                    for workload in workloads:
                        with self.subTest(gc=enabled, tree=cls.__name__, workload=workload[0]):
                            row = measure_phase(cls, baseline, workload)
                            operation = workload[1]
                            self.assertEqual(row['size_before'], 0 if operation == 'insert' else 20)
                            self.assertEqual(row['size_after'], 0 if operation == 'delete' else 20)
                            self.assertEqual(row['true_results'], len(workload[2]) if workload[3] else 0)
                            self.assertGreaterEqual(row['elapsed_ns'], 0)
                            self.assertEqual(gc.isenabled(), enabled)
                            if operation == 'search' and cls is not SplayTree:
                                self.assertEqual(row['rotations'], 0)
        finally:
            gc.enable() if original_gc else gc.disable()

    def test_summary_uses_trial_statistics(self):
        """Summary medians and ranges match known synthetic measurements."""
        rows = [dict(tree='AVLTree', workload='insert_random', key_count=10,
                     operation_count=10, seconds=value, rotations=value,
                     height_before=-1, height_after=3) for value in (1, 9, 2)]
        summary = summarize(rows)[0]
        self.assertEqual(summary['median_seconds'], 2)
        self.assertEqual(summary['min_seconds'], 1)
        self.assertEqual(summary['max_seconds'], 9)
        self.assertEqual(summary['trials'], 3)
        self.assertEqual(summary['median_rotations'], 2)

    def test_end_to_end_files_and_overwrite_protection(self):
        """Small runs produce raw data, summary, and completed metadata."""
        with tempfile.TemporaryDirectory() as directory:
            dataset, output = Path(directory) / 'data', Path(directory) / 'results'
            generate_dataset(dataset, 12, 12)

            # Hide progress messages while checking a small complete run.
            with contextlib.redirect_stdout(io.StringIO()):
                rows = run_benchmarks(dataset, output, trials=2, queries=15)
            self.assertEqual(len(rows), 48)
            with (output / 'raw.csv').open(newline='') as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 48)
            with (output / 'summary.csv').open(newline='') as stream:
                summary = list(csv.DictReader(stream))
                self.assertEqual(len(summary), 24)
                self.assertTrue(all(row['trials'] == '2' for row in summary))
            metadata = json.loads((output / 'metadata.json').read_text())
            self.assertEqual(metadata['status'], 'complete')
            self.assertTrue(metadata['validation_enabled'])
            with self.assertRaises(FileExistsError):
                run_benchmarks(dataset, output)

    def test_incorrect_key_count_is_rejected(self):
        """A file with more keys than its recorded count is rejected."""
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / 'data'
            generate_dataset(dataset, 10, 10)

            # Add a key without increasing the recorded count.
            with (dataset / 'insert_keys.txt').open('a') as stream:
                stream.write('Changed12345\n')
            with self.assertRaisesRegex(ValueError, 'Incorrect count'):
                load_dataset(dataset)


    def test_multiple_sizes_load_once_and_run_five_trials(self):
        """Prefix sizes share one source load and get separate five-trial results."""
        from benchmarks.plot import discover_results, load_results
        with tempfile.TemporaryDirectory() as folder:
            dataset, output = Path(folder) / 'data', Path(folder) / 'scaling'
            generate_dataset(dataset, 12, 12)
            source = (dataset / 'insert_keys.txt').read_bytes()
            with patch('benchmarks.workload_runner.load_dataset', wraps=load_dataset) as loader:
                with contextlib.redirect_stdout(io.StringIO()):
                    rows = run_benchmarks(dataset, output, sizes=[12, 4], validate=False)
            loader.assert_called_once_with(dataset)
            self.assertEqual(len(rows), 2 * 5 * 8 * 3)
            self.assertEqual((dataset / 'insert_keys.txt').read_bytes(), source)
            for size in (4, 12):
                selected = [r for r in rows if r['key_count'] == size]
                self.assertEqual({r['trial'] for r in selected}, set(range(1, 6)))
                self.assertEqual({r['workload_seed'] for r in selected}, set(range(520, 525)))
                self.assertTrue(all(r['operation_count'] == size for r in selected))
                metadata = json.loads((output / str(size) / 'metadata.json').read_text())
                self.assertEqual(metadata['selected_key_count'], size)
                self.assertEqual(metadata['selected_missing_count'], size)
                self.assertEqual(metadata['dataset_manifest']['files']['insert_keys.txt']['count'], 12)
                self.assertEqual(metadata['status'], 'complete')
            directories = discover_results([output])
            self.assertEqual(len(directories), 2)
            groups, metadata = load_results(directories)
            self.assertEqual({key[0] for key in groups}, {4, 12})

    def test_selected_prefixes_and_query_override(self):
        """Use the first n keys from both source files, with an explicit query count."""
        from benchmarks.workload_runner import make_workloads
        with tempfile.TemporaryDirectory() as folder:
            dataset, output = Path(folder) / 'data', Path(folder) / 'scaling'
            generate_dataset(dataset, 10, 10)
            keys, misses, manifest = load_dataset(dataset)
            with patch('benchmarks.workload_runner.make_workloads', wraps=make_workloads) as workloads:
                with contextlib.redirect_stdout(io.StringIO()):
                    rows = run_benchmarks(dataset, output, sizes=[4, 8], trials=1, queries=7)
            self.assertEqual([call.args[:2] for call in workloads.call_args_list],
                             [(keys[:4], misses[:4]), (keys[:8], misses[:8])])
            for row in rows:
                self.assertEqual(row['operation_count'], 7 if row['operation'] == 'search' else row['key_count'])

    def test_invalid_sizes_do_not_create_output(self):
        """Reject empty, repeated, too-small, or unavailable sizes before starting."""
        with tempfile.TemporaryDirectory() as folder:
            dataset = Path(folder) / 'data'
            generate_dataset(dataset, 10, 6)
            for index, sizes in enumerate(([], [1], [4, 4], [7], [11])):
                output = Path(folder) / str(index)
                with self.subTest(sizes=sizes), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(ValueError):
                        run_benchmarks(dataset, output, sizes=sizes)
                    self.assertFalse(output.exists())


    def test_progress_tracks_completed_phases_and_closes(self):
        """The progress bar advances once per phase, not once per key."""
        with tempfile.TemporaryDirectory() as folder:
            dataset, output = Path(folder) / 'data', Path(folder) / 'results'
            generate_dataset(dataset, 5, 5)
            with patch('benchmarks.workload_runner.tqdm') as progress:
                bar = progress.return_value
                bar.disable = False
                with contextlib.redirect_stdout(io.StringIO()):
                    run_benchmarks(dataset, output, trials=1)
            self.assertEqual(progress.call_args.kwargs['total'], 24)
            self.assertEqual(bar.update.call_count, 24)
            self.assertTrue(all(call.args == (1,) for call in bar.update.call_args_list))
            bar.close.assert_called_once()

    def test_progress_closes_when_a_phase_fails(self):
        """A failed phase does not advance progress and still closes the display."""
        with tempfile.TemporaryDirectory() as folder:
            dataset, output = Path(folder) / 'data', Path(folder) / 'results'
            generate_dataset(dataset, 5, 5)
            with patch('benchmarks.workload_runner.tqdm') as progress:
                with patch('benchmarks.workload_runner.measure_phase', side_effect=RuntimeError('test failure')):
                    with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
                        run_benchmarks(dataset, output, trials=1)
            progress.return_value.update.assert_not_called()
            progress.return_value.close.assert_called_once()
            self.assertEqual(json.loads((output / 'metadata.json').read_text())['status'], 'failed')
