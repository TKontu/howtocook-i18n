# TODO — HowToCook English Translation

Phased checklist. Each phase ends in a state you can stop at safely.

## Phase 0 — Setup
- [ ] Create the **toolkit repo** (this code) on GitHub.
- [ ] **Fork** `Anduin2017/HowToCook` for the content; clone the fork.
- [ ] In the content fork: `git remote add upstream https://github.com/Anduin2017/HowToCook` (enables sync).
- [ ] Clone with `GIT_LFS_SKIP_SMUDGE=1` (skip ~350 LFS images; only paths matter).
- [ ] Install local model server (Ollama / vLLM / llama.cpp).
- [ ] Pull a draft model (e.g. `qwen2.5:32b-instruct`) and a *different* critic model.
- [ ] `python translate.py --repo ../HowToCook --dry-run --limit 5` to confirm plumbing.

## Phase 1 — Glossary (do before bulk translation)
- [ ] Build the extraction pass: scan all files for frequent culinary terms/units.
- [ ] LLM-propose English equivalents; export to a review sheet.
- [ ] Human-review into `glossary.json` (`terms`); fix the literal-translation traps
      the prior fork hit (小葱→scallion, etc.).
- [ ] Lock the `boilerplate` map (headers, difficulty, calories, footer).

## Phase 2 — Pilot (tune before scale)
- [ ] Translate ~15–20 recipes across all categories (`--limit`).
- [ ] Read every pilot output end-to-end; note recurring issues.
- [ ] Adjust glossary + prompt rules until pilots are clean.
- [ ] Confirm numbered steps stay numbered and no boilerplate is dropped.

## Phase 3 — Full draft
- [ ] Run the full draft pass over all 364 dishes + 17 tips (resumable).
- [ ] Review the manifest; triage `needs_review` files.

## Phase 4 — Refinement & QA (where the spare compute goes)
- [ ] Build `refine.py`: self-critique/refinement pass (critic model, N rounds).
- [ ] Add targeted back-translation verification for flagged files.
- [ ] Run refinement across the corpus.
- [ ] `python validate.py --repo ../HowToCook` → drive `needs_review` to zero.
- [ ] Human-review the residual flagged set.

## Phase 5 — Links, index, site
- [ ] `python translate.py --repo ../HowToCook --rewrite-links`.
- [ ] Build `build_index.py`: English index from manifest `name_en` fields.
- [ ] (Optional) Adapt upstream's `readme-generate.js`; build the static site/PDF.
- [ ] Replace Chinese-typography lint (textlint rules) with English-appropriate lint.

## Phase 6 — Publish & maintain
- [ ] Decide layout: sibling `.en.md` upstream-PR style, or strip to EN-only branch.
- [ ] Write the fork README; credit upstream and the prior Teygeta fork.
- [ ] Publish.
- [ ] Establish sync routine: `git pull upstream` → re-run draft (delta only) →
      refine → validate.

## Open decisions (resolve during Phase 1–2)
- [ ] Units: keep 斤/两 glossed, or convert to grams?
- [ ] Difficulty stars & calorie wording: keep as-is or localize?
- [ ] Tips files (free-form, not templated): same pipeline or lighter handling?
- [ ] Publishing form: sibling files (PR-friendly) vs EN-only fork (cleaner product)?
- [ ] Use the prior fork as a second-opinion baseline in `refine.py`, or ignore it?
