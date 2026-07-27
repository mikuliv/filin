"""Audit author, committer and Co-authored-by identities across every Git ref."""
from __future__ import annotations

import json
import re
from collections import Counter

from .common import HOLDER, dump, finish, git, parser

KNOWN_AUTHORS = {
    ("mikuliv", "ruslan.pockatilov@gmail.com"): HOLDER,
    ("mikuliv", "64185192+mikuliv@users.noreply.github.com"): HOLDER,
}
KNOWN_COMMITTERS = {**KNOWN_AUTHORS, ("GitHub", "noreply@github.com"): "GitHub web automation"}
TRAILER = re.compile(r"(?im)^Co-authored-by:\s*(.+?)\s*<([^>]+)>\s*$")


def audit() -> tuple[list[dict], dict]:
    raw = git("log", "--all", "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e")
    authors, committers, coauthors = Counter(), Counter(), Counter()
    first = last = None
    commits = []
    for item in raw.split("\x1e"):
        fields = item.strip("\n").split("\x1f", 5)
        if len(fields) != 6:
            continue
        sha, an, ae, cn, ce, body = fields
        commits.append(sha); authors[(an, ae)] += 1; committers[(cn, ce)] += 1
        for name, email in TRAILER.findall(body): coauthors[(name.strip(), email.strip())] += 1
    chronological = git("log", "--all", "--reverse", "--format=%H").splitlines()
    if chronological: first, last = chronological[0], chronological[-1]
    errors = []
    for identity in authors:
        if identity not in KNOWN_AUTHORS: errors.append({"code": "unknown_author", "identity": list(identity)})
    for identity in committers:
        if identity not in KNOWN_COMMITTERS: errors.append({"code": "unknown_committer", "identity": list(identity)})
    for identity in coauthors:
        if identity not in KNOWN_AUTHORS: errors.append({"code": "unknown_coauthor", "identity": list(identity)})
    details = {
        "scope": "git log --all", "commit_count": len(commits), "unique_commit_count": len(set(commits)),
        "first_commit": first, "last_commit": last,
        "authors": [{"name": n, "email": e, "count": c, "mapped_to": KNOWN_AUTHORS.get((n, e)), "review_required": (n, e) not in KNOWN_AUTHORS} for (n,e),c in sorted(authors.items())],
        "committers": [{"name": n, "email": e, "count": c, "mapped_to": KNOWN_COMMITTERS.get((n, e)), "authorship": (n,e) in KNOWN_AUTHORS, "review_required": (n,e) not in KNOWN_COMMITTERS} for (n,e),c in sorted(committers.items())],
        "coauthors": [{"name": n, "email": e, "count": c, "mapped_to": KNOWN_AUTHORS.get((n,e)), "review_required": (n,e) not in KNOWN_AUTHORS} for (n,e),c in sorted(coauthors.items())],
        "review_required": bool(errors),
    }
    return errors, details


def main() -> int:
    args = parser(__doc__).parse_args(); errors, details = audit()
    dump("docs/licensing/git-authorship.json", details)
    dump("docs/licensing/git-authorship-audit.json", details)
    return finish("audit_git_authors", errors, details, args.strict)


if __name__ == "__main__": raise SystemExit(main())

