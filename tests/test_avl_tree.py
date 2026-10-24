"""AVL-specific balancing and validation tests."""

import unittest

from methods import AVLTree
from methods.avl_tree import _Node
from tests.tree_contract import TreeContractTests, snapshot


class TestAVLTree(TreeContractTests, unittest.TestCase):
    """Run the shared contract plus AVL-specific checks."""

    tree_class = AVLTree

    def test_insertion_rotation_cases(self):
        """LL/RR count once; LR/RL count twice and produce a balanced root."""
        for keys, count in (([3, 2, 1], 1), ([1, 2, 3], 1),
                            ([3, 1, 2], 2), ([1, 3, 2], 2)):
            with self.subTest(keys=keys):
                tree = self.make_tree(keys)
                self.assertEqual(tree._root.key, 2)
                self.assertEqual(tree.rotation_count, count)
                self.assertEqual(tree.height(), 1)
                self.assert_contents(tree, {1, 2, 3})

    def test_deletion_rotation_cases(self):
        """Deletion handles zero-balance children and double rotations both ways."""
        cases = [([4, 2, 5, 1, 3], 5, 1), ([2, 1, 4, 3, 5], 1, 1),
                 ([5, 2, 7, 1, 4, 6, 3], 6, 2),
                 ([3, 6, 1, 7, 4, 2, 5], 2, 2)]
        for keys, deleted, rotations in cases:
            with self.subTest(keys=keys):
                tree = self.make_tree(keys)

                # Count only the rotations caused by deletion.
                tree.reset_rotation_count()
                self.assertTrue(tree.delete(deleted))
                self.assertEqual(tree.rotation_count, rotations)
                self.assert_contents(tree, set(keys) - {deleted})

    def test_search_and_failed_mutations_do_not_reshape(self):
        """AVL lookup, duplicate insertion, and missing deletion are observational."""
        tree = self.make_tree(range(15))
        before, count = snapshot(tree), tree.rotation_count
        self.assertTrue(tree.search(1))
        self.assertFalse(tree.search(100))
        self.assertFalse(tree.insert(1))
        self.assertFalse(tree.delete(100))
        self.assertEqual(snapshot(tree), before)
        self.assertEqual(tree.rotation_count, count)

    def test_validation_rejects_stale_height(self):
        """Validation recomputes height instead of trusting cached metadata."""
        tree = self.make_tree([2, 1, 3])
        tree._root.height += 1
        with self.assertRaisesRegex(AssertionError, 'Incorrect height'):
            tree.validate()

    def test_validation_rejects_unbalanced_tree_with_correct_heights(self):
        """Correct height metadata alone does not make an unbalanced tree valid."""
        tree = self.make_tree()

        # Build an invalid chain with correct heights to isolate the balance check.
        tree._root = _Node(3)
        tree._root.left = _Node(2)
        tree._root.left.left = _Node(1)
        tree._root.left.height = 1
        tree._root.height = 2
        tree._size = 3
        with self.assertRaisesRegex(AssertionError, 'AVL balance violated'):
            tree.validate()
