"""Tree implementations and their shared interface."""

# Expose the interface and implementations through the methods package.
from .base_tree import BaseTree
from .avl_tree import AVLTree
from .red_black_tree import RedBlackTree
from .splay_tree import SplayTree

__all__ = ["BaseTree", "AVLTree", "RedBlackTree", "SplayTree"]
