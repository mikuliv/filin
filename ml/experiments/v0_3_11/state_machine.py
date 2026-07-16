"""Причинная burden-aware state machine v0.3.11."""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict, deque

ATTACK_CLASSES=("port_scan","auth_failures","web_probe","low_rate_dos","beacon")

@dataclass(frozen=True)
class Evidence:
    run_id: str; activity_key: str; window_index: int
    top_class: str="benign"; attack_probability: float=0.0; benign_probability: float=1.0
    margin: float=1.0; conformal_set: tuple[str,...]=("benign",)

@dataclass(frozen=True)
class Policy:
    strong_probability: float=.70; strong_margin: float=.10; strong_benign_ceiling: float=.20
    weak_probability: float=.35; weak_margin: float=0.; weak_benign_ceiling: float=.50
    repetition: str="two_consecutive"; pending_ttl: int=2; ambiguity_margin: float=.03
    dedup_ttl: int=3; benign_reset_probability: float=.80; benign_reset_margin: float=.30

@dataclass
class Decision:
    primary_state: str; alert_emitted: bool=False; alert_event_id: str|None=None
    duplicate_alert_suppressed: bool=False; pending_started: bool=False; pending_confirmed: bool=False
    pending_reset: bool=False; pending_expired: bool=False; class_conflict_detected: bool=False
    dedup_key_created: bool=False; dedup_key_expired: bool=False

class BurdenAwareDecisionEngine:
    def __init__(self, policy: Policy=Policy()):
        self.policy=policy;self.pending={};self.history=defaultdict(lambda:deque(maxlen=3));self.alert_class={};self.dedup={};self.events=[]
    def _key(self,e): return (e.run_id,e.activity_key)
    def update(self,e:Evidence)->Decision:
        key=self._key(e); p=self.policy
        expired=[k for k,v in self.dedup.items() if k[0]==e.run_id and e.window_index-v>p.dedup_ttl]
        for k in expired:self.dedup.pop(k,None)
        pending=self.pending.get(key); pending_expired=False
        if pending and e.window_index-pending[1]>=p.pending_ttl:
            self.pending.pop(key,None);pending=None;pending_expired=True
        conformal=set(e.conformal_set); attack=e.top_class in ATTACK_CLASSES
        novel=not conformal; ambiguous=len(conformal)>1 or e.margin<p.ambiguity_margin
        if novel:return Decision("review_required:novel",pending_expired=pending_expired)
        if ambiguous:return Decision("review_required:ambiguous",pending_expired=pending_expired)
        strong=attack and conformal=={e.top_class} and e.attack_probability>=p.strong_probability and e.margin>=p.strong_margin and e.benign_probability<=p.strong_benign_ceiling
        weak=attack and e.top_class in conformal and e.attack_probability>=p.weak_probability and e.margin>=p.weak_margin and e.benign_probability<=p.weak_benign_ceiling
        prior_class=self.alert_class.get(key)
        if prior_class and (strong or weak) and prior_class!=e.top_class:
            return Decision("review_required:class_conflict",class_conflict_detected=True,pending_expired=pending_expired)
        dedup_key=(e.run_id,e.activity_key,e.top_class)
        if prior_class==e.top_class and (strong or weak) and dedup_key in self.dedup:
            return Decision(f"post_alert_continuation:{e.top_class}",duplicate_alert_suppressed=True,pending_expired=pending_expired)
        if strong:
            event=f"{e.run_id}:{e.activity_key}:{e.top_class}:{e.window_index}"
            self.alert_class[key]=e.top_class;self.dedup[dedup_key]=e.window_index;self.pending.pop(key,None);self.events.append(event)
            return Decision(f"alert_emitted:{e.top_class}",True,event,pending_confirmed=bool(pending),dedup_key_created=True,pending_expired=pending_expired)
        if weak:
            hist=self.history[key];hist.append((e.window_index,e.top_class))
            confirmed=(p.repetition=="two_consecutive" and len(hist)>=2 and hist[-2][1]==e.top_class and hist[-2][0]==e.window_index-1) or (p.repetition=="two_of_three" and sum(c==e.top_class for _,c in hist)>=2)
            if confirmed:
                event=f"{e.run_id}:{e.activity_key}:{e.top_class}:{e.window_index}";self.alert_class[key]=e.top_class;self.dedup[dedup_key]=e.window_index;self.pending.pop(key,None);self.events.append(event)
                return Decision(f"alert_emitted:{e.top_class}",True,event,pending_confirmed=True,dedup_key_created=True,pending_expired=pending_expired)
            started=key not in self.pending;self.pending[key]=(e.top_class,e.window_index)
            return Decision(f"pre_alert_pending:{e.top_class}",pending_started=started,pending_expired=pending_expired)
        benign=e.benign_probability>=p.benign_reset_probability and e.margin>=p.benign_reset_margin
        reset=benign and key in self.pending
        if reset:self.pending.pop(key,None);self.history.pop(key,None)
        return Decision("benign",pending_reset=reset,pending_expired=pending_expired)

    def unresolved_keys(self): return set(self.pending)
