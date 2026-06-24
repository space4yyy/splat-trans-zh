---
name: translate-splatoon-zh
description: Translate Japanese, English, or mixed-language Splatoon content into natural Simplified Chinese using official CN localization, exact weapon/stage/gear names, and established Chinese player terminology. 斯普拉遁日英转简中翻译；适用于短句、截图、UI、武器、装备、地图、公告、对话、攻略、社交帖、字幕和翻译校对。
---

# 斯普拉遁日英转简中翻译

输出自然、可直接使用的简体中文。保留原意、语气、数字、条件、格式和游戏术语。

## 高效查术语

不要把 `references/glossary/` 下的全部文件加载进上下文。

不要因为原文长就自动查表。先判断文本里是否有斯普拉遁专名、简称、武器/地图/装备名或战术黑话；没有这些候选项时，直接翻译。

只查询候选词。优先使用本地文本搜索工具，首选 `rg`：

```bash
rg -n -F -e 'ロングブラスター' -e 'カニタンク' \
  references/glossary/*.tsv references/community-terms.tsv
```

如果没有 `rg`，使用 `grep -nF`、编辑器搜索或其他有边界的文本搜索。内置 Python 查询脚本只是便利工具，不是普通翻译的运行前提。官方术语查询会优先路由到可能的领域文件，只在必要时回退：

```bash
python3 scripts/lookup_glossary.py --text '<source text>'
python3 scripts/lookup_community_terms.py --text '<source text>'
```

如果没有本地执行或文件搜索能力，根据上下文和通用知识翻译。能联网时核实未知专名；否则保留为 `「原文」`。不要编造音译，也不要把整份 TSV 当作兜底加载。

游戏解包本地化结果用于确定官方名称。社群术语只用于黑话和战术含义，不能证明某个译名是官方名。`seeded` 社群条目只当线索；遇到敏感、争议或高风险表达时，先在线核实。

对既可能是简称、也可能是普通日语词的表达，只有在斯普拉遁语境成立时才采用社群含义。社群查询会把歧义匹配标成 `语境=可能` 或 `语境=需确认`；必须结合句子判断，不要自动接受。只有周围材料明确是游戏语境时，才使用 `--context splatoon`。正式文本优先官方全名，玩家闲聊优先通行中文昵称。

按文本类型选择查找路径：

| 场景 | 先查 | 再查 | 输出原则 |
| --- | --- | --- | --- |
| 游戏内名称、UI、武器、地图、装备 | `references/glossary/*.tsv` | 当前官方简中资料 | 用官方或表内首选译名 |
| 攻略、社交帖、玩家吐槽 | `references/glossary/*.tsv` | `references/community-terms.tsv` | 正式名称和通行黑话按语境混用 |
| 对战简称、战术黑话、鲑鱼跑口语 | `references/community-terms.tsv` | 日文社群来源 | 只在游戏语境成立时采用社群含义 |
| 新赛季、更新公告、未入表新名词 | 当前官方资料 | `references/glossary/*.tsv` | 来源不足时保留 `「原文」` 并说明待确认 |
| 人名、团体、歌曲、品牌、活动标题 | `references/glossary/*.tsv` | 官方页面或游戏数据 | 未确认时保留 `「原文」`，不要音译 |
| 纯普通日英文本 | 不查表 | 无 | 直接自然翻译，不强行套斯普拉遁术语 |

只在需要时读取额外文件：

- `references/translation-guide.md`：处理歧义、黑话、对话、截图、双关、校对、更新公告或来源冲突。
- `references/game-data-sources.md`：只在维护术语表时读取。
- `references/japanese-community-source.md`：需要 Wiki 路由、来源限制或在线社群核实时读取。
- `references/translation-regression-cases.tsv`：只用于维护和回归审查；普通翻译不要加载。
- `references/correction-workflow.md`：用户指出翻译错误后按此流程处理。

## 翻译规则

1. 按片段识别日语、英语或混合文本。
2. 只根据已有证据判断游戏语境，不强行套术语。
3. 按场景调整文风：UI 简短，公告精确，对话保留角色感，玩家发言自然口语化。
4. 同一概念全文保持一个中文说法。不要自创简称，也不要把非官方说法标成官方。
5. 交付前检查漏译、逻辑反转、数值、日期、占位符和格式。

截图翻译要保留视觉分组；看不清的文字标为 `[无法辨认]`。

未知的人名、地名、团体名、道具名或其他专名，保留原文并放入 `「」`，例如 `「ウズシオ諸島」`。不要音译。已确认的作品标题继续用 `《》`，普通引语用 `“”`，不要用 `【】` 标记未知名词。

## 输出格式

短句翻译默认只输出译文；只有术语、歧义或来源问题值得说明时才补充解释。

长文本使用：

```markdown
## 译文
<translation>

## 关键术语
<only useful clarifications>
```

只有真实不确定时才写 `待确认`。如果用户要求校对，先列问题，再给干净修订版。

## 维护术语表

- Python 只作为术语表再生成和校验工具；普通翻译不依赖 Python。
- 用 `python3 scripts/check_game_data_version.py` 检查来源新鲜度。
- 用 `scripts/import_game_localizations.py` 重新生成游戏解包术语。
- 官方术语按领域存放：`core.tsv`、`weapons.tsv`、`stages.tsv`、`gear.tsv`。
- 用 `python3 scripts/check_glossary.py references/glossary` 校验官方术语修改。
- 用 `python3 scripts/check_community_terms.py references/community-terms.tsv` 校验社群术语修改。
- 用 `python3 scripts/check_translation_cases.py references/translation-regression-cases.tsv` 校验黄金翻译用例。
- 用 `python3 scripts/smoke_test.py` 跑回归检查。
- 用 `python3 scripts/validate_all.py` 跑全部离线检查。
- `references/community-terms.tsv` 保持简洁、转述式记录；不要复制 Wiki 原文长段或评论。
- 用户纠错被官方或可靠来源确认后，更新相关 reference；如果同类错误可能复发，增加回归用例。
