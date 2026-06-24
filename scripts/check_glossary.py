#!/usr/bin/env python3
"""Validate the Splatoon translation glossary TSV."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

from glossary_files import group_for_category, resolve_glossaries

REQUIRED_COLUMNS = [
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
ALLOWED_LANGUAGES = {"ja", "en"}
ALLOWED_STATUSES = {"verified", "community", "contextual", "review"}
PLACEHOLDER_VALUES = {"-", "—", "N/A", "n/a", "None", "none", "null"}
GENERATED_EVIDENCE_PREFIX = "游戏语言文件："


def validate(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    seen: dict[tuple[str, str], int] = {}
    aliases: dict[tuple[str, str], set[str]] = defaultdict(set)
    global_line = 1

    for path in paths:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != REQUIRED_COLUMNS:
                errors.extend(
                    [
                        f"{path} 表头不匹配：应为 " + " | ".join(REQUIRED_COLUMNS),
                        "实际表头：" + " | ".join(reader.fieldnames or []),
                    ]
                )
                continue

            for line_number, row in enumerate(reader, start=2):
                global_line += 1
                location = f"{path.name}:{line_number}"
                source = row["原文"].strip()
                language = row["语言"].strip()
                preferred = row["首选简中译名"].strip()
                category = row["类别"].strip()
                evidence = row["依据"].strip()
                status = row["状态"].strip()

                for column in ("原文", "语言", "首选简中译名", "类别", "适用作品", "依据", "状态"):
                    if not row[column].strip():
                        errors.append(f"{location}：{column} 不能为空")

                if language not in ALLOWED_LANGUAGES:
                    errors.append(f"{location}：未知语言 {language!r}")
                if status not in ALLOWED_STATUSES:
                    errors.append(f"{location}：未知状态 {status!r}")
                if source in PLACEHOLDER_VALUES or preferred in PLACEHOLDER_VALUES:
                    errors.append(
                        f"{location}：术语和译名不能使用占位值 {source!r}/{preferred!r}"
                    )
                if "\n" in source or "\r" in source or "\n" in preferred or "\r" in preferred:
                    errors.append(f"{location}：术语和译名不能包含换行控制字符")
                if source != row["原文"] or preferred != row["首选简中译名"]:
                    errors.append(f"{location}：原文和首选简中译名不能有首尾空白")

                expected_group = group_for_category(category)
                if path.suffix == ".tsv" and path.stem in {"core", "weapons", "stages", "gear"} and path.stem != expected_group:
                    errors.append(
                        f"{location}：类别 {category!r} 应放在 {expected_group}.tsv"
                    )
                if status == "community" and evidence.startswith(GENERATED_EVIDENCE_PREFIX):
                    errors.append(f"{location}：游戏语言文件依据不能标为 community")
                if status in {"contextual", "review"} and not row["备注"].strip():
                    errors.append(f"{location}：{status} 状态必须填写备注")
                if "http://" in evidence:
                    errors.append(f"{location}：依据 URL 必须使用 HTTPS")

                key = (language, source.casefold())
                if key in seen:
                    errors.append(
                        f"{location}：与先前条目重复术语 {language}:{source}"
                    )
                else:
                    seen[key] = global_line

                row_aliases: set[str] = set()
                for alias in row["别名"].split("|"):
                    alias = alias.strip()
                    if alias:
                        alias_key = alias.casefold()
                        if alias_key in row_aliases:
                            errors.append(f"{location}：重复别名 {alias}")
                        row_aliases.add(alias_key)
                        if alias == source:
                            errors.append(f"{location}：别名不能与原文相同 {alias}")
                        if alias in PLACEHOLDER_VALUES:
                            errors.append(f"{location}：别名不能使用占位值 {alias}")
                        aliases[(language, alias.casefold())].add(preferred)

    for (language, alias), preferred_terms in sorted(aliases.items()):
        if len(preferred_terms) > 1:
            errors.append(
                f"别名冲突：{language}:{alias} 映射到 "
                + "、".join(sorted(preferred_terms))
            )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: check_glossary.py <glossary.tsv-or-dir> [...]", file=sys.stderr)
        return 2

    paths = resolve_glossaries([Path(value) for value in sys.argv[1:]])
    if not paths or any(not path.is_file() for path in paths):
        print("一个或多个术语文件不存在", file=sys.stderr)
        return 2

    errors = validate(paths)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    row_count = 0
    for path in paths:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            row_count += sum(1 for _ in handle) - 1
    print(f"OK: {len(paths)} glossary files ({row_count} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
