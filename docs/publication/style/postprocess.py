"""Post-processes pandoc's LaTeX: shaded table header rows and version separators."""
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read()
# shade every header row: the line(s) between \toprule and \midrule inside longtables
src = re.sub(r"(\\toprule\\noalign\{\}\n)(?!\\rowcolor|\\endfirsthead)", r"\1\\rowcolor{tblhead}", src)
# a row whose first cell is RULE becomes a thin separator (used for the v1 -> v2 change)
src = re.sub(r"^RULE(?:\s*&\s*)*\\\\\s*$", r"\\versionrule", src, flags=re.M)


def _pad(m):
    """Keep the outer \\tabcolsep so the shaded header row ends with the rules."""
    spec = m.group(1)
    n = spec.count("\\real{")
    if n:
        spec = spec.replace(f"- {2 * (n - 1)}\\tabcolsep)", f"- {2 * n}\\tabcolsep)")
    spec = re.sub(r"^@\{\}", "", spec)
    spec = re.sub(r"@\{\}$", "", spec)
    return "\\begin{longtable}[]{" + spec + "}"


src = re.sub(r"\\begin\{longtable\}\[\]\{(@\{\}.*?@\{\})\}(?=\n)", _pad, src, flags=re.S)
# keep a table's caption, header and first rows together, and keep a heading with what
# follows it; a heading directly followed by a table moves with the table
src = src.replace("\\begin{longtable}[]", "\\mrfskeep{9\\baselineskip}\n\\begin{longtable}[]")
src = re.sub(r"\\begin\{mrfscompact\}\s*\\mrfskeep\{9\\baselineskip\}\n", r"\\mrfskeep{9\\baselineskip}\n\\begin{mrfscompact}\n", src)
HEAD = r"\\hypertarget\{[^}]*\}\{%\n\\(?:sub)*section\*?\{(?:[^{}]|\{[^{}]*\})*\}\\label\{[^}]*\}\}\n*"
src = re.sub("(" + HEAD + r")\\mrfskeep\{9\\baselineskip\}\n", r"\\mrfskeep{12\\baselineskip}\n\1", src)
src = re.sub(r"(?m)^(?<!\\mrfskeep\{12\\baselineskip\}\n)(" + HEAD + ")", r"\\mrfskeep{6\\baselineskip}\n\1", src)
# a little padding above header cells so multi-line headers clear the top rule
src = re.sub(r"(\\begin\{minipage\}\[b\]\{\\linewidth\}\\(?:raggedright|raggedleft|centering))\n",
             r"\1\\vspace{2pt}\n", src)
open(sys.argv[1], "w", encoding="utf-8").write(src)
