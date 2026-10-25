"""Small synthetic TEST fixtures only, never exported as experimental evidence."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import yaml
from satquery_research.manifests import write_csv,image_digest
from satquery_research import runner

def test_end_to_end_pairing_schema_and_resume(tmp_path,monkeypatch):
    config=yaml.safe_load(Path('research/configs/pilot.yaml').read_text())
    config['generator']['name']='legacy_style_opaque'
    config['cloud_levels']=[0,.2]
    config['bootstrap']['iterations']=100
    calls=[]
    class TestModel:
        hardware={'test_fixture':True}
        def __init__(self,cfg): pass
        def predict(self,image,question):
            calls.append(question)
            return dict(prediction_raw='yes',inference_latency_ms=1,image_grid_thw=[[1,2,2]],
                        peak_allocated_bytes=0,peak_reserved_bytes=0)
    def fake_prepare(cfg,folder):
        rows=[]
        for i in range(2):
            image=np.full((32,32,3),40+i,np.uint8)
            sid='scene_'+image_digest(image)
            relative=f'originals/{sid}.png';(folder/'originals').mkdir(exist_ok=True)
            Image.fromarray(image).save(folder/relative)
            rows.append(dict(scene_id=sid,question_id=f'q{i}',question='TEST fixture?',answer='yes',
                category='yes_no',partition='development',original_path=relative))
        write_csv(folder/'roster_all.csv',rows);write_csv(folder/'roster_selected.csv',rows)
        return rows,rows
    monkeypatch.setattr(runner,'prepare',fake_prepare)
    monkeypatch.setattr(runner,'QwenRunner',TestModel)
    folder=runner.run(config,'all',tmp_path)
    manifest=json.loads((folder/'experiment_manifest.json').read_text())
    assert manifest['status']=='complete'
    assert manifest['completion']['completed_predictions']==22
    predictions=pd.read_csv(folder/'predictions.csv')
    assert {'question_id','prediction_raw','correct','numeric_absolute_error','input_digest'}<=set(predictions)
    repairs=pd.read_csv(folder/'repair_outputs.csv')
    assert repairs.groupby(['scene_id','seed','target_fraction']).cloudy_digest.nunique().eq(1).all()
    assert set(repairs.mask_source)=={'reference','predicted'}
    runner.run(config,'all',tmp_path)
    assert len(calls)==22
    assert len(pd.read_csv(folder/'predictions.csv'))==22
