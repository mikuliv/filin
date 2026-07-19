from __future__ import annotations
import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_recall_fscore_support, f1_score, confusion_matrix, log_loss, brier_score_loss
from .common import CLASSES, ATTACK_CLASSES

def expected_calibration_error(y, probabilities, bins=10):
    y=np.asarray(y); p=np.asarray(probabilities); pred=p.argmax(1); truth=np.array([CLASSES.index(x) for x in y]); conf=p.max(1); total=0.
    for low in np.linspace(0,1,bins,endpoint=False):
        mask=(conf>=low)&(conf<(low+1/bins) if low+1/bins<1 else conf<=1)
        if mask.any(): total+=mask.mean()*abs((pred[mask]==truth[mask]).mean()-conf[mask].mean())
    return float(total)

def evaluate(labels, records):
    labels=np.asarray(["beacon" if x=="beacon_simulation" else str(x) for x in labels]); pred=np.asarray([x["top_class"] for x in records]); probs=np.asarray([[x["joint_class_probabilities"][c] for c in CLASSES] for x in records])
    precision,recall,f1,support=precision_recall_fscore_support(labels,pred,labels=CLASSES,zero_division=0)
    per={c:{"precision":float(precision[i]),"recall":float(recall[i]),"f1":float(f1[i]),"support":int(support[i])} for i,c in enumerate(CLASSES)}
    benign=labels=="benign"; attack=~benign; predicted_attack=pred!="benign"
    sets=[set(x["conformal_set"]) for x in records]; covered=np.array([y in s for y,s in zip(labels,sets)]); wrong_only=np.array([bool(s) and y not in s for y,s in zip(labels,sets)])
    binary=attack.astype(int); gate=1-probs[:,0]
    onehot=np.eye(len(CLASSES))[[CLASSES.index(x) for x in labels]]
    result={"row_count":len(labels),"accuracy":float(accuracy_score(labels,pred)),"balanced_accuracy":float(balanced_accuracy_score(labels,pred)),"macro_precision":float(np.mean(precision)),"macro_recall":float(np.mean(recall)),"macro_f1":float(f1_score(labels,pred,labels=CLASSES,average="macro",zero_division=0)),"weighted_f1":float(f1_score(labels,pred,average="weighted",zero_division=0)),"benign_precision":per["benign"]["precision"],"benign_recall":per["benign"]["recall"],"benign_f1":per["benign"]["f1"],"FPR":float(predicted_attack[benign].mean()) if benign.any() else 0.,"attack_macro_precision":float(np.mean([per[c]["precision"] for c in ATTACK_CLASSES])),"attack_macro_recall":float(np.mean([per[c]["recall"] for c in ATTACK_CLASSES])),"attack_macro_f1":float(np.mean([per[c]["f1"] for c in ATTACK_CLASSES])),"per_class":per,"confusion_matrix":confusion_matrix(labels,pred,labels=CLASSES).tolist(),"zero_recall_classes":[c for c in ATTACK_CLASSES if per[c]["support"] and per[c]["recall"]==0],"candidate_evidence_recall":float((pred[attack]==labels[attack]).mean()) if attack.any() else 0.,"strong_evidence_precision":float(np.mean([r["top_class"]==y for r,y in zip(records,labels) if r["strong_evidence"]])) if any(r["strong_evidence"] for r in records) else 1.0}
    result["calibration"]={"gate_log_loss":float(log_loss(binary,np.column_stack([1-gate,gate]),labels=[0,1])),"gate_brier":float(brier_score_loss(binary,gate)),"gate_ece":expected_calibration_error(np.where(binary==1,"port_scan","benign"),np.column_stack([1-gate,gate, np.zeros((len(gate),4))])),"joint_log_loss":float(log_loss(labels,probs,labels=CLASSES)),"joint_brier":float(np.mean((probs-onehot)**2)),"joint_ece":expected_calibration_error(labels,probs),"class_coverage":sorted(set(labels))}
    result["conformal"]={"empirical_coverage_overall":float(covered.mean()),"coverage_per_class":{c:float(covered[labels==c].mean()) if (labels==c).any() else None for c in CLASSES},"average_set_size":float(np.mean([len(s) for s in sets])),"median_set_size":float(np.median([len(s) for s in sets])),"singleton_rate":float(np.mean([len(s)==1 for s in sets])),"multi_class_rate":float(np.mean([len(s)>1 for s in sets])),"empty_set_rate":float(np.mean([not s for s in sets])),"wrong_only_rate":float(wrong_only.mean()),"true_attack_class_included_rate":float(covered[attack].mean()) if attack.any() else None,"benign_included_rate":float(covered[benign].mean()) if benign.any() else None}
    return result

