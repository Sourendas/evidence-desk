"""CLI: python cli.py "question" [--snippet TEXT ...] [--url URL ...] [--web] [--md out.md] [--json]"""
import argparse
import json

from evidence_desk.agent import EvidenceDesk
from evidence_desk.report import to_markdown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--snippet", action="append", default=[])
    ap.add_argument("--snippet-file", action="append", default=[])
    ap.add_argument("--url", action="append", default=[])
    ap.add_argument("--web", action="store_true", help="also search Wikipedia (keyless)")
    ap.add_argument("--md", help="write markdown report to this path")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    snippets = a.snippet + [open(p, encoding="utf-8").read() for p in a.snippet_file]
    r = EvidenceDesk().run(a.question, snippets, a.url, a.web).to_dict()
    md = to_markdown(r)
    if a.md:
        open(a.md, "w", encoding="utf-8").write(md)
    print(json.dumps(r, indent=2) if a.json else md)


if __name__ == "__main__":
    main()
