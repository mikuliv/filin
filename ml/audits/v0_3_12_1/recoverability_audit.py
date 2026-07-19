def classify(inventory: dict) -> dict:
    if inventory["frozen_51_feature_table_found"]: status="frozen_core_evaluable"
    elif inventory["categories"]["pcap"] or inventory["categories"]["zeek_logs"]: status="rebuildable_but_not_frozen"
    elif inventory["categories"]["raw_feature_tables"]: status="rebuildable_but_not_frozen"
    else: status="insufficient_sources"
    return {"stage":inventory["stage"],"classification":status,"scientific_regression_evaluable":status in ("frozen_core_evaluable","frozen_window_evaluable"),"v0312_compatibility_changed":False}

