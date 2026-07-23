from __future__ import annotations

import argparse
import json

import ml.experiments.v0_3_17.run_campaign as campaign


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--rate", type=int, default=100)
    args = parser.parse_args()
    if not 60 <= args.seconds <= 600 or not 20 <= args.rate <= 100:
        parser.error("smoke bounds are 60..600 seconds and 20..100 events/s")
    frozen = campaign.protocol()
    official_run = frozen["campaign"]["runs"][1]
    sessions = [
        item for item in frozen["campaign"]["sessions"]
        if item["run"] == official_run["run_id"]
    ]
    run_spec = {
        **official_run,
        "run_id": "local_rehearsal_high_load_smoke_r8",
        "duration_seconds": args.seconds,
        "minimum_continuous_seconds": args.seconds,
        "seed": 34901,
        "certificate_session_id": "cert-session-v0317-r8-smoke",
        "instance_namespace": "v0317-r8-smoke",
        "evidence_root": "smoke-r8",
    }

    def smoke_control(value, run_index):
        return {
            "control_id": "ctl_v0317_r8_high_load_smoke",
            "run_id": value["run_id"],
            "duration_seconds": args.seconds,
            "seed": value["seed"],
            "source_instance_id": f"traffic-{value['instance_namespace']}",
            "phases": [{"start_second": 0, "end_second": args.seconds, "phase": "burst", "rate": args.rate}],
        }

    campaign.source_control = smoke_control
    result = campaign.execute_run(2, run_spec, sessions)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
