from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from incident_reconstruction.builder import write_json
from incident_reconstruction.hypothesis import build_hypothesis_bundle,load_catalog,validate_analysis
from incident_reconstruction.hypothesis_scenarios import run_campaign,source
def main():
 out=ROOT/"ml/reports/v0_4_2";out.mkdir(parents=True,exist_ok=True);campaign=run_campaign();bundle=build_hypothesis_bundle(source());a=bundle["hypothesis_analysis"];r=validate_analysis(a);catalog,sha=load_catalog()
 for name,value in [("synthetic_campaign_result.json",campaign),("representative_hypothesis_analysis.json",a),("representative_hypothesis_set.json",a["hypothesis_sets"]),("representative_comparisons.json",a["comparisons"]),("representative_explanations.json",a["explanations"]),("representative_analyst_questions.json",a["analyst_questions"]),("representative_hypothesis_bundle.json",bundle),("official_run_journal.json",{"schema_version":"v0_4_2_journal_v1","run_id":"v042-r1-official-52001","protocol_revision":1,"rule_catalog_sha256":sha,"positive_passed":campaign["positive_scenario_passed_count"],"negative_rejected":campaign["negative_scenario_rejected_count"],"semantic_sha256":bundle["manifest"]["semantic_result_sha256"],"forbidden_calls":0})]:write_json(out/name,value)
 print(json.dumps({"positive":campaign["positive_scenario_passed_count"],"negative":campaign["negative_scenario_rejected_count"],"rules":catalog["rule_count"],**r,"semantic_sha256":bundle["manifest"]["semantic_result_sha256"]},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
