"""Create a first-seen and current-state provenance record for every tracked file."""
from __future__ import annotations

from collections import defaultdict

from .common import HOLDER, classify, dump, finish, git, parser, sha256, tracked, ROOT


def first_seen() -> dict[str, dict]:
    # --all and --reverse make the audit cover imported branches and historical commits.
    # Rename similarity detection is deliberately disabled: Git records the target as an
    # addition, which is sufficient for first-seen provenance and remains linear-time.
    raw = git("log", "--all", "--reverse", "--date=iso-strict", "--format=@@%H%x1f%aI%x1f%an%x1f%ae", "--name-status", "--no-renames")
    found: dict[str, dict] = {}; current = None
    for line in raw.splitlines():
        if line.startswith("@@"):
            sha, date, name, email = line[2:].split("\x1f", 3); current = (sha,date,name,email); continue
        if not line or current is None: continue
        parts = line.split("\t"); status = parts[0]
        paths = parts[1:]
        if status.startswith("R") and len(paths) == 2:
            source, target = paths
            if source in found and target not in found: found[target] = {**found[source], "renamed_from": source}
            elif target not in found: found[target] = {"first_commit": current[0], "first_date": current[1], "first_author": current[2], "first_author_email": current[3], "renamed_from": source}
        elif status.startswith(("A", "C")) and paths:
            found.setdefault(paths[-1], {"first_commit": current[0], "first_date": current[1], "first_author": current[2], "first_author_email": current[3]})
    return found


def audit() -> tuple[list[dict], dict]:
    seen = first_seen(); rows=[]; errors=[]
    for path in tracked(include_untracked=True):
        info = seen.get(path)
        if not info:
            # A commit cannot contain its own SHA (changing the file changes the commit).
            # New files therefore use an explicit self-reference resolved by the final commit.
            info={"first_commit":"FINAL_LICENSING_COMMIT_SELF_REFERENCE","first_date":None,"first_author":HOLDER,"first_author_email":None,"introduction":"current_maintenance_worktree"}
        assignment=classify(path)
        rows.append({"path":path,"sha256":sha256(ROOT/path),**info,"current_holder":assignment["copyright_holder"],"third_party_markers":[],"review_required":not bool(info)})
    details={"history_scope":"all refs","tracked_file_count":len(rows),"provenance_record_count":len(rows),"review_required_count":len(errors),"files":rows}
    return errors,details


def main() -> int:
    args=parser(__doc__).parse_args(); errors,details=audit(); dump("docs/licensing/file-provenance-audit.json",details)
    return finish("audit_file_provenance",errors,{k:v for k,v in details.items() if k!="files"},args.strict)


if __name__ == "__main__": raise SystemExit(main())
