import pytest
from satquery_research.metrics import normalize_answer,numeric_value,score_answer,transitions
from satquery_research.statistics import scene_bootstrap

def test_normalization():
    assert normalize_answer('  YES.\n')=='yes'
    assert normalize_answer('No, because trees')=='no, because trees'
    assert normalize_answer('ＴＷＯ')=='two'

def test_numeric_exact_not_tolerance():
    assert score_answer('2.0','2')['correct']==0
    assert score_answer('2.0','2')['numeric_absolute_error']==0
    assert numeric_value('many') is None and numeric_value('9'*1000) is None

def test_transitions():
    r=transitions([0,1,1,0],[1,0,1,0])
    assert [r[k] for k in ['recovered','damaged','unchanged_correct','unchanged_incorrect']]==[1,1,1,1]

def test_bootstrap_clusters():
    r=scene_bootstrap(['a']*50+['b']*50,[1]*50+[-1]*50,iterations=500)
    assert r['n_scenes']==2 and r['ci_low']==-1 and r['ci_high']==1
    assert r==scene_bootstrap(['a']*50+['b']*50,[1]*50+[-1]*50,iterations=500)

def test_single_scene_no_interval():
    assert scene_bootstrap(['a']*20,[1]*20)['ci_low'] is None
