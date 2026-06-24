"""Shared glossary file routing."""

from __future__ import annotations

from pathlib import Path


GLOSSARY_DIR = Path(__file__).resolve().parent.parent / "references" / "glossary"
GLOSSARY_FILES = {
    "core": GLOSSARY_DIR / "core.tsv",
    "weapons": GLOSSARY_DIR / "weapons.tsv",
    "stages": GLOSSARY_DIR / "stages.tsv",
    "gear": GLOSSARY_DIR / "gear.tsv",
}

WEAPON_CATEGORIES = {"主武器", "特殊武器", "副武器", "武器类别", "武器系统"}
STAGE_CATEGORIES = {"对战地图", "鲑鱼跑地图"}
GEAR_CATEGORIES = {"头部装备", "服装", "鞋子", "装备能力", "装备品牌", "装备系统"}


def group_for_category(category: str) -> str:
    if category in WEAPON_CATEGORIES:
        return "weapons"
    if category in STAGE_CATEGORIES:
        return "stages"
    if category in GEAR_CATEGORIES:
        return "gear"
    return "core"


def resolve_glossaries(paths: list[Path] | None = None) -> list[Path]:
    if paths:
        resolved: list[Path] = []
        for path in paths:
            if path.is_dir():
                resolved.extend(sorted(path.glob("*.tsv")))
            else:
                resolved.append(path)
        return resolved
    return list(GLOSSARY_FILES.values())
