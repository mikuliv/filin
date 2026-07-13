"""Фиксированные исторические опорные значения v0.3.4/v0.3.5."""
V034={'macro_f1':0.9465240641711229,'balanced_accuracy':0.9913194444444443,'benign_recall':0.9479166666666666,'false_positive_rate':0.052083333333333336,'hard_negative_benign_recall':1.0,'attack_macro_recall':1.0,'collapsed_attack_precision':0.8571428571428571,'collapsed_attack_recall':1.0}
V035={'macro_f1':1.0,'balanced_accuracy':1.0,'benign_recall':1.0,'false_positive_rate':0.0,'hard_negative_benign_recall':1.0,'attack_macro_recall':1.0,'collapsed_attack_precision':1.0,'collapsed_attack_recall':1.0}
def compare(current):
 return {'v0_3_4':V034,'v0_3_5':V035,'vs_v0_3_4':{k:current[k]-v for k,v in V034.items()},'vs_v0_3_5':{k:current[k]-v for k,v in V035.items()},'used_for_candidate_tuning':False}
