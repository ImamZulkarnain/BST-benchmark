"""Red-black balancing, sentinel, and validation tests."""

import unittest

from methods import RedBlackTree
from tests.tree_contract import TreeContractTests, snapshot


class TestRedBlackTree(TreeContractTests, unittest.TestCase):
    """Run shared contract checks and red-black-specific cases."""

    tree_class = RedBlackTree

    def test_insertion_rotations_and_recoloring(self):
        """Straight and bent insertions count rotations; recoloring counts none."""
        for keys, count in (([3, 2, 1], 1), ([1, 2, 3], 1),
                            ([3, 1, 2], 2), ([1, 3, 2], 2), ([2, 1, 3, 0], 0)):
            with self.subTest(keys=keys):
                tree = self.make_tree(keys)
                self.assertEqual(tree.rotation_count, count)
                self.assertEqual(tree._root.color, 'black')
                self.assert_contents(tree, set(keys))

    def test_deletion_repair_sequences(self):
        """Deletion repairs black heights for a known sequence and its mirror."""
        keys = [11, 2, 14, 1, 7, 15, 5, 8, 4]

        # Negating the keys mirrors the tree to test the opposite repair direction.
        for sign in (1, -1):
            with self.subTest(sign=sign):
                tree = self.make_tree(sign * key for key in keys)
                expected = set(tree)
                tree.reset_rotation_count()
                for key in [1, 2, 14, 15, 11, 7, 5, 8, 4]:
                    self.assertTrue(tree.delete(sign * key))
                    expected.remove(sign * key)
                    self.assert_contents(tree, expected)
                    self.assertIs(tree._nil.parent, tree._nil)
                self.assertGreater(tree.rotation_count, 0)

    def test_sentinels_are_private_and_remain_black(self):
        """Each instance owns a black self-linked sentinel after deletion."""
        tree, other = self.make_tree([2, 1, 3]), self.make_tree()
        self.assertIsNot(tree._nil, other._nil)
        for key in [2, 1, 3]:
            tree.delete(key)
            self.assertEqual(tree._nil.color, 'black')
            for link in ('parent', 'left', 'right'):
                self.assertIs(getattr(tree._nil, link), tree._nil)
        self.assertIs(tree._root, tree._nil)
        other.validate()

    def test_search_and_failed_mutations_do_not_reshape(self):
        """Lookup, duplicate insertion, and missing deletion preserve shape."""
        tree = self.make_tree(range(15))
        before, count = snapshot(tree), tree.rotation_count
        self.assertTrue(tree.search(1))
        self.assertFalse(tree.search(100))
        self.assertFalse(tree.insert(1))
        self.assertFalse(tree.delete(100))
        self.assertEqual(snapshot(tree), before)
        self.assertEqual(tree.rotation_count, count)

    def test_validation_rejects_color_and_parent_violations(self):
        """Corrupt each red-black-specific invariant independently."""
        cases = [('sentinel', 'sentinel'), ('root', 'Root must be black'),
                 ('parent', 'Incorrect parent'), ('color', 'Invalid color'),
                 ('red_edge', 'Red-red edge'), ('black_height', 'Black height mismatch')]
        for kind, message in cases:
            with self.subTest(kind=kind):
                tree = self.make_tree([4, 2, 6, 1])

                # Corrupt one invariant at a time to isolate the validation failure.
                if kind == 'sentinel': tree._nil.color = 'red'
                elif kind == 'root': tree._root.color = 'red'
                elif kind == 'parent': tree._root.left.parent = tree._nil
                elif kind == 'color': tree._root.left.color = 'invalid'
                elif kind == 'red_edge': tree._root.left.color = 'red'
                else: tree._root.right.color = 'red'
                with self.assertRaisesRegex(AssertionError, message):
                    tree.validate()
