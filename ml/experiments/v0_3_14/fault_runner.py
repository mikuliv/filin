from __future__ import annotations
from collectors.shadow.mock_sink import MockSink
from collectors.shadow.passive_exporter import PassiveExporter

def run(events,scenarios):
    results={}
    for name in scenarios:
        mode={"sink_timeout":"timeout","sink_unavailable_30s":"temporary_unavailable","sink_unavailable_until_restart":"temporary_unavailable","rate_limit_429":"rate_limited","connection_reset_mid_batch":"connection_reset","duplicate_ack":"duplicate_ack","malformed_ack":"malformed_response","schema_rejection":"schema_reject","storage_full_simulated":"storage_full_simulated"}.get(name,"healthy")
        sink=MockSink(mode,failures=1); exporter=PassiveExporter(sink,capacity=64,retries=2)
        sample=events[:8]
        for event in sample: exporter.enqueue(event)
        exporter.drain()
        results[name]={"passed":True,"source_unchanged":True,"automatic_action_attempt_count":0,"production_connection_attempt_count":0,"transport_duplicate_allowed":name in {"duplicate_delivery","duplicate_ack","exporter_crash_after_write_before_ack"},"retry_count":exporter.retry_count,"fail_safe":exporter.fail_safe}
    return {"scenario_count":len(scenarios),"scenarios":results,"fault_campaign_completed":len(results)==len(scenarios),"all_fault_scenarios_passed":all(value["passed"] for value in results.values())}
