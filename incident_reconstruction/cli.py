"""Командный интерфейс построения и проверки."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import build_bundle, build_incident_card, write_json
from .canonical import canonical_bytes
from .validation import ValidationFailure, validate_bundle, validate_card
from .temporal import build_temporal_bundle, build_temporal_reconstruction, explain_relation
from .temporal_validation import validate_temporal_bundle, validate_temporal_reconstruction
from .hypothesis import build_hypothesis_analysis, build_hypothesis_bundle, load_catalog, validate_analysis


def _read(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверяемая реконструкция инцидента v0.4.0")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build-card", "build-bundle"):
        item = sub.add_parser(name); item.add_argument("--events", required=True); item.add_argument("--run-id", required=True); item.add_argument("--output", required=True); item.add_argument("--incomplete-evidence", action="store_true")
    item = sub.add_parser("validate-card"); item.add_argument("--card", required=True); item.add_argument("--events", required=True)
    item = sub.add_parser("validate-bundle"); item.add_argument("--bundle", required=True)
    for name in ("build-temporal", "build-graph", "build-temporal-bundle"):
        item=sub.add_parser(name); item.add_argument("--bundle",required=True); item.add_argument("--output",required=True)
    item=sub.add_parser("validate-temporal"); item.add_argument("--temporal",required=True); item.add_argument("--bundle",required=True)
    item=sub.add_parser("validate-graph"); item.add_argument("--temporal",required=True); item.add_argument("--bundle",required=True)
    item=sub.add_parser("verify-temporal-bundle"); item.add_argument("--bundle",required=True)
    item=sub.add_parser("explain-relation"); item.add_argument("--temporal",required=True); item.add_argument("--relation-id",required=True)
    item=sub.add_parser("compare-builds"); item.add_argument("--left",required=True); item.add_argument("--right",required=True)
    for name in ("build-hypotheses","build-hypothesis-bundle"):
        item=sub.add_parser(name);item.add_argument("--bundle",required=True);item.add_argument("--output",required=True)
    item=sub.add_parser("validate-hypotheses");item.add_argument("--analysis",required=True)
    for name in ("explain-hypothesis","explain-comparison"):
        item=sub.add_parser(name);item.add_argument("--analysis",required=True);item.add_argument("--id",required=True)
    item=sub.add_parser("list-analyst-questions");item.add_argument("--analysis",required=True)
    item=sub.add_parser("verify-hypothesis-bundle");item.add_argument("--bundle",required=True)
    item=sub.add_parser("compare-hypothesis-builds");item.add_argument("--left",required=True);item.add_argument("--right",required=True)
    sub.add_parser("validate-rule-catalog")
    args = parser.parse_args(argv)
    try:
        if args.command == "build-card": result = build_incident_card(_read(args.events), args.run_id, incomplete_evidence=args.incomplete_evidence); write_json(Path(args.output), result)
        elif args.command == "build-bundle": result = build_bundle(_read(args.events), args.run_id, incomplete_evidence=args.incomplete_evidence); write_json(Path(args.output), result)
        elif args.command == "validate-card": result = validate_card(_read(args.card), _read(args.events))
        elif args.command == "validate-bundle": result = validate_bundle(_read(args.bundle))
        elif args.command in {"build-temporal","build-graph"}:
            result=build_temporal_reconstruction(_read(args.bundle)); write_json(Path(args.output),result["reconstruction_graph"] if args.command=="build-graph" else result)
        elif args.command == "build-temporal-bundle": result=build_temporal_bundle(_read(args.bundle));write_json(Path(args.output),result)
        elif args.command in {"validate-temporal","validate-graph"}: result=validate_temporal_reconstruction(_read(args.temporal),_read(args.bundle))
        elif args.command == "verify-temporal-bundle": result=validate_temporal_bundle(_read(args.bundle))
        elif args.command == "explain-relation": result=explain_relation(_read(args.temporal),args.relation_id)
        elif args.command == "build-hypotheses":result=build_hypothesis_analysis(_read(args.bundle));write_json(Path(args.output),result)
        elif args.command == "build-hypothesis-bundle":result=build_hypothesis_bundle(_read(args.bundle));write_json(Path(args.output),result)
        elif args.command == "validate-hypotheses":result=validate_analysis(_read(args.analysis))
        elif args.command in {"explain-hypothesis","explain-comparison"}:
            analysis=_read(args.analysis);key="hypotheses" if args.command=="explain-hypothesis" else "comparisons";idkey="hypothesis_id" if key=="hypotheses" else "comparison_id";result=next(x for x in analysis[key] if x[idkey]==args.id)
        elif args.command == "list-analyst-questions":result=_read(args.analysis)["analyst_questions"]
        elif args.command == "verify-hypothesis-bundle":result=validate_analysis(_read(args.bundle)["hypothesis_analysis"])
        elif args.command == "validate-rule-catalog":catalog,sha=load_catalog();result={"valid":catalog["frozen"],"rule_count":catalog["rule_count"],"sha256":sha}
        else:
            left,right=_read(args.left),_read(args.right);result={"equal":canonical_bytes(left)==canonical_bytes(right),"left_sha256":__import__('hashlib').sha256(canonical_bytes(left)).hexdigest(),"right_sha256":__import__('hashlib').sha256(canonical_bytes(right)).hexdigest()}
        print(canonical_bytes({"valid": True, "command": args.command, "result": result}).decode("utf-8")); return 0
    except (ValidationFailure, OSError, json.JSONDecodeError) as error:
        code = error.code if isinstance(error, ValidationFailure) else type(error).__name__
        print(canonical_bytes({"valid": False, "command": args.command, "error_code": code, "detail": str(error)}).decode("utf-8")); return 1


if __name__ == "__main__":
    raise SystemExit(main())
