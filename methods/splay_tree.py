"""Bottom-up splay tree with parent links and counted primitive rotations."""


from .base_tree import BaseTree


class _Node:
    """A compact integer/string-key node with child and parent links."""

    __slots__ = ("key", "left", "right", "parent")

    def __init__(self, key):
        """Create a leaf containing key with no parent; return None."""
        self.key = key
        self.left = None
        self.right = None
        self.parent = None


class SplayTree(BaseTree):
    """Unique integer or string set with amortized O(log n) search, insert, and delete.

    Bounds count key comparisons; string comparison depends on key length. An
    individual operation can take O(n); height can be n - 1. Storage is O(n).
    All traversals and updates are iterative, so a valid deep tree does not
    exhaust Python's recursion limit. Updates use O(1) auxiliary space; height
    and iteration use O(h), where h is the tree height.
    """
    def __init__(self):
        """Create an empty tree with zero size and rotation count."""
        super().__init__()
        self._root = None
        self._size = 0

    def _rotate_left(self, node):
        """Rotate node toward its right child, repair links, and count once."""
        pivot = node.right
        if pivot is None:
            raise AssertionError("Left rotation requires a right child")

        # Move the middle subtree before promoting the right child.
        node.right = pivot.left
        if pivot.left is not None:
            pivot.left.parent = node

        # Reconnect the promoted child to the old parent or tree root.
        pivot.parent = node.parent
        if node.parent is None:
            self._root = pivot
        elif node is node.parent.left:
            node.parent.left = pivot
        else:
            node.parent.right = pivot
        pivot.left = node
        node.parent = pivot
        self._record_rotation()

    def _rotate_right(self, node):
        """Rotate node toward its left child, repair links, and count once."""
        pivot = node.left
        if pivot is None:
            raise AssertionError("Right rotation requires a left child")

        # Move the middle subtree before promoting the left child.
        node.left = pivot.right
        if pivot.right is not None:
            pivot.right.parent = node

        # Reconnect the promoted child to the old parent or tree root.
        pivot.parent = node.parent
        if node.parent is None:
            self._root = pivot
        elif node is node.parent.right:
            node.parent.right = pivot
        else:
            node.parent.left = pivot
        pivot.right = node
        node.parent = pivot
        self._record_rotation()

    def _splay(self, node):
        """Move an existing node to the root with zig, zig-zig, or zig-zag steps."""
        while node.parent is not None:
            parent = node.parent
            grandparent = parent.parent
            if grandparent is None:
                # Zig: node is a direct child of the root.
                if node is parent.left:
                    self._rotate_right(parent)
                else:
                    self._rotate_left(parent)

            # Left-left zig-zig rotates the grandparent, then the parent.
            elif node is parent.left and parent is grandparent.left:
                self._rotate_right(grandparent)
                self._rotate_right(parent)

            # Right-right zig-zig performs two left rotations.
            elif node is parent.right and parent is grandparent.right:
                self._rotate_left(grandparent)
                self._rotate_left(parent)

            # Left-right zig-zag rotates the parent, then the grandparent.
            elif node is parent.right and parent is grandparent.left:
                self._rotate_left(parent)
                self._rotate_right(grandparent)
            else:
                self._rotate_right(parent)
                self._rotate_left(grandparent)

    def search(self, key):
        """Return whether key exists, splaying the match or last visited node.

        An empty tree returns False without rotating. An unsuccessful search
        may rotate nodes but preserves stored keys and size.
        """
        node = self._root
        last = None
        while node is not None:
            # Remember the last visited node in case the key is missing.
            last = node

            # Smaller keys go left; larger keys go right.
            if key < node.key:
                node = node.left
            elif key > node.key:
                node = node.right
            else:
                self._splay(node)
                return True

        # An unsuccessful search still moves this node to the root.
        if last is not None:
            self._splay(last)
        return False

    def insert(self, key):
        """Insert key and splay it to the root; return whether it was new.

        A duplicate returns False but splays the existing node to the root.
        """
        if self._root is None:
            self._root = _Node(key)
            self._size = 1
            return True
        node = self._root
        while True:
            # Smaller keys go left; larger keys go right.
            if key < node.key:
                if node.left is None:
                    added = _Node(key)
                    node.left = added
                    break
                node = node.left
            elif key > node.key:
                if node.right is None:
                    added = _Node(key)
                    node.right = added
                    break
                node = node.right
            else:
                self._splay(node)
                return False

        # Attach the new leaf before moving it to the root.
        added.parent = node
        self._size += 1
        self._splay(added)
        return True

    def delete(self, key):
        """Splay and remove key, joining its subtrees; return whether removed.

        If key is absent, splay the last visited node and return False. To join
        two subtrees, splay the maximum of the left subtree and attach the
        right subtree as its right child.
        """
        # Search moves the matching key to the root before deletion.
        if not self.search(key):
            return False
        removed = self._root

        # Detach the subtrees so they can be joined without the removed root.
        left, right = removed.left, removed.right
        if left is not None:
            left.parent = None
        if right is not None:
            right.parent = None
        removed.left = removed.right = None
        if left is None:
            self._root = right
        else:
            self._root = left

            # The largest left key has an empty right link for the other subtree.
            maximum = left
            while maximum.right is not None:
                maximum = maximum.right

            # Promote that maximum before attaching the right subtree.
            self._splay(maximum)
            maximum.right = right
            if right is not None:
                right.parent = maximum
        self._size -= 1
        return True

    def __len__(self):
        """Take no arguments and return the stored key count in O(1)."""
        return self._size

    def height(self):
        """Return maximum root-to-leaf edge count in O(n), or -1 when empty."""
        if self._root is None:
            return -1
        maximum = 0

        # Track depths with a stack to handle deep trees without recursion.
        stack = [(self._root, 0)]
        while stack:
            node, depth = stack.pop()
            maximum = max(maximum, depth)
            if node.left is not None:
                stack.append((node.left, depth + 1))
            if node.right is not None:
                stack.append((node.right, depth + 1))
        return maximum


    def validate(self):
        """Return None if valid, otherwise raise a descriptive AssertionError.

        Take no arguments and check BST ordering, parent links, cycles, shared
        children, and size without mutation. There is no balance constraint.
        Validation takes O(n) time and O(n) auxiliary space.
        """
        seen = set()

        # Track each node with its allowed key bounds and expected parent.
        stack = [(self._root, None, None, None)]
        while stack:
            node, lower, upper, parent = stack.pop()
            if node is None:
                continue
            if not isinstance(node, _Node):
                raise AssertionError("Root and children must be nodes or None")
            identity = id(node)

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
            stack.append((node.right, node.key, upper, node))
            stack.append((node.left, lower, node.key, node))

        # The reachable node count must match the stored size.
        if len(seen) != self._size:
            raise AssertionError(f"Size mismatch: stored {self._size}, reachable {len(seen)}")
