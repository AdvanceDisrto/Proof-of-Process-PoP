"""Reference behavior for Tessera-G single-tile RTL, not a cryptographic verifier."""
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

MAX_NODES = 16
NO_PARENT = 255

class State(IntEnum):
    EMPTY = 0
    ACCEPTED = 1
    REFUTED = 2
    DEPENDENCY_BLOCKED = 3
    UNDETERMINED = 4
    INVALID_TOPOLOGY = 5

@dataclass(frozen=True)
class Node:
    local_verdict: int
    parent_a: Optional[int]
    parent_b: Optional[int]
    effective: State

class TesseraModel:
    def __init__(self, max_nodes: int = MAX_NODES):
        if not 1 <= max_nodes <= 254:
            raise ValueError("8-bit index reserves 255 as no-parent sentinel")
        self.max_nodes = max_nodes
        self.nodes: list[Node] = []
        self.overflow_seen = False

    def append(self, verdict: int, pa: Optional[int] = None,
               pb: Optional[int] = None) -> State:
        if len(self.nodes) == self.max_nodes:
            self.overflow_seen = True
            raise OverflowError("DAG tile is full")
        prev = len(self.nodes)
        if (any(p is not None and (not isinstance(p, int) or not 0 <= p < prev)
                for p in (pa, pb)) or
                (pa is not None and pa == pb)):
            state = State.INVALID_TOPOLOGY
        elif any(self.nodes[p].effective != State.ACCEPTED
                 for p in (pa, pb) if p is not None):
            state = State.DEPENDENCY_BLOCKED
        elif verdict == 1:
            state = State.ACCEPTED
        elif verdict == 2:
            state = State.REFUTED
        else:
            state = State.UNDETERMINED
        self.nodes.append(Node(verdict, pa, pb, state))
        return state

    def reset(self):
        self.nodes.clear()
        self.overflow_seen = False

    def export_visualizer(self):
        """Two-parent DAGE shader representation. Visualizes statuses, not proof authenticity."""
        result=[]
        depths=[]
        for i,node in enumerate(self.nodes):
            parents=(node.parent_a,node.parent_b)
            known_parents=[p for p in parents if p is not None and 0 <= p < i]
            depth=1+max((depths[p] for p in known_parents), default=-1)
            result.append(dict(
                parent_a=-1 if node.parent_a is None else node.parent_a,
                parent_b=-1 if node.parent_b is None else node.parent_b,
                depth=depth,
                local_verdict=node.local_verdict,
                effective=int(node.effective),
            ))
            depths.append(depth)
        return result
