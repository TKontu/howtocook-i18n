#!/usr/bin/env python3
"""
HowToCook -> English translator.

Per file:
  1. skip if already done and source hash unchanged (manifest)
  2. LLM-translate the whole markdown (glossary + rules in the prompt)
  3. deterministically normalize the fixed template strings (headers, difficulty,
     calories, closing line) so the LLM can never drift on them
  4. validate structure; on failure, record and keep going
  5. write sibling <name>.en.md  (relative image paths keep working untouched)
Second pass: rewrite internal *.md cross-links to *.en.md.

LLM backend = local Ollama (http://localhost:11434). Swap call_llm() for any
local server (llama.cpp, vLLM, LM Studio) — it just takes/returns a string.

Usage:
  python translate.py --repo ../HowToCook --model qwen2.5:14b-instruct
  python translate.py --repo ../HowToCook --dry-run        # no LLM, tests plumbing
  python translate.py --repo ../HowToCook --limit 10       # pilot on 10 files
  python translate.py --repo ../HowToCook --rewrite-links  # run link pass only
"""
import argparse, hashlib, json, re, sys, time, urllib.request
from pathlib import Path

HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
FULLWIDTH = re.compile(r'[\uff01-\uff5e\u3000-\u303f]')  # full-width punct/space
IMG = re.compile(r'!\[[^\]]*\]\([^)]*\)')
MDLINK = re.compile(r'(?<!\!)\[[^\]]+\]\(([^)]+)\)')
H2 = re.compile(r'^##\s+(.+)$', re.M)

CANON_H2 = ["Required Ingredients and Tools", "Portions", "Steps", "Additional Notes"]


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def load_glossary(p: Path):
    g = json.loads(p.read_text(encoding="utf-8"))
    return g["boilerplate"], g["terms"]


def build_prompt(terms: dict):
    gloss = "\n".join(f"  {zh} -> {en}" for zh, en in terms.items())
    return (
        "You are a professional culinary translator. Translate the following "
        "Chinese recipe from a cookbook into natural English for a home cook.\n"
        "RULES:\n"
        "- Translate ALL Chinese text, including the title.\n"
        "- The H1 title MUST be exactly: '# How to Make <English dish name>'.\n"
        "- Preserve every markdown structure exactly: heading levels, list markers, "
        "numbering, blank lines, tables.\n"
        "- Do NOT translate, move, or alter image paths, URLs, or text inside (...) "
        "link targets. Leave file/image names in Chinese.\n"
        "- Keep all numbers and units; convert full-width punctuation to ASCII.\n"
        "- Use these section headings VERBATIM when you encounter them:\n"
        "    必备原料和工具 -> ## Required Ingredients and Tools\n"
        "    计算 -> ## Portions\n"
        "    操作 -> ## Steps\n"
        "    附加内容 -> ## Additional Notes\n"
        "- Use this terminology consistently:\n" + gloss + "\n"
        "- Output ONLY the translated markdown, no preamble, no code fences."
    )


def call_llm(system: str, user: str, model: str, host: str) -> str:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request(f"{host}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"].strip()


def normalize(text: str, boilerplate: dict) -> str:
    """Force the fixed template strings to canonical English, regardless of the LLM."""
    for zh, en in boilerplate.items():
        text = text.replace(zh, en)
    # collapse any LLM variants of the 4 headers to canonical forms
    fixes = {
        r'^##\s+.*Ingredients?.*Tools?.*$': "## Required Ingredients and Tools",
        r'^##\s+(Portion|Serving|Calculation|Quantit).*$': "## Portions",
        r'^##\s+(Steps?|Instructions?|Operation|Method).*$': "## Steps",
        r'^##\s+(Additional|Extra|Notes?|Tips?).*$': "## Additional Notes",
    }
    for pat, rep in fixes.items():
        text = re.sub(pat, rep, text, flags=re.M)
    return text


def english_name(text: str) -> str:
    m = re.search(r'^#\s+How to Make\s+(.+?)\s*$', text, re.M)
    return m.group(1).strip() if m else ""


def validate(text: str, src: str):
    problems = []
    h2 = H2.findall(text)
    if h2 != CANON_H2:
        problems.append(f"headers={h2} (want {CANON_H2})")
    if len(IMG.findall(text)) != len(IMG.findall(src)):
        problems.append("image count changed")
    # residual Chinese in *visible* text (ignore link/image targets)
    stripped = MDLINK.sub("", IMG.sub("", text))
    if HAN.search(stripped):
        problems.append("residual Chinese text")
    if FULLWIDTH.search(stripped):
        problems.append("full-width punctuation remains")
    return problems


def out_path(src: Path) -> Path:
    return src.with_suffix(".en.md")


def translate_file(src: Path, system, boilerplate, model, host, dry):
    raw = src.read_text(encoding="utf-8")
    if dry:
        # plumbing test: just run deterministic boilerplate, leave the rest
        text = normalize(raw, boilerplate)
    else:
        text = normalize(call_llm(system, raw, model, host), boilerplate)
    problems = validate(text, raw)
    out_path(src).write_text(text, encoding="utf-8")
    return raw, text, problems


def rewrite_links(repo: Path):
    """Make English files link to English files: foo.md -> foo.en.md (skip images/already-en)."""
    n = 0
    for f in repo.rglob("*.en.md"):
        t = f.read_text(encoding="utf-8")
        def repl(m):
            target = m.group(1)
            if target.endswith(".en.md") or not target.endswith(".md"):
                return m.group(0)
            # only repo-internal links (relative, or this repo's github blob URLs)
            if target.startswith(("http://", "https://")) and "Anduin2017/HowToCook" not in target:
                return m.group(0)
            return m.group(0).replace(target, target[:-3] + ".en.md")
        new = MDLINK.sub(repl, t)
        if new != t:
            f.write_text(new, encoding="utf-8"); n += 1
    print(f"link pass: rewrote links in {n} files")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--model", default="qwen2.5:14b-instruct")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--glossary", default="glossary.json")
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rewrite-links", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo)

    if a.rewrite_links:
        rewrite_links(repo); return

    boilerplate, terms = load_glossary(Path(a.glossary))
    system = build_prompt(terms)
    mpath = Path(a.manifest)
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {}

    # translate dishes first (templated), then tips
    files = sorted(repo.glob("dishes/**/*.md")) + sorted(repo.glob("tips/**/*.md"))
    files = [f for f in files if not f.name.endswith(".en.md")
             and "template" not in f.parts]
    if a.limit:
        files = files[:a.limit]

    done = failed = skipped = 0
    for i, src in enumerate(files, 1):
        rel = str(src.relative_to(repo))
        h = sha(src.read_text(encoding="utf-8"))
        rec = manifest.get(rel)
        if rec and rec.get("hash") == h and rec.get("status") == "ok":
            skipped += 1; continue
        t0 = time.time()
        try:
            raw, text, problems = translate_file(src, system, boilerplate,
                                                 a.model, a.host, a.dry_run)
            status = "ok" if not problems else "needs_review"
            manifest[rel] = {"hash": h, "status": status,
                             "out": str(out_path(src).relative_to(repo)),
                             "name_en": english_name(text), "problems": problems,
                             "secs": round(time.time() - t0, 1)}
            done += 1 if status == "ok" else 0
            failed += 1 if problems else 0
            flag = "OK " if not problems else "REV"
            print(f"[{i}/{len(files)}] {flag} {rel}  {problems if problems else ''}")
        except Exception as e:
            manifest[rel] = {"hash": h, "status": "error", "error": str(e)}
            failed += 1
            print(f"[{i}/{len(files)}] ERR {rel}: {e}")
        mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    print(f"\ndone={done} needs_review/err={failed} skipped={skipped}")
    print("Next: review flagged files in manifest, then: "
          "python translate.py --repo %s --rewrite-links" % a.repo)


if __name__ == "__main__":
    main()
