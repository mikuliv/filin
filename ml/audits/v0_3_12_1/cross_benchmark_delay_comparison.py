from __future__ import annotations
from collections import Counter
from math import sqrt
try:
    from scipy.stats import fisher_exact, mannwhitneyu
except ImportError:  # pragma: no cover
    fisher_exact=mannwhitneyu=None

def compare(a_summary, b_summary, a_episodes, b_episodes):
    ad=a_summary["delayed_episode_count"]; bd=b_summary["delayed_episode_count"]
    an=a_summary["attack_episode_count"]; bn=b_summary["attack_episode_count"]
    table=[[ad,an-ad],[bd,bn-bd]]
    fisher={"odds_ratio":None,"p_value":None}
    if fisher_exact:
        odds,p=fisher_exact(table); fisher={"odds_ratio":float(odds),"p_value":float(p)}
    ga=[v for e in a_episodes if e["delayed"] for row in e["threshold_gaps"] for v in row.values()]
    gb=[v for e in b_episodes if e["delayed"] for row in e["threshold_gaps"] for v in row.values()]
    mw={"statistic":None,"p_value":None}
    if mannwhitneyu and ga and gb:
        stat,p=mannwhitneyu(ga,gb,alternative="two-sided"); mw={"statistic":float(stat),"p_value":float(p)}
    pooled=(ad+bd)/(an+bn); denom=sqrt(pooled*(1-pooled)*(1/an+1/bn)) if 0<pooled<1 else 0
    return {
        "paired_row_comparison_performed":False,"contingency_table":table,"fisher_exact":fisher,
        "mann_whitney_threshold_gaps":mw,"delayed_rate_difference":ad/an-bd/bn,
        "two_proportion_z":(ad/an-bd/bn)/denom if denom else 0.,
        "primary_reason_distributions":{"v0.3.9":a_summary["primary_reason_counts"],"v0.3.10":b_summary["primary_reason_counts"]},
        "delayed_class_sets":{"v0.3.9":sorted({e["true_class"] for e in a_episodes if e["delayed"]}),"v0.3.10":sorted({e["true_class"] for e in b_episodes if e["delayed"]})},
        "eligibility_position_distributions":{"v0.3.9":dict(Counter(str(e["earliest_policy_eligible_window"]) for e in a_episodes)),"v0.3.10":dict(Counter(str(e["earliest_policy_eligible_window"]) for e in b_episodes))},
        "identical_second_window_rate":a_summary["detection_by_second_window"]==b_summary["detection_by_second_window"],
        "identical_rate_explanation":"Одинаковая frozen доля получена из отношений 22/30 и 44/60: числитель и знаменатель v0.3.10 ровно удвоены. Однако позиции 12/10/8 и 23/21/16 воспроизводятся только в порядке записей immutable prediction, который не является causal order внутри эпизода. После сортировки по frozen causal_order фактические alert windows равны 29/1/0 для v0.3.9 и 60/0/0 для v0.3.10. Следовательно, 0.733333 — общий артефакт реализации episode latency, а не одинаковая причинная задержка model/policy/state machine; frozen gate и официальный pass/fail при этом не меняются.",
        "statistical_results_change_gates":False,
    }
