# HowToCook → English translation toolkit

A resumable, **quality-first** pipeline to translate the public-domain
[Anduin2017/HowToCook](https://github.com/Anduin2017/HowToCook) recipes into
English with a **local LLM**. See `ARCHITECTURE.md` for the full design and
`TODO.md` for the build plan.

## Prior art (checked)

An English fork already exists — [Teygeta/HowToCook-en](https://github.com/Teygeta/HowToCook-en) —
but it is a weak baseline, not a finished product:

- last commit ~April 2025 (stale by over a year);
- 296 of upstream's current 364 recipes (missing ~68 newer dishes);
- ~59 files still contain Chinese; numbered steps were flattened to bullets;
  some boilerplate (calories, the Issue/PR footer) was dropped; literal
  terminology ("Small onion" for 小葱, "## Operation"/"## Calculation").

With local compute and a multi-pass approach we can do clearly better. The prior
fork is kept only as an optional second-opinion baseline.

## Two repositories

- **This toolkit repo** — the pipeline code (yours, reusable).
- **A fork of HowToCook** — the translated content, produced by running this
  toolkit, with the original added as an `upstream` remote so new/changed recipes
  can be pulled and re-translated. (Fork, don't start a detached repo — that's
  what preserves upstream sync.)

## Why the design works

- **Public domain (Unlicense)** — translate and republish freely.
- **Folder names are already English**; only filenames are Chinese.
- **All 364 recipes share one 4-section template** → most of each file is
  translated *deterministically*, and that template is a strong automatic
  validation signal.
- Output is **sibling `<name>.en.md`** next to each original, so relative image
  paths keep working untouched and no filename slug map is needed.

## Quality-first pipeline (summary)

1. glossary extraction & human curation → corpus-wide consistency
2. deterministic boilerplate (headers, difficulty, calories, footer)
3. draft translation (large local model, temp 0, numbered lists preserved)
4. self-critique / refinement (a *different* critic model, N rounds)
5. targeted back-translation verification for flagged files
6. normalization → 7. blocking validation → 8. human-review queue
9. link rewrite → 10. English index/site → 11. upstream sync (delta only)

`translate.py` implements stages 2–3, 6–7, 9 today; `refine.py` (stages 4–5) and
`build_index.py` (stage 10) are on the TODO.

## Setup

```bash
git clone https://github.com/Anduin2017/HowToCook   # GIT_LFS_SKIP_SMUDGE=1 to skip images
cd HowToCook && git remote add upstream https://github.com/Anduin2017/HowToCook
ollama pull qwen2.5:32b-instruct      # draft model; pull a different model as critic
```

## Workflow

```bash
python translate.py --repo ./HowToCook --dry-run --limit 5     # 0. plumbing test
python translate.py --repo ./HowToCook --model qwen2.5:32b-instruct --limit 15   # pilot
python translate.py --repo ./HowToCook --model qwen2.5:32b-instruct              # full draft
# (refine.py — self-critique + back-translation — to be added: Phase 4)
python translate.py --repo ./HowToCook --rewrite-links         # link pass
python validate.py  --repo ./HowToCook                         # QA report
```

`manifest.json` hashes each source file: runs are resumable, and after
`git pull upstream` only changed recipes are reprocessed.

## Tuning

`glossary.json` is the main lever. `boilerplate` = exact strings replaced
deterministically; `terms` = culinary glossary injected into every prompt. Grow
the glossary during the pilot rather than fiddling with the model.

## Open decisions

Unit conversion (斤/两), difficulty/calorie wording, tips-file handling, and
publish form (sibling-file PR vs EN-only fork) — tracked in `TODO.md`.
