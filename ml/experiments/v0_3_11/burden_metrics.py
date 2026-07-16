"""Burden-aware window и episode metrics."""
from collections import Counter,defaultdict

def calculate(rows:list[dict])->dict:
    counts=Counter(r["primary_state"].split(":",1)[0] for r in rows);attack=[r for r in rows if r.get("true_class")!="benign"]
    episodes=defaultdict(list)
    for r in rows:episodes[(r["run_id"],r["episode_id"])].append(r)
    attack_eps=[v for v in episodes.values() if v[0].get("true_class")!="benign"]
    pending_eps=sum(any(x["primary_state"].startswith("pre_alert_pending:") for x in ep[:next((i for i,x in enumerate(ep) if x.get("alert_emitted")),len(ep))]) for ep in attack_eps)
    unresolved=sum(any(x["primary_state"].startswith("pre_alert_pending:") for x in ep) and not any(x.get("alert_emitted") for x in ep) for ep in attack_eps)
    after=[]
    for ep in attack_eps:
        pos=next((i for i,x in enumerate(ep) if x.get("alert_emitted")),None)
        if pos is not None:after.extend(ep[pos+1:])
    suppressed=sum(bool(r.get("duplicate_alert_suppressed")) for r in rows)
    false_supp=sum(bool(r.get("duplicate_alert_suppressed")) and not r["primary_state"].startswith("post_alert_continuation:") for r in rows)
    reviews=counts["review_required"]
    return {"pre_alert_pending_count":counts["pre_alert_pending"],"pre_alert_pending_attack_window_rate":sum(r["primary_state"].startswith("pre_alert_pending:") for r in attack)/max(len(attack),1),
      "pre_alert_pending_episode_rate":pending_eps/max(len(attack_eps),1),"unresolved_pending_episode_count":unresolved,"unresolved_pending_episode_rate":unresolved/max(len(attack_eps),1),
      "post_alert_continuation_count":counts["post_alert_continuation"],"post_alert_continuation_rate":counts["post_alert_continuation"]/max(len(after),1),
      "duplicate_alert_suppressed_count":suppressed,"duplicate_suppression_precision":(suppressed-false_supp)/max(suppressed,1),"duplicate_false_suppression_count":false_supp,
      "review_window_count":reviews,"review_window_rate":reviews/max(len(rows),1),"attack_review_window_rate":sum(r["primary_state"].startswith("review_required:") for r in attack)/max(len(attack),1),
      "legacy_pending_control_count":counts["pre_alert_pending"]+counts["post_alert_continuation"],"legacy_pending_affects_pass_fail":False}
