#!/usr/bin/env python3
"""Run small regression checks for lookup behavior and known terminology."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
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


def run_failure(script: str, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        raise AssertionError(f"Expected failure from {script} {' '.join(args)}")
    return result.stderr + result.stdout


def check_glossary_rejects_bad_rows() -> None:
    header = "\t".join(
        ["原文", "语言", "首选简中译名", "别名", "类别", "适用作品", "备注", "依据", "状态"]
    )
    bad_rows = [
        "-\tja\t-\t\t主武器\t斯普拉遁3\t\t游戏语言文件：X#Y\tverified",
        "Bad Gear\ten\t坏装备\t别名|别名\t头部装备\t斯普拉遁3\t\t游戏语言文件：X#Y\tcommunity",
        "Contextual\ten\t语境词\t\t机制\t全系列\t\thttps://example.com\tcontextual",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "weapons.tsv"
        path.write_text(header + "\n" + "\n".join(bad_rows) + "\n", encoding="utf-8")
        output = run_failure("check_glossary.py", str(path))
    require(output, "术语和译名不能使用占位值")
    require(output, "类别 '头部装备' 应放在 gear.tsv")
    require(output, "游戏语言文件依据不能标为 community")
    require(output, "contextual 状态必须填写备注")
    require(output, "重复别名")


def main() -> int:
    check_glossary_rejects_bad_rows()

    weapon = run("lookup_glossary.py", "--text", "ホットブラスター艶")
    require(weapon, "ホットブラスター艶\t火热爆破枪 艳")
    reject(weapon, "\tブラスター\t爆破枪")

    weapon_domain = run(
        "lookup_glossary.py", "--domain", "weapons", "--query", "ホットブラスター艶"
    )
    require(weapon_domain, "ホットブラスター艶\t火热爆破枪 艳")

    title = run("lookup_glossary.py", "--text", "スプラトゥーン レイダース")
    require(title, "スプラトゥーンレイダース\t斯普拉遁 涂击队")
    reject(title, "突袭者")

    event = run("lookup_glossary.py", "--text", "ビッグビッグラン")
    require(event, "ビッグビッグラン\t超级大型跑")

    mixed_domains = run(
        "lookup_glossary.py",
        "--text",
        "ロングブラスターでナンプラー遺跡のエリアを抑えた。",
    )
    require(mixed_domains, "ロングブラスター\t远距爆破枪")
    require(mixed_domains, "ナンプラー遺跡\t鱼露遗迹")

    glossary_json = json.loads(
        run("lookup_glossary.py", "--json", "--query", "ロングブラスター")
    )
    assert glossary_json[0]["source"] == "ロングブラスター"
    assert glossary_json[0]["preferred_zh"] == "远距爆破枪"

    slang = run(
        "lookup_community_terms.py",
        "--text",
        "イカ速ガン積みして盤面を荒らしまくる",
    )
    require(slang, "盤面を荒らす\t搅乱场面")
    reject(slang, "盤面\t场面")

    stage_short_name = run("lookup_community_terms.py", "--text", "どんぴこ")
    require(stage_short_name, "どんぴこ\t鲑鱼心脏斗技场")

    abbreviations = run(
        "lookup_community_terms.py",
        "--text",
        "スクイクを消して。スシはカニ吐かせてから前出る。バケツもいる。",
    )
    require(abbreviations, "スクイク\t鱿快洁")
    require(abbreviations, "スシ\t小绿")
    require(abbreviations, "カニ\t螃蟹坦克")
    require(abbreviations, "バケツ\t飞溅泼桶")

    ambiguous = run("lookup_community_terms.py", "--text", "カニを食べた")
    require(ambiguous, "カニ\t螃蟹坦克")
    require(ambiguous, "语境=需确认")

    game_context = run(
        "lookup_community_terms.py", "--text", "カニ吐かせてから前に出る"
    )
    require(game_context, "カニ\t螃蟹坦克")
    require(game_context, "语境=可能")

    community_json = json.loads(
        run("lookup_community_terms.py", "--json", "--text", "カニ吐かせて")
    )
    crab = next(item for item in community_json if item["source"] == "カニ")
    assert crab["recommended_zh"] == "螃蟹坦克"
    assert crab["context_confidence"] == "可能"

    forced_context = run(
        "lookup_community_terms.py", "--context", "splatoon", "--text", "カニ"
    )
    require(forced_context, "カニ\t螃蟹坦克")
    reject(forced_context, "语境=")

    salmon = run(
        "lookup_community_terms.py",
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


if __name__ == "__main__":
    raise SystemExit(main())
