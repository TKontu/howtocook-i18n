# Architecture — HowToCook English Translation

## 1. Goal and quality bar

Produce a **complete, current, and high-quality** English edition of
[Anduin2017/HowToCook](https://github.com/Anduin2017/HowToCook), using local
compute and a multi-pass LLM pipeline that trades cycles for quality.

The bar is set explicitly against the existing prior art,
[Teygeta/HowToCook-en](https://github.com/Teygeta/HowToCook-en), which we must beat:

| Dimension | Prior fork (Teygeta) | Our target |
|---|---|---|
| Coverage | 296 / 364 recipes | 100% of current upstream |
| Freshness | ~13 months stale | Re-syncs with upstream on demand |
| Residual Chinese | ~59 files with leftover zh | 0 (hard-validated) |
| Step numbering | Flattened to bullets | Preserved exactly |
| Boilerplate (calories, footer) | Sometimes dropped | Always present, deterministic |
| Terminology | Literal/inconsistent | Glossary-enforced, consistent |
| Punctuation | Full-width `～`,`（）` remain | Normalized to ASCII |

The prior fork is kept only as an optional **second-opinion baseline** for spot
checks, not as a starting point.

## 2. Repository topology

Two repositories with distinct responsibilities:

1. **Toolkit repo (new, you own it).** The pipeline: `translate.py`, `validate.py`,
   `glossary.json`, this `ARCHITECTURE.md`, `TODO.md`, `README.md`. Reusable,
   small, no recipe content.
2. **Content fork (fork of HowToCook).** The translated recipes, produced by
   running the toolkit. Configured with the original as an `upstream` remote so
   deltas can be pulled and re-translated.

```
toolkit-repo/                      content-fork/ (fork of Anduin2017/HowToCook)
  translate.py                       dishes/
  validate.py                          meat_dish/
  refine.py            ─ runs on ─>      可乐鸡翅.md       (original, untouched)
  glossary.json                          可乐鸡翅.en.md    (generated)
  manifest.json (state)              tips/
  ARCHITECTURE.md / TODO.md          remote: upstream -> Anduin2017/HowToCook
```

Output uses **sibling `*.en.md` files** in the same directory as each source, so
relative image paths keep resolving with zero rewriting and no filename slug map
is needed. Filenames stay Chinese; the English dish name lives in the H1.

## 3. Why this corpus is easy to validate

Confirmed by scanning the real repo: all **364 dish files** follow one template —
H1 `# X的做法`, then a difficulty line, a calorie line, and exactly four H2
sections in fixed order (`必备原料和工具 / 计算 / 操作 / 附加内容`), then a fixed
Issue/PR footer. No YAML frontmatter. This means the bulk of each file can be
translated **deterministically** and the same template is a near-perfect
**validation oracle**.

## 4. Pipeline (quality-first, multi-pass)

```
            ┌─────────────────────────────────────────────────────────┐
 corpus ───>│ 0. analyze   1. glossary   2. boilerplate                │
            │ 3. draft     4. self-critique/refine   5. back-translate │
            │ 6. normalize 7. validate   8. human-review queue         │
            │ 9. link-rewrite   10. index/site   11. upstream sync     │
            └─────────────────────────────────────────────────────────┘
```

**Stage 0 — Corpus analysis.** Already done: counts, template confirmation,
image/link inventory. Re-run after each upstream sync.

**Stage 1 — Glossary extraction & curation.** A pre-pass scans every file for
high-frequency culinary nouns/verbs/units and proposes English equivalents (LLM),
which a human reviews once into `glossary.json`. This is the single biggest
quality lever; doing it before bulk translation guarantees corpus-wide
consistency. `boilerplate` (exact-string) entries are translated deterministically
and never sent to the model.

**Stage 2 — Deterministic boilerplate layer.** The four section headers, the
difficulty/calorie labels, and the footer are replaced by exact-string mapping —
not the model — eliminating the most common drift seen in the prior fork.

**Stage 3 — Draft translation.** A large local model (see §5) translates the
variable prose with the glossary injected, temperature 0, with explicit rules:
preserve heading levels, **keep numbered lists numbered**, leave image/link
targets and numbers untouched, convert full-width punctuation to ASCII.

**Stage 4 — Self-critique / refinement.** A second model pass receives
`(source, draft)` and rewrites for: faithfulness (no added/dropped meaning),
fluency (natural cookbook English), completeness (every source line represented),
terminology (matches glossary), and structure (sections/numbering intact). Using
a *different* model from the draft model gives an ensemble cross-check. Iterate up
to N rounds while the critic still finds substantive issues — this is where your
spare compute goes.

**Stage 5 — Back-translation verification (targeted).** For files the critic or
validator flags, translate the English back to Chinese and semantically compare to
the source (embedding similarity or an LLM judge). Large divergence => route to
human review. Run on flagged files only; optionally on all for max assurance.

**Stage 6 — Normalization.** Force the canonical English headers/boilerplate via
regex regardless of model output, so consistency is guaranteed even if a pass
varied.

**Stage 7 — Validation (automated, blocking).** Per file: exactly the four
canonical H2s in order; image-count unchanged vs source; numbered-step count
preserved; zero residual Han characters in visible text; no full-width
punctuation; all relative links resolve. Failures are marked `needs_review` in the
manifest, never silently shipped.

**Stage 8 — Human review queue.** Only files that fail validation or back-
translation. The manifest lists them with their specific problems.

**Stage 9 — Link rewrite.** Internal `*.md` cross-links become `*.en.md` so
English files reference English files; Chinese path segments are preserved.

**Stage 10 — Index / site.** Generate an English index (adapt upstream's
`.github/readme-generate.js`) from the `name_en` fields recorded in the manifest;
optionally build the static site.

**Stage 11 — Upstream sync loop.** `git pull upstream`; the manifest's per-file
content hash detects changed/added recipes; only those re-enter the pipeline.

## 5. Model strategy (local compute)

- **Draft model:** a strong zh→en instruct model, e.g. Qwen2.5-32B/72B-Instruct.
- **Critic model:** a *different* family if possible (e.g. a Llama/DeepSeek-class
  instruct model) for genuine cross-checking rather than self-agreement.
- **Judge/embeddings:** any local embedding model for back-translation similarity.
- Temperature 0 for draft/normalize; small temperature allowed for the critic's
  rewrite. Recipes are short, so full files fit in context — translate whole-file
  to preserve context, never chunk mid-recipe.
- Concurrency limited by VRAM; the manifest makes the whole run resumable, so
  long unattended runs are safe.

## 6. State and idempotency

`manifest.json` keys each source path to `{hash, status, out, name_en, problems,
passes, secs}`. Re-running skips unchanged `ok` files and reprocesses anything
whose source hash changed or that needs review. This is what makes both the
quality iterations and the upstream syncs cheap and repeatable.

## 7. Components

| File | Role | Status |
|---|---|---|
| `glossary.json` | boilerplate (deterministic) + terms (prompt-injected) | seed exists, expand in Stage 1 |
| `translate.py` | discovery, draft, normalize, validate, manifest, link-rewrite | working (draft path) |
| `refine.py` | self-critique/refinement + back-translation | **to build (Stage 4–5)** |
| `validate.py` | standalone QA report | working |
| `build_index.py` | English index/site generation | to build (Stage 10) |
