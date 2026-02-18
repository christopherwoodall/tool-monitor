# merkle.py
# SHA-256 Merkle tree for plan integrity verification.
#
# Guarantees: a committed plan cannot be silently mutated between the safety
# gate and execution. Any tampered step causes verify_leaf() to return False
# before the tool model ever receives that node.
#
# stdlib only — zero external dependencies.

import hashlib
import json
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _serialize(step: dict[str, Any]) -> str:
    """Deterministic serialization. sort_keys is non-negotiable."""
    return json.dumps(step, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# MerkleTree
# ---------------------------------------------------------------------------

class MerkleTree:
    """
    Builds a binary SHA-256 Merkle tree from a list of plan step dicts.

    Leaf  = SHA256(json.dumps(step, sort_keys=True))
    Node  = SHA256(left_child + right_child)
    Root  = single hash representing the entire plan

    Odd-length layers duplicate the last node before pairing — standard
    Bitcoin-style Merkle construction.
    """

    def __init__(self, steps: list[dict[str, Any]]) -> None:
        if not steps:
            raise ValueError("Cannot build a Merkle tree from an empty step list.")

        self._leaves: list[str] = [_sha256(_serialize(s)) for s in steps]
        self._root: str = self._build_tree(list(self._leaves))

    # ------------------------------------------------------------------
    # Tree construction
    # ------------------------------------------------------------------

    def _build_tree(self, nodes: list[str]) -> str:
        """Recursively reduce a layer of nodes to a single root hash."""
        if len(nodes) == 1:
            return nodes[0]

        # Pad odd-length layers by duplicating the last node.
        if len(nodes) % 2 != 0:
            nodes = nodes + [nodes[-1]]

        parents = [
            _sha256(nodes[i] + nodes[i + 1])
            for i in range(0, len(nodes), 2)
        ]
        return self._build_tree(parents)

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_leaf(self, index: int, step: dict[str, Any]) -> bool:
        """
        Recompute the leaf hash for `step` and compare against the stored value.

        Returns False immediately on any mismatch or out-of-bounds index.
        Callers must treat False as a hard halt — do not retry or recover.
        """
        if index < 0 or index >= len(self._leaves):
            return False
        return _sha256(_serialize(step)) == self._leaves[index]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def root(self) -> str:
        """Hex-encoded SHA-256 root hash of the committed plan."""
        return self._root

    @property
    def leaves(self) -> list[str]:
        """Shallow copy of leaf hashes in step order."""
        return list(self._leaves)
