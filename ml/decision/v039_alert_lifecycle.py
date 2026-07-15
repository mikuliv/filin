"""Episode-first lifecycle с hysteresis без доступа к episode metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from v039_signed_evidence import SignedClassEvidence


@dataclass
class _State:
    state: str = "observing"
    active_class: str | None = None
    pending: list[str] = field(default_factory=list)
    active_age: int = 0
    benign_streak: int = 0
    idle_windows: int = 0
    last_timestamp: datetime | None = None
    evidence: SignedClassEvidence | None = None


class AlertLifecycle:
    def __init__(self, *, decay=.7, activation_threshold=1.2, weak_repeat_policy="consistent_2_of_3",
                 active_minimum_hold_windows=2, state_ttl_windows=3, inactivity_seconds=180):
        self.parameters=locals().copy(); self.parameters.pop("self")
        self.states={}; self.decay=decay; self.activation_threshold=activation_threshold
        self.repeat_count=2; self.repeat_depth=3 if weak_repeat_policy.endswith("3") else 4
        self.hold=active_minimum_hold_windows; self.ttl=state_ttl_windows; self.inactivity_seconds=inactivity_seconds

    def _new(self):
        return _State(evidence=SignedClassEvidence(self.decay,self.activation_threshold))

    def reset_run(self): self.states.clear()

    def update(self, record: dict) -> dict:
        if "episode_id" in record:
            raise ValueError("Lifecycle не принимает episode_id")
        key=record["asset_state_key"]; now=record["timestamp"]
        if isinstance(now,str): now=datetime.fromisoformat(now.replace("Z","+00:00"))
        state=self.states.setdefault(key,self._new())
        if state.last_timestamp and (now-state.last_timestamp).total_seconds()>self.inactivity_seconds:
            state=self.states[key]=self._new()
        state.last_timestamp=now; before=state.state; scores=state.evidence.update(record)
        attack=record["top_class"] if record["top_class"] != "benign" else None
        if state.active_class:
            state.active_age += 1
            if record["strong_benign_evidence"]: state.benign_streak += 1
            else: state.benign_streak=0
            if attack and attack != state.active_class and record["strong_attack_evidence"]:
                state.active_class=attack; state.state=f"active:{attack}"; state.active_age=0
            elif state.benign_streak>=2 and state.active_age>=self.hold:
                state.state=f"cooldown:{state.active_class}"; state.active_class=None; state.pending.clear()
            else: state.state=f"active:{state.active_class}"
        elif record["strong_attack_evidence"]:
            state.active_class=attack; state.state=f"active:{attack}"; state.active_age=0; state.pending.clear()
        elif record["strong_benign_evidence"]:
            state.pending.clear(); state.state="observing"
        elif record["weak_attack_evidence"]:
            state.idle_windows=0
            state.pending=(state.pending+[attack])[-self.repeat_depth:]
            confirmed=state.pending.count(attack)>=self.repeat_count or scores[attack]>=self.activation_threshold
            if confirmed: state.active_class=attack; state.state=f"active:{attack}"; state.active_age=0; state.pending.clear()
            else: state.state=f"pending:{attack}"
        elif record["novel_evidence"]: state.state="review:novel"; state.pending.clear(); state.idle_windows=0
        elif record["ambiguous_evidence"]: state.state="review:ambiguous"
        elif state.pending:
            state.idle_windows+=1
            if state.idle_windows>=self.ttl:state.pending.clear();state.state="observing";state.idle_windows=0
            else:state.state="review:weak"
        else: state.state="observing"
        return {"state_before":before,"state_after":state.state,"final_decision":state.state,
            "active_alert_class":state.active_class,"pending_class":state.pending[-1] if state.pending else None,
            "signed_scores":scores}
