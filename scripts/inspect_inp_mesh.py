#!/usr/bin/env python3
"""Inventory an Abaqus INP mesh without importing it into Abaqus/CAE."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def options(line: str) -> tuple[str, dict[str, str], set[str]]:
    fields = [field.strip() for field in line[1:].split(",")]
    keyword = fields[0].upper()
    values: dict[str, str] = {}
    flags: set[str] = set()
    for field in fields[1:]:
        if "=" in field:
            key, value = field.split("=", 1)
            values[key.strip().upper()] = value.strip()
        elif field:
            flags.add(field.upper())
    return keyword, values, flags


def expand_set(values: list[int], generate: bool) -> list[int]:
    if not generate:
        return values
    expanded: list[int] = []
    if len(values) % 3:
        raise ValueError("GENERATE set data must contain start,end,step triples")
    for index in range(0, len(values), 3):
        start, end, step = values[index:index + 3]
        expanded.extend(range(start, end + 1, step))
    return expanded


def parse_inp(path: Path) -> dict:
    nodes: dict[int, tuple[float, float, float]] = {}
    elements: dict[int, tuple[int, ...]] = {}
    element_types: dict[int, str] = {}
    elsets: dict[str, set[int]] = defaultdict(set)
    nsets: dict[str, set[int]] = defaultdict(set)
    mode = None
    current_type = ""
    current_set = ""
    current_generate = False

    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for number, raw in enumerate(stream, 1):
            line = raw.strip()
            if not line or line.startswith("**"):
                continue
            if line.startswith("*"):
                keyword, opts, flags = options(line)
                mode = None
                if keyword == "NODE":
                    mode = "node"
                    current_set = opts.get("NSET", "")
                elif keyword == "ELEMENT":
                    mode = "element"
                    current_type = opts.get("TYPE", "").upper()
                    current_set = opts.get("ELSET", "")
                    if not current_type:
                        raise ValueError(f"Line {number}: ELEMENT block has no TYPE")
                elif keyword in {"ELSET", "NSET"}:
                    mode = keyword.lower()
                    current_set = opts.get(keyword, "")
                    current_generate = "GENERATE" in flags
                    if not current_set:
                        raise ValueError(f"Line {number}: {keyword} block has no name")
                continue

            fields = [field.strip() for field in line.split(",") if field.strip()]
            if mode == "node":
                if len(fields) < 4:
                    raise ValueError(f"Line {number}: invalid node record")
                label = int(fields[0])
                nodes[label] = tuple(float(value) for value in fields[1:4])
                if current_set:
                    nsets[current_set].add(label)
            elif mode == "element":
                if len(fields) < 2:
                    raise ValueError(f"Line {number}: invalid element record")
                label = int(fields[0])
                connectivity = tuple(int(value) for value in fields[1:])
                elements[label] = connectivity
                element_types[label] = current_type
                if current_set:
                    elsets[current_set].add(label)
            elif mode in {"elset", "nset"}:
                values = expand_set([int(value) for value in fields], current_generate)
                (elsets if mode == "elset" else nsets)[current_set].update(values)

    missing_nodes = sorted({node for conn in elements.values() for node in conn if node not in nodes})
    if missing_nodes:
        raise ValueError(f"Elements reference {len(missing_nodes)} missing nodes")
    return {
        "nodes": nodes,
        "elements": elements,
        "element_types": element_types,
        "elsets": elsets,
        "nsets": nsets,
    }


def cluster(values: list[float], tolerance: float) -> list[dict]:
    if not values:
        return []
    groups: list[list[float]] = [[values[0]]]
    for value in values[1:]:
        if abs(value - sum(groups[-1]) / len(groups[-1])) <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [
        {"center": sum(group) / len(group), "count": len(group), "min": min(group), "max": max(group)}
        for group in groups
    ]


def summarize(data: dict, axis: int, tolerance: float, component: str | None) -> dict:
    nodes = data["nodes"]
    elements = data["elements"]
    selected = set(elements)
    if component:
        matches = [name for name in data["elsets"] if name.lower() == component.lower()]
        if not matches:
            raise ValueError(f"Component ELSET not found: {component}")
        selected = set(data["elsets"][matches[0]])

    centroids = []
    for label in selected:
        conn = elements[label]
        centroids.append(sum(nodes[node][axis] for node in conn) / len(conn))
    centroids.sort()

    bounds = None
    if nodes:
        coords = list(nodes.values())
        bounds = {
            "min": [min(point[index] for point in coords) for index in range(3)],
            "max": [max(point[index] for point in coords) for index in range(3)],
        }

    return {
        "node_count": len(nodes),
        "element_count": len(elements),
        "element_types": dict(sorted(Counter(data["element_types"].values()).items())),
        "bounds": bounds,
        "elsets": {name: len(labels) for name, labels in sorted(data["elsets"].items())},
        "nsets": {name: len(labels) for name, labels in sorted(data["nsets"].items())},
        "layer_axis": "xyz"[axis],
        "layer_component": component or "ALL",
        "candidate_layer_bands": cluster(centroids, tolerance),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inp", type=Path)
    parser.add_argument("--axis", choices="xyz", default="z")
    parser.add_argument("--component", help="Restrict layer detection to one ELSET")
    parser.add_argument("--tolerance", type=float, default=1e-7)
    parser.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args()

    data = parse_inp(args.inp)
    result = summarize(data, "xyz".index(args.axis), args.tolerance, args.component)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.json_path:
        args.json_path.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
