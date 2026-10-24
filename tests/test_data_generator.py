"""Dataset format, reproducibility, and input validation checks."""

import json
import tempfile
import unittest
from pathlib import Path

from data.generate import ALPHABET, generate_dataset


class TestDatasetGenerator(unittest.TestCase):
    """Verify generator output independently of its internal bookkeeping."""

    def test_reproducibility_uniqueness_and_metadata(self):
        """Same seed yields identical files with correct counts and length statistics."""
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / 'first', Path(directory) / 'second'
            manifest = generate_dataset(first, 200, 100, seed=42)
            self.assertEqual(manifest, generate_dataset(second, 200, 100, seed=42))

            # Track both files together to check that their keys never overlap.
            all_keys = set()
            for name, count in [('insert_keys.txt', 200), ('missing_keys.txt', 100)]:
                raw = (first / name).read_bytes()
                self.assertEqual(raw, (second / name).read_bytes())
                keys = raw.decode('ascii').splitlines()
                self.assertEqual(len(keys), count)
                self.assertEqual(len(set(keys)), count)
                self.assertTrue(all_keys.isdisjoint(keys))
                all_keys.update(keys)
                self.assertTrue(all(10 <= len(k) <= 24 and set(k) <= set(ALPHABET) for k in keys))
                self.assertEqual(manifest['files'][name]['count'], count)
                self.assertEqual(manifest['files'][name]['length_counts'],
                                 {str(n): sum(len(k) == n for k in keys) for n in range(10, 25)})
            self.assertEqual(json.loads((first / 'manifest.json').read_text()), manifest)

    def test_invalid_options_create_no_output(self):
        """Invalid counts and lengths fail before a directory is created."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'invalid'
            for options in [dict(count=0), dict(missing_count=-1), dict(min_length=9),
                            dict(max_length=25), dict(min_length=20, max_length=10)]:
                with self.subTest(options=options):
                    with self.assertRaises(ValueError):
                        generate_dataset(output, **options)
                    self.assertFalse(output.exists())

    def test_existing_output_is_preserved(self):
        """Regeneration refuses to overwrite an existing dataset."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'keys'
            generate_dataset(output, 5, 0)
            original = (output / 'insert_keys.txt').read_bytes()

            # Repeat generation must leave the existing files untouched.
            with self.assertRaises(FileExistsError):
                generate_dataset(output, 10, 10)
            self.assertEqual((output / 'insert_keys.txt').read_bytes(), original)
            self.assertEqual((output / 'missing_keys.txt').read_bytes(), b'')

    def test_fixed_length_and_different_seeds(self):
        """Boundary lengths are supported, and changing the seed changes keys."""
        with tempfile.TemporaryDirectory() as directory:
            for length in (10, 24):
                paths = [Path(directory) / f'{length}_{seed}' for seed in (1, 2)]
                for seed, path in zip((1, 2), paths):
                    generate_dataset(path, 10, 10, seed=seed, min_length=length, max_length=length)
                    self.assertTrue(all(len(k) == length for k in (path / 'insert_keys.txt').read_text().splitlines()))
                self.assertNotEqual((paths[0] / 'insert_keys.txt').read_bytes(),
                                    (paths[1] / 'insert_keys.txt').read_bytes())
