"""Shared integer/string-key tree interface and rotation instrumentation."""

from abc import ABC, abstractmethod


class BaseTree(ABC):
    """Common contract for AVL, red-black, and splay trees.

    Store unique integer or string keys without associated values. Each tree
    must contain one consistent key type; mixing integers and strings is
    unsupported. Strings use case-sensitive Python lexicographic ordering.
    Concrete trees must support construction without arguments, start empty,
    and call super().__init__() to initialize rotation instrumentation.

    Implementations manage their own nodes, balancing, and size. Insert,
    search, and delete may reorganize nodes even when returning False. Height
    measurement, iteration, and validation must preserve the tree and rotation
    counter, and should run outside benchmark timing.
    """
    def __init__(self):
        """Take no arguments and initialize the rotation count to zero."""
        self._rotation_count = 0

    @property
    def rotation_count(self):
        """Return cumulative primitive rotations since construction or reset.

        This read-only property counts each left or right rotation as one.
        Double rotations, including splay zig-zig and zig-zag steps, count as
        two. Count rotations in all operations, including unsuccessful
        operations. Recoloring and other non-rotation updates do not count.
        """
        return self._rotation_count

    def reset_rotation_count(self):
        """Take no arguments and reset the counter; return None.

        Preserve the stored keys, tree shape, and size. Use this before each
        benchmark phase to measure that phase's rotations independently.
        """
        self._rotation_count = 0

    def _record_rotation(self):
        """Take no arguments and record one primitive rotation; return None.

        Concrete implementations call this helper exactly once per completed
        left or right rotation, not again for a composite rotation step.
        """
        self._rotation_count += 1

    @abstractmethod
    def insert(self, key):
        """Insert key; return True if added, False if already present.

        Duplicate insertion preserves the stored keys and size, but may
        reorganize nodes and perform rotations.
        """
        raise NotImplementedError

    @abstractmethod
    def search(self, key):
        """Find key; return True if present, otherwise False.

        An empty tree returns False. Successful and unsuccessful searches may
        reorganize nodes but must preserve stored keys and size.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, key):
        """Remove key; return True if removed, False if absent.

        A missing key, including in an empty tree, leaves stored keys and size
        unchanged, but may still trigger restructuring and rotations.
        """
        raise NotImplementedError

    @abstractmethod
    def __len__(self):
        """Take no arguments and return the number of unique stored keys.

        Maintain a count for O(1) access; an empty tree returns zero.
        """
        raise NotImplementedError

    @abstractmethod
    def height(self):
        """Take no arguments and return the maximum root-to-leaf edge count.

        Return -1 for an empty tree and 0 for a single node. Preserve tree
        shape and counters. Computing height need not take O(1).
        """
        raise NotImplementedError

    def _is_empty_node(self, node):
        """Return whether this link represents a missing child."""
        return node is None

    def __iter__(self):
        """Yield keys in sorted order without changing the tree.

        Trees provide _root and nodes with key, left, and right attributes. An
        empty tree yields nothing; changing the tree during iteration is
        unsupported.
        """
        stack = []
        node = self._root
        while stack or not self._is_empty_node(node):
            # Save ancestors while moving to the smallest remaining key.
            while not self._is_empty_node(node):
                stack.append(node)
                node = node.left

            # Yield this key, then explore its right subtree.
            node = stack.pop()
            yield node.key
            node = node.right

    @abstractmethod
    def validate(self):
        """Take no arguments; return None if valid, otherwise raise AssertionError.

        Report a useful explanation for each detected violation. Check strict
        BST ordering throughout subtrees, reachable node count against size,
        absence of cycles or shared child nodes, and parent pointers if used.
        Exclude sentinel nodes from the stored-key count.

        AVL trees also check stored heights and balance factors. Red-black
        trees check valid colors, a black root, black missing-child sentinels,
        no red-red parent/child edges, and equal black height on all paths from
        each node to a missing child. Splay trees have no extra balance rule.
        An empty tree is valid when its size is zero.

        Inspect without modifying nodes, stored metadata, or counters.
        """
        raise NotImplementedError
