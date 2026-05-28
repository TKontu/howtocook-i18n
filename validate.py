#!/usr/bin/env python3
"""Re-validate all *.en.md against their Chinese source. Run after any manual edits.
Usage: python validate.py --repo ../HowToCook"""
import argparse, re
from pathlib import Path

HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
FULLWIDTH = re.compile(r'[\uff01-\uff5e\u3000-\u303f]')
IMG = re.compile(r'!\[[^\]]*\]\([^)]*\)')
MDLINK = re.compile(r'(?<!\!)\[[^\]]+\]\(([^)]+)\)')
H2 = re.compile(r'^##\s+(.+)$', re.M)
CANON = ["Required Ingredients and Tools", "Portions", "Steps", "Additional Notes"]


def check(en: Path):
    zh = en.with_name(en.name[:-6] + ".md")  # strip .en.md -> .md
    t = en.read_text(encoding="utf-8")
    p = []
    if zh.exists():
        s = zh.read_text(encoding="utf-8")
        if len(IMG.findall(t)) != len(IMG.findall(s)):
            p.append("image-count")
    if "dishes" in en.parts and H2.findall(t) != CANON:
        p.append("headers")
    body = MDLINK.sub("", IMG.sub("", t))
    if HAN.search(body):
        p.append("residual-zh")
    if FULLWIDTH.search(body):
        p.append("fullwidth-punct")
    # links should resolve
    for tgt in MDLINK.findall(t):
        if tgt.startswith(("http", "#")):
            continue
        if not (en.parent / tgt).exists():
            p.append(f"deadlink:{tgt}")
    return p


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True)
    repo = Path(ap.parse_args().repo)
    files = sorted(repo.rglob("*.en.md"))
    bad = 0
    for f in files:
        probs = check(f)
        if probs:
            bad += 1
            print(f"FAIL {f.relative_to(repo)}: {', '.join(probs)}")
    print(f"\n{len(files)} files, {len(files)-bad} clean, {bad} need attention")


if __name__ == "__main__":
    main()
