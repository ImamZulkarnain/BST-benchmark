"""Reusable tree correctness checks and test fixtures."""

import random
from collections import deque


def snapshot(tree):
    """Return node identities, links, and metadata to detect unwanted mutation."""
    # Red-black uses a sentinel; other trees use None for missing children.
    nil = getattr(tree, '_nil', None)
    result = []
    stack = [tree._root]
    while stack:
        node = stack.pop()
        if node is nil:
            continue
        result.append((id(node), node.key, id(node.left), id(node.right),
                       id(getattr(node, 'parent', None)),
                       getattr(node, 'height', None), getattr(node, 'color', None)))
        stack.extend((node.left, node.right))
    return id(tree._root), len(tree), tuple(result)


def measured_height(tree):
    """Independently measure edge height using breadth-first traversal."""
    # Red-black uses a sentinel; other trees use None for missing children.
    nil = getattr(tree, '_nil', None)
    queue = deque([] if tree._root is nil else [(tree._root, 0)])
    height = -1
    while queue:
        node, height = queue.popleft()
        for child in (node.left, node.right):
            if child is not nil:
                queue.append((child, height + 1))
    return height


class TreeContractTests:
    """Inherited tests executed separately for each concrete tree class."""

    def make_tree(self, keys=()):
        """Build and return this test class's tree from an iterable of keys."""
        tree = self.tree_class()
        for key in keys:
            tree.insert(key)
        return tree

    def assert_contents(self, tree, expected):
        """Compare keys, count, height, and invariants against independent expectations."""
        self.assertEqual(list(tree), sorted(expected))
        self.assertEqual(len(tree), len(expected))

        # Compare with an independent height calculation.
        self.assertEqual(tree.height(), measured_height(tree))
        self.assertIsNone(tree.validate())

    def test_empty_tree(self):
        """Empty operations return the specified values without rotations."""
        tree = self.make_tree()
        self.assert_contents(tree, set())
        self.assertEqual(tree.height(), -1)
        self.assertIs(tree.search(1), False)
        self.assertIs(tree.delete(1), False)
        self.assertEqual(tree.rotation_count, 0)

    def test_singleton_delete_and_reuse(self):
        """A tree can transition from empty to singleton and back repeatedly."""
        tree = self.make_tree()
        for key in (0, -1, 10**100):
            self.assertIs(tree.insert(key), True)
            self.assertEqual(tree.height(), 0)
            self.assertIs(tree.search(key), True)
            self.assertIs(tree.insert(key), False)
            self.assert_contents(tree, {key})
            self.assertIs(tree.delete(key), True)
            self.assertIs(tree.delete(key), False)
            self.assert_contents(tree, set())

    def test_duplicates_and_missing_keys(self):
        """Duplicates and failed operations preserve keys and size."""
        keys = {-10**100, -3, 0, 7, 10**100}
        tree = self.make_tree(sorted(keys))
        for key in sorted(keys):
            self.assertIs(tree.insert(key), False)
            self.assertIs(tree.search(key), True)
            self.assert_contents(tree, keys)
        for key in (-4, 1, 8):
            self.assertIs(tree.search(key), False)
            self.assertIs(tree.delete(key), False)
            self.assert_contents(tree, keys)

    def test_observers_and_counter_reset_preserve_structure(self):
        """Iteration, height, validation, and counter reset do not reshape nodes."""
        tree = self.make_tree(range(20))
        before = snapshot(tree)
        count = tree.rotation_count
        self.assertGreater(count, 0)
        self.assert_contents(tree, set(range(20)))
        self.assertEqual(snapshot(tree), before)
        self.assertEqual(tree.rotation_count, count)
        self.assertIsNone(tree.reset_rotation_count())
        self.assertEqual(tree.rotation_count, 0)
        self.assertEqual(snapshot(tree), before)
        with self.assertRaises(AttributeError):
            tree.rotation_count = 99

    def test_iterators_are_independent(self):
        """Two iterators can traverse the same unchanged tree independently."""
        tree = self.make_tree([3, 1, 2])
        first, second = iter(tree), iter(tree)
        self.assertEqual(next(first), 1)
        self.assertEqual(list(second), [1, 2, 3])
        self.assertEqual(list(first), [2, 3])

    def test_deletion_orders(self):
        """Ascending, descending, and shuffled deletions preserve remaining keys."""
        for mode in ('ascending', 'descending', 'shuffled'):
            with self.subTest(mode=mode):
                keys = list(range(80))
                random.Random(17).shuffle(keys)
                tree = self.make_tree(keys)
                order = sorted(keys, reverse=mode == 'descending')
                if mode == 'shuffled':
                    random.Random(42).shuffle(order)
                expected = set(keys)
                for key in order:
                    self.assertIs(tree.delete(key), True)
                    expected.remove(key)
                    self.assert_contents(tree, expected)

    def test_repeated_root_deletion(self):
        """Removing the current root repeatedly eventually empties the tree."""
        tree = self.make_tree([8, 4, 12, 2, 6, 10, 14, 1, 3, 5, 7, 9, 11, 13, 15])
        expected = set(tree)
        while expected:
            key = tree._root.key
            self.assertIs(tree.delete(key), True)
            expected.remove(key)
            self.assert_contents(tree, expected)

    def test_randomized_operations_against_set(self):
        """Reproducible mixed operations agree with Python's independent set model."""
        # Fixed seeds make a failing random sequence reproducible.
        for seed in (0, 7, 42):
            tree, expected = self.make_tree(), set()
            rng = random.Random(seed)
            for step in range(600):
                key, operation = rng.randrange(-100, 101), rng.randrange(3)
                with self.subTest(seed=seed, step=step, key=key, operation=operation):
                    # Apply the same operation to a Python set as an independent reference.
                    if operation == 0:
                        self.assertIs(tree.insert(key), key not in expected)
                        expected.add(key)
                    elif operation == 1:
                        self.assertIs(tree.delete(key), key in expected)
                        expected.discard(key)
                    else:
                        self.assertIs(tree.search(key), key in expected)
                    self.assert_contents(tree, expected)

    def test_instances_are_independent(self):
        """Mutations and counter resets in one instance do not affect another."""
        first, second = self.make_tree(range(5)), self.make_tree(range(5))
        before, count = snapshot(second), second.rotation_count
        first.delete(2)
        first.reset_rotation_count()
        self.assertEqual(snapshot(second), before)
        self.assertEqual(second.rotation_count, count)
        self.assert_contents(second, set(range(5)))

    def test_validation_rejects_size_mismatch(self):
        """Validation detects a wrong stored size, even on an empty tree."""
        for keys in ([], [1, 2, 3]):
            tree = self.make_tree(keys)
            tree._size += 1
            with self.assertRaisesRegex(AssertionError, 'Size mismatch'):
                tree.validate()

    def test_validation_rejects_order_cycle_and_shared_child(self):
        """Validation detects corrupt ordering, cycles, and reused children."""
        for kind in ('order', 'cycle', 'shared'):
            with self.subTest(kind=kind):
                tree = self.make_tree([1, 3, 2])

                # Break one rule at a time and check that validation rejects the tree.
                if kind == 'order':
                    tree._root.left.key = 100
                elif kind == 'cycle':
                    tree._root.left.left = tree._root
                else:
                    tree._root.right = tree._root.left
                with self.assertRaisesRegex(AssertionError, 'BST ordering|Cycle or shared'):
                    tree.validate()

    def test_alphanumeric_string_operations(self):
        """String keys preserve case-sensitive ordering through every operation."""
        keys = ['A000000001', 'a000000001', '0000000000', 'Z9b8C7d6E5',
                'Ab12Cd34Ef56Gh78Ij90Kl12', 'A000000010', 'A000000002']
        tree = self.make_tree()
        expected = set()
        for key in keys:
            self.assertIs(tree.insert(key), True)
            expected.add(key)
            self.assert_contents(tree, expected)
        for key in keys:
            self.assertIs(tree.search(key), True)
            self.assertIs(tree.insert(key), False)
        self.assertIs(tree.search('Missing12345'), False)
        self.assertIs(tree.delete('Missing12345'), False)
        self.assert_contents(tree, expected)
        for key in keys:
            self.assertIs(tree.delete(key), True)
            expected.remove(key)
            self.assert_contents(tree, expected)
