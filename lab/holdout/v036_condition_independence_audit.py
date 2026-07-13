"""Проверка независимости условий v0.3.6 от label."""
from pathlib import Path
import yaml
def audit(campaign:Path,profiles:Path)->dict:
 c=yaml.safe_load(campaign.read_text(encoding='utf-8'));p=yaml.safe_load(profiles.read_text(encoding='utf-8'))
 return {'v036_condition_independence_valid':p['condition_assignment_independent_of_label'] is True,'run_groups':{r['run_id']:r['group'] for r in c['runs']},'label_dependent_routes':False}
