import numpy as np
import pytest
from satquery_research.repair import repair

@pytest.mark.parametrize('algorithm',['telea','navier_stokes','auto'])
def test_exact_unmasked_pixels(algorithm):
    image=np.random.default_rng(5).integers(0,256,(32,32,3),dtype=np.uint8)
    original=image.copy();mask=np.zeros((32,32),np.uint8);mask[8:20,5:15]=255
    output,meta=repair(image,mask,algorithm,3)
    assert np.array_equal(output[mask==0],image[mask==0])
    assert np.array_equal(original,image) and meta['radius']==3

def test_empty_noop():
    image=np.full((20,20,3),50,np.uint8)
    output,meta=repair(image,np.zeros((20,20),np.uint8))
    assert np.array_equal(output,image) and meta['empty_mask_noop']

def test_full_rejected():
    with pytest.raises(ValueError): repair(np.zeros((20,20,3),np.uint8),np.full((20,20),255,np.uint8))
