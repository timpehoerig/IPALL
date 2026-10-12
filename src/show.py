from dataclasses import dataclass
from typing import Optional
import argparse


@dataclass
class cb_has_external_clause:
    pass


@dataclass
class cb_decide:
    pass


@dataclass
class is_decision:
    decision: int


@dataclass
class notify_new_decision_level:
    level: int


@dataclass
class cb_propagate:
    lit: Optional[int]


@dataclass
class cb_add_reason_clause_lit:
    lit: int
    reason: int


@dataclass
class notify_backtrack:
    level: int


type Stmt = cb_propagate | cb_has_external_clause | cb_decide | notify_new_decision_level | is_decision | cb_add_reason_clause_lit | notify_backtrack | None


def parse_line(line: str) -> Stmt:
    match line:
        case line if line.startswith("cb_propagate"):
            lit = int(line.split()[1])
            if lit == 0:
                return cb_propagate(None)
            return cb_propagate(lit)

        case line if line.startswith("cb_has_external_clause"):
            return cb_has_external_clause()

        case line if line.startswith("cb_decide"):
            return cb_decide()

        case line if line.startswith("notify_new_decision_level"):
            return notify_new_decision_level(int(line.split()[1]))

        case line if line.startswith("is_decision"):
            return is_decision(int(line.split()[1]))

        case line if line.startswith("cb_add_reason_clause_lit"):
            _, lit, reason = line.split()
            return cb_add_reason_clause_lit(int(lit), int(reason))

        case line if line.startswith("notify_backtrack"):
            return notify_backtrack(int(line.split()[1]))

        case _:
            return None


@dataclass
class Node:
    level: int
    decision: int

    parent: Optional[Node]
    children: list[Node]


def build_tree(path: str) -> Node:
    node = Node(level=0, decision=0, parent=None, children=[])

    lvl = 0

    with open(path, "r") as file:
        for line in file:
            match parse_line(line):

                case None:
                    continue

                case cb_propagate(_):
                    continue

                case cb_has_external_clause():
                    continue

                case cb_decide():
                    continue

                case notify_new_decision_level(level):
                    lvl = level

                case is_decision(decision):
                    if decision == 0:
                        continue
                    child = Node(lvl, decision, node, [])
                    node.children.append(child)
                    node = child

                case cb_add_reason_clause_lit(_):
                    continue

                case notify_backtrack(level):
                    while node.level > level:
                        if node.parent is None:
                            raise Exception("Cant backtrack further:", node)
                        node = node.parent

    return node


def pretty_inner(node: Node, out: str = "") -> str:
    assert node.level != 0 and node.decision != 0

    out += f"{node.decision}@{node.level}"

    if node.children == []:
        return f"{out}\n"

    for child in node.children:
        out += pretty_inner(child, out)

    return out


def pretty(node: Node) -> str:
    assert node.level == 0 and node.decision == 0
    count = 0
    out = ""
    for child in node.children:
        out += f"{count}: {pretty_inner(child)}"
    return out


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Building a decision tree"
    )

    parser.add_argument(
        dest="path",
        type=str
    )

    return parser


if __name__ == "__main__":

    args = parser().parse_args()

    t = build_tree(args.path)
    print(pretty(t))
