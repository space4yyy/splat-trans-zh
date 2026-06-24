#!/usr/bin/env python3
"""Return compact Japanese community-term matches for source text."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


DEFAULT_TERMS = Path(__file__).resolve().parent.parent / "references" / "community-terms.tsv"
SPACE_RE = re.compile(r"\s+")
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


def normalize(value: str) -> str:
    return SPACE_RE.sub("", value).casefold()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--query")
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output matches as JSON")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--terms", type=Path, default=DEFAULT_TERMS)
    parser.add_argument(
        "--context",
        choices=("auto", "splatoon", "general"),
        default="auto",
        help="Control ambiguous ordinary-word interpretation",
    )
    return parser.parse_args()


def context_confidence(term: str, text: str, mode: str) -> str:
    if term not in AMBIGUOUS_TERMS:
        return "确定"
    if mode == "splatoon":
        return "确定"
    if mode == "general":
        return "需确认"
    hints = (*AMBIGUOUS_TERMS[term], *SPLATOON_HINTS)
    return "可能" if any(hint in text for hint in hints) else "需确认"


def as_json_row(row: dict[str, str], confidence: str) -> dict[str, str]:
    return {
        "source": row["日文"],
        "recommended_zh": row["推荐简中"],
        "category": row["类别"],
        "note": row["说明"],
        "source_url": row["来源"],
        "status": row["状态"],
        "context_confidence": confidence,
    }


def main() -> int:
    args = parse_args()
    text = args.query if args.query is not None else args.text
    target = normalize(text)
    exact = args.query is not None

    with args.terms.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    matches: list[dict[str, str]] = []
    matched_forms: dict[str, str] = {}
    for row in rows:
        term = normalize(row["日文"])
        variants = tuple(normalize(value) for value in SEARCH_VARIANTS.get(row["日文"], ()))
        present = [value for value in (term, *variants) if value in target]
        if term == target or (not exact and len(term) >= 2 and present):
            matches.append(row)
            matched_forms[row["日文"]] = max(present or [term], key=len)

    matches.sort(key=lambda row: len(normalize(row["日文"])), reverse=True)
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
                    as_json_row(
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
            fields.extend([row["来源"], f"状态={row['状态']}"])
        print("\t".join(fields))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
