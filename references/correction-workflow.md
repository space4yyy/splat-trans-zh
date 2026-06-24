# Correction workflow

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
   - Add a lookup assertion to `scripts/smoke_test.py` for terminology or matching bugs.
   - Add a golden case to `translation-regression-cases.tsv` for translation behavior.
6. **Validate**
   - Run `python3 scripts/validate_all.py`.

Never retain a disproven inference as an alias. Keep an alternative only when reliable evidence shows that users actually use it.
