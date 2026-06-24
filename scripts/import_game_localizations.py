#!/usr/bin/env python3
"""Merge aligned Splatoon 3 localization names into split glossary TSV files."""

from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from glossary_files import GLOSSARY_FILES, group_for_category, resolve_glossaries

DEFAULT_URLS = {
    "ja": "https://leanny.github.io/splat3/data/language/JPja.json",
    "zh": "https://leanny.github.io/splat3/data/language/CNzh.json",
    "en": "https://leanny.github.io/splat3/data/language/EUen.json",
}

SECTIONS = [
    ("主武器", "CommonMsg/Weapon/WeaponName_Main"),
    ("特殊武器", "CommonMsg/Weapon/WeaponName_Special"),
    ("副武器", "CommonMsg/Weapon/WeaponName_Sub"),
    ("武器类别", "CommonMsg/Weapon/WeaponTypeName"),
    ("对战地图", "CommonMsg/VS/VSStageName"),
    ("鲑鱼跑地图", "CommonMsg/Coop/CoopStageName"),
    ("头部装备", "CommonMsg/Gear/GearName_Head"),
    ("服装", "CommonMsg/Gear/GearName_Clothes"),
    ("鞋子", "CommonMsg/Gear/GearName_Shoes"),
    ("装备能力", "CommonMsg/Gear/GearPowerName"),
    ("装备品牌", "CommonMsg/Gear/GearBrandName"),
]

FIELDNAMES = [
    "原文",
    "语言",
    "首选简中译名",
    "别名",
    "类别",
    "适用作品",
    "备注",
    "依据",
    "状态",
]

TAG_RE = re.compile(r"\[(?:/?[^\]]+)\]")
SPACE_RE = re.compile(r"[ \u3000]+")


@dataclass(frozen=True)
class GeneratedRow:
    source: str
    language: str
    chinese: str
    category: str
    evidence: str
    sort_key: tuple[int, str, str]


def load_json(location: str) -> dict[str, Any]:
    if location.startswith(("https://", "http://")):
        request = urllib.request.Request(
            location,
            headers={"User-Agent": "translate-splatoon-zh glossary importer"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    with Path(location).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clean_text(value: str) -> str:
    value = TAG_RE.sub("", value)
    value = value.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return SPACE_RE.sub(" ", value).strip()


def read_existing(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != FIELDNAMES:
                raise ValueError(f"Glossary header does not match schema: {path}")
            rows.extend(reader)
    return rows


def generated_rows(
    japanese: dict[str, Any],
    chinese: dict[str, Any],
    english: dict[str, Any],
) -> list[GeneratedRow]:
    rows: list[GeneratedRow] = []
    seen: dict[tuple[str, str], str] = {}

    for section_index, (category, section) in enumerate(SECTIONS):
        language_sections = {
            "ja": japanese.get(section, {}),
            "zh": chinese.get(section, {}),
            "en": english.get(section, {}),
        }
        if not all(isinstance(value, dict) for value in language_sections.values()):
            raise ValueError(f"Missing or invalid localization section: {section}")

        common_ids = set.intersection(
            *(set(value) for value in language_sections.values())
        )
        for message_id in sorted(common_ids):
            ja = clean_text(language_sections["ja"][message_id])
            zh = clean_text(language_sections["zh"][message_id])
            en = clean_text(language_sections["en"][message_id])
            if not ja or not zh or not en:
                continue
            if ja == "-" or zh == "-" or en == "-":
                continue

            # Side Order has untranslated generic weapon-class placeholders.
            if message_id.endswith("_Sdodr") and ja == zh == en:
                continue

            evidence = f"游戏语言文件：{section}#{message_id}"
            for language, source in (("ja", ja), ("en", en)):
                key = (language, source.casefold())
                previous = seen.get(key)
                if previous is not None:
                    if previous != zh:
                        raise ValueError(
                            f"Conflicting localization for {language}:{source}: "
                            f"{previous!r} vs {zh!r}"
                        )
                    continue
                seen[key] = zh
                rows.append(
                    GeneratedRow(
                        source=source,
                        language=language,
                        chinese=zh,
                        category=category,
                        evidence=evidence,
                        sort_key=(section_index, message_id, language),
                    )
                )
    return rows


def merge_rows(
    existing: list[dict[str, str]],
    generated: list[GeneratedRow],
) -> list[dict[str, str]]:
    generated_by_key = {
        (row.language, row.source.casefold()): row for row in generated
    }
    merged: list[dict[str, str]] = []
    consumed: set[tuple[str, str]] = set()

    for current in existing:
        key = (current["语言"], current["原文"].casefold())
        replacement = generated_by_key.get(key)
        if replacement is None:
            merged.append(current)
            continue

        aliases = [item.strip() for item in current["别名"].split("|") if item.strip()]
        old_preferred = current["首选简中译名"].strip()
        if old_preferred and old_preferred != replacement.chinese:
            aliases.append(old_preferred)
        aliases = list(dict.fromkeys(item for item in aliases if item != replacement.chinese))

        updated = dict(current)
        updated.update(
            {
                "首选简中译名": replacement.chinese,
                "别名": "|".join(aliases),
                "类别": replacement.category,
                "适用作品": "斯普拉遁3",
                "依据": replacement.evidence,
                "状态": "verified",
            }
        )
        merged.append(updated)
        consumed.add(key)

    for row in sorted(generated, key=lambda item: item.sort_key):
        key = (row.language, row.source.casefold())
        if key in consumed:
            continue
        merged.append(
            {
                "原文": row.source,
                "语言": row.language,
                "首选简中译名": row.chinese,
                "别名": "",
                "类别": row.category,
                "适用作品": "斯普拉遁3",
                "备注": "",
                "依据": row.evidence,
                "状态": "verified",
            }
        )
        consumed.add(key)
    return merged


def write_rows(rows: list[dict[str, str]]) -> None:
    grouped = {name: [] for name in GLOSSARY_FILES}
    for row in rows:
        grouped[group_for_category(row["类别"])].append(row)
    for name, path in GLOSSARY_FILES.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=FIELDNAMES,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(grouped[name])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jp", default=DEFAULT_URLS["ja"])
    parser.add_argument("--zh", default=DEFAULT_URLS["zh"])
    parser.add_argument("--en", default=DEFAULT_URLS["en"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    existing = read_existing(resolve_glossaries())
    generated = generated_rows(
        load_json(args.jp),
        load_json(args.zh),
        load_json(args.en),
    )
    merged = merge_rows(existing, generated)
    write_rows(merged)
    print(
        f"OK: generated {len(generated)} language rows; "
        f"glossary now contains {len(merged)} rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
