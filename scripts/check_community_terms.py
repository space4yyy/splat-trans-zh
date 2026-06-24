#!/usr/bin/env python3
"""Validate the compact Japanese community terminology table."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


FIELDS = ["日文", "推荐简中", "类别", "说明", "来源", "状态"]
STATUSES = {"seeded", "verified"}


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
            term = row["日文"].strip()
            if term in seen:
                errors.append(f"第 {line} 行：与第 {seen[term]} 行重复术语 {term}")
            else:
                seen[term] = line
            if row["状态"] not in STATUSES:
                errors.append(f"第 {line} 行：未知状态 {row['状态']!r}")
            if not row["来源"].startswith("https://"):
                errors.append(f"第 {line} 行：来源必须是 HTTPS URL")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: check_community_terms.py <community-terms.tsv>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    with path.open("r", encoding="utf-8-sig") as handle:
        count = sum(1 for _ in handle) - 1
    print(f"OK: {path} ({count} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
