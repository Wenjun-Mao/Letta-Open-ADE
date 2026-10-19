from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.openapi_zh.manual_text import (
    SUMMARY_TRANSLATIONS,
    DESCRIPTION_TRANSLATIONS,
    TAG_TRANSLATIONS,
)
from scripts.openapi_zh.titles import TITLE_TRANSLATIONS
from scripts.openapi_zh.tokens import TITLE_TOKEN_TRANSLATIONS


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


TOKEN_SPLIT_PATTERN = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|\d+")
ASCII_LETTER_PATTERN = re.compile(r"[A-Za-z]")


def _contains_ascii_letters(value: str) -> bool:
    return bool(ASCII_LETTER_PATTERN.search(value))


def _split_title_tokens(value: str) -> list[str]:
    chunks = re.split(r"[\s_\-/]+", value.strip())
    tokens: list[str] = []

    for chunk in chunks:
        if not chunk:
            continue

        if chunk.isupper() and len(chunk) > 1:
            tokens.append(chunk)
            continue

        camel_tokens = TOKEN_SPLIT_PATTERN.findall(chunk)
        if camel_tokens:
            tokens.extend(camel_tokens)
        else:
            tokens.append(chunk)

    return tokens


def _translate_title_value(
    value: str,
    missing_titles: set[str],
    unknown_title_tokens: set[str],
) -> str:
    if value in TITLE_TRANSLATIONS:
        return TITLE_TRANSLATIONS[value]

    if not _contains_ascii_letters(value):
        return value

    tokens = _split_title_tokens(value)
    if not tokens:
        missing_titles.add(value)
        return value

    translated_tokens: list[str] = []
    unknown_tokens: list[str] = []

    for token in tokens:
        translated = TITLE_TOKEN_TRANSLATIONS.get(token.lower())
        if translated:
            translated_tokens.append(translated)
        else:
            translated_tokens.append(token)
            unknown_tokens.append(token)

    translated_value = " ".join(translated_tokens)
    if translated_value != value:
        for token in unknown_tokens:
            if _contains_ascii_letters(token):
                unknown_title_tokens.add(token)
        return translated_value

    missing_titles.add(value)
    return value


def _translate_document_fields(
    node: Any,
    missing_summaries: set[str],
    missing_descriptions: set[str],
    missing_titles: set[str],
    unknown_title_tokens: set[str],
) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "summary" and isinstance(value, str):
                if not _contains_ascii_letters(value):
                    continue

                translated = SUMMARY_TRANSLATIONS.get(value)
                if translated is None:
                    missing_summaries.add(value)
                else:
                    node[key] = translated
                continue

            if key == "description" and isinstance(value, str):
                if not _contains_ascii_letters(value):
                    continue

                translated = DESCRIPTION_TRANSLATIONS.get(value)
                if translated is None:
                    missing_descriptions.add(value)
                else:
                    node[key] = translated
                continue

            if key == "title" and isinstance(value, str):
                node[key] = _translate_title_value(
                    value, missing_titles, unknown_title_tokens
                )
                continue

            _translate_document_fields(
                value,
                missing_summaries,
                missing_descriptions,
                missing_titles,
                unknown_title_tokens,
            )
    elif isinstance(node, list):
        for item in node:
            _translate_document_fields(
                item,
                missing_summaries,
                missing_descriptions,
                missing_titles,
                unknown_title_tokens,
            )


def _apply_top_level_translations(openapi_payload: dict[str, Any]) -> None:
    info = openapi_payload.get("info")
    if isinstance(info, dict):
        if isinstance(info.get("title"), str):
            info["title"] = "ADE API"
        if isinstance(info.get("summary"), str):
            info["summary"] = "面向 ADE 与本地 ADE API 工作流的运行时与控制 API"
        if isinstance(info.get("description"), str):
            info["description"] = (
                "提供用于 ADE API 运行时/控制/测试编排的版本化 API 路由。"
                "面向后端优先的 API 调用，并用于 ADE Web 集成。"
            )

    servers = openapi_payload.get("servers")
    if isinstance(servers, list):
        for server in servers:
            if isinstance(server, dict) and isinstance(server.get("description"), str):
                if server["description"] == "ADE API local":
                    server["description"] = "ADE API 本地服务"


def _apply_tag_translations(openapi_payload: dict[str, Any]) -> None:
    tags = openapi_payload.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict) and isinstance(tag.get("name"), str):
                tag["name"] = TAG_TRANSLATIONS.get(tag["name"], tag["name"])

    paths = openapi_payload.get("paths")
    if not isinstance(paths, dict):
        return

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            operation_tags = operation.get("tags")
            if not isinstance(operation_tags, list):
                continue
            operation["tags"] = [
                TAG_TRANSLATIONS.get(tag, tag) if isinstance(tag, str) else tag
                for tag in operation_tags
            ]


def _write_missing_report(
    report_path: Path,
    missing_summaries: set[str],
    missing_descriptions: set[str],
    missing_titles: set[str],
    unknown_title_tokens: set[str],
) -> None:
    payload = {
        "missing_summaries": sorted(missing_summaries),
        "missing_descriptions": sorted(missing_descriptions),
        "missing_titles": sorted(missing_titles),
        "unknown_title_tokens": sorted(unknown_title_tokens),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_canonical_json(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate manually curated Chinese OpenAPI artifact."
    )
    parser.add_argument(
        "--source",
        default="docs/openapi/ade-api-openapi.json",
        help="Source English OpenAPI artifact path.",
    )
    parser.add_argument(
        "--target",
        default="docs/openapi/ade-api-openapi-zh.json",
        help="Target Chinese OpenAPI artifact path.",
    )
    parser.add_argument(
        "--frontend-target",
        default="apps/ade-web/public/openapi/ade-api-openapi-zh.json",
        help="Frontend copy path for Chinese OpenAPI artifact.",
    )
    parser.add_argument(
        "--missing-report",
        default="docs/openapi/zh_openapi_missing_terms.json",
        help="Path to write untranslated term report for incremental curation.",
    )
    parser.add_argument(
        "--no-missing-report",
        action="store_true",
        help="Disable writing missing-term report.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    source_path = (project_root / args.source).resolve()
    target_path = (project_root / args.target).resolve()
    frontend_target_path = (project_root / args.frontend_target).resolve()
    missing_report_path = (project_root / args.missing_report).resolve()

    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected OpenAPI root object.")

    missing_summaries: set[str] = set()
    missing_descriptions: set[str] = set()
    missing_titles: set[str] = set()
    unknown_title_tokens: set[str] = set()

    _translate_document_fields(
        payload,
        missing_summaries,
        missing_descriptions,
        missing_titles,
        unknown_title_tokens,
    )
    _apply_top_level_translations(payload)
    _apply_tag_translations(payload)

    rendered = _canonical_json(payload)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    frontend_target_path.parent.mkdir(parents=True, exist_ok=True)

    target_path.write_text(rendered, encoding="utf-8")
    frontend_target_path.write_text(rendered, encoding="utf-8")

    print(f"[OK] Wrote Chinese OpenAPI artifact: {target_path}")
    print(f"[OK] Synced frontend Chinese OpenAPI artifact: {frontend_target_path}")
    if not args.no_missing_report:
        _write_missing_report(
            missing_report_path,
            missing_summaries,
            missing_descriptions,
            missing_titles,
            unknown_title_tokens,
        )
        print(f"[OK] Wrote missing-term report: {missing_report_path}")
        print(
            "[INFO] missing terms "
            f"summaries={len(missing_summaries)} "
            f"descriptions={len(missing_descriptions)} "
            f"titles={len(missing_titles)} "
            f"unknown_title_tokens={len(unknown_title_tokens)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
