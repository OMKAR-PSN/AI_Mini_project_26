"""Read-only archive/directory validation before any policy selection. No model imports."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import unicodedata
import zipfile
import numpy as np
import pandas as pd
from PIL import Image
from .manifests import digest, image_digest

METHODS = ['telea_predicted','ns_predicted','telea_oracle','cpu_auto_predicted']
KEY = ['scene_id','question_id','seed','target_fraction']

class Source:
    def __init__(self,path):
        self.path=Path(path).resolve();self.archive=None
        if self.path.is_file():
            self.archive=zipfile.ZipFile(self.path)
            names=self.archive.namelist()
            if len(names)!=len(set(names)): raise ValueError('Duplicate archive member names')
            roots=[n[:-len('experiment_manifest.json')] for n in names if n.endswith('experiment_manifest.json')]
            if len(roots)!=1: raise ValueError('Expected exactly one run manifest in ZIP')
            self.prefix=roots[0]
            self.names={n[len(self.prefix):] for n in names if n.startswith(self.prefix) and not n.endswith('/')}
        else:
            self.prefix='';self.names={p.relative_to(self.path).as_posix() for p in self.path.rglob('*') if p.is_file()}
        self.hashes={n:hashlib.sha256(self.read(n)).hexdigest() for n in sorted(self.names)}

    def read(self,name):
        p=PurePosixPath(name.replace('\\','/'))
        if p.is_absolute() or '..' in p.parts or ':' in str(p): raise ValueError('Unsafe artifact path')
        if self.archive: return self.archive.read(self.prefix+p.as_posix())
        resolved=(self.path/str(p)).resolve()
        if not resolved.is_relative_to(self.path): raise ValueError('Artifact escapes run directory')
        return resolved.read_bytes()

    def json(self,name): return json.loads(self.read(name))
    def frame(self,name):
        f=pd.read_csv(io.BytesIO(self.read(name)),dtype=str,keep_default_na=False)
        numeric=['target_fraction','achieved_fraction','detector_fraction','correct','seed','radius',
                 'inference_latency_ms','repair_latency_ms','tp','fp','fn','tn','f1','mask_fraction']
        for col in numeric:
            if col in f: f[col]=pd.to_numeric(f[col].replace('',np.nan),errors='raise')
        return f
    def array(self,name):
        data=io.BytesIO(self.read(name))
        if name.endswith('.npy'):return np.load(data,allow_pickle=False)
        with Image.open(data) as image:return np.array(image)

def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC',str(value)).casefold().strip().split()).rstrip('.!?').strip()

def transitions(before,after):
    b=np.asarray(before,dtype=bool);a=np.asarray(after,dtype=bool)
    return dict(recovered=int((~b&a).sum()),damaged=int((b&~a).sum()),
                preserved=int((b&a).sum()),unrecovered=int((~b&~a).sum()))

def pair(predictions,method):
    a=predictions[predictions.condition=='cloudy']
    b=predictions[predictions.condition==method]
    if a.duplicated(KEY).any() or b.duplicated(KEY).any():raise ValueError('Duplicate prediction key')
    joined=a.merge(b,on=KEY,suffixes=('_cloudy','_repair'),how='outer',indicator=True,validate='one_to_one')
    if not joined['_merge'].eq('both').all():raise ValueError('Missing paired predictions')
    for col in ['question','answer','category','partition','generator','cloudy_digest']:
        if not joined[col+'_cloudy'].eq(joined[col+'_repair']).all():raise ValueError('Input-key mismatch: '+col)
    if not joined.input_digest_cloudy.eq(joined.cloudy_digest_repair).all():raise ValueError('Cloudy input identity mismatch')
    return joined.drop(columns='_merge')

def validate(source):
    errors=[];checks={};warnings=[]
    def check(label,condition):
        checks[label]=bool(condition)
        if not condition:errors.append(label)
    m=source.json('experiment_manifest.json');identity=source.json('identity.json');cfg=m['config']
    check('run identity',digest(identity)[:20]==m['run_id'])
    check('configuration hash',digest(cfg)==m['configuration_hash'] and identity['config']==cfg)
    check('source fingerprint agreement',identity['source']==m['source_fingerprints'])
    root=Path(__file__).resolve().parents[3]
    line_endings=[];unmatched=[]
    for name,sha in m['source_fingerprints'].items():
        path=root/name
        if not path.exists():unmatched.append(name);continue
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()==sha:continue
        if hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()==sha:line_endings.append(name)
        else:unmatched.append(name)
    if line_endings:warnings.append('Source hashes match after CRLF→LF normalization: '+', '.join(line_endings))
    if unmatched:warnings.append('Current checkout differs from historical source; source identity retained, not rewritten: '+', '.join(unmatched))
    check('dataset revision',cfg['dataset']['revision']=='35de41f26170edda2ccc4f88c0f62f641bb9e1f1')
    check('model and processor revisions',cfg['vlm']['revision']=='66285546d2b821cf421d4f5eb2576359d3770cd3' and m['processor']['revision']==cfg['vlm']['revision'])
    check('generator revision',cfg['generator']['revision']=='d0787cbdc1b39a7976f89aa085f1430f3207eda6')
    missing=sorted(set(m['output_files'])-source.names);check('manifest files present',not missing)
    check('run complete without reported errors',m['status']=='complete' and m['errors']==0)
    check('no error records',not any(n.startswith('records/errors/') for n in source.names))
    p=source.frame('predictions.csv');roster=source.frame('roster_selected.csv');all_roster=source.frame('roster_all.csv')
    e=source.frame('e0_detector_metrics.csv');rep=source.frame('repair_outputs.csv')
    levels=cfg['cloud_levels'];seeds=cfg['cloud_seeds'];scenes=set(roster.scene_id)
    expected=len(roster)*(1+len(seeds)*len(levels)*5)
    check('prediction counts',len(p)==expected==m['completion']['completed_predictions']==m['completion']['expected_predictions_if_enabled'])
    check('e0 counts',len(e)==len(scenes)*len(seeds)*len(levels)==m['completion']['completed_e0'])
    check('repair counts',len(rep)==len(e)*4==m['completion']['completed_repairs'])
    check('unique predictions',not p.duplicated(KEY+['condition']).any())
    check('unique scene conditions',not e.duplicated(['scene_id','seed','target_fraction']).any())
    check('unique repairs',not rep.duplicated(['scene_id','seed','target_fraction','variant']).any())
    check('roster IDs unique',not roster.question_id.duplicated().any() and not all_roster.question_id.duplicated().any())
    check('scene disjoint partition',all_roster.groupby('scene_id').partition.nunique().eq(1).all())
    check('development only',set(p.partition)=={'development'} and set(roster.partition)=={'development'})
    check('prediction roster identities',set(p.question_id)==set(roster.question_id))
    from .scene_split import split_scenes,select_roster
    expected_partition=split_scenes(all_roster.scene_id,cfg['split_seed'],cfg['development_fraction'])
    check('reproduced scene partition',all_roster.partition.eq(all_roster.scene_id.map(expected_partition)).all())
    selection=cfg['selection']
    expected_roster=select_roster(all_roster.to_dict('records'),selection['partition'],selection['max_scenes'],selection['questions_per_scene'],cfg['roster_seed'])
    check('reproduced selected question IDs',set(r['question_id'] for r in expected_roster)==set(roster.question_id))
    lookup=roster.set_index('question_id')
    for col in ['scene_id','question','answer','category','partition','original_path']:
        check('consistent '+col,p[col].eq(p.question_id.map(lookup[col])).all())
    check('raw prediction normalization',p.prediction_raw.map(normalized).eq(p.prediction_normalized).all())
    check('raw answer normalization',p.answer.map(normalized).eq(p.answer_normalized).all())
    check('independent exact match',p.prediction_raw.map(normalized).eq(p.answer.map(normalized)).astype(int).eq(p.correct).all())
    check('shared declared prompt',m['prompt_template']=='Answer the satellite image question with only a short answer, without explanation.\nQuestion: {question}')
    warnings.append('Prompt consistency verified from shared manifest and matching source; rendered per-call prompts/token IDs were not saved.')
    for qid,group in p.groupby('question_id'):
        clean=group[group.condition=='clean'];other=group[group.condition!='clean']
        expected_keys={(seed,float(level),method) for seed in seeds for level in levels for method in ['cloudy']+METHODS}
        actual=set(other[['seed','target_fraction','condition']].itertuples(index=False,name=None))
        check('complete grid '+qid,len(clean)==1 and actual==expected_keys)
    # Validate PNG/NPY content, not just their filenames.
    arrays={}
    def artifact(path,sha):
        if path not in arrays: arrays[path]=source.array(path)
        value=arrays[path]
        if image_digest(value)!=sha: raise ValueError('Digest mismatch: '+path)
        return value
    try:
        for _,row in e.iterrows():
            values={name:artifact(row[name+'_path'],row[name+'_digest']) for name in ['original','cloudy','predicted','reference','opacity','transparency']}
            reference=values['reference'];predicted=values['predicted'];opacity=values['opacity']
            assert reference.shape==predicted.shape==values['cloudy'].shape[:2]
            assert reference.dtype==predicted.dtype==np.uint8 and np.isin(reference,[0,255]).all() and np.isin(predicted,[0,255]).all()
            assert np.isfinite(opacity).all() and np.array_equal((opacity>=float(row.opacity_threshold))*255,reference)
            assert np.array_equal(1-opacity,values['transparency'])
            pr=predicted>0;rf=reference>0
            for name,array in [('tp',pr&rf),('fp',pr&~rf),('fn',~pr&rf),('tn',~pr&~rf)]:assert int(row[name])==int(array.sum())
            assert np.isclose(row.achieved_fraction,rf.mean()) and np.isclose(row.detector_fraction,pr.mean())
        elook=e.set_index(['scene_id','seed','target_fraction'])
        rlook=rep.set_index(['scene_id','seed','target_fraction','variant'])
        for _,row in rep.iterrows():
            original=elook.loc[(row.scene_id,row.seed,row.target_fraction)]
            assert row.cloudy_digest==original.cloudy_digest
            assert row.mask_digest==original[row.mask_source+'_digest']
            mask=arrays[original[row.mask_source+'_path']]
            out=artifact(row.input_path,row.input_digest);cloudy=arrays[original.cloudy_path]
            assert np.array_equal(out[mask==0],cloudy[mask==0])
        for _,row in p.iterrows():
            artifact(row.input_path,row.input_digest)
            if row.condition=='clean':assert row.scene_id=='scene_'+row.input_digest
            else:
                original=elook.loc[(row.scene_id,row.seed,row.target_fraction)]
                assert row.cloudy_digest==original.cloudy_digest
                if row.condition=='cloudy':assert row.input_digest==original.cloudy_digest
                else:
                    repaired=rlook.loc[(row.scene_id,row.seed,row.target_fraction,row.condition)]
                    assert row.input_digest==repaired.input_digest and row.mask_digest==repaired.mask_digest
        check('all scientific artifact identities and unmasked pixels',True)
    except (AssertionError,ValueError,KeyError,FileNotFoundError) as exc:
        check('all scientific artifact identities and unmasked pixels',False);errors.append(str(exc))
    for method in METHODS:
        try:check('exact pairing '+method,len(pair(p,method))==len(roster)*len(seeds)*len(levels))
        except ValueError as exc:check('exact pairing '+method,False);errors.append(str(exc))
    # Compare source CSVs against atomic records, preserving raw answer strings.
    for kind,frame in [('predictions',p),('e0',e),('repairs',rep)]:
        names=sorted(n for n in source.names if n.startswith('records/'+kind+'/') and n.endswith('.json'))
        check('checkpoint count '+kind,len(names)==len(frame))
        ids=KEY+['condition'] if kind=='predictions' else ['scene_id','seed','target_fraction']+(['variant'] if kind=='repairs' else [])
        def key(row):return tuple('' if pd.isna(row.get(c)) else str(float(row[c])) if c in ['seed','target_fraction'] else str(row[c]) for c in ids)
        csvmap={key(r):r for r in frame.to_dict('records')}
        okay=True
        for name in names:
            raw=source.json(name);row=csvmap.get(key(raw))
            if row is None:okay=False;break
            for col,value in raw.items():
                saved=row.get(col,'')
                if value is None: same=saved=='' or pd.isna(saved)
                elif isinstance(value,(int,float)) and not isinstance(value,bool):
                    try:same=np.isclose(float(saved),value,rtol=1e-12,atol=1e-12)
                    except ValueError:same=False
                else:same=str(value)==str(saved)
                if not same:okay=False;errors.append(f'Checkpoint/CSV mismatch {kind}: {col}');break
        check('checkpoint content '+kind,okay)
    summaries=source.frame('accuracy_by_category.csv')
    for _,row in summaries.iterrows():
        subset=p[(p.condition==row.condition)&(p.target_fraction==row.target_fraction)]
        if row.category!='overall':subset=subset[subset.category==row.category]
        check('accuracy '+row.condition+str(row.target_fraction)+row.category,np.isclose(subset.correct.mean(),float(row.estimate)))
    paired=pd.read_csv(io.BytesIO(source.read('paired_comparisons.csv')),keep_default_na=False)
    for i,row in paired.iterrows():
        if row.before=='clean':
            subset=p[p.condition=='cloudy'].merge(p[p.condition=='clean'][['question_id','correct']],on='question_id',suffixes=('','_before'),validate='many_to_one')
            before='correct_before';after='correct'
        else:subset=pair(p,row.after);before='correct_cloudy';after='correct_repair'
        subset=subset[subset.target_fraction>0] if row.target_fraction=='all_nonzero' else subset[subset.target_fraction==float(row.target_fraction)]
        category='category' if row.before=='clean' else 'category_cloudy'
        if row.category!='overall':subset=subset[subset[category]==row.category]
        trans=transitions(subset[before],subset[after])
        correct=all(trans[a]==int(row[b]) for a,b in [('recovered','recovered'),('damaged','damaged'),('preserved','unchanged_correct'),('unrecovered','unchanged_incorrect')])
        correct=correct and np.isclose((subset[after]-subset[before]).mean(),row.accuracy_difference) and len(subset)==int(row.n_records)
        check('paired summary '+str(i),correct)
    completeness=source.frame('pairing_completeness.csv')
    check('saved pairing completeness',len(completeness)==5 and all(int(r.matched)==len(roster)*len(seeds)*len(levels) and int(r.excluded_unmatched)==0 for _,r in completeness.iterrows()))
    return dict(status='passed' if not errors else 'failed',policy_selection_allowed=not errors,
        run_id=m['run_id'],configuration_hash=m['configuration_hash'],source_inventory_digest=digest(source.hashes),
        counts=dict(scenes=len(scenes),questions=len(roster),predictions=len(p),cloud_conditions=len(e),repairs=len(rep)),
        checks=checks,errors=errors,warnings=warnings,missing_files=missing),p,e,rep,roster
