"""Structural DAG pattern inspection: *not* causal discovery or factual certification."""
from __future__ import annotations

import re
from collections import defaultdict


def classify(edges: list[tuple[str, str]], x: str, y: str, z: str) -> dict:
    if any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", v)
           for edge in edges for v in edge) or len(edges) > 1024 or len(edges) != len(set(edges)):
        raise ValueError("invalid or duplicate DAG edges")
    if not all(isinstance(n, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", n) for n in [x,y,z]):
        raise ValueError("invalid DAG node")
    if len({x, y, z}) != 3:
        raise ValueError("DAG model requires distinct x, y, z")
    edges = set(edges)
    if any(a == b for a,b in edges):
        raise ValueError("self-loop")
    graph = defaultdict(list)
    nodes = {x, y, z}
    for a,b in edges:
        graph[a].append(b)
        nodes.update((a,b))
    visited, active = set(), set()
    def dfs(node):
        if node in active: raise ValueError("directed cycle")
        if node in visited: return
        active.add(node)
        for child in graph[node]: dfs(child)
        active.remove(node)
        visited.add(node)
    for n in nodes: dfs(n)
    patterns = {
       "confounder_shape": (z,x) in edges and (z,y) in edges,
       "collider_shape": (x,z) in edges and (y,z) in edges,
       "mediator_shape": (x,z) in edges and (z,y) in edges,
       "instrument_candidate_shape": (z,x) in edges and (z,y) not in edges and (x,y) in edges,
    }
    return {"protocol":"ITM-CAUSAL-STRUCTURE-v1","acyclic":True,"node_count":len(nodes),
            "edge_count":len(edges),"patterns":patterns,
            "causal_effect_identified":False,"hidden_confounding_ruled_out":False,
            "instrument_assumptions_proven":False,"physical_or_legal_truth_proven":False,
            "explanation":"These are directed-graph shapes, not measurements or identification proofs."}
