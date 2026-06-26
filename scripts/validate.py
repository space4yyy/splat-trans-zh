#!/usr/bin/env python3
"""Validate skill data and run offline regression checks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path

from glossary_files import group_for_category, resolve_glossaries


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
REFERENCES = ROOT / "references"
DEFAULT_METADATA = REFERENCES / "game-data-version.json"
GLOSSARY_COLUMNS = [
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
GLOSSARY_LANGUAGES = {"ja", "en"}
GLOSSARY_STATUSES = {"verified", "community", "contextual", "review"}
PLACEHOLDER_VALUES = {"-", "—", "N/A", "n/a", "None", "none", "null"}
GENERATED_EVIDENCE_PREFIX = "游戏语言文件："
COMMUNITY_COLUMNS = ["日文", "推荐简中", "类别", "说明", "来源", "状态", "风险"]
COMMUNITY_STATUSES = {"seeded", "verified"}
COMMUNITY_RISKS = {"低", "中", "高"}
CASE_COLUMNS = ["编号", "类型", "原文", "参考译文", "必须包含", "禁止包含", "说明"]
CASE_TYPES = {"公告", "攻略", "对话", "吐槽", "未知专名", "鲑鱼跑", "补丁", "术语", "短句", "社交帖", "系统"}


def split_values(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def validate_glossary_paths(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    seen: dict[tuple[str, str], int] = {}
    aliases: dict[tuple[str, str], set[str]] = defaultdict(set)
    global_line = 1

    for path in paths:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != GLOSSARY_COLUMNS:
                errors.extend(
                    [
                        f"{path} 表头不匹配：应为 " + " | ".join(GLOSSARY_COLUMNS),
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

                if language not in GLOSSARY_LANGUAGES:
                    errors.append(f"{location}：未知语言 {language!r}")
                if status not in GLOSSARY_STATUSES:
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
                if (
                    path.suffix == ".tsv"
                    and path.stem in {"core", "weapons", "stages", "gear"}
                    and path.stem != expected_group
                ):
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
                    errors.append(f"{location}：与先前条目重复术语 {language}:{source}")
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


def validate_community_path(path: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != COMMUNITY_COLUMNS:
            return [
                "表头不匹配：应为 " + " | ".join(COMMUNITY_COLUMNS),
                "实际表头：" + " | ".join(reader.fieldnames or []),
            ]
        for line, row in enumerate(reader, start=2):
            for field in COMMUNITY_COLUMNS:
                if not row[field].strip():
                    errors.append(f"第 {line} 行：{field} 不能为空")
            term = row["日文"].strip()
            if term in seen:
                errors.append(f"第 {line} 行：与第 {seen[term]} 行重复术语 {term}")
            else:
                seen[term] = line
            if row["状态"] not in COMMUNITY_STATUSES:
                errors.append(f"第 {line} 行：未知状态 {row['状态']!r}")
            if row["风险"] not in COMMUNITY_RISKS:
                errors.append(f"第 {line} 行：未知风险 {row['风险']!r}")
            if row["风险"] == "高" and not row["说明"].strip():
                errors.append(f"第 {line} 行：高风险术语必须说明语气或限制")
            if not row["来源"].startswith("https://"):
                errors.append(f"第 {line} 行：来源必须是 HTTPS URL")
    return errors


def validate_cases_path(path: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != CASE_COLUMNS:
            return [
                "表头不匹配：应为 " + " | ".join(CASE_COLUMNS),
                "实际表头：" + " | ".join(reader.fieldnames or []),
            ]
        for line, row in enumerate(reader, start=2):
            for field in CASE_COLUMNS:
                if not row[field].strip():
                    errors.append(f"第 {line} 行：{field} 不能为空")
            case_id = row["编号"].strip()
            if case_id in seen:
                errors.append(f"第 {line} 行：与第 {seen[case_id]} 行重复编号 {case_id}")
            else:
                seen[case_id] = line
            if row["类型"] not in CASE_TYPES:
                errors.append(f"第 {line} 行：未知类型 {row['类型']!r}")
            for required in split_values(row["必须包含"]):
                if required not in row["参考译文"]:
                    errors.append(f"第 {line} 行：参考译文缺少 {required!r}")
            for forbidden in split_values(row["禁止包含"]):
                if forbidden in row["参考译文"]:
                    errors.append(f"第 {line} 行：参考译文包含禁用内容 {forbidden!r}")
    return errors


def report_errors(errors: list[str]) -> int:
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


def count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig") as handle:
        return sum(1 for _ in handle) - 1


def command_glossary(args: argparse.Namespace) -> int:
    paths = resolve_glossaries(args.paths)
    if not paths or any(not path.is_file() for path in paths):
        print("一个或多个术语文件不存在", file=sys.stderr)
        return 2
    errors = validate_glossary_paths(paths)
    if report_errors(errors):
        return 1
    row_count = sum(count_rows(path) for path in paths)
    print(f"OK: {len(paths)} glossary files ({row_count} entries)")
    return 0


def command_community(args: argparse.Namespace) -> int:
    errors = validate_community_path(args.path)
    if report_errors(errors):
        return 1
    print(f"OK: {args.path} ({count_rows(args.path)} entries)")
    return 0


def command_cases(args: argparse.Namespace) -> int:
    errors = validate_cases_path(args.path)
    if report_errors(errors):
        return 1
    print(f"OK: {args.path} ({count_rows(args.path)} cases)")
    return 0


def run_lookup(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "lookup.py"), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def require(output: str, expected: str) -> None:
    if expected not in output:
        raise AssertionError(f"Expected {expected!r} in:\n{output}")


def reject(output: str, unexpected: str) -> None:
    if unexpected in output:
        raise AssertionError(f"Unexpected {unexpected!r} in:\n{output}")


def check_glossary_rejects_bad_rows() -> None:
    header = "\t".join(GLOSSARY_COLUMNS)
    bad_rows = [
        "-\tja\t-\t\t主武器\t斯普拉遁3\t\t游戏语言文件：X#Y\tverified",
        "Bad Gear\ten\t坏装备\t别名|别名\t头部装备\t斯普拉遁3\t\t游戏语言文件：X#Y\tcommunity",
        "Contextual\ten\t语境词\t\t机制\t全系列\t\thttps://example.com\tcontextual",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "weapons.tsv"
        path.write_text(header + "\n" + "\n".join(bad_rows) + "\n", encoding="utf-8")
        errors = validate_glossary_paths([path])
    output = "\n".join(errors)
    require(output, "术语和译名不能使用占位值")
    require(output, "类别 '头部装备' 应放在 gear.tsv")
    require(output, "游戏语言文件依据不能标为 community")
    require(output, "contextual 状态必须填写备注")
    require(output, "重复别名")


def command_smoke(_: argparse.Namespace) -> int:
    check_glossary_rejects_bad_rows()

    weapon = run_lookup("glossary", "--text", "ホットブラスター艶")
    require(weapon, "ホットブラスター艶\t火热爆破枪 艳")
    reject(weapon, "\tブラスター\t爆破枪")

    weapon_domain = run_lookup(
        "glossary", "--domain", "weapons", "--query", "ホットブラスター艶"
    )
    require(weapon_domain, "ホットブラスター艶\t火热爆破枪 艳")

    title = run_lookup("glossary", "--text", "スプラトゥーン レイダース")
    require(title, "スプラトゥーンレイダース\t斯普拉遁 涂击队")
    reject(title, "突袭者")

    event = run_lookup("glossary", "--text", "ビッグビッグラン")
    require(event, "ビッグビッグラン\t超级大型跑")

    mixed_domains = run_lookup(
        "glossary",
        "--text",
        "ロングブラスターでナンプラー遺跡のエリアを抑えた。",
    )
    require(mixed_domains, "ロングブラスター\t远距爆破枪")
    require(mixed_domains, "ナンプラー遺跡\t鱼露遗迹")

    glossary_json = json.loads(
        run_lookup("glossary", "--json", "--query", "ロングブラスター")
    )
    assert glossary_json[0]["source"] == "ロングブラスター"
    assert glossary_json[0]["preferred_zh"] == "远距爆破枪"

    slang = run_lookup(
        "community",
        "--text",
        "イカ速ガン積みして盤面を荒らしまくる",
    )
    require(slang, "盤面を荒らす\t搅乱场面")
    reject(slang, "盤面\t场面")

    stage_short_name = run_lookup("community", "--text", "どんぴこ")
    require(stage_short_name, "どんぴこ\t鲑鱼心脏斗技场")

    abbreviations = run_lookup(
        "community",
        "--text",
        "スクイクを消して。スシはカニ吐かせてから前出る。バケツもいる。",
    )
    require(abbreviations, "スクイク\t鱿快洁")
    require(abbreviations, "スシ\t小绿")
    require(abbreviations, "カニ\t螃蟹坦克")
    require(abbreviations, "バケツ\t飞溅泼桶")

    ambiguous = run_lookup("community", "--text", "カニを食べた")
    require(ambiguous, "カニ\t螃蟹坦克")
    require(ambiguous, "语境=需确认")

    game_context = run_lookup("community", "--text", "カニ吐かせてから前に出る")
    require(game_context, "カニ\t螃蟹坦克")
    require(game_context, "语境=可能")

    community_json = json.loads(
        run_lookup("community", "--json", "--text", "カニ吐かせて")
    )
    crab = next(item for item in community_json if item["source"] == "カニ")
    assert crab["recommended_zh"] == "螃蟹坦克"
    assert crab["context_confidence"] == "可能"

    forced_context = run_lookup("community", "--context", "splatoon", "--text", "カニ")
    require(forced_context, "カニ\t螃蟹坦克")
    reject(forced_context, "语境=")

    salmon = run_lookup(
        "community",
        "--text",
        "海岸のオオモノを間引きして、寄せた後は金イクラを納品。雑魚処理も忘れずに。",
    )
    require(salmon, "オオモノ\t大型鲑鱼")
    require(salmon, "間引き\t提前清怪")
    require(salmon, "寄せ\t引怪")
    require(salmon, "金イクラ\t金鲑鱼卵")
    require(salmon, "納品\t交蛋")
    require(salmon, "雑魚処理\t清杂")

    print("OK: smoke tests passed")
    return 0


def read_bytes(location: str) -> bytes:
    if location.startswith(("https://", "http://")):
        request = urllib.request.Request(
            location,
            headers={"User-Agent": "translate-splatoon-zh version checker"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    return Path(location).read_bytes()


def command_version(args: argparse.Namespace) -> int:
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    overrides = {"JPja": args.jp, "CNzh": args.zh, "EUen": args.en}
    changed = False

    for name, recorded in metadata["sources"].items():
        location = overrides[name] or recorded["url"]
        content = read_bytes(location)
        digest = hashlib.sha256(content).hexdigest()
        status = "OK"
        if digest != recorded["sha256"] or len(content) != recorded["bytes"]:
            status = "CHANGED"
            changed = True
        print(
            f"{status}: {name} bytes={len(content)} sha256={digest} "
            f"recorded_at={metadata['checked_at']}"
        )
    return 1 if changed else 0


def command_all(args: argparse.Namespace) -> int:
    commands = [
        (command_glossary, argparse.Namespace(paths=[REFERENCES / "glossary"])),
        (command_community, argparse.Namespace(path=REFERENCES / "community-terms.tsv")),
        (command_cases, argparse.Namespace(path=REFERENCES / "translation-regression-cases.tsv")),
        (command_smoke, argparse.Namespace()),
    ]
    for command, namespace in commands:
        status = command(namespace)
        if status:
            return status
    print("OK: all offline validations passed")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    all_parser = subparsers.add_parser("all", help="Run every offline validation")
    all_parser.set_defaults(func=command_all)

    glossary = subparsers.add_parser("glossary", help="Validate official glossary TSVs")
    glossary.add_argument("paths", type=Path, nargs="+")
    glossary.set_defaults(func=command_glossary)

    community = subparsers.add_parser("community", help="Validate community terms TSV")
    community.add_argument("path", type=Path)
    community.set_defaults(func=command_community)

    cases = subparsers.add_parser("cases", help="Validate translation regression cases")
    cases.add_argument("path", type=Path)
    cases.set_defaults(func=command_cases)

    smoke = subparsers.add_parser("smoke", help="Run lookup regression tests")
    smoke.set_defaults(func=command_smoke)

    version = subparsers.add_parser("version", help="Check recorded game data hashes")
    version.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    version.add_argument("--jp")
    version.add_argument("--zh")
    version.add_argument("--en")
    version.set_defaults(func=command_version)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
