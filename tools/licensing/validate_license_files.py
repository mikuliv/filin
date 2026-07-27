"""Validate official license texts and required root notices."""
from __future__ import annotations
from .common import ROOT, finish, parser, sha256

EXPECTED={"LICENSE":"3f3d9e0024b1921b067d6f7f88deb4a60cbe7a78e76c64e3f1d7fc3b779b9d04","LICENSES/MPL-2.0.txt":"3f3d9e0024b1921b067d6f7f88deb4a60cbe7a78e76c64e3f1d7fc3b779b9d04","LICENSES/CC-BY-4.0.txt":"9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411","DCO.txt":"c33e3ea46847ac93235d1a6a7f7f58502514f75c1a374759d29015d681dd4129"}
REQUIRED=[*EXPECTED,"COPYRIGHT.md","AUTHORS.md","NOTICE","THIRD_PARTY_NOTICES.md","TRADEMARKS.md","REUSE.toml","CONTRIBUTING.md","DCO.txt"]
def validate(root=ROOT):
 errors=[]
 for path in REQUIRED:
  if not (root/path).is_file():errors.append({"code":"missing_license_or_notice_file","path":path})
 for path,expected in EXPECTED.items():
  if (root/path).is_file() and sha256(root/path)!=expected:errors.append({"code":"official_license_text_modified","path":path})
 if (root/"COPYRIGHT.md").is_file() and "Руслан Покатилов" not in (root/"COPYRIGHT.md").read_text(encoding="utf-8"):errors.append({"code":"copyright_holder_missing"})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_license_files",e,{"required_count":len(REQUIRED)},a.strict)
if __name__=="__main__":raise SystemExit(main())
