import json
from types import SimpleNamespace
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml
from satquery_research.manifests import Checkpoints,write_csv,source_fingerprint
from satquery_research.cloud_generation import generate
from satquery_research.analysis import paired_table
from satquery_research.vlm import require_gpu,ModelUnavailable

def test_resume_and_mismatch(tmp_path):
    cp=Checkpoints(tmp_path,{'config':1});cp.put('e0',['s',1],{'tp':3})
    again=Checkpoints(tmp_path,{'config':1});again.put('e0',['s',1],{'tp':3})
    assert len(again.rows('e0'))==1
    with pytest.raises(ValueError): Checkpoints(tmp_path,{'config':2})
    with pytest.raises(ValueError): cp.put('e0',['s',1],{'tp':5})

def test_published_determinism_and_preservation():
    import torch
    torch.set_num_threads(1)
    config=yaml.safe_load(Path('research/configs/pilot.yaml').read_text())['generator']
    image=np.full((64,64,3),80,np.uint8); original=image.copy()
    a=generate(image,.3,101,config);b=generate(image,.3,101,config)
    for x,y in zip(a[:3],b[:3]): assert np.array_equal(x,y)
    assert np.array_equal(image,original)
    assert a[1].shape==(64,64) and a[2].dtype==np.uint8

def test_clean_exact():
    cfg=dict(name='published',opacity_threshold=.2)
    image=np.full((8,8,3),24,np.uint8)
    out,opacity,mask,_=generate(image,0,1,cfg)
    assert np.array_equal(image,out) and not mask.any() and not opacity.any()

def test_pairing_rejects_changed_input():
    base=dict(scene_id='s',question_id='q',seed=1,target_fraction=.2,generator='published',partition='test',correct=1,prediction_normalized='yes')
    frame=pd.DataFrame([dict(base,condition='cloudy',input_digest='abc',cloudy_digest='abc'),dict(base,condition='telea_predicted',input_digest='def',cloudy_digest='wrong')])
    with pytest.raises(ValueError): paired_table(frame,'cloudy','telea_predicted')
    frame.loc[1,'cloudy_digest']='abc'
    assert len(paired_table(frame,'cloudy','telea_predicted'))==1

@pytest.mark.parametrize('available,free',[(False,0),(True,6*1024**3)])
def test_gpu_failure_before_model_download(available,free):
    fake=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:available,mem_get_info=lambda:(free,free)))
    with pytest.raises(ModelUnavailable): require_gpu(fake)

def test_model_loading_failure(monkeypatch):
    import satquery_research.vlm as vlm
    monkeypatch.setattr(vlm,'require_gpu',lambda _: (_ for _ in ()).throw(RuntimeError('test load failure')))
    with pytest.raises(ModelUnavailable,match='Model loading failed'): vlm.QwenRunner({})

def test_csv_schema_and_sources(tmp_path):
    write_csv(tmp_path/'result.csv',[dict(scene_id='s',tp=1,fp=0,fn=0,tn=2)])
    assert set(pd.read_csv(tmp_path/'result.csv'))=={'scene_id','tp','fp','fn','tn'}
    assert source_fingerprint()
