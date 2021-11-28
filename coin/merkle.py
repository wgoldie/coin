from __future__ import annotations
from functools import cache
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

    @cache
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
        if isinstance(node, ChildMerkleNode):
            return (node.parent_a, node.parent_b)
        return tuple()

    def print(self) -> None:
        bfs([self], ChildMerkleNode.visit, set())


def bfs(
    nodes: typing.Iterable[MerkleNode[P]],
    visit: typing.Callable[[MerkleNode[P]], typing.Iterable[MerkleNode[P]]],
    visited: typing.Set[bytes],
) -> None:
    new_nodes: typing.List[MerkleNode[P]] = []
    for node in nodes:
        node_hash = node.node_hash()
        if node_hash in visited:
            continue
        visited.add(node_hash)
        new_nodes.extend(visit(node))
    if len(new_nodes) > 0:
        bfs(new_nodes, visit, visited)


def dfs(
    node: MerkleNode[P],
) -> typing.Generator[MerkleNode[P], None, None]:
    nodes = [node]
    visited = set()
    while len(nodes) > 0:
        new_nodes: typing.List[MerkleNode[P]] = []
        for node in nodes:
            yield node
            node_hash = node.node_hash()
            if node_hash in visited:
                return
            visited.add(node_hash)

            new_nodes.extend(ChildMerkleNode.visit(node))
        nodes = new_nodes


@dataclass(frozen=True)
class MerkleForest(typing.Generic[P]):
    trees: typing.Tuple[MerkleNode[P], ...]

    def add_node(self, payload: P) -> MerkleForest[P]:
        trees = list(self.trees)
        new_leaf = LeafMerkleNode(height=0, payload=payload)
        rhs_tree: MerkleNode[P] = new_leaf
        for _ in range(1, len(trees) + 1):
            if trees[-1].height == rhs_tree.height:
                rhs_tree = ChildMerkleNode(parent_a=trees.pop(), parent_b=rhs_tree)
            else:
                break
        trees.append(rhs_tree)
        return MerkleForest(trees=tuple(trees))

    @cache
    def merge(self) -> MerkleNode[P]:
        acc_tree = None
        for i in range(len(self.trees)):
            if acc_tree is not None:
                acc_tree = ChildMerkleNode(parent_a=self.trees[-i], parent_b=acc_tree)
            else:
                acc_tree = self.trees[-i]
        return acc_tree if acc_tree is not None else NullMerkleNode()


def build_merkle_tree(
    items: typing.Iterable[P],
) -> typing.Optional[MerkleNode[P]]:
    items_iter = iter(items)
    lhs_init = next(items_iter, None)
    if lhs_init is None:
        return None

    forest = MerkleForest(trees=(LeafMerkleNode(height=0, payload=lhs_init),))
    for item in items_iter:
        forest = forest.add_node(item)

    return forest.merge()
