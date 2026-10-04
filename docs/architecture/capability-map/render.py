"""Validate the capability inventory and render its documentation views."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from static_map import render_svg


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STATUSES = {"implemented", "partial", "experimental", "proposed", "deferred"}
MARKER = "__INVENTORY_DATA__"


def source_path(reference: str, data: dict, root: Path = ROOT) -> Path:
    alias, separator, tail = reference.partition(":")
    if not separator or alias not in data["roots"] or not tail:
        raise ValueError(f"Invalid source reference: {reference}")
    path = (root / data["roots"][alias] / tail).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Source escapes repository: {reference}")
    if not path.exists():
        raise ValueError(f"Missing source: {reference}")
    return path


def validate(data: dict, root: Path = ROOT) -> dict[str, int]:
    if data.get("schema") != "ade-capability-inventory-v1":
        raise ValueError("Unsupported inventory schema")
    domains = {item["id"]: item for item in data["domains"]}
    if len(domains) != len(data["domains"]):
        raise ValueError("Duplicate domain")
    if set(domains) != {"character", "memory", "interface", "external-tools"}:
        raise ValueError("Capability domains differ from ADR 0061")
    ids: set[str] = set()
    sources: set[str] = set()
    for entry in [*data["entries"], *data["records"]]:
        if entry["id"] in ids:
            raise ValueError(f"Duplicate entry: {entry['id']}")
        ids.add(entry["id"])
        if "domain" in entry:
            domain = entry["domain"]
            if domain not in {*domains, "support", "adjacent"}:
                raise ValueError(f"Unknown domain: {domain}")
            if (
                domain in domains
                and entry["subsystem"] not in domains[domain]["subsystems"]
            ):
                raise ValueError(f"Unknown subsystem for {entry['id']}")
            if entry["status"] not in STATUSES:
                raise ValueError(f"Unknown status for {entry['id']}")
            for key in ("input", "output", "evidence", "gap", "next_check"):
                if not isinstance(entry[key], str) or not entry[key].strip():
                    raise ValueError(f"Missing {key} for {entry['id']}")
            if entry["status"] not in {"proposed", "deferred"} and not entry["code"]:
                raise ValueError(f"Existing entry lacks source: {entry['id']}")
        for reference in [*entry["code"], *entry.get("tests", [])]:
            source_path(reference, data, root)
            sources.add(reference)
    flow_ids: set[str] = set()
    for flow in data["flows"]:
        if flow["id"] in flow_ids:
            raise ValueError("Duplicate flow")
        flow_ids.add(flow["id"])
        if not flow["steps"] or not flow["note"]:
            raise ValueError("Flow lacks timing/authority description")
        for start, end, label in flow["edges"]:
            if start not in ids or end not in ids or not label:
                raise ValueError(f"Invalid edge: {start} -> {end}")
    return {
        "entries": len(data["entries"]),
        "records": len(data["records"]),
        "sources": len(sources),
        "flows": len(flow_ids),
    }


def browser_payload(data: dict) -> dict:
    payload = copy.deepcopy(data)
    for entry in [*payload["entries"], *payload["records"]]:
        for key in ("code", "tests"):
            if key in entry:
                entry[key] = [
                    source_path(ref, data).relative_to(ROOT).as_posix()
                    for ref in entry[key]
                ]
    return payload


def render_html(data: dict, template: str) -> str:
    if template.count(MARKER) != 1:
        raise ValueError("Template must have one data marker")
    encoded = json.dumps(
        browser_payload(data), ensure_ascii=True, separators=(",", ":")
    )
    # Keep source text inert inside the embedded JSON script element.
    encoded = (
        encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )
    return template.replace(MARKER, encoded)


def source_links(references: list[str], data: dict) -> str:
    links = []
    for reference in references:
        path = source_path(reference, data).relative_to(ROOT)
        target = f"../../../{path.as_posix()}"
        links.append(f"[{path.name}]({target})")
    return ", ".join(links) or "None; no implementation is implied."


def render_markdown(data: dict) -> str:
    domains = {item["id"]: item["name"] for item in data["domains"]}
    domains.update({"support": "Supporting Register", "adjacent": "Adjacent Features"})
    lines = [
        "# ADE Capability Inventory",
        "",
        "Generated from [inventory.json](inventory.json); edit that source, not this view.",
        f"Reviewed: {data['reviewed_at']}. Source baseline: `{data['source_baseline']}`.",
        "",
        data["scope"],
        "",
        "Status is implementation scope, not a claim that tests were rerun or behavior was released.",
        "See the [entrypoint](README.md) for status definitions and authority boundaries.",
    ]
    for domain_id, title in domains.items():
        lines.extend(["", f"## {title}"])
        if domain_id in {"support", "adjacent"}:
            lines.extend(
                [
                    "",
                    "This register is outside the four-domain L1/L2/L3 capability hierarchy.",
                ]
            )
        for entry in data["entries"]:
            if entry["domain"] != domain_id:
                continue
            lines.extend(
                [
                    "",
                    f"### {entry['id']}: {entry['name']}",
                    f"Owner: **{title} / {entry['subsystem']}**. Implementation: **{entry['status']}**.",
                    f"Input: {entry['input']}. Output: {entry['output']}.",
                    f"Code: {source_links(entry['code'], data)} Tests: {source_links(entry['tests'], data)}",
                    f"Evidence limit: {entry['evidence']}",
                    f"Known gap: {entry['gap']}",
                    f"Next isolated check: {entry['next_check']}",
                ]
            )
    lines.extend(["", "## Stored Records", "", "Records are not processing modules."])
    for record in data["records"]:
        lines.extend(
            [
                "",
                f"### {record['id']}: {record['name']}",
                record["authority"],
                f"Sources: {source_links(record['code'], data)}",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and reject stale generated views without writing",
    )
    args = parser.parse_args()
    data = json.loads((HERE / "inventory.json").read_text())
    counts = validate(data)
    outputs = {
        HERE / "ade-capability-map.html": render_html(
            data, (HERE / "template.html").read_text()
        ),
        HERE / "inventory.md": render_markdown(data),
        HERE / "ade-capability-map.svg": render_svg(data),
    }
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit(f"Stale generated view: {path.relative_to(ROOT)}")
        else:
            path.write_text(content)
    action = "Checked" if args.check else "Rendered"
    print(
        f"{action}: {counts['entries']} pieces, {counts['records']} record families, {counts['flows']} flows, {counts['sources']} source/test references"
    )


if __name__ == "__main__":
    main()
