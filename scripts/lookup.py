#!/usr/bin/env python3
"""Lookup official glossary rows and community terms."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from glossary_files import GLOSSARY_FILES, resolve_glossaries


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TERMS = ROOT / "references" / "community-terms.tsv"
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
SEARCH_VARIANTS = {
    "前に出る": ("前出", "前に出"),
    "盤面を荒らす": ("盤面を荒ら",),
    "吐く": ("吐か", "吐き", "吐け", "吐い"),
    "芋る": ("芋ら", "芋り", "芋れ", "芋っ"),
}
AMBIGUOUS_TERMS = {
    "カニ": ("吐", "スペシャル", "バリア", "タンク", "発動", "貯め", "割"),
    "バケツ": ("ブキ", "武器", "編成", "キル", "射程", "イベント", "持"),
    "ホット": ("ブキ", "武器", "ブラスター", "キル", "射程", "持"),
    "エリア": ("ガチ", "ルール", "塗", "確保", "カウント", "打開", "抑え"),
    "ヤグラ": ("ガチ", "ルール", "乗", "カウント", "関門", "打開", "抑え"),
    "ホコ": ("ガチ", "ルール", "持", "割", "カウント", "関門", "打開"),
    "アサリ": ("ガチ", "ルール", "ゴール", "集", "入", "カウント", "打開"),
    "海岸": ("シャケ", "オオモノ", "金イクラ", "納品", "カゴ", "湧", "処理"),
    "処理": ("シャケ", "オオモノ", "雑魚", "金イクラ", "カゴ", "湧", "海岸"),
}
SPLATOON_HINTS = (
    "スプラ",
    "ブキ",
    "武器",
    "インク",
    "キル",
    "デス",
    "スペシャル",
    "味方",
    "敵",
    "シャケ",
    "バイト",
    "ガチ",
    "ナワバリ",
    "イベントマッチ",
)


def normalized(value: str) -> str:
    return SPACE_RE.sub("", value).casefold()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def glossary_relevance(row: dict[str, str], text: str, exact: bool) -> tuple[int, int] | None:
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
        if len(text_normalized) >= 2 and text_normalized in source_normalized:
            return (1, len(text_normalized))
        return None
    if source_folded in text_folded or source_normalized in text_normalized:
        minimum = 2 if row["语言"] == "ja" else 3
        if len(source_normalized) >= minimum:
            return (2, len(source))
    return None


def compact_glossary_row(row: dict[str, str], details: bool) -> str:
    fields = [row["语言"], row["原文"], row["首选简中译名"], row["类别"]]
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


def glossary_json_row(row: dict[str, str]) -> dict[str, str | list[str]]:
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


def lookup_glossary(args: argparse.Namespace) -> int:
    text = args.query if args.query is not None else args.text
    text_normalized = normalized(text)
    exact = args.query is not None
    matches: list[tuple[tuple[int, int], dict[str, str]]] = []

    hinted = inferred_domains(text) if args.domain == "auto" and not args.glossary else []
    for glossary in search_order(text, args.domain, args.glossary):
        for row in load_rows(glossary):
            if args.language and row["语言"] != args.language:
                continue
            score = glossary_relevance(row, text, exact)
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
    for _, row in filtered:
        key = (row["语言"], row["原文"], row["首选简中译名"])
        if key in emitted:
            continue
        output_rows.append(row)
        emitted.add(key)
        if len(output_rows) >= args.limit:
            break

    if args.json:
        print(json.dumps([glossary_json_row(row) for row in output_rows], ensure_ascii=False))
    else:
        for row in output_rows:
            print(compact_glossary_row(row, args.details))
    return 0


def context_confidence(term: str, text: str, mode: str) -> str:
    if term not in AMBIGUOUS_TERMS:
        return "确定"
    if mode == "splatoon":
        return "确定"
    if mode == "general":
        return "需确认"
    hints = (*AMBIGUOUS_TERMS[term], *SPLATOON_HINTS)
    return "可能" if any(hint in text for hint in hints) else "需确认"


def community_json_row(row: dict[str, str], confidence: str) -> dict[str, str]:
    return {
        "source": row["日文"],
        "recommended_zh": row["推荐简中"],
        "category": row["类别"],
        "note": row["说明"],
        "source_url": row["来源"],
        "status": row["状态"],
        "risk": row["风险"],
        "context_confidence": confidence,
    }


def lookup_community(args: argparse.Namespace) -> int:
    text = args.query if args.query is not None else args.text
    target = normalized(text)
    exact = args.query is not None

    with args.terms.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    matches: list[dict[str, str]] = []
    matched_forms: dict[str, str] = {}
    for row in rows:
        term = normalized(row["日文"])
        variants = tuple(normalized(value) for value in SEARCH_VARIANTS.get(row["日文"], ()))
        present = [value for value in (term, *variants) if value in target]
        if term == target or (not exact and len(term) >= 2 and present):
            matches.append(row)
            matched_forms[row["日文"]] = max(present or [term], key=len)

    matches.sort(key=lambda row: len(normalized(row["日文"])), reverse=True)
    filtered: list[dict[str, str]] = []
    for row in matches:
        short = matched_forms[row["日文"]]
        occurrences = target.count(short)
        covered = 0
        for other in matches:
            long = matched_forms[other["日文"]]
            if len(long) > len(short) and short in long:
                covered += target.count(long) * long.count(short)
        if occurrences > covered:
            filtered.append(row)

    output_rows = filtered[: args.limit]
    if args.json:
        print(
            json.dumps(
                [
                    community_json_row(
                        row,
                        context_confidence(row["日文"], text, args.context),
                    )
                    for row in output_rows
                ],
                ensure_ascii=False,
            )
        )
        return 0

    for row in output_rows:
        fields = [row["日文"], row["推荐简中"], row["类别"], row["说明"]]
        confidence = context_confidence(row["日文"], text, args.context)
        if confidence != "确定":
            fields.append(f"语境={confidence}")
        if args.details:
            fields.extend([row["来源"], f"状态={row['状态']}", f"风险={row['风险']}"])
        print("\t".join(fields))
    return 0


def add_text_query_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="Find all terms contained in source text")
    group.add_argument("--query", help="Find one term")
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output matches as JSON")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    glossary = subparsers.add_parser("glossary", help="Search official glossary TSVs")
    add_text_query_args(glossary)
    glossary.add_argument("--language", choices=("ja", "en"))
    glossary.add_argument("--limit", type=int, default=20)
    glossary.add_argument(
        "--domain",
        choices=("auto", "all", "core", "weapons", "stages", "gear"),
        default="auto",
    )
    glossary.add_argument(
        "--glossary",
        type=Path,
        action="append",
        help="TSV file or directory; repeat to search multiple locations",
    )
    glossary.set_defaults(func=lookup_glossary)

    community = subparsers.add_parser("community", help="Search community terms")
    add_text_query_args(community)
    community.add_argument("--limit", type=int, default=15)
    community.add_argument("--terms", type=Path, default=DEFAULT_TERMS)
    community.add_argument(
        "--context",
        choices=("auto", "splatoon", "general"),
        default="auto",
        help="Control ambiguous ordinary-word interpretation",
    )
    community.set_defaults(func=lookup_community)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
