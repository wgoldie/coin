from __future__ import annotations
import abc
import typing
from dataclasses import dataclass
from coin.util import hash_byte_sets


class CoinHashable(typing.Protocol):
    def hash(self) -> bytes:
        ...


P = typing.TypeVar("P", bound=CoinHashable)


class MerkleNode(abc.ABC, typing.Generic[P]):
    height: int
    payload: P

    def get_parents(self) -> typing.Iterable[MerkleNode[P]]:
        ...

    def node_hash(self) -> bytes:
        pass

    def __str__(self) -> str:
        return f"{self.height} {str(self.node_hash())}"

    def print_children(self) -> str:
        pass


class NullMerkleNode(MerkleNode[typing.Any]):
    height: int = 0

    def get_parents(self) -> typing.Iterable[MerkleNode[typing.Any]]:
        return tuple()

    def node_hash(self) -> bytes:
        return b""


@dataclass(frozen=True)
class LeafMerkleNode(MerkleNode[P], typing.Generic[P]):
    height: int
    payload: P

    def node_hash(self) -> bytes:
        return self.payload.hash()

    def get_parents(self) -> typing.Iterable[MerkleNode[P]]:
        return tuple()


@dataclass(frozen=True)
class ChildMerkleNode(MerkleNode[P], typing.Generic[P]):
    parent_a: MerkleNode[P]
    parent_b: MerkleNode[P]

    def node_hash(self) -> bytes:
        return hash_byte_sets(self.parent_a.node_hash(), self.parent_b.node_hash())

    @property
    def height(self) -> typing.Optional[int]:  # type: ignore
        return 1 + max(
            self.parent_a.height if self.parent_a.height is not None else 0,
            self.parent_b.height if self.parent_b.height is not None else 0,
        )

    @staticmethod
    def visit(node: MerkleNode[P]) -> typing.Iterable[MerkleNode[P]]:
        print(node)
        if isinstance(node, ChildMerkleNode):
            return (node.parent_a, node.parent_b)
        return tuple()

    def print(self) -> None:
        bfs([self], ChildMerkleNode.visit, set())


def bfs(
    nodes: typing.Iterable[MerkleNode[P]],
    visit: typing.Callable[[MerkleNode[P]], typing.Iterable[MerkleNode[P]]],
    visited: typing.Set[MerkleNode[P]],
) -> None:
    new_nodes: typing.List[MerkleNode[P]] = []
    for node in nodes:
        if node in visited:
            continue
        visited.add(node)
        new_nodes.extend(visit(node))
    if len(new_nodes) > 0:
        bfs(new_nodes, visit, visited)


def build_merkle_tree(
    items: typing.Iterable[P],
) -> typing.Optional[MerkleNode[P]]:
    items_iter = iter(items)
    lhs_init = next(items_iter, None)
    if lhs_init is None:
        return None
    lhs_trees: typing.List[MerkleNode[P]] = [LeafMerkleNode(height=0, payload=lhs_init)]
    for item in items_iter:
        new_leaf = LeafMerkleNode(height=0, payload=item)
        rhs_tree: MerkleNode[P] = new_leaf
        for _ in range(1, len(lhs_trees) + 1):
            if lhs_trees[-1].height == rhs_tree.height:
                rhs_tree = ChildMerkleNode(parent_a=lhs_trees.pop(), parent_b=rhs_tree)
            else:
                break
        lhs_trees.append(rhs_tree)

    acc_tree = None
    for i in range(len(lhs_trees)):
        if acc_tree is not None:
            acc_tree = ChildMerkleNode(parent_a=lhs_trees[-i], parent_b=acc_tree)
        else:
            acc_tree = lhs_trees[-i]
    return acc_tree
