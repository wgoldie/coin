import abc
import typing
from dataclasses import dataclass
from functools import cached_property
from coin.transaction import SignedTransaction
from coin.util import hash_byte_sets


class MerkleNode(abc.ABC):
    node_hash: bytes
    height: typing.Optional[int]

    def get_parents(self) -> typing.Iterable["MerkleNode"]:
        ...

    def __str__(self) -> str:
        return f"{self.height} {str(self.node_hash)}"

    def print_children(self) -> str:
        pass


@dataclass(frozen=True)
class LeafMerkleNode(MerkleNode):
    node_hash: bytes
    height: typing.Optional[int]

    def get_parents(self) -> typing.Iterable["MerkleNode"]:
        return tuple()


@dataclass(frozen=True)
class ChildMerkleNode(MerkleNode):
    parent_a: MerkleNode
    parent_b: MerkleNode

    @cached_property
    def node_hash(self) -> bytes:  # type: ignore
        return hash_byte_sets(self.parent_a.node_hash, self.parent_b.node_hash)

    @property
    def height(self) -> typing.Optional[int]:  # type: ignore
        return 1 + max(
            self.parent_a.height if self.parent_a.height is not None else 0,
            self.parent_b.height if self.parent_b.height is not None else 0,
        )

    @staticmethod
    def visit(node: MerkleNode) -> typing.Iterable["MerkleNode"]:
        print(node)
        if isinstance(node, ChildMerkleNode):
            return (node.parent_a, node.parent_b)
        return tuple()

    def print(self) -> None:
        bfs([self], ChildMerkleNode.visit, set())


def bfs(
    nodes: typing.Iterable[MerkleNode],
    visit: typing.Callable[[MerkleNode], typing.Iterable[MerkleNode]],
    visited: typing.Set[MerkleNode],
) -> None:
    new_nodes: typing.List[MerkleNode] = []
    for node in nodes:
        if node in visited:
            continue
        visited.add(node)
        new_nodes.extend(visit(node))
    if len(new_nodes) > 0:
        bfs(new_nodes, visit, visited)


def build_merkle_tree(
    transactions: typing.Iterable[SignedTransaction],
) -> typing.Optional[MerkleNode]:
    transactions_iter = iter(transactions)
    lhs_init = next(transactions_iter, None)
    if lhs_init is None:
        return None
    lhs_trees: typing.List[MerkleNode] = [
        LeafMerkleNode(node_hash=lhs_init.hash, height=0)
    ]
    for transaction in transactions_iter:
        new_leaf = LeafMerkleNode(node_hash=transaction.hash, height=0)
        rhs_tree: MerkleNode = new_leaf
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
