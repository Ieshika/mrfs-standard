"""Builds the three MRFS publication PDFs: Overview, Technical Standard, Validation Report.

Requires pandoc (3.x) and XeLaTeX with Latin Modern, TeX Gyre Heros and DejaVu Sans Mono.

Usage (from the repository root):
    python docs/publication/make_publication_docs.py .
    python docs/publication/build_publication.py
Outputs: docs/MRFS-Overview.pdf, docs/MRFS-Technical-Standard.pdf, docs/MRFS-Validation-Report.pdf
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STYLE = HERE / "style"
OUT = HERE.parent
KEEP = os.environ.get("MRFS_KEEP_TEX")  # optional: a directory in which to keep the .tex for inspection

VERSION = "2.0.0"
STATUS = "Published"
DATE = "11 October 2026"

DOCS = [
    {
        "name": "MRFS-Overview",
        "title": "MRFS Overview",
        "subtitle": "What the Marketplace Ranking Fairness Standard does, in brief",
        "short": "MRFS Overview",
        "front": None,
        "body": ["overview.md"],
        "appendix": [],
        "after": [],
        "toc": False,
    },
    {
        "name": "MRFS-Technical-Standard",
        "title": "MRFS Technical Standard",
        "subtitle": "Metrics, decision rules, audit procedure, governance and data specification",
        "short": "MRFS Technical Standard",
        "front": "standard/00_front.md",
        "body": ["standard/01_introduction.md", "standard/02_metrics.md", "standard/03_audit.md",
                 "standard/04_governance.md", "standard/05_data.md", "standard/06_limitations.md"],
        "appendix": ["standard/07_appendix_a.md", "standard/08_appendices.md"],
        "after": ["standard/09_references.md"],
        "toc": True,
        "sectionbreak": True,
    },
    {
        "name": "MRFS-Validation-Report",
        "title": "MRFS Validation Report",
        "subtitle": "Behaviour of the reference implementation on synthetic data",
        "short": "MRFS Validation Report",
        "front": "validation/00_front.md",
        "body": ["validation/validation.md"],
        "appendix": [],
        "after": [],
        "toc": True,
    },
]


def fill(text: str, doc: dict) -> str:
    return (text.replace("{{TITLE}}", doc["title"]).replace("{{SUBTITLE}}", doc["subtitle"])
            .replace("{{VERSION}}", VERSION).replace("{{STATUS}}", STATUS).replace("{{DATE}}", DATE))


def pandoc_fragment(md: Path, doc: dict, tmp: Path, numbered: bool) -> str:
    src = tmp / (md.stem + ".filled.md")
    src.write_text(fill(md.read_text(encoding="utf-8"), doc), encoding="utf-8")
    args = ["pandoc", str(src), "-f", "markdown", "-t", "latex", "--lua-filter", str(STYLE / "mrfs-filter.lua")]
    if numbered:
        args.append("--number-sections")
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def build(doc: dict, tmp: Path) -> Path:
    meta = (f"\\newcommand{{\\mrfsshorttitle}}{{{doc['short']}}}\n"
            f"\\newcommand{{\\mrfsversion}}{{Version {VERSION}}}\n"
            f"\\newcommand{{\\mrfsstatus}}{{{STATUS}}}\n")
    style = (STYLE / "mrfs-style.tex").read_text(encoding="utf-8")
    if doc.get("sectionbreak"):
        # each chapter of the Standard starts on a new page
        style += "\n\\newcommand{\\sectionbreak}{\\clearpage}\n"
    header = tmp / "header.tex"
    header.write_text(meta + style, encoding="utf-8")

    before = fill((STYLE / "cover.tex").read_text(encoding="utf-8"), doc)
    if doc["front"]:
        before += "\n\\mrfsfrontmatter\n" + pandoc_fragment(HERE / doc["front"], doc, tmp, False) + "\n\\clearpage\n"
    (tmp / "before.tex").write_text(before, encoding="utf-8")

    # body, appendices and references are converted in one pass so internal links resolve
    parts = []
    for f in doc["body"]:
        parts.append(fill((HERE / f).read_text(encoding="utf-8"), doc))
    if doc["appendix"]:
        parts.append("```{=latex}\n\\clearpage\n\\appendix\n```")
        for f in doc["appendix"]:
            parts.append(fill((HERE / f).read_text(encoding="utf-8"), doc))
    for f in doc["after"]:
        parts.append("```{=latex}\n\\clearpage\n```")
        parts.append(fill((HERE / f).read_text(encoding="utf-8"), doc))
    combined = tmp / "body.md"
    combined.write_text("\n\n".join(parts) + "\n", encoding="utf-8")

    tex = tmp / f"{doc['name']}.tex"
    args = ["pandoc", str(combined), "-f", "markdown", "-o", str(tex),
            "--template", str(STYLE / "mrfs-template.tex"),
            "--lua-filter", str(STYLE / "mrfs-filter.lua"),
            "-H", str(header), "-B", str(tmp / "before.tex"),
            "-M", f"pdftitle={doc['title']}", "-M", "pdfsubject=Marketplace Ranking Fairness Standard",
            "--number-sections"]
    if doc["toc"]:
        args += ["--toc", "--toc-depth=2"]
    subprocess.run(args, check=True)
    if doc["front"]:
        t = tex.read_text(encoding="utf-8")
        # arabic numbering restarts at the first chapter
        marker = "\\tableofcontents}\n\\clearpage\n" if doc["toc"] else None
        if marker and marker in t:
            t = t.replace(marker, marker + "\\mrfsmainmatter\n", 1)
        tex.write_text(t, encoding="utf-8")
    subprocess.run([sys.executable, str(STYLE / "postprocess.py"), str(tex)], check=True)
    for _ in range(3):
        r = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                           cwd=tmp, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-4000:])
            raise SystemExit(f"xelatex failed for {doc['name']}")
    log = (tmp / f"{doc['name']}.log").read_text(encoding="utf-8", errors="replace")
    for line in log.splitlines():
        if line.startswith(("Overfull", "LaTeX Warning: Reference", "LaTeX Warning: There were undefined")):
            print(f"  [{doc['name']}] {line}")
    out = OUT / f"{doc['name']}.pdf"
    shutil.copy(tmp / f"{doc['name']}.pdf", out)
    return out


def main():
    only = set(sys.argv[1:])
    for doc in DOCS:
        if only and doc["name"] not in only:
            continue
        with tempfile.TemporaryDirectory() as d:
            d = KEEP or d
            print("built", build(doc, Path(d)))


if __name__ == "__main__":
    main()
