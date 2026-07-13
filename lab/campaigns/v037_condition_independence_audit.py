"""Forensic v0.3.7 condition audit without asserted success constants."""


def audit(campaign):
    records = campaign.get("condition_application_records") or []
    required = {"run_id", "environment_profile_id", "application_evidence", "rollback_evidence"}
    complete = bool(records) and all(required <= set(record) for record in records)
    verified = complete and all(
        record["application_evidence"].get("status") == "passed"
        and record["rollback_evidence"].get("status") == "passed"
        for record in records
    )
    status = "passed" if verified else ("failed" if records else "not_executed")
    return {
        "status": status,
        "reason": None if verified else ("condition_evidence_invalid" if records else "condition_application_evidence_unavailable"),
        "v037_condition_independence_valid": verified,
        "application_records_complete": complete,
        "condition_application_verified": verified,
        "record_count": len(records),
    }
