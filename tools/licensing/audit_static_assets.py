"""Audit tracked images, fonts and web assets without network access."""
from __future__ import annotations

import re

from .common import ASSET_SUFFIXES, ROOT, dump, finish, parser, sha256, tracked

MARKERS = re.compile(rb"(?i)(copyright|license|author|creator|adobe|font family|metadata)")


def audit() -> tuple[list[dict],dict]:
    rows=[]; errors=[]
    for path in tracked():
        suffix=(ROOT/path).suffix.lower()
        if suffix not in ASSET_SUFFIXES and suffix not in {".js",".css"}: continue
        data=(ROOT/path).read_bytes(); markers=sorted(set(x.decode("ascii","ignore").lower() for x in MARKERS.findall(data)))
        minified=suffix in {".js",".css"} and bool(data) and max((len(x) for x in data.splitlines()),default=0)>1000
        external = any(token in data.lower() for token in (b"copyright (c)",b"all rights reserved",b"sourceMappingURL="))
        review=external and not markers
        if review: errors.append({"code":"static_asset_provenance_unknown","path":path})
        rows.append({"path":path,"sha256":sha256(ROOT/path),"asset_type":suffix.lstrip("."),"size":len(data),"embedded_markers":markers,"minified":minified,"distribution_allowed":not review,"review_required":review})
    details={"asset_count":len(rows),"image_count":sum((ROOT/r["path"]).suffix.lower() in ASSET_SUFFIXES for r in rows),"font_count":sum((ROOT/r["path"]).suffix.lower() in {".woff",".woff2",".ttf",".otf"} for r in rows),"review_required_count":len(errors),"assets":rows}
    return errors,details


def main()->int:
    args=parser(__doc__).parse_args(); errors,details=audit(); dump("docs/licensing/static-assets-audit.json",details)
    return finish("audit_static_assets",errors,{k:v for k,v in details.items() if k!="assets"},args.strict)


if __name__ == "__main__": raise SystemExit(main())
