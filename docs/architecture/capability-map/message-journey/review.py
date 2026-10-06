"""Offline integrity checks and JSON assembly for the proposed ADE figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GROUP_KEYS = {"id", "label", "logo", "direction", "gap", "align", "children"}
NODE_KEYS = {"id", "label", "sub", "shape", "lines", "width"}
EDGE_KEYS = {"id", "from", "to", "label", "around", "quiet"}
STEP_KEYS = {"label", "caption", "flow", "nodes"}
BEAT_KEYS = {"edges", "say", "show", "light", "ms"}
HOP_KEYS = {"edge", "back", "data"}
ROW_KEYS = {"tag", "tone", "text", "meta", "mark", "mono"}
TONES = {"blue", "purple", "green", "orange", "gray"}
DOMAINS = {"character", "memory", "interface", "external-tools"}
ACCEPTANCE_WRITES = {"save-user", "save-accepted-run"}
SUCCESS_WRITES = {
    "commit-facts",
    "commit-index",
    "commit-dialogue",
    "commit-summary",
    "commit-run",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def keys(item: dict, allowed: set[str], name: str) -> None:
    require(isinstance(item, dict), f"Expected object: {name}")
    require(not item.keys() - allowed, f"Unsupported interfig fields: {name}")


def load() -> tuple[dict, dict, dict]:
    def read(path: Path) -> dict | list:
        return json.loads(path.read_text())

    evidence = read(HERE / "evidence.json")
    presentation = evidence["presentation"]
    figure = {
        "title": presentation["title"],
        "source": presentation["source"],
        "props": {
            "layout": read(HERE / "layout.json"),
            "edges": read(HERE / "edges.json"),
            "steps": read(HERE / "steps.json"),
            **{key: presentation[key] for key in ("theme", "speed", "autoplay")},
        },
    }
    return figure, evidence, read(HERE.parent / "inventory.json")


def validate(figure: dict, evidence: dict, inventory: dict) -> dict[str, int]:
    keys(figure, {"title", "source", "props"}, "Figure")
    props = figure["props"]
    keys(props, {"layout", "edges", "steps", "theme", "speed", "autoplay"}, "FlowProps")
    require(props["autoplay"] is False, "Review figure must start paused")
    keys(
        props["theme"],
        {"accent", "fg", "muted", "bg", "surface", "border", "font"},
        "theme",
    )
    nodes, groups, ancestors = {}, {}, {}
    all_ids = set()

    def walk(item: dict, parents: tuple[str, ...] = ()) -> None:
        group = "children" in item
        keys(item, GROUP_KEYS if group else NODE_KEYS, str(item.get("id")))
        identity = item["id"]
        require(identity not in all_ids, f"Duplicate layout ID: {identity}")
        all_ids.add(identity)
        if group:
            require(
                item.get("direction", "column") in {"row", "column"},
                "Invalid direction",
            )
            require(
                item.get("align", "center") in {"start", "center", "end"},
                "Invalid alignment",
            )
            groups[identity] = item
            for child in item["children"]:
                walk(child, (*parents, identity))
        else:
            require(
                item.get("shape", "box") in {"box", "decision", "store"},
                "Invalid shape",
            )
            require(isinstance(item["label"], str), "Review labels must be plain text")
            nodes[identity], ancestors[identity] = item, parents

    walk(props["layout"])
    require(DOMAINS <= groups.keys(), "Missing L1 domain")
    for domain in DOMAINS:
        require(groups[domain]["label"].startswith("L1"), "Missing visible L1 depth")
    bindings = evidence["node_bindings"]
    require(nodes.keys() == bindings.keys(), "Node/inventory mapping differs")
    entries = {
        entry["id"]: entry for entry in [*inventory["entries"], *inventory["records"]]
    }
    subsystem_groups = evidence["subsystem_groups"]
    for group_id, name in subsystem_groups.items():
        require(name in groups[group_id]["label"], f"Subsystem label drift: {group_id}")
        require(groups[group_id]["label"].startswith("L2"), "Missing visible L2 depth")
    for identity, references in bindings.items():
        require(references or identity == "candidate", f"Unmapped node: {identity}")
        for reference in references:
            require(reference in entries, f"Unknown inventory ID: {reference}")
            entry = entries[reference]
            require(
                reference in nodes[identity]["sub"], f"Missing visible ID: {reference}"
            )
            if "status" in entry:
                require(
                    f"[{entry['status']}]" in nodes[identity]["sub"].lower(),
                    f"Status drift: {reference}",
                )
                require(
                    entry["domain"] in ancestors[identity],
                    f"Ownership drift: {reference}",
                )
                if entry["domain"] in DOMAINS:
                    require(
                        nodes[identity]["sub"].startswith("L3 - "),
                        f"Missing visible L3 depth: {reference}",
                    )
                    owners = [
                        subsystem_groups.get(parent) for parent in ancestors[identity]
                    ]
                    require(
                        entry["subsystem"] in owners,
                        f"Subsystem ownership drift: {reference}",
                    )
            else:
                require(
                    nodes[identity].get("shape") == "store",
                    f"Record is not a store: {reference}",
                )
    require(
        bindings["behavior"] == ["CHAR-03", "CHAR-04"],
        "Character generation must remain shared",
    )

    edges = {}
    for edge in props["edges"]:
        keys(edge, EDGE_KEYS, str(edge.get("id")))
        require(edge["id"] not in edges, f"Duplicate edge ID: {edge['id']}")
        require(
            edge["from"] in nodes and edge["to"] in nodes,
            f"Unknown edge endpoint: {edge['id']}",
        )
        require(
            edge.get("around", "above") in {"above", "below"}, "Invalid edge routing"
        )
        require(
            not {edge["from"], edge["to"]} & {"views", "external"},
            "Deferred node has a runtime edge",
        )
        edges[edge["id"]] = edge

    edge_modes, sources = {}, set()
    contract = (ROOT / "docs/product-contract.md").read_text()
    for claim in evidence["claims"]:
        require(claim["mode"] in {"current", "experimental"}, "Invalid claim mode")
        require(claim["condition"] and claim["sources"], "Claim lacks condition/source")
        for edge_id in claim["edges"]:
            require(
                edge_id in edges and edge_id not in edge_modes,
                f"Invalid edge provenance: {edge_id}",
            )
            edge_modes[edge_id] = claim["mode"]
            if claim["mode"] == "experimental":
                require(
                    "EXPERIMENTAL" in edges[edge_id]["label"],
                    "Experimental edge lacks visible status",
                )
        for pc in claim["pcs"]:
            require(pc in contract, f"Unknown product agreement: {pc}")
        for source in claim["sources"]:
            alias, separator, tail = source["path"].partition(":")
            require(separator and alias in inventory["roots"], "Invalid source alias")
            path = (ROOT / inventory["roots"][alias] / tail).resolve()
            require(path.is_relative_to(ROOT), "Source escapes repository")
            require(path.is_file(), f"Missing source: {source['path']}")
            require(
                source["anchor"] in path.read_text(), f"Missing source anchor: {source}"
            )
            sources.add(source["path"])
    require(edges.keys() == edge_modes.keys(), "Edge lacks source provenance")

    def hops(value: str | dict | list) -> list[str]:
        values = value if isinstance(value, list) else [value]
        result = []
        for hop in values:
            if isinstance(hop, dict):
                keys(hop, HOP_KEYS, "hop")
                require(
                    not hop.get("back"),
                    "Use explicit return edges, not reversed arrows",
                )
                hop = hop["edge"]
            require(isinstance(hop, str) and hop in edges, f"Unknown hop: {hop}")
            result.append(hop)
        if len(result) > 1:
            require(
                set(result) <= ACCEPTANCE_WRITES or set(result) <= SUCCESS_WRITES,
                "Parallel beat is not an atomic visibility group",
            )
        return result

    modes = evidence["step_modes"]
    require(len(modes) == len(props["steps"]), "Step/status mapping differs")
    used_edges, beats = set(), 0
    for step, mode in zip(props["steps"], modes, strict=True):
        keys(step, STEP_KEYS, step["label"])
        require(
            mode in {"current", "experimental", "unimplemented"}, "Invalid step mode"
        )
        if mode == "experimental":
            require(
                "experimental" in step["label"].lower(),
                "Experimental tour lacks visible status",
            )
        require(set(step.get("nodes", [])) <= nodes.keys(), "Unknown step node")
        for beat in step["flow"]:
            beats += 1
            keys(beat, BEAT_KEYS, "beat")
            require(
                set(beat.get("light", [])) <= nodes.keys(), "Unknown highlighted node"
            )
            for identity, content in beat.get("show", {}).items():
                require(identity in nodes, f"Unknown content node: {identity}")
                require(isinstance(content, str | list), "Invalid content")
                if isinstance(content, list):
                    for row in content:
                        keys(row, ROW_KEYS, "content row")
                        require(
                            isinstance(row["text"], str),
                            "Content text must be a string",
                        )
                        require(row.get("tone", "blue") in TONES, "Invalid row tone")
            active = hops(beat["edges"]) if "edges" in beat else []
            require(
                not active or mode != "unimplemented",
                "Unimplemented tour animates a runtime edge",
            )
            require(
                mode != "current"
                or all(edge_modes[edge] == "current" for edge in active),
                "Experimental edge leaked into current tour",
            )
            used_edges.update(active)
    require(used_edges == edges.keys(), "Declared edge has no narrated use")
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "tours": len(modes),
        "beats": beats,
        "source_files": len(sources),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit",
        action="store_true",
        help="Print assembled Figure JSON; do not render or write",
    )
    args = parser.parse_args()
    figure, evidence, inventory = load()
    counts = validate(figure, evidence, inventory)
    print(
        json.dumps(
            figure if args.emit else {"valid_review_specification": counts}, indent=2
        )
    )


if __name__ == "__main__":
    main()
