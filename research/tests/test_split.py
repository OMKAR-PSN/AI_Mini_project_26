import numpy as np
from satquery_research.scene_split import split_scenes,select_roster
from satquery_research.manifests import image_digest

def test_scene_disjoint_and_reproducible():
    split=split_scenes([str(i) for i in range(100)]*20)
    assert split==split_scenes(list(reversed(list(split))))
    dev={s for s,p in split.items() if p=='development'}
    test={s for s,p in split.items() if p=='test'}
    assert len(dev)==20 and len(test)==80 and not dev&test

def test_digest_and_layout():
    x=np.arange(18,dtype=np.uint8).reshape(2,3,3)
    assert image_digest(x)==image_digest(x.copy())
    assert image_digest(x)!=image_digest(x.transpose(1,0,2))

def test_roster_keeps_numeric():
    rows=[dict(scene_id=str(i),question_id=str(i),partition='development',answer='100000') for i in range(10)]
    assert len(select_roster(rows,'development',10,3,4))==10
