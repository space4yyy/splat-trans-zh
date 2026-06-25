---
name: translate-splatoon-zh
description: Translate Japanese, English, or mixed-language Splatoon content into natural Simplified Chinese using official CN localization, exact weapon/stage/gear names, and established Chinese player terminology. 斯普拉遁日英转简中翻译；适用于短句、截图、UI、武器、装备、地图、公告、对话、攻略、社交帖、字幕和翻译校对。
---

# 斯普拉遁日英转简中翻译

输出自然、可直接使用的简体中文。保留原意、语气、数字、条件、格式和游戏术语。

## 输出契约

当用户请求是 `翻译:`、`翻译：`、`translate:` 或只给出待翻译文本时，只输出译文正文。即使原文有多行、列表或标题，也不要输出“译文如下”、背景说明、推荐译文、官方术语版、社群口语版、关键术语、翻译解析、Markdown 标题或项目符号外的额外内容。

保留原文的段落、列表和换行结构；原文是列表就输出对应中文列表，原文是标题就输出中文标题。不要增加原文没有的栏目。

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
python3 scripts/lookup.py glossary --text '<source text>'
python3 scripts/lookup.py community --text '<source text>'
```

默认离线翻译。不要为了普通短句、攻略问句、玩家吐槽、方向指示、常见地图/武器简称而使用 WebSearch。只有遇到当前活动、新公告、新作未入表名称、用户明确要求核实、来源冲突、纠错追溯、或敏感/高风险 `seeded` 社群条目时，才联网核实。没有联网或本地查不到时，根据上下文翻译；未知专名保留为 `「原文」`。不要编造音译，也不要把整份 TSV 当作兜底加载。

游戏解包本地化结果用于确定官方名称。社群术语只用于黑话和战术含义，不能证明某个译名是官方名。`seeded` 社群条目只当线索；遇到敏感、争议或高风险表达时，先说明不确定，必要时再在线核实。

对既可能是简称、也可能是普通日语词的表达，只有在斯普拉遁语境成立时才采用社群含义。社群查询会把歧义匹配标成 `语境=可能` 或 `语境=需确认`；必须结合句子判断，不要自动接受。只有周围材料明确是游戏语境时，才使用 `--context splatoon`。正式文本优先官方全名，玩家闲聊优先通行中文昵称。

按文本类型选择查找路径：

| 场景 | 先查 | 再查 | 输出原则 |
| --- | --- | --- | --- |
| 游戏内名称、UI、武器、地图、装备 | `references/glossary/*.tsv` | 仅在未入表且疑似新内容时查官方资料 | 用官方或表内首选译名 |
| 攻略、社交帖、玩家吐槽 | `references/glossary/*.tsv` | `references/community-terms.tsv` | 正式名称和通行黑话按语境混用 |
| 对战简称、战术黑话、鲑鱼跑口语 | `references/community-terms.tsv` | 只在高风险或用户要求时查日文社群来源 | 只在游戏语境成立时采用社群含义 |
| 新赛季、更新公告、未入表新名词 | `references/glossary/*.tsv` | 当前官方资料 | 来源不足时保留 `「原文」` 并说明待确认 |
| 人名、团体、歌曲、品牌、活动标题 | `references/glossary/*.tsv` | 仅在疑似官方名称缺失时查官方页面或游戏数据 | 未确认时保留 `「原文」`，不要音译 |
| 纯普通日英文本 | 不查表 | 无 | 直接自然翻译，不强行套斯普拉遁术语 |

只在需要时读取额外文件：

- `references/translation-guide.md`：处理歧义、黑话、对话、截图、双关、校对、更新公告或来源冲突。
- `references/maintenance.md`：维护术语表、检查游戏数据来源、处理用户纠错或在线社群核实时读取。
- `references/translation-regression-cases.tsv`：只用于维护和回归审查；普通翻译不要加载。

## 翻译规则

1. 按片段识别日语、英语或混合文本。
2. 只根据已有证据判断游戏语境，不强行套术语。
3. 按场景调整文风：UI 简短，公告精确，对话保留角色感，玩家发言自然口语化。
4. 同一概念全文保持一个中文说法。不要自创简称，也不要把非官方说法标成官方。
5. 交付前检查漏译、逻辑反转、数值、日期、占位符和格式。

截图翻译要保留视觉分组；看不清的文字标为 `[无法辨认]`。

未知的人名、地名、团体名、道具名或其他专名，保留原文并放入 `「」`，例如 `「ウズシオ諸島」`。不要音译。已确认的作品标题继续用 `《》`，普通引语用 `“”`，不要用 `【】` 标记未知名词。

## 输出格式

短句、标题、聊天消息、社交帖、截图单行文案和社交媒体多行列表默认只输出一版译文。不要添加 `##` 标题、推荐译文、官方术语版、社群口语版、关键术语、翻译解析、思路说明或额外项目符号。

只有用户明确要求解释、校对、比较版本、或原文存在真实歧义/来源冲突且会影响译文时，才在译文后补充一句简短说明。不要为了展示查到的术语而解释。

只有用户要求翻译长公告、文章、访谈、字幕稿，且没有要求“只给译文”时，才使用：

```markdown
## 译文
<translation>

## 关键术语
<only useful clarifications>
```

只有真实不确定时才写 `待确认`。如果用户要求校对，先列问题，再给干净修订版。

## 维护术语表

- Python 只作为术语表再生成和校验工具；普通翻译不依赖 Python。
- 用 `python3 scripts/validate.py version` 检查来源新鲜度。
- 用 `scripts/import_game_localizations.py` 重新生成游戏解包术语。
- 官方术语按领域存放：`core.tsv`、`weapons.tsv`、`stages.tsv`、`gear.tsv`。
- 用 `python3 scripts/validate.py glossary references/glossary` 校验官方术语修改。
- 用 `python3 scripts/validate.py community references/community-terms.tsv` 校验社群术语修改。
- 用 `python3 scripts/validate.py cases references/translation-regression-cases.tsv` 校验黄金翻译用例。
- 用 `python3 scripts/validate.py smoke` 跑回归检查。
- 用 `python3 scripts/validate.py all` 跑全部离线检查。
- `references/community-terms.tsv` 保持简洁、转述式记录；不要复制 Wiki 原文长段或评论。
- 用户纠错被官方或可靠来源确认后，更新相关 reference；如果同类错误可能复发，增加回归用例。
