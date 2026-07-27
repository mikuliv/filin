"""Validate future-only DCO and contribution provenance rules."""
from __future__ import annotations
from .common import ROOT, finish, parser
def validate(root=ROOT):
 errors=[]
 for path in ("CONTRIBUTING.md","DCO.txt","docs/licensing/contribution-provenance.md"):
  if not (root/path).is_file():errors.append({"code":"contribution_policy_file_missing","path":path})
 if (root/"CONTRIBUTING.md").is_file():
  text=(root/"CONTRIBUTING.md").read_text(encoding="utf-8")
  for token,code in [("Signed-off-by","signed_off_instruction_missing"),("не применяется задним числом","dco_future_only_missing"),("Сторонний код","third_party_contribution_rule_missing"),("Модели","model_contribution_rule_missing"),("PCAP","sensitive_data_rule_missing")]:
   if token not in text:errors.append({"code":code})
 return errors
def main():
 a=parser(__doc__).parse_args();e=validate(a.root);return finish("validate_contribution_policy",e,{},a.strict)
if __name__=="__main__":raise SystemExit(main())

