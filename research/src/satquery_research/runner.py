"""Single-process, atomic item checkpoints; stage changes safely resume the same run."""
import argparse
import io
import json
import os
from pathlib import Path
import time
import numpy as np
from PIL import Image
import yaml
from .manifests import (REPO, Checkpoints, digest, image_digest, atomic_bytes, atomic_json,
                        write_csv, environment, source_fingerprint, utcnow)
from .datasets import prepare
from .cloud_generation import generate
from .cloud_detection import detect, PARAMETERS
from .repair import repair
from .metrics import mask_metrics, score_answer
from .vlm import QwenRunner, ModelUnavailable, PROMPT

VARIANTS = {'telea_predicted':('telea','predicted'),
    'ns_predicted':('navier_stokes','predicted'), 'telea_oracle':('telea','reference'),
    'cpu_auto_predicted':('auto','predicted')}

def save_array(folder, relative, array):
    stream = io.BytesIO()
    if relative.endswith('.npy'): np.save(stream,array,allow_pickle=False)
    else: Image.fromarray(array).save(stream,format='PNG')
    atomic_bytes(folder/relative,stream.getvalue())
    return relative

def load_image(folder, relative):
    with Image.open(folder/relative) as image: return np.array(image)

def verify_artifact(folder, row, name):
    array = load_image(folder,row[name+'_path'])
    if image_digest(array) != row[name+'_digest']: raise ValueError('Artifact digest mismatch: '+name)
    return array

def export_records(cp):
    for kind, filename in [('e0','e0_detector_metrics.csv'),('repairs','repair_outputs.csv'),
                           ('predictions','predictions.csv'),('errors','execution_errors.csv')]:
        rows = cp.rows(kind)
        if rows: write_csv(cp.folder/filename,rows)

def record_error(cp, stage, key, exc):
    row = dict(stage=stage,item_key=key,error_type=type(exc).__name__,error=str(exc),time=utcnow())
    # Errors are an append-only event stream; successful items alone are completion checkpoints.
    cp.put('errors', [stage,key,row['time']],row)
    print(f'{stage} failed: {type(exc).__name__}: {exc}',flush=True)

def predict_item(cp, model, question, condition, image_row, key):
    if cp.get('predictions',key) is not None: return
    image = verify_artifact(cp.folder,image_row,'input')
    result = model.predict(Image.fromarray(image).convert('RGB'),question['question'])
    row = dict(question, **image_row, condition=condition, **result,
               **score_answer(result['prediction_raw'],question['answer']))
    cp.put('predictions',key,row)
    export_records(cp)

def run(config, stage='cpu', output_root=None):
    if stage not in ('prepare','cpu','all'): raise ValueError('Unknown stage')
    levels, seeds = config['cloud_levels'], config['cloud_seeds']
    if not levels or len(set(levels))!=len(levels) or any(not 0<=x<=1 for x in levels):
        raise ValueError('Cloud levels must be unique nonempty fractions in [0,1]')
    if not seeds or len(set(seeds))!=len(seeds) or any(not isinstance(x,int) or not 0<=x<2**32 for x in seeds):
        raise ValueError('Cloud seeds must be unique uint32 integers')
    import torch
    os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
    torch.set_num_threads(config['cpu_threads'])
    env = environment()
    identity = dict(config=config, source=source_fingerprint(), packages=env['packages'],
                    python=env['python'], torch_version=env.get('torch_version'),
                    cuda_version=env.get('cuda_version'), gpu=env.get('gpu'))
    run_id = digest(identity)[:20]
    folder = Path(output_root or config['output_dir'])/run_id
    cp = Checkpoints(folder,identity)
    manifest_path = folder/'experiment_manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else dict(
        run_id=run_id, configuration_hash=digest(config), started_at=utcnow(), config=config,
        environment=env, source_fingerprints=identity['source'], detector_parameters=PARAMETERS,
        prompt_template=PROMPT, normalization='NFKC casefold whitespace and terminal .!? only',
        processor=dict(revision=config['vlm']['revision'],use_fast=False),
        generation=dict(do_sample=False,num_beams=1,use_cache=True,max_new_tokens=config['vlm']['max_new_tokens']))
    manifest.update(status='running',requested_stage=stage,last_started_at=utcnow())
    atomic_json(manifest_path,manifest)
    start = time.perf_counter()
    try:
        all_rows, selected = prepare(config,folder)
        roster_hash = digest(selected)
        if manifest.get('roster_digest',roster_hash) != roster_hash: raise ValueError('Roster changed within run')
        manifest['roster_digest'] = roster_hash
        if stage == 'prepare':
            manifest['status'] = 'prepared'
            return folder
        groups = {}
        for row in selected: groups.setdefault(row['scene_id'],[]).append(row)
        for scene_number,(sid, questions) in enumerate(sorted(groups.items()),1):
            original = load_image(folder,questions[0]['original_path'])
            for seed in config['cloud_seeds']:
                for target in config['cloud_levels']:
                    key = [sid,seed,target]
                    base = dict(scene_id=sid,partition=questions[0]['partition'],seed=seed,
                        target_fraction=target,generator=config['generator']['name'])
                    path = 'images/'+digest(key)[:24]
                    e0 = cp.get('e0',key)
                    if e0 is None:
                        try:
                            t = time.perf_counter()
                            cloudy,opacity,reference,metadata = generate(original,target,seed,config['generator'])
                            predicted, detection = detect(cloudy)
                            e0 = dict(base,**metadata,**detection,**mask_metrics(predicted,reference),
                                achieved_fraction=float((reference>0).mean()),
                                generation_detection_ms=1000*(time.perf_counter()-t),
                                original_path=questions[0]['original_path'],original_digest=image_digest(original),
                                opacity_threshold=config['generator']['opacity_threshold'])
                            for name,array in [('cloudy',cloudy),('reference',reference),('predicted',predicted)]:
                                e0[name+'_path']=save_array(folder,path+'/'+name+'.png',array)
                                e0[name+'_digest']=image_digest(array)
                            for name,array in [('opacity',opacity),('transparency',1-opacity)]:
                                e0[name+'_path']=save_array(folder,path+'/'+name+'.npy',array)
                                e0[name+'_digest']=image_digest(array)
                            cp.put('e0',key,e0)
                        except Exception as exc:
                            record_error(cp,'e0',key,exc); continue
                    cloudy = verify_artifact(folder,e0,'cloudy')
                    for variant,(algorithm,mask_source) in VARIANTS.items():
                        repair_key = key+[variant]
                        previous = cp.get('repairs',repair_key)
                        if previous is not None:
                            verify_artifact(folder,previous,'input')
                            if previous['cloudy_digest'] != e0['cloudy_digest']:
                                raise ValueError('Repair checkpoint cloudy input mismatch')
                            continue
                        try:
                            mask = verify_artifact(folder,e0,mask_source)
                            radius = 10 if variant=='cpu_auto_predicted' else config['repair_radius']
                            repaired,metadata = repair(cloudy,mask,algorithm,radius)
                            row = dict(base,**metadata,variant=variant,mask_source=mask_source,
                                mask_digest=e0[mask_source+'_digest'],cloudy_digest=e0['cloudy_digest'],
                                achieved_fraction=e0['achieved_fraction'],input_digest=image_digest(repaired),
                                input_path=save_array(folder,path+'/'+variant+'.png',repaired))
                            cp.put('repairs',repair_key,row)
                        except Exception as exc: record_error(cp,'repair',repair_key,exc)
                    export_records(cp)
            print(f'CPU scene {scene_number}/{len(groups)} complete',flush=True)
        manifest['vlm_status']='not requested; no E1/E2 accuracy results'
        if stage == 'all':
            try: model = QwenRunner(config['vlm'])
            except ModelUnavailable as exc:
                record_error(cp,'model_loading','shared_loader',exc)
                manifest['vlm_status']='blocked: '+str(exc)
            else:
                manifest['vlm_status']='inference attempted'
                for question in selected:
                    sid = question['scene_id']; qid = question['question_id']
                    image = load_image(folder,question['original_path'])
                    clean = dict(input_path=question['original_path'],input_digest=image_digest(image),
                                 seed=None,target_fraction=0.,achieved_fraction=0.,generator=config['generator']['name'])
                    try: predict_item(cp,model,question,'clean',clean,[qid,'clean'])
                    except Exception as exc: record_error(cp,'prediction',[qid,'clean'],exc)
                    for seed in config['cloud_seeds']:
                        for target in config['cloud_levels']:
                            key = [sid,seed,target]
                            e0 = cp.get('e0',key)
                            if e0 is None: continue
                            base = dict(seed=seed,target_fraction=target,achieved_fraction=e0['achieved_fraction'],
                                generator=e0['generator'],cloudy_digest=e0['cloudy_digest'])
                            conditions = {'cloudy':dict(base,input_path=e0['cloudy_path'],input_digest=e0['cloudy_digest'])}
                            for variant in VARIANTS:
                                row = cp.get('repairs',key+[variant])
                                if row is not None:
                                    conditions[variant]=dict(base,input_path=row['input_path'],input_digest=row['input_digest'],
                                        repair_latency_ms=row['repair_latency_ms'],mask_source=row['mask_source'],
                                        mask_digest=row['mask_digest'],radius=row['radius'])
                            for condition,item in conditions.items():
                                try: predict_item(cp,model,question,condition,item,[qid,seed,target,condition])
                                except Exception as exc: record_error(cp,'prediction',[qid,seed,target,condition],exc)
                manifest['vlm_hardware']=model.hardware
        export_records(cp)
        expected_e0=len(groups)*len(config['cloud_seeds'])*len(config['cloud_levels'])
        expected_predictions=len(selected)*(1+len(config['cloud_seeds'])*len(config['cloud_levels'])*5)
        manifest['completion']=dict(expected_e0=expected_e0,completed_e0=len(cp.rows('e0')),
            expected_repairs=expected_e0*4,completed_repairs=len(cp.rows('repairs')),
            expected_predictions_if_enabled=expected_predictions,completed_predictions=len(cp.rows('predictions')))
        complete=(len(cp.rows('e0'))==expected_e0 and len(cp.rows('repairs'))==expected_e0*4)
        if stage=='all': complete=complete and len(cp.rows('predictions'))==expected_predictions
        manifest['status']='cpu_complete' if complete and stage=='cpu' else 'complete' if complete else 'partial'
        from .analysis import analyze
        analyze(folder)
        return folder
    except Exception as exc:
        record_error(cp,'run','fatal',exc); manifest['status']='failed'; raise
    finally:
        manifest.update(last_finished_at=utcnow(),last_invocation_seconds=time.perf_counter()-start,
            errors=len(cp.rows('errors')),output_files=sorted(str(p.relative_to(folder)).replace('\\','/')
            for p in folder.rglob('*') if p.is_file()))
        atomic_json(manifest_path,manifest)

def main(default_config='pilot.yaml'):
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default=str(REPO/'research/configs'/default_config))
    parser.add_argument('--stage',choices=['prepare','cpu','all'],default='cpu')
    parser.add_argument('--output-root')
    args=parser.parse_args()
    config=yaml.safe_load(Path(args.config).read_text(encoding='utf-8'))
    print('Run directory:',run(config,args.stage,args.output_root),flush=True)

if __name__=='__main__': main()
