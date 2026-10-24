# AVL tree with unique integer or string keys.

from .base_tree import BaseTree


class _Node:
    """A node stores its key, children, and height."""

    __slots__ = ("key", "left", "right", "height")

    def __init__(self, key):
        """Create a leaf with height zero."""
        self.key = key
        self.left = None
        self.right = None
        self.height = 0


class AVLTree(BaseTree):
    """AVL tree with unique keys and counted rotations."""

    def __init__(self):
        """Start with an empty tree and zero rotations."""
        super().__init__()
        self._root = None
        self._size = 0

    @staticmethod
    def _height(node):
        """Return the stored height, or -1 for a missing child."""
        return -1 if node is None else node.height

    @classmethod
    def _update_height(cls, node):
        """Update this node's height using its children."""
        node.height = 1 + max(cls._height(node.left), cls._height(node.right))

    @classmethod
    def _balance_factor(cls, node):
        """Return left height minus right height."""
        return cls._height(node.left) - cls._height(node.right)

    def _rotate_left(self, node):
        """Rotate left and return the new subtree root."""
        pivot = node.right
        if pivot is None:
            raise AssertionError("Left rotation requires a right child")

        # Move the middle subtree before promoting the right child.
        node.right = pivot.left
        pivot.left = node

        # Update the old root first because it is now a child of the pivot.
        self._update_height(node)
        self._update_height(pivot)
        self._record_rotation()
        return pivot

    def _rotate_right(self, node):
        """Rotate right and return the new subtree root."""
        pivot = node.left
        if pivot is None:
            raise AssertionError("Right rotation requires a left child")

        # Move the middle subtree before promoting the left child.
        node.left = pivot.right
        pivot.right = node

        # Update the old root first because it is now a child of the pivot.
        self._update_height(node)
        self._update_height(pivot)
        self._record_rotation()
        return pivot

    def _rebalance(self, node):
        """Update the height and return a balanced subtree root."""
        self._update_height(node)
        balance = self._balance_factor(node)

        # The left side is too tall; a right-heavy child needs an extra rotation.
        if balance > 1:
            if self._balance_factor(node.left) < 0:
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)

        # The right side is too tall; a left-heavy child needs an extra rotation.
        if balance < -1:
            if self._balance_factor(node.right) > 0:
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        return node

    def insert(self, key):
        """Insert a key and return True if it was new."""
        # A rotation may replace the root; update the count only for a new key.
        self._root, added = self._insert(self._root, key)
        if added:
            self._size += 1
        return added

    def _insert(self, node, key):
        """Insert into this subtree; return its root and whether a key was added."""
        # An empty position is where the new leaf belongs.
        if node is None:
            return _Node(key), True

        # Smaller keys go into the left subtree; larger keys go into the right.
        if key < node.key:
            node.left, added = self._insert(node.left, key)
        elif key > node.key:
            node.right, added = self._insert(node.right, key)
        else:
            # The key already exists, so do not add another node.
            return node, False

        # Rebalance each ancestor on the way back up if a node was added.
        return (self._rebalance(node), True) if added else (node, False)

    def search(self, key):
        """Return True if the key exists; leave the tree unchanged."""
        node = self._root

        # Follow left or right links until the key is found or the path ends.
        while node is not None:
            if key < node.key:
                node = node.left
            elif key > node.key:
                node = node.right
            else:
                return True
        return False

    def delete(self, key):
        """Delete a key and return True if it was present."""
        # Deletion may replace the root; reduce the count only if a key was found.
        self._root, removed = self._delete(self._root, key)
        if removed:
            self._size -= 1
        return removed

    def _delete(self, node, key):
        """Delete from this subtree; return its root and whether a key was removed."""
        # Reaching an empty position means the key is absent.
        if node is None:
            return None, False

        # Find the key in the left or right subtree according to its value.
        if key < node.key:
            node.left, removed = self._delete(node.left, key)
        elif key > node.key:
            node.right, removed = self._delete(node.right, key)
        else:
            # With at most one child, replace this node with that child or None.
            if node.left is None:
                return node.right, True
            if node.right is None:
                return node.left, True

            # With two children, find the smallest key in the right subtree.
            successor = node.right
            while successor.left is not None:
                successor = successor.left

            # Copy the successor key here, then remove its original node.
            node.key = successor.key
            node.right, removed = self._delete(node.right, successor.key)

        # Repair heights and balance on the way back up after a removal.
        return (self._rebalance(node), True) if removed else (node, False)

    def __len__(self):
        """Return the number of stored keys."""
        return self._size

    def height(self):
        """Return the tree height, or -1 if empty."""
        return self._height(self._root)


    def validate(self):
        """Check the tree without changing it; raise AssertionError if invalid."""
        seen = set()
        heights = {}

        # Each entry holds a node, allowed key bounds, and a revisit flag.
        stack = [(self._root, None, None, False)]
        while stack:
            node, lower, upper, visited = stack.pop()
            if node is None:
                continue
            identity = id(node)
            if not visited:
                # Seeing the same object twice means a cycle or shared child.
                if identity in seen:
                    raise AssertionError(f"Cycle or shared child at key {node.key}")
                seen.add(identity)

                # Bounds from all ancestors enforce ordering across whole subtrees.
                if lower is not None and node.key <= lower:
                    raise AssertionError(f"BST ordering violated at key {node.key}: must exceed {lower}")
                if upper is not None and node.key >= upper:
                    raise AssertionError(f"BST ordering violated at key {node.key}: must be below {upper}")

                # Revisit the parent after both children have been checked.
                stack.append((node, lower, upper, True))
                stack.append((node.right, node.key, upper, False))
                stack.append((node.left, lower, node.key, False))
            else:
                # Compute actual heights from the checked children, not stored values.
                left = -1 if node.left is None else heights[id(node.left)]
                right = -1 if node.right is None else heights[id(node.right)]
                actual = 1 + max(left, right)
                if node.height != actual:
                    raise AssertionError(f"Incorrect height at key {node.key}: stored {node.height}, expected {actual}")

                # AVL children may differ in height by at most one.
                if abs(left - right) > 1:
                    raise AssertionError(f"AVL balance violated at key {node.key}: left {left}, right {right}")
                heights[identity] = actual

        # The number of reachable nodes must match the maintained count.
        if len(seen) != self._size:
            raise AssertionError(f"Size mismatch: stored {self._size}, reachable {len(seen)}")
