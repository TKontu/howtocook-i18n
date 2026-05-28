# howtocook-i18n

> A local-LLM pipeline that translates the [HowToCook](https://github.com/Anduin2017/HowToCook) recipe collection into English — structure-aware, glossary-driven, and fully resumable.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

`HowToCook` is a 360+ recipe cookbook written in Simplified Chinese. This toolkit
translates it to English with a model running entirely on your own machine — no
API keys, no data leaving your computer — while preserving markdown structure,
keeping terminology consistent, and validating every file it produces.

It runs against a **fork** of HowToCook and writes each translation as a sibling
`<name>.en.md` next to the original, so relative image links keep working and the
fork can still pull upstream updates.

## Features

- **Local-only.** Talks to a local model server (Ollama / vLLM / llama.cpp). Nothing is sent to a third party.
- **Structure-preserving.** Headings, numbered steps, lists, image paths, and links survive intact.
- **Consistent terminology.** A culinary glossary is injected into every prompt; fixed boilerplate is translated deterministically.
- **Validated output.** Every file is checked for the correct section template, matching image counts, resolving links, and zero residual Chinese.
- **Resumable & sync-friendly.** A content-hash manifest skips unchanged files, so runs can be interrupted and upstream changes re-translated incrementally.

## Quick start

```bash
# 1. Fork HowToCook, then clone your fork (skip the ~350 LFS images — only paths matter)
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/<you>/HowToCook
cd HowToCook && git remote add upstream https://github.com/Anduin2017/HowToCook && cd ..

# 2. Get this toolkit and a local model
git clone https://github.com/<you>/howtocook-i18n && cd howtocook-i18n
ollama pull qwen2.5:32b-instruct      # strong zh→en; use a smaller tag for speed

# 3. Smoke-test with no model, then translate
python translate.py --repo ../HowToCook --dry-run --limit 5
python translate.py --repo ../HowToCook --model qwen2.5:32b-instruct
python translate.py --repo ../HowToCook --rewrite-links
python validate.py  --repo ../HowToCook
```

## Usage

```
python translate.py --repo PATH        # translate dishes + tips into sibling .en.md files
  --model NAME                          # local model tag (default: qwen2.5:14b-instruct)
  --host URL                            # model server (default: http://localhost:11434)
  --limit N                             # process only the first N files (piloting)
  --dry-run                             # run deterministic + validation stages, no model
  --rewrite-links                       # second pass: point .md cross-links at .en.md

python validate.py --repo PATH          # QA report over all .en.md files
```

`manifest.json` records a hash and status per source file. Re-running skips files
already translated cleanly; after `git pull upstream`, only changed recipes are
reprocessed.

## How it works

```
analyze → glossary → boilerplate → draft → refine → normalize → validate → link-rewrite → index
```

Most of each recipe is fixed template text (four standard sections, a difficulty
and calorie line, a footer) that is translated by exact-string mapping for
guaranteed consistency. The model handles only the variable prose, with the
glossary supplied as context. Output is then normalized to canonical headings and
checked against the template before it is accepted.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full multi-pass design
(including the self-critique and back-translation stages) and [`TODO.md`](./TODO.md)
for the roadmap.

## Configuration

`glossary.json` is the main quality lever and is meant to be edited:

- **`boilerplate`** — exact strings replaced deterministically (section headings, labels, footer).
- **`terms`** — culinary terms injected into every prompt so wording stays consistent across the whole corpus.

## Repository layout

| Path | Purpose |
|---|---|
| `translate.py` | translation driver: discovery, draft, normalize, validate, link-rewrite |
| `validate.py` | standalone QA report |
| `glossary.json` | boilerplate map + culinary glossary |
| `ARCHITECTURE.md` | full pipeline design |
| `TODO.md` | roadmap |

This repo holds the **tooling**; the translated recipes live in your **HowToCook fork**.

## Roadmap

- [x] Draft translation, deterministic boilerplate, normalization, validation, link rewriting
- [ ] Self-critique / refinement pass with a second model (`refine.py`)
- [ ] Targeted back-translation verification
- [ ] Glossary extraction pass over the full corpus
- [ ] English index / site generation

## Contributing

Issues and pull requests are welcome — glossary additions and prompt improvements
especially.

## Related

- [Anduin2017/HowToCook](https://github.com/Anduin2017/HowToCook) — the original cookbook (source).
- [Teygeta/HowToCook-en](https://github.com/Teygeta/HowToCook-en) — an earlier community English translation.

## License

Released under the MIT License — see [`LICENSE`](./LICENSE). The HowToCook recipe
content is released into the public domain (The Unlicense) by its authors.
