"""Разрешённый post-hoc анализ Random Forest."""
def analyze(model,features):
 pairs=sorted(zip(features,model.feature_importances_),key=lambda x:x[1],reverse=True)
 return {'importance_method':'impurity','most_used_features':[{'feature':f,'importance':float(v)} for f,v in pairs],'used_for_tuning':False}
