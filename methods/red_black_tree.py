"""Red-black integer/string-key tree with parent links and a shared black sentinel."""


from .base_tree import BaseTree

_RED = "red"
_BLACK = "black"


class _Node:
    """A compact node; the sentinel's key is never compared or yielded."""

    __slots__ = ("key", "color", "left", "right", "parent")

    def __init__(self, key, color = _RED):
        """Create a node with key and color and initially self-linked pointers."""
        self.key = key
        self.color = color
        self.left = self.right = self.parent = self


class RedBlackTree(BaseTree):
    """Unique integer or string set with O(log n) search, insertion, and deletion.

    Bounds count key comparisons; string comparison depends on key length.
    Storage is O(n); size lookup is O(1). Height measurement takes O(n) time
    and O(log n) auxiliary space on a valid tree. Recoloring is not counted as
    a rotation. Each tree owns its own black leaf sentinel.
    """
    def __init__(self):
        """Create an empty tree with zero size and rotations."""
        super().__init__()

        # One black sentinel stands for all missing children; its key is ignored.
        self._nil = _Node(0, _BLACK)
        self._root = self._nil
        self._size = 0

    def _rotate_left(self, node):
        """Rotate node toward its right child, update links, and count once."""
        pivot = node.right
        if pivot is self._nil:
            raise AssertionError("Left rotation requires a right child")

        # Move the middle subtree before promoting the right child.
        node.right = pivot.left
        if pivot.left is not self._nil:
            pivot.left.parent = node

        # Reconnect the promoted child to the old parent or tree root.
        pivot.parent = node.parent
        if node.parent is self._nil:
            self._root = pivot
        elif node is node.parent.left:
            node.parent.left = pivot
        else:
            node.parent.right = pivot
        pivot.left = node
        node.parent = pivot
        self._record_rotation()

    def _rotate_right(self, node):
        """Rotate node toward its left child, update links, and count once."""
        pivot = node.left
        if pivot is self._nil:
            raise AssertionError("Right rotation requires a left child")

        # Move the middle subtree before promoting the left child.
        node.left = pivot.right
        if pivot.right is not self._nil:
            pivot.right.parent = node

        # Reconnect the promoted child to the old parent or tree root.
        pivot.parent = node.parent
        if node.parent is self._nil:
            self._root = pivot
        elif node is node.parent.right:
            node.parent.right = pivot
        else:
            node.parent.left = pivot
        pivot.right = node
        node.parent = pivot
        self._record_rotation()

    def _find(self, key):
        """Return the node matching key, or the sentinel if absent."""
        node = self._root
        while node is not self._nil:
            # Smaller keys go left; larger keys go right.
            if key < node.key:
                node = node.left
            elif key > node.key:
                node = node.right
            else:
                return node
        return self._nil

    def search(self, key):
        """Return whether key exists without modifying the tree or counters."""
        return self._find(key) is not self._nil

    def insert(self, key):
        """Insert key and return True; return False unchanged for a duplicate."""
        parent = self._nil
        node = self._root
        while node is not self._nil:
            parent = node

            # Smaller keys go left; larger keys go right.
            if key < node.key:
                node = node.left
            elif key > node.key:
                node = node.right
            else:
                return False

        # Attach a new red leaf where the search reached an empty link.
        added = _Node(key)
        added.left = added.right = self._nil
        added.parent = parent
        if parent is self._nil:
            self._root = added
        elif key < parent.key:
            parent.left = added
        else:
            parent.right = added
        self._fix_insert(added)
        self._size += 1
        return True

    def _fix_insert(self, node):
        """Repair red-red edges above an inserted node; return None."""
        # Repair upward while a red node has a red parent.
        while node.parent.color == _RED:
            if node.parent is node.parent.parent.left:
                uncle = node.parent.parent.right

                # Recolor a red parent and uncle, then check the grandparent.
                if uncle.color == _RED:
                    node.parent.color = uncle.color = _BLACK
                    node.parent.parent.color = _RED
                    node = node.parent.parent
                else:
                    # Straighten the left-right bend before rotating the grandparent.
                    if node is node.parent.right:
                        node = node.parent
                        self._rotate_left(node)
                    node.parent.color = _BLACK
                    node.parent.parent.color = _RED
                    self._rotate_right(node.parent.parent)
            else:
                uncle = node.parent.parent.left

                # Recolor a red parent and uncle, then check the grandparent.
                if uncle.color == _RED:
                    node.parent.color = uncle.color = _BLACK
                    node.parent.parent.color = _RED
                    node = node.parent.parent
                else:
                    # Mirror case: straighten the right-left bend first.
                    if node is node.parent.left:
                        node = node.parent
                        self._rotate_right(node)
                    node.parent.color = _BLACK
                    node.parent.parent.color = _RED
                    self._rotate_left(node.parent.parent)

        # The root must stay black after insertion.
        self._root.color = _BLACK

    def _transplant(self, old, new):
        """Replace old's subtree with new, including its parent link; return None."""
        if old.parent is self._nil:
            self._root = new
        elif old is old.parent.left:
            old.parent.left = new
        else:
            old.parent.right = new

        # A temporary sentinel parent lets deletion repair a missing child.
        new.parent = old.parent

    def delete(self, key):
        """Remove key and return True; return False unchanged if absent."""
        target = self._find(key)
        if target is self._nil:
            return False
        removed = target
        original_color = removed.color

        # With at most one child, replace the target directly.
        if target.left is self._nil:
            replacement = target.right
            self._transplant(target, replacement)
        elif target.right is self._nil:
            replacement = target.left
            self._transplant(target, replacement)
        else:
            # With two children, find the smallest node in the right subtree.
            removed = target.right
            while removed.left is not self._nil:
                removed = removed.left
            original_color = removed.color
            replacement = removed.right
            if removed.parent is target:
                replacement.parent = removed
            else:
                # Detach the successor before moving it to the target position.
                self._transplant(removed, replacement)
                removed.right = target.right
                removed.right.parent = removed
            self._transplant(target, removed)
            removed.left = target.left
            removed.left.parent = removed
            removed.color = target.color

        # Removing a black node can leave a path short of one black node.
        if original_color == _BLACK:
            self._fix_delete(replacement)
        self._size -= 1

        # Do not retain a deleted node through the sentinel's temporary parent.
        self._nil.parent = self._nil
        return True

    def _fix_delete(self, node):
        """Restore black heights after removing a black node; return None."""
        while node is not self._root and node.color == _BLACK:
            # Mirror case: straighten the right-left bend first.
            if node is node.parent.left:
                sibling = node.parent.right

                # Rotate a red sibling so the new sibling is black.
                if sibling.color == _RED:
                    sibling.color = _BLACK
                    node.parent.color = _RED
                    self._rotate_left(node.parent)
                    sibling = node.parent.right

                # Two black children let us recolor the sibling and move the repair upward.
                if sibling.left.color == _BLACK and sibling.right.color == _BLACK:
                    sibling.color = _RED
                    node = node.parent
                else:
                    # Prepare the far child for the final left rotation.
                    if sibling.right.color == _BLACK:
                        sibling.left.color = _BLACK
                        sibling.color = _RED
                        self._rotate_right(sibling)
                        sibling = node.parent.right

                    # Transfer the parent color and rotate to finish this repair.
                    sibling.color = node.parent.color
                    node.parent.color = _BLACK
                    sibling.right.color = _BLACK
                    self._rotate_left(node.parent)
                    node = self._root
            else:
                sibling = node.parent.left

                # Rotate a red sibling so the new sibling is black.
                if sibling.color == _RED:
                    sibling.color = _BLACK
                    node.parent.color = _RED
                    self._rotate_right(node.parent)
                    sibling = node.parent.left

                # Mirror case: recolor and move upward when both children are black.
                if sibling.right.color == _BLACK and sibling.left.color == _BLACK:
                    sibling.color = _RED
                    node = node.parent
                else:
                    # Prepare the far child for the final right rotation.
                    if sibling.left.color == _BLACK:
                        sibling.right.color = _BLACK
                        sibling.color = _RED
                        self._rotate_left(sibling)
                        sibling = node.parent.left

                    # Transfer the parent color and rotate to finish this repair.
                    sibling.color = node.parent.color
                    node.parent.color = _BLACK
                    sibling.left.color = _BLACK
                    self._rotate_right(node.parent)
                    node = self._root
        node.color = _BLACK

    def __len__(self):
        """Take no arguments and return the number of stored keys in O(1)."""
        return self._size

    def height(self):
        """Return maximum root-to-leaf edge count, or -1 for an empty tree."""
        if self._root is self._nil:
            return -1
        maximum = 0

        # Track depths with a stack to handle deep trees without recursion.
        stack = [(self._root, 0)]
        while stack:
            node, depth = stack.pop()
            maximum = max(maximum, depth)
            if node.left is not self._nil:
                stack.append((node.left, depth + 1))
            if node.right is not self._nil:
                stack.append((node.right, depth + 1))
        return maximum

    def _is_empty_node(self, node):
        """Return whether this link is the black sentinel."""
        return node is self._nil

    def validate(self):
        """Return None if valid; otherwise raise a descriptive AssertionError.

        Check sentinel, ordering, parent links, structure, size, colors, red-
        red edges, and equal black heights. Take no arguments and make no
        changes. Validation takes O(n) time and O(n) auxiliary space.
        """
        nil = self._nil
        if nil.color != _BLACK or nil.left is not nil or nil.right is not nil or nil.parent is not nil:
            raise AssertionError("Invalid black sentinel or sentinel links")
        if not isinstance(self._root, _Node):
            raise AssertionError("Root must be a node or the sentinel")
        if self._root.parent is not nil:
            raise AssertionError("Root parent must be the sentinel")
        if self._root.color != _BLACK:
            raise AssertionError("Root must be black")
        seen = set()

        # Each missing child contributes one black sentinel to its path.
        black_heights = {id(nil): 1}
        stack = [(self._root, None, None, nil, False)]
        while stack:
            node, lower, upper, parent, visited = stack.pop()
            if node is nil:
                continue
            if not isinstance(node, _Node):
                raise AssertionError("Child must be a node or the sentinel")
            identity = id(node)
            if not visited:
                # A repeated object means a cycle or a shared child.
                if identity in seen:
                    raise AssertionError(f"Cycle or shared child at key {node.key}")
                seen.add(identity)
                if node.parent is not parent:
                    raise AssertionError(f"Incorrect parent at key {node.key}")

                # Ancestor bounds check ordering throughout the whole subtree.
                if lower is not None and node.key <= lower:
                    raise AssertionError(f"BST ordering violated at key {node.key}: must exceed {lower}")
                if upper is not None and node.key >= upper:
                    raise AssertionError(f"BST ordering violated at key {node.key}: must be below {upper}")
                if node.color not in (_RED, _BLACK):
                    raise AssertionError(f"Invalid color at key {node.key}")
                if node.color == _RED and parent.color == _RED:
                    raise AssertionError(f"Red-red edge at key {node.key}")

                # Check children first, then return to compare their black heights.
                stack.append((node, lower, upper, parent, True))
                stack.append((node.right, node.key, upper, node, False))
                stack.append((node.left, lower, node.key, node, False))
            else:
                left = black_heights[id(node.left)]
                right = black_heights[id(node.right)]

                # Both child paths must contain the same number of black nodes.
                if left != right:
                    raise AssertionError(f"Black height mismatch at key {node.key}: left {left}, right {right}")
                black_heights[identity] = left + (node.color == _BLACK)

        # The reachable node count must match the stored size.
        if len(seen) != self._size:
            raise AssertionError(f"Size mismatch: stored {self._size}, reachable {len(seen)}")
