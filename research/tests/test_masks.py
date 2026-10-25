import numpy as np
import pytest
from satquery_research.metrics import validate_mask, mask_metrics
from satquery_research.cloud_generation import opacity_mask

@pytest.mark.parametrize('mask',[np.zeros((3,4),float),np.ones((3,4),np.uint8),np.zeros((4,3),np.uint8),np.zeros((3,4,1),np.uint8)])
def test_invalid_mask(mask):
    with pytest.raises(ValueError): validate_mask(mask,(3,4))

def test_empty_convention():
    zero=np.zeros((3,4),np.uint8)
    result=mask_metrics(zero,zero)
    assert result['f1'] is None and result['both_empty'] and result['tn']==12

def test_known_confusion():
    reference=np.array([[255,255],[0,0]],np.uint8)
    predicted=np.array([[255,0],[255,0]],np.uint8)
    assert {k:mask_metrics(predicted,reference)[k] for k in ['tp','fp','fn','tn']}==dict(tp=1,fp=1,fn=1,tn=1)

def test_opacity_orientation():
    mask=opacity_mask(np.array([[0,.2,.9],[.19,0,1]],np.float32),.2)
    assert mask.tolist()==[[0,255,255],[0,0,255]] and mask.dtype==np.uint8

@pytest.mark.parametrize('value',[np.nan,-.1,1.1])
def test_invalid_opacity(value):
    with pytest.raises(ValueError): opacity_mask(np.array([[value]]),.2)
