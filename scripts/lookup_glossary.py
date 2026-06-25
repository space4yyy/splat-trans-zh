#!/usr/bin/env python3
"""Return only glossary rows relevant to a source phrase or text."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from glossary_files import GLOSSARY_FILES, resolve_glossaries

SPACE_RE = re.compile(r"\s+")
DOMAIN_HINTS = {
    "weapons": (
        "ブラスター", "シューター", "ローラー", "チャージャー", "スロッシャー",
        "スピナー", "マニューバー", "シェルター", "ストリンガー", "ワイパー",
        "ウェポン", "ボム", "タンク", "武器", "weapon", "blaster",
    ),
    "stages": ("ステージ", "地区", "市場", "放水路", "遺跡", "大橋", "どんぴこ", "stage"),
    "gear": ("ギア", "アタマ", "フク", "クツ", "ブランド", "服", "鞋", "帽", "gear"),
}


def normalized(value: str) -> str:
    return SPACE_RE.sub("", value).casefold()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def relevance(row: dict[str, str], text: str, exact: bool) -> tuple[int, int] | None:
    source = row["原文"].strip()
    if not source:
        return None

    source_folded = source.casefold()
    text_folded = text.casefold()
    source_normalized = normalized(source)
    text_normalized = normalized(text)

    if source_folded == text_folded or source_normalized == text_normalized:
        return (3, len(source))
    if exact:
        if (
            len(text_normalized) >= 2
            and text_normalized in source_normalized
        ):
            return (1, len(text_normalized))
        return None
    if source_folded in text_folded or source_normalized in text_normalized:
        # Suppress noisy one-character fragments and short English common words.
        minimum = 2 if row["语言"] == "ja" else 3
        if len(source_normalized) >= minimum:
            return (2, len(source))
    return None


def compact(row: dict[str, str], details: bool) -> str:
    fields = [
        row["语言"],
        row["原文"],
        row["首选简中译名"],
        row["类别"],
    ]
    if row["别名"]:
        fields.append(f"别名={row['别名']}")
    if details:
        fields.extend(
            [
                f"作品={row['适用作品']}",
                f"状态={row['状态']}",
                f"依据={row['依据']}",
            ]
        )
        if row["备注"]:
            fields.append(f"备注={row['备注']}")
    return "\t".join(fields)


def as_json_row(row: dict[str, str]) -> dict[str, str | list[str]]:
    return {
        "language": row["语言"],
        "source": row["原文"],
        "preferred_zh": row["首选简中译名"],
        "aliases": [item.strip() for item in row["别名"].split("|") if item.strip()],
        "category": row["类别"],
        "work": row["适用作品"],
        "note": row["备注"],
        "evidence": row["依据"],
        "status": row["状态"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="Find all glossary terms contained in source text")
    group.add_argument(
        "--query",
        help="Find one term; prefer exact matches, then source-name fragments",
    )
    parser.add_argument("--language", choices=("ja", "en"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output matches as JSON")
    parser.add_argument(
        "--domain",
        choices=("auto", "all", "core", "weapons", "stages", "gear"),
        default="auto",
    )
    parser.add_argument(
        "--glossary",
        type=Path,
        action="append",
        help="TSV file or directory; repeat to search multiple locations",
    )
    return parser.parse_args()


def inferred_domains(text: str) -> list[str]:
    folded = text.casefold()
    return [
        name
        for name, hints in DOMAIN_HINTS.items()
        if any(hint.casefold() in folded for hint in hints)
    ]


def search_order(text: str, domain: str, custom: list[Path] | None) -> list[Path]:
    if custom:
        return resolve_glossaries(custom)
    if domain in GLOSSARY_FILES:
        return [GLOSSARY_FILES[domain]]
    if domain == "all":
        return resolve_glossaries()

    hinted = inferred_domains(text)
    preferred = ["core", *hinted]
    return [
        GLOSSARY_FILES[name]
        for name in dict.fromkeys([*preferred, *GLOSSARY_FILES])
    ]


def main() -> int:
    args = parse_args()
    text = args.query if args.query is not None else args.text
    text_normalized = normalized(text)
    exact = args.query is not None
    matches: list[tuple[tuple[int, int], dict[str, str]]] = []

    hinted = inferred_domains(text) if args.domain == "auto" and not args.glossary else []
    for glossary in search_order(text, args.domain, args.glossary):
        for row in load_rows(glossary):
            if args.language and row["语言"] != args.language:
                continue
            score = relevance(row, text, exact)
            if score:
                matches.append((score, row))
        if matches and args.domain == "auto" and (
            exact or not hinted or glossary.stem not in hinted
        ):
            break

    matches.sort(key=lambda item: item[0], reverse=True)
    filtered: list[tuple[tuple[int, int], dict[str, str]]] = []
    for score, row in matches:
        short = normalized(row["原文"])
        occurrences = text_normalized.count(short)
        covered = 0
        for _, other in matches:
            if other["语言"] != row["语言"]:
                continue
            long = normalized(other["原文"])
            if len(long) > len(short) and short in long:
                covered += text_normalized.count(long) * long.count(short)
        if occurrences > covered:
            filtered.append((score, row))

    emitted: set[tuple[str, str, str]] = set()
    output_rows: list[dict[str, str]] = []
    count = 0
    for _, row in filtered:
        key = (row["语言"], row["原文"], row["首选简中译名"])
        if key in emitted:
            continue
        output_rows.append(row)
        emitted.add(key)
        count += 1
        if count >= args.limit:
            break
    if args.json:
        print(json.dumps([as_json_row(row) for row in output_rows], ensure_ascii=False))
    else:
        for row in output_rows:
            print(compact(row, args.details))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
