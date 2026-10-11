"""Assembles the curated MRFS release folder from an explicit file list.

Only the files listed in MANIFEST are copied. Document sources and build scripts stay in
the repository and are not part of the release folder.

Usage (from the repository root):
    python tools/make_release.py [--name MRFS-v2.0.0]
Output: dist/<name>/, dist/<name>.zip and dist/<name>/SHA256SUMS.txt
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (source in the repository, path in the release)
MANIFEST = [
    ("docs/MRFS-Overview.pdf", "MRFS-Overview.pdf"),
    ("docs/MRFS-Technical-Standard.pdf", "MRFS-Technical-Standard.pdf"),
    ("docs/MRFS-Validation-Report.pdf", "MRFS-Validation-Report.pdf"),
    ("tools/release_README.md", "README.md"),
    ("CHANGELOG.md", "CHANGELOG.md"),
    ("CITATION.cff", "CITATION.cff"),
    ("LICENSE", "LICENSE"),
    ("docs/LICENSE-CC-BY-4.0.md", "LICENSE-CC-BY-4.0.md"),
    ("docs/References.md", "References.md"),
    ("requirements.txt", "reference-implementation/requirements.txt"),
    ("tools/release_README_reference_implementation.md", "reference-implementation/README.md"),
    ("src/metrics.py", "reference-implementation/metrics.py"),
    ("src/test_metrics.py", "reference-implementation/test_metrics.py"),
    ("src/generate_synthetic_audit.py", "reference-implementation/generate_synthetic_audit.py"),
    ("src/run_validation.py", "reference-implementation/run_validation.py"),
    ("src/run_validation_review.py", "reference-implementation/run_validation_review.py"),
    ("src/generate_sample_audit_report.py", "reference-implementation/generate_sample_audit_report.py"),
    ("src/validation_results", "reference-implementation/validation_results"),
    ("src/sample_audit_report", "reference-implementation/sample_audit_report"),
]

# Optional pre-release term check: one term per line in tools/release_forbidden_terms.txt
# (kept out of version control). The release is refused if any term appears in a text file.
_TERMS = Path(__file__).resolve().parent / "release_forbidden_terms.txt"
FORBIDDEN = tuple(t.strip().lower() for t in _TERMS.read_text(encoding="utf-8").splitlines()
                  if t.strip()) if _TERMS.exists() else ()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="MRFS-v2.0.0")
    args = ap.parse_args()
    out = ROOT / "dist" / args.name
    if out.exists():
        sys.exit(f"{out} exists; move it aside first")
    for src, dst in MANIFEST:
        s, d = ROOT / src, out / dst
        if not s.exists():
            sys.exit(f"missing: {src}")
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        else:
            shutil.copy2(s, d)
    files = sorted(p for p in out.rglob("*") if p.is_file())
    problems = []
    for p in files:
        # CHANGELOG.md keeps the released v1.x history unchanged, so it is not scanned
        if p.suffix in {".md", ".py", ".json", ".cff", ".txt"} and p.name != "CHANGELOG.md":
            low = p.read_text(encoding="utf-8", errors="replace").lower()
            problems += [f"{p.relative_to(out)}: '{w}'" for w in FORBIDDEN if w in low]
    if problems:
        sys.exit("release check failed:\n  " + "\n  ".join(problems))
    with open(out / "SHA256SUMS.txt", "w") as f:
        for p in files:
            f.write(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}\n")
    shutil.make_archive(str(out), "zip", out.parent, out.name)
    print(f"{len(files)} files in {out}; archive {out}.zip")


if __name__ == "__main__":
    main()
