import numpy as np
import pandas as pd
import pytest
from satquery_research.phase3b_integrity import pair,transitions
from satquery_research.phase3b_policies import (threshold_action,agreement_action,quality_action,grouped_choices,
    decisions,metrics,cluster_intervals,partial_aurc)
from satquery_research.phase3b_analysis import numeric_sensitivity

def paired_fixture():
    base=dict(scene_id='s',question_id='q',seed=101,target_fraction=.2,question='Count?',answer='2',category='numeric',partition='development',generator='published',cloudy_digest='original')
    return pd.DataFrame([dict(base,condition='cloudy',input_digest='original',correct=0),dict(base,condition='telea_predicted',input_digest='repair',correct=1)])

def policy_fixture():
    rows=[]
    for scene in ['a','b','c']:
        for i in range(3):
            row=dict(scene_id=scene,question_id=scene+str(i),seed=101,target_fraction=.2,
                partition='development',category='yes_no',detector_fraction=.1*i,detector_latency_ms=2)
            for method in ['cloudy','telea_predicted','ns_predicted','cpu_auto_predicted']:
                row.update({method+'_correct':i%2,method+'_prediction':'yes' if method=='cloudy' else 'no',method+'_latency_ms':10,method+'_repair_ms':3})
            rows.append(row)
    return pd.DataFrame(rows)

def test_exact_pairing():
    p=pair(paired_fixture(),'telea_predicted')
    assert len(p)==1 and p.iloc[0].correct_repair==1

@pytest.mark.parametrize('defect',['missing','duplicate','identity','question'])
def test_bad_pairing(defect):
    f=paired_fixture()
    if defect=='missing':f=f.iloc[:1]
    if defect=='duplicate':f=pd.concat([f,f.iloc[[0]]])
    if defect=='identity':f.loc[1,'cloudy_digest']='different'
    if defect=='question':f.loc[1,'question']='different'
    with pytest.raises(ValueError):pair(f,'telea_predicted')

def test_four_transitions():
    assert transitions([0,1,1,0],[1,0,1,0])==dict(recovered=1,damaged=1,preserved=1,unrecovered=1)

@pytest.mark.parametrize('coverage,expected',[(.1,'cloudy'),(.2,'cloudy'),(.20001,'cpu_auto_predicted')])
def test_threshold_boundary(coverage,expected):assert threshold_action(coverage,.2)==expected

def test_abstention():
    assert agreement_action('yes','yes')=='cloudy'
    assert agreement_action('yes','no')=='abstain'

def test_scene_grouped_selection():
    f=policy_fixture();choices,folds=grouped_choices(f)
    for fold in folds:assert fold['held_scene'] not in fold['training_scenes'].split('|')
    assert len(choices)==3

def test_no_test_tuning():
    f=policy_fixture();f.loc[0,'partition']='test'
    with pytest.raises(ValueError):grouped_choices(f)

@pytest.mark.parametrize('policy',['P0','P1','P2','P3','P4','P5'])
def test_decisions_do_not_use_ground_truth(policy):
    f=policy_fixture();choices,_=grouped_choices(f)
    a=decisions(f,policy,choices)
    for col in f:
        if col.endswith('_correct'):f[col]=1-f[col]
    b=decisions(f,policy,choices)
    assert a.action.tolist()==b.action.tolist()

def test_selective_risk_and_cost():
    f=policy_fixture();r=decisions(f,'P5',hybrid_threshold=.1)
    result=metrics(r)
    assert result['coverage']==pytest.approx(2/3)
    assert result['selective_risk']==.5
    assert result['mean_vqa_calls']==pytest.approx(4/3)

def test_zero_coverage():
    r=decisions(policy_fixture(),'P4');m=metrics(r)
    assert m['coverage']==0 and m['selective_risk'] is None and m['selective_accuracy'] is None
    assert cluster_intervals(r,iterations=100)['risk_ci_low'] is None

def test_cluster_interval_reproducibility():
    r=decisions(policy_fixture(),'P0')
    assert cluster_intervals(r,iterations=200)==cluster_intervals(r,iterations=200)

def test_observed_interval_aurc():
    r=partial_aurc([(.5,.2),(1,.4),(.5,.2)])
    assert r['partial_aurc']==pytest.approx(.15) and r['coverage_min']==.5
    assert partial_aurc([(.5,.2)])['partial_aurc'] is None
    with pytest.raises(ValueError):partial_aurc([(.5,.2),(.5,.3)])

def test_deterministic_csv():
    f=policy_fixture();choices,_=grouped_choices(f)
    assert decisions(f,'P3',choices).to_csv(index=False)==decisions(f,'P3',choices).to_csv(index=False)

def test_secondary_numeric_strictness():
    assert numeric_sensitivity('two')==numeric_sensitivity('2.0')
    assert numeric_sensitivity('1,234')==1234
    assert numeric_sensitivity('there are 2') is None
