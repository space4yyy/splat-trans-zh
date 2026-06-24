#!/usr/bin/env python3
"""Validate translation regression cases and their explicit constraints."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


FIELDS = ["编号", "类型", "原文", "参考译文", "必须包含", "禁止包含", "说明"]
TYPES = {"公告", "攻略", "对话", "吐槽", "未知专名"}


def split_values(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != FIELDS:
            return [
                "表头不匹配：应为 " + " | ".join(FIELDS),
                "实际表头：" + " | ".join(reader.fieldnames or []),
            ]
        for line, row in enumerate(reader, start=2):
            for field in FIELDS:
                if not row[field].strip():
                    errors.append(f"第 {line} 行：{field} 不能为空")
            case_id = row["编号"].strip()
            if case_id in seen:
                errors.append(f"第 {line} 行：与第 {seen[case_id]} 行重复编号 {case_id}")
            else:
                seen[case_id] = line
            if row["类型"] not in TYPES:
                errors.append(f"第 {line} 行：未知类型 {row['类型']!r}")
            for required in split_values(row["必须包含"]):
                if required not in row["参考译文"]:
                    errors.append(f"第 {line} 行：参考译文缺少 {required!r}")
            for forbidden in split_values(row["禁止包含"]):
                if forbidden in row["参考译文"]:
                    errors.append(f"第 {line} 行：参考译文包含禁用内容 {forbidden!r}")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: check_translation_cases.py <translation-regression-cases.tsv>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    with path.open("r", encoding="utf-8-sig") as handle:
        count = sum(1 for _ in handle) - 1
    print(f"OK: {path} ({count} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
