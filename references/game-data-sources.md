# Game localization sources

Use the following aligned Splatoon 3 language files when regenerating exact in-game terminology:

- Japanese: `https://leanny.github.io/splat3/data/language/JPja.json`
- Simplified Chinese: `https://leanny.github.io/splat3/data/language/CNzh.json`
- English: `https://leanny.github.io/splat3/data/language/EUen.json`

These files are mirrors of extracted game localization data. Treat matching Chinese strings as in-game names, but describe Leanny's site as a community-hosted mirror rather than a Nintendo website.

## Imported paths

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

`game-data-version.json` records the last checked date, byte sizes, and SHA-256 hashes. Run `scripts/check_game_data_version.py` before refreshing the glossary. A `CHANGED` result means the mirror has new content and the metadata must be updated after reviewing and importing it.
