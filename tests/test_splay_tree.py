"""Splay rotation, access semantics, deep-tree, and validation tests."""

import unittest

from methods import SplayTree
from methods.splay_tree import _Node
from tests.tree_contract import TreeContractTests


def make_shape(keys):
    """Build a plain BST fixture without splaying to isolate rotation cases."""
    tree = SplayTree()
    for key in keys:
        added = _Node(key)
        if tree._root is None:
            tree._root = added
        else:
            node = tree._root
            while True:
                # Build the fixture directly so normal insertion does not splay it.
                side = 'left' if key < node.key else 'right'
                child = getattr(node, side)
                if child is None:
                    setattr(node, side, added)
                    added.parent = node
                    break
                node = child
        tree._size += 1
    return tree


class TestSplayTree(TreeContractTests, unittest.TestCase):
    """Run shared checks plus splay-specific root and rotation expectations."""

    tree_class = SplayTree

    def test_all_splay_rotation_cases(self):
        """Both zig, both zig-zig, and both zig-zag cases use exact counts."""
        cases = [([2, 1], 1, 1), ([1, 2], 2, 1),
                 ([3, 2, 1], 1, 2), ([1, 2, 3], 3, 2),
                 ([3, 1, 2], 2, 2), ([1, 3, 2], 2, 2)]
        for keys, target, rotations in cases:
            with self.subTest(keys=keys):
                tree = make_shape(keys)
                tree.validate()
                self.assertTrue(tree.search(target))
                self.assertEqual(tree._root.key, target)
                self.assertEqual(tree.rotation_count, rotations)
                self.assert_contents(tree, set(keys))
                self.assertTrue(tree.search(target))
                self.assertEqual(tree.rotation_count, rotations)

    def test_insert_and_duplicate_splay_to_root(self):
        """Both new and duplicate insertion make the requested key the root."""
        tree = self.make_tree()
        for key in [8, 2, 12, 5, 10]:
            self.assertTrue(tree.insert(key))
            self.assertEqual(tree._root.key, key)
            tree.validate()
        tree.reset_rotation_count()
        self.assertFalse(tree.insert(2))
        self.assertEqual(tree._root.key, 2)
        self.assertGreater(tree.rotation_count, 0)
        self.assert_contents(tree, {8, 2, 12, 5, 10})

    def test_missing_search_and_delete_splay_last_visited(self):
        """Misses below, within, and above the range splay the last visited node."""
        for operation in ('search', 'delete'):
            for key, last in [(1, 5), (7, 5), (13, 15), (20, 15)]:
                with self.subTest(operation=operation, key=key):
                    tree = make_shape([10, 5, 15])
                    self.assertFalse(getattr(tree, operation)(key))
                    self.assertEqual(tree._root.key, last)
                    self.assertEqual(tree.rotation_count, 1)
                    self.assert_contents(tree, {5, 10, 15})

    def test_delete_joins_subtrees(self):
        """Deleting a root splays its left maximum before attaching the right tree."""
        tree = make_shape([10, 5, 15, 2, 8, 7, 9, 12, 18])
        self.assertTrue(tree.delete(10))
        self.assertEqual(tree._root.key, 9)
        self.assertEqual(tree._root.right.key, 15)
        self.assertEqual(tree.rotation_count, 2)
        self.assert_contents(tree, {2, 5, 7, 8, 9, 12, 15, 18})

    def test_delete_root_with_one_child(self):
        """Root deletion correctly handles either sole subtree."""
        for keys in ([2, 1], [1, 2]):
            with self.subTest(keys=keys):
                tree = make_shape(keys)
                self.assertTrue(tree.delete(keys[0]))
                self.assertIsNone(tree._root.parent)
                self.assert_contents(tree, {keys[1]})

    def test_deep_chains_do_not_require_recursion(self):
        """Valid 3,000-node chains support observers, search, and deletion."""
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                keys = sorted(range(3000), reverse=reverse)
                tree = self.make_tree(keys)

                # A valid splay chain can be deeper than the usual recursion limit.
                self.assertEqual(tree.height(), 2999)
                self.assert_contents(tree, set(keys))
                self.assertTrue(tree.search(keys[0]))
                self.assertEqual(tree._root.key, keys[0])
                tree.validate()
                for key in keys:
                    self.assertTrue(tree.delete(key))
                self.assert_contents(tree, set())

    def test_validation_rejects_bad_parent_links(self):
        """Both root and child parent pointers must agree with actual structure."""
        for root in (True, False):
            tree = make_shape([2, 1, 3])
            if root:
                tree._root.parent = tree._root.left
            else:
                tree._root.left.parent = None
            with self.assertRaisesRegex(AssertionError, 'Incorrect parent'):
                tree.validate()
