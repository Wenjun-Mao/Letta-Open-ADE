"""Dependency-free SVG overview of the canonical capability inventory."""

from __future__ import annotations

from html import escape
from textwrap import wrap


COLORS = {"recall": "#0b5da8", "retain": "#087d70"}


def render_svg(data: dict) -> str:
    pieces = {item["id"]: item for item in [*data["entries"], *data["records"]]}
    nodes: dict[str, tuple[int, int, int, int]] = {}
    background: list[str] = []
    foreground: list[str] = []

    def text(x, y, value, size=18, color="#11283d", bold=False):
        foreground.append(
            f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}"'
            f' font-weight="{600 if bold else 400}">{escape(value)}</text>'
        )

    def panel(x, y, width, height, title, color="#b5cbe0", fill="#f8fbff"):
        background.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}"'
            f' rx="16" fill="{fill}" stroke="{color}"/>'
        )
        text(x + 20, y + 35, title, 25, bold=True)

    def node(id_, x, y, width, height=110):
        item = pieces[id_]
        status = item.get("status", "stored record")
        stored = "authority" in item
        level = (
            "L3 / " if item.get("domain") in {d["id"] for d in data["domains"]} else ""
        )
        nodes[id_] = (x, y, width, height)
        dashed = ' stroke-dasharray="7 5"' if status == "deferred" else ""
        foreground.append(
            f'<g id="{id_}"><title>{escape(item["name"])}</title>'
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}"'
            f' rx="{24 if stored else 9}" fill="white" stroke="#afc4d6"{dashed}/>'
        )
        compact = height < 100
        text(
            x + 15,
            y + (20 if compact else 24),
            level + id_,
            11 if compact else 13,
            "#597086",
        )
        lines = wrap(item["name"], max(20, (width - 30) // (9 if compact else 11)))
        if len(lines) > 2:
            raise ValueError(f"Static label requires more room: {id_}")
        for index, line in enumerate(lines):
            text(
                x + 15,
                y + (44 if compact else 49) + 22 * index,
                line,
                16 if compact else 19,
                bold=True,
            )
        if compact:
            foreground.append(
                f'<text x="{x + width - 15}" y="{y + 20}" font-size="11" fill="#475569" text-anchor="end">{escape(status.upper())}</text>'
            )
        else:
            text(x + 15, y + height - 12, status.upper(), 12, "#475569")
        foreground.append("</g>")

    def row(ids, x, y, width, height=110, gap=28):
        cell = (width - gap * (len(ids) - 1)) // len(ids)
        for index, id_ in enumerate(ids):
            node(id_, x + index * (cell + gap), y, cell, height)

    def entries(domain, subsystem):
        return [
            item["id"]
            for item in data["entries"]
            if item["domain"] == domain and item["subsystem"] == subsystem
        ]

    def anchor(id_, side):
        x, y, width, height = nodes[id_]
        return {
            "top": (x + width // 2, y),
            "bottom": (x + width // 2, y + height),
            "left": (x, y + height // 2),
            "right": (x + width, y + height // 2),
        }[side]

    def edge(flow, start, end, points, label=None):
        if not any(a == start and b == end for a, b, _ in flow["edges"]):
            raise ValueError(f"Overview edge not in canonical flow: {start} -> {end}")
        color = COLORS[flow["id"]]
        path = " ".join(
            f"{'M' if index == 0 else 'L'} {x} {y}"
            for index, (x, y) in enumerate(points)
        )
        foreground.append(
            f'<path data-from="{start}" data-to="{end}" d="{path}" fill="none"'
            f' stroke="{color}" stroke-width="3" marker-end="url(#{flow["id"]})"/>'
        )
        if label:
            x, y, value = label
            text(x, y, value, 16, color, True)

    text(40, 54, "ADE / Capability and dataflow map", 38, bold=True)
    text(
        40,
        92,
        "Domain -> Subsystem -> Module = L1 / L2 / L3 ownership, not execution depth.",
        22,
    )
    text(
        40,
        128,
        "Blue: recall and respond. Green: review and retain. Records are not processing modules.",
        18,
        "#475569",
    )
    panel(40, 165, 400, 925, "L1 / Character", "#d7b6a8", "#fffaf7")
    text(62, 244, "L2 / Persona Definition", 21, bold=True)
    node("CHAR-01", 62, 270, 356)
    node("CHAR-02", 62, 406, 356)
    node("REC-DEFINITION", 62, 546, 356, 100)
    text(62, 693, "L2 / Conversation Behavior", 21, bold=True)
    node("CHAR-03", 62, 721, 356)
    node("CHAR-04", 62, 856, 356)
    node("CHAR-05", 62, 991, 356, 85)

    panel(490, 165, 1710, 1075, "L1 / Memory")
    text(516, 268, "L2 / Recall & Context", 24, bold=True)
    row(entries("memory", "Recall & Context"), 516, 304, 1658, 120)
    text(
        516,
        484,
        "Stored records / not processing modules",
        21,
        bold=True,
    )
    row(["REC-DIALOGUE", "REC-FACTS", "REC-SUMMARY", "REC-INDEX"], 516, 513, 1658, 110)
    text(516, 706, "L2 / Retention & Updates", 24, bold=True)
    row(entries("memory", "Retention & Updates"), 516, 744, 1658, 120)
    text(516, 985, "L2 / Organization & Maintenance", 24, bold=True)
    row(entries("memory", "Organization & Maintenance"), 516, 1022, 1658, 120)
    text(
        516,
        1193,
        "Existing compaction stays MEM-09. MEM-10 alone reserves an additional optional view.",
        19,
        "#475569",
    )
    panel(40, 1110, 400, 130, "L1 / External Tools", "#b4a98c", "#faf8f2")
    text(62, 1168, "L2 / External Information & Actions", 16, bold=True)
    node("EXT-01", 62, 1180, 356, 48)

    interface = next(item for item in data["domains"] if item["id"] == "interface")
    panel(40, 1285, 2160, 380, "L1 / Interface", "#b2cdbf", "#f2f8f5")
    for index, subsystem in enumerate(interface["subsystems"]):
        x = 62 + index * 539
        text(x, 1361, "L2 / " + subsystem, 20, bold=True)
        for offset, id_ in enumerate(entries("interface", subsystem)):
            node(id_, x, 1384 + 85 * offset, 511, 75)

    panel(
        40,
        1710,
        2160,
        240,
        "Supporting register / shared machinery, outside the four capability domains",
        fill="#f0f4f7",
    )
    support = [item["id"] for item in data["entries"] if item["domain"] == "support"]
    row(support[:4], 62, 1768, 2116, 75)
    row(support[4:], 62, 1858, 2116, 75)
    panel(
        40,
        1980,
        1400,
        165,
        "Adjacent features / retain their existing owners",
        fill="#f6f8fb",
    )
    row(["ADJ-01", "ADJ-02"], 62, 2040, 1356, 85)
    panel(1470, 1980, 730, 165, "Stored operational records", fill="#eef3f8")
    node("REC-RUNS", 1492, 2040, 686, 85)

    recall, retain = data["flows"][:2]
    for a, b, label in recall["edges"][:3]:
        x, y, width, height = nodes[a]
        bx, by, _, bh = nodes[b]
        edge(recall, a, b, [(x + width, y + height // 2), (bx, by + bh // 2)])
        text(x + width - 15, y + height + 27, label, 15, COLORS["recall"])
    source_x, source_y = anchor("MEM-04", "top")
    target_x, target_y = anchor("CHAR-03", "right")
    edge(
        recall,
        "MEM-04",
        "CHAR-03",
        [
            (source_x, source_y),
            (source_x, 227),
            (462, 227),
            (462, target_y),
            (target_x, target_y),
        ],
        (1010, 219, "delivered evidence"),
    )
    edge(
        recall,
        "CHAR-03",
        "CHAR-04",
        [anchor("CHAR-03", "bottom"), anchor("CHAR-04", "top")],
    )
    text(72, 850, "same generation call", 13, COLORS["recall"])
    edge(recall, "REC-FACTS", "MEM-02", [(1135, 513), (1135, 424)])
    edge(
        recall,
        "REC-DIALOGUE",
        "MEM-02",
        [(712, 513), (712, 501), (1101, 501), (1101, 424)],
    )
    text(1148, 459, "fact access", 15, COLORS["recall"])
    edge(
        retain,
        "CHAR-04",
        "MEM-06",
        [(418, 911), (472, 911), (472, 674), (1345, 674), (1345, 744)],
        (650, 666, "reference-only candidate reply"),
    )
    for a, b in [("MEM-05", "MEM-06"), ("MEM-06", "MEM-07")]:
        x, y, width, height = nodes[a]
        bx, by, _, bh = nodes[b]
        edge(retain, a, b, [(x + width, y + height // 2), (bx, by + bh // 2)])
    edge(
        retain,
        "MEM-06",
        "MEM-08",
        [(1345, 864), (1345, 930), (1626, 930), (1626, 1005), (783, 1005), (783, 1022)],
        (835, 918, "prepare embeddings before finalization"),
    )
    edge(
        retain,
        "MEM-08",
        "MEM-07",
        [(516, 1082), (502, 1082), (502, 957), (1907, 957), (1907, 864)],
    )
    text(1450, 945, "prepared representation", 16, COLORS["retain"], True)
    for offset, record in enumerate(["REC-FACTS", "REC-DIALOGUE"]):
        x, y = anchor("MEM-07", "top")
        bx, by = anchor(record, "bottom")
        lane = 637 + 13 * offset
        edge(
            retain,
            "MEM-07",
            record,
            [(x + offset * 14, y), (x + offset * 14, lane), (bx, lane), (bx, by)],
        )
    text(1600, 633, "atomic accepted changes", 16, COLORS["retain"], True)
    text(
        40,
        2190,
        "Simplified main loop; HTML exposes all named edges in three views. Input capture precedes generation; finalization stays atomic.",
        18,
        "#475569",
    )
    text(
        40,
        2224,
        f"Reviewed {data['reviewed_at']} / source {data['source_baseline'][:12]}. Status describes code scope, not semantic acceptance or release.",
        17,
        "#475569",
    )
    if set(nodes) != set(pieces):
        raise ValueError("Static overview omits registered pieces")
    markers = "".join(
        f'<marker id="{id_}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>'
        for id_, color in COLORS.items()
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="2240" height="2260" viewBox="0 0 2240 2260" role="img" aria-labelledby="title desc">'
        '<title id="title">ADE capability responsibility and simplified dataflow map</title>'
        '<desc id="desc">Four capability domains, supporting and adjacent registers; select a module in the accompanying HTML for source references and all flow boundaries.</desc>'
        f'<defs>{markers}</defs><rect width="2240" height="2260" fill="#f6f8fb"/>'
        '<g font-family="Helvetica Neue, Helvetica, Arial, sans-serif">'
        + "".join(background + foreground)
        + "</g></svg>\n"
    )
