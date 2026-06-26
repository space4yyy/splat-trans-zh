# Maintenance

## Correction workflow

Apply this process when a user reports a mistranslation.

1. **Classify the error**
   - Exact name, community slang, meaning, tone, formatting, date/number, or unsupported inference.
2. **Recheck the source**
   - Search the game glossary first.
   - For current or missing names, check direct Nintendo Simplified Chinese material.
   - Use Japanese community sources only for slang and usage.
3. **State the correction**
   - Acknowledge whether the previous wording was sourced, inferred, or invented.
   - Give the corrected translation without defending the old output.
4. **Update the narrowest resource**
   - Official name: the matching file under `references/glossary/`.
   - Slang or abbreviation: `community-terms.tsv`.
   - General behavior: `translation-guide.md` or `SKILL.md`.
   - Source freshness: `game-data-version.json`.
5. **Prevent recurrence**
   - Add a lookup assertion to `scripts/validate.py smoke` for terminology or matching bugs.
   - Add a golden case to `translation-regression-cases.tsv` for translation behavior.
6. **Validate**
   - Run `python3 scripts/validate.py all`.

Never retain a disproven inference as an alias. Keep an alternative only when reliable evidence shows that users actually use it.

## Game localization sources

Use the following aligned Splatoon 3 language files when regenerating exact in-game terminology:

- Japanese: `https://leanny.github.io/splat3/data/language/JPja.json`
- Simplified Chinese: `https://leanny.github.io/splat3/data/language/CNzh.json`
- English: `https://leanny.github.io/splat3/data/language/EUen.json`

These files are mirrors of extracted game localization data. Treat matching Chinese strings as in-game names, but describe Leanny's site as a community-hosted mirror rather than a Nintendo website.

Imported paths:

- `CommonMsg/Weapon/WeaponName_Main`
- `CommonMsg/Weapon/WeaponName_Special`
- `CommonMsg/Weapon/WeaponName_Sub`
- `CommonMsg/Weapon/WeaponTypeName`
- `CommonMsg/VS/VSStageName`
- `CommonMsg/Coop/CoopStageName`
- `CommonMsg/Gear/GearName_Head`
- `CommonMsg/Gear/GearName_Clothes`
- `CommonMsg/Gear/GearName_Shoes`
- `CommonMsg/Gear/GearPowerName`
- `CommonMsg/Gear/GearBrandName`

Align entries by message path and internal ID, never by list position or translated text. Strip display markup such as Japanese ruby tags before matching. Preserve model codes and stylized suffixes exactly as localized.

Use `scripts/import_game_localizations.py` to download or read the three files, merge them into the category files under `references/glossary/`, and preserve hand-curated aliases and notes.

`game-data-version.json` records the last checked date, byte sizes, and SHA-256 hashes. Run `python3 scripts/validate.py version` before refreshing the glossary. A `CHANGED` result means the mirror has new content and the metadata must be updated after reviewing and importing it.

## Japanese community source

Primary community reference:

- Splatoon3 攻略＆検証 Wiki: `https://wikiwiki.jp/splatoon3mix/`

Use it for Japanese player slang, tactics, abbreviations, weapon usage, Salmon Run terminology, and wording context. Do not use it to override exact Simplified Chinese names extracted from the game.

Route by question:

- Battle slang and tactics: `https://wikiwiki.jp/splatoon3mix/用語集/対戦関連用語`
- Game abbreviations: `https://wikiwiki.jp/splatoon3mix/用語集/ゲーム内用語の略称一覧`
- Salmon Run and world terms: `https://wikiwiki.jp/splatoon3mix/用語集/スプラトゥーン世界の用語`
- General TPS terms: `https://wikiwiki.jp/splatoon3mix/用語集/対戦以外のTPS関連用語`
- Derogatory or sensitive terms: `https://wikiwiki.jp/splatoon3mix/用語集/注意すべき用語`
- Weapon-specific context: append the exact Japanese weapon name to `https://wikiwiki.jp/splatoon3mix/`

When online tools are available, open only the most relevant page and find the source term. Do not load every page. Treat definitions as community-authored and potentially disputed. Prefer page content over comments; use comments only to understand current usage.

The site prohibits reposting comments beyond legally permitted quotation. Store only short paraphrased conclusions with the source URL, not copied articles or comment threads.

Rows marked `seeded` in `community-terms.tsv` are locally curated starting points and have not necessarily been checked line-by-line against the linked page. Change a row to `verified` only after confirming its usage on the cited page.

Use the `风险` column to decide review priority:

- `高`: derogatory, judgmental, or easy to overstate. Verify before using in formal text.
- `中`: ambiguous abbreviation, context-sensitive map/mode/weapon term, or wording that may need sentence-level judgment.
- `低`: common tactical or system wording with low harm if paraphrased naturally.

## SkillHub release workflow

Use this process when publishing or updating this skill on 小红书 SkillHub.

Install or refresh the uploader if needed:

```bash
npm install -g "https://fe-video-qc.xhscdn.com/fe-platform-file/104101b8320o5lkablm0653u0hejenq0004pf88njcmq3g.tgz"
mkdir -p ~/.agents/skills/skillhub-upload
cp "$(npm root -g)/@xhs/skillhub-upload/skill/SKILL.md" \
  ~/.agents/skills/skillhub-upload/SKILL.md
```

Validated publish parameters for this project:

- Local skill path: `/Users/space4/Projects/splat-trans-zh`
- Skill ID: `translate-splatoon-zh`
- Display name: `斯普拉遁翻译`
- Source: `original`
- Tag: `效率工具`

Do not submit with the frontmatter `name` (`translate-splatoon-zh`) as the display name; SkillHub rejected it as too long. Keep the platform display name short and pass the stable Skill ID explicitly.

Before submitting, run local validation and dry-run:

```bash
python3 scripts/validate.py all
node /opt/homebrew/lib/node_modules/@xhs/skillhub-upload/cli/index.mjs publish \
  /Users/space4/Projects/splat-trans-zh \
  --dry-run --agent \
  --source original \
  --tag 效率工具 \
  --name 斯普拉遁翻译 \
  --identifier translate-splatoon-zh
```

After reviewing the dry-run payload, submit:

```bash
printf 'submit\n' | node /opt/homebrew/lib/node_modules/@xhs/skillhub-upload/cli/index.mjs publish \
  /Users/space4/Projects/splat-trans-zh \
  --agent \
  --source original \
  --tag 效率工具 \
  --name 斯普拉遁翻译 \
  --identifier translate-splatoon-zh
```

If the CLI returns `NEED_LOGIN`, run:

```bash
node /opt/homebrew/lib/node_modules/@xhs/skillhub-upload/cli/index.mjs login --agent
```

Follow the device authorization prompt, then rerun the submit command. The first successful SkillHub submission used `skill_id=2684` and `version_id=3269`; future updates should keep the same Skill ID and publish a new version.
