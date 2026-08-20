#!/usr/bin/env python3
"""Audit an Abaqus-generated INP against a small JSON acceptance contract."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


STEP_RE = re.compile(r"\bname\s*=\s*([^,]+)", re.I)
TYPE_RE = re.compile(r"\btype\s*=\s*([^,]+)", re.I)
MAP_RE = re.compile(r"\b(bstep|binc|estep|einc)\s*=\s*([^,]+)", re.I)


def keyword(line: str) -> str:
    return line[1:].split(",", 1)[0].strip().upper()


def parse(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    steps: list[str] = []
    element_types: Counter[str] = Counter()
    current_step = "Initial"
    mappings: dict[str, list[dict[str, int]]] = {}
    dflux: dict[str, list[dict]] = {}
    controls: dict[str, dict] = {}
    comments: list[str] = []
    keyword_counts: Counter[str] = Counter()

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("**"):
            comments.append(line)
            index += 1
            continue
        if not line.startswith("*") or line.startswith("**"):
            index += 1
            continue
        key = keyword(line)
        keyword_counts[key] += 1
        if key == "STEP":
            match = STEP_RE.search(line)
            current_step = match.group(1).strip() if match else "<unnamed>"
            steps.append(current_step)
        elif key == "ELEMENT":
            match = TYPE_RE.search(line)
            if match:
                element_types[match.group(1).strip().upper()] += 1
        elif key == "TEMPERATURE" and "FILE=" in line.upper():
            values = {}
            for name, value in MAP_RE.findall(line):
                try:
                    values[name.lower()] = int(float(value.strip().strip('"')))
                except ValueError:
                    values[name.lower()] = value.strip().strip('"')
            mappings.setdefault(current_step, []).append(values)
        elif key in {"STATIC", "HEAT TRANSFER"}:
            next_index = index + 1
            while next_index < len(lines) and (not lines[next_index].strip() or lines[next_index].lstrip().startswith("**")):
                next_index += 1
            if next_index < len(lines) and not lines[next_index].lstrip().startswith("*"):
                values = [float(value) for value in lines[next_index].split(",") if value.strip()]
                if len(values) >= 4:
                    controls[current_step] = {
                        "initial_increment": values[0],
                        "time_period": values[1],
                        "minimum_increment": values[2],
                        "maximum_increment": values[3],
                    }
        elif key == "DFLUX":
            next_index = index + 1
            while next_index < len(lines) and (not lines[next_index].strip() or lines[next_index].lstrip().startswith("**")):
                next_index += 1
            if next_index < len(lines) and not lines[next_index].lstrip().startswith("*"):
                fields = [field.strip() for field in lines[next_index].split(",") if field.strip()]
                if len(fields) >= 3 and fields[1].upper() == "BF":
                    dflux.setdefault(current_step, []).append({"region": fields[0], "magnitude": float(fields[2])})
        index += 1

    return {
        "steps": steps,
        "element_type_blocks": dict(element_types),
        "temperature_mappings": mappings,
        "step_controls": controls,
        "body_heat_flux": dflux,
        "keyword_counts": dict(keyword_counts),
        "comments": comments,
        "text": "\n".join(lines),
    }


def close(a: float, b: float, tolerance: float = 1e-9) -> bool:
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


def audit(data: dict, contract: dict) -> list[str]:
    failures: list[str] = []
    if re.search(r"(?im)^\s*\*CONFLICTS\b", data["text"]):
        failures.append("illegal *Conflicts keyword found")

    for step, mappings in data["temperature_mappings"].items():
        for mapping in mappings:
            binc = mapping.get("binc")
            if isinstance(binc, int) and binc < 1:
                failures.append(f"{step}: explicit BINC must be positive, got {binc}")

    exact_steps = contract.get("exact_steps")
    if exact_steps is not None and data["steps"] != exact_steps:
        failures.append("step sequence differs from exact_steps")

    for step in contract.get("required_steps", []):
        if step not in data["steps"]:
            failures.append(f"missing required step: {step}")

    for step, expected in contract.get("step_controls", {}).items():
        actual = data["step_controls"].get(step)
        if actual is None:
            failures.append(f"missing controls for step: {step}")
            continue
        for key, value in expected.items():
            if key not in actual or not close(actual[key], float(value)):
                failures.append(f"{step} {key}: expected {value}, got {actual.get(key)}")

    for step, expected in contract.get("temperature_mappings", {}).items():
        actual_list = data["temperature_mappings"].get(step, [])
        if len(actual_list) != 1:
            failures.append(f"{step}: expected one temperature mapping, got {len(actual_list)}")
            continue
        actual = actual_list[0]
        for key, value in expected.items():
            if actual.get(key.lower()) != int(value):
                failures.append(f"{step} mapping {key}: expected {value}, got {actual.get(key.lower())}")

    mapping_policy = contract.get("temperature_mapping_policy", {})
    all_mappings = [
        (step, mapping)
        for step, mappings in data["temperature_mappings"].items()
        for mapping in mappings
    ]
    if "expected_total" in mapping_policy:
        expected_total = int(mapping_policy["expected_total"])
        if len(all_mappings) != expected_total:
            failures.append(
                f"temperature mapping total: expected {expected_total}, got {len(all_mappings)}"
            )
    if mapping_policy.get("exactly_one_per_step"):
        for step, mappings in data["temperature_mappings"].items():
            if len(mappings) != 1:
                failures.append(f"{step}: expected exactly one temperature mapping, got {len(mappings)}")
    for parameter in ("binc", "einc"):
        if mapping_policy.get(f"omit_{parameter}"):
            for step, mapping in all_mappings:
                if parameter in mapping:
                    failures.append(f"{step}: expected {parameter.upper()} to be omitted")

    for key, expected in contract.get("keyword_counts", {}).items():
        actual = data["keyword_counts"].get(str(key).upper(), 0)
        if actual != int(expected):
            failures.append(f"keyword {str(key).upper()} count: expected {expected}, got {actual}")

    for step, expected in contract.get("body_heat_flux", {}).items():
        actual_list = data["body_heat_flux"].get(step, [])
        if len(actual_list) != 1:
            failures.append(f"{step}: expected one body heat flux, got {len(actual_list)}")
            continue
        actual = actual_list[0]
        if "region" in expected and actual["region"].lower() != str(expected["region"]).lower():
            failures.append(f"{step} flux region: expected {expected['region']}, got {actual['region']}")
        if "magnitude" in expected and not close(actual["magnitude"], float(expected["magnitude"])):
            failures.append(f"{step} flux magnitude: expected {expected['magnitude']}, got {actual['magnitude']}")

    for pattern in contract.get("forbidden_patterns", []):
        if re.search(pattern, data["text"], re.I | re.M):
            failures.append(f"forbidden pattern found: {pattern}")
    for pattern in contract.get("required_patterns", []):
        if not re.search(pattern, data["text"], re.I | re.M):
            failures.append(f"required pattern missing: {pattern}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inp", type=Path)
    parser.add_argument("contract", type=Path, help="JSON validation contract")
    parser.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args()

    data = parse(args.inp)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    failures = audit(data, contract)
    report = {
        "input": str(args.inp),
        "step_count": len(data["steps"]),
        "steps": data["steps"],
        "element_type_blocks": data["element_type_blocks"],
        "temperature_mappings": data["temperature_mappings"],
        "step_controls": data["step_controls"],
        "body_heat_flux": data["body_heat_flux"],
        "keyword_counts": data["keyword_counts"],
        "failure_count": len(failures),
        "failures": failures,
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.json_path:
        args.json_path.write_text(text + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
