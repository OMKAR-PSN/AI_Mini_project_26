"""Small development-only policies. Decision functions never receive labels or oracle masks."""
import numpy as np
import pandas as pd

THRESHOLDS=(.1,.2,.3,.4,.5)
ACTIONS=('cloudy','telea_predicted','ns_predicted')
SEED=314159

def threshold_action(measured,threshold):return 'cpu_auto_predicted' if measured>threshold else 'cloudy'

def agreement_action(direct,repaired):return 'cloudy' if direct==repaired else 'abstain'

def quality_bin(measured):return 0 if measured<=.1 else 1 if measured<=.3 else 2

def quality_action(measured,mapping):return mapping[quality_bin(measured)]

def fit_threshold(training):
    # Tie-break by fewer repairs, then larger threshold. No test/validation labels used here.
    candidates=[]
    for threshold in THRESHOLDS:
        repair=training.detector_fraction.to_numpy()>threshold
        correct=np.where(repair,training.cpu_auto_predicted_correct,training.cloudy_correct)
        candidates.append((float(correct.mean()),-int(repair.sum()),threshold))
    return max(candidates)[2]

def fit_quality(training):
    mapping=[]
    for index in range(3):
        subset=training[training.detector_fraction.map(quality_bin)==index]
        if subset.empty:mapping.append('cloudy');continue
        means=[float(subset[action+'_correct'].mean()) for action in ACTIONS]
        mapping.append(ACTIONS[int(np.argmax(means))])
    return mapping

def grouped_choices(frame):
    if set(frame.partition)!={'development'}:raise ValueError('Policy fitting restricted to development data')
    scenes=sorted(frame.scene_id.unique())
    if len(scenes)<3:raise ValueError('Need at least three development scenes for grouped selection')
    selected={};folds=[]
    for held in scenes:
        train=frame[frame.scene_id!=held];validation=frame[frame.scene_id==held]
        assert not set(train.scene_id)&set(validation.scene_id)
        threshold=fit_threshold(train);mapping=fit_quality(train)
        selected[held]=(threshold,mapping)
        folds.append(dict(held_scene=held,training_scenes='|'.join(sorted(train.scene_id.unique())),
            threshold=threshold,quality_bin_low=mapping[0],quality_bin_mid=mapping[1],quality_bin_high=mapping[2]))
    return selected,folds

def metrics(frame):
    answered=frame.action!='abstain';correct=frame.policy_correct.to_numpy(dtype=float)
    base=frame.cloudy_correct.to_numpy(dtype=float);n=len(frame);na=int(answered.sum())
    return dict(n_records=n,n_scenes=int(frame.scene_id.nunique()),coverage=na/n,
        selective_accuracy=float(correct[answered].mean()) if na else None,
        selective_risk=float(1-correct[answered].mean()) if na else None,
        abstention_rate=1-na/n,recovered=int(((base==0)&(correct==1)&answered).sum()),
        damaged=int(((base==1)&(correct==0)&answered).sum()),
        withheld_correct=int(((base==1)&~answered).sum()),withheld_incorrect=int(((base==0)&~answered).sum()),
        answered_correct_fraction=float(correct[answered].sum()/n),
        mean_vqa_calls=float(frame.vqa_calls.mean()),mean_estimated_latency_ms=float(frame.estimated_latency_ms.mean()),
        p95_estimated_latency_ms=float(frame.estimated_latency_ms.quantile(.95)),
        **{'action_'+a:int((frame.action==a).sum()) for a in ['cloudy','cpu_auto_predicted','telea_predicted','ns_predicted','abstain']})

def cluster_intervals(frame,iterations=2000,seed=SEED):
    # Intervals are conditional on already selected OOF actions, not full selection-process CIs.
    groups=[]
    for _,g in frame.groupby('scene_id',sort=True):
        answered=g.action!='abstain'
        groups.append([len(g),int(answered.sum()),float(g.loc[answered,'policy_correct'].sum())])
    a=np.array(groups);rng=np.random.default_rng(seed)
    samples=a[rng.integers(0,len(a),(iterations,len(a)))].sum(axis=1)
    coverage=samples[:,1]/samples[:,0]
    valid=samples[:,1]>0
    risk=1-samples[valid,2]/samples[valid,1]
    quant=lambda x:[float(v) for v in np.quantile(x,[.025,.975])] if len(x) and len(a)>1 else [None,None]
    cl,ch=quant(coverage);rl,rh=quant(risk)
    return dict(coverage_ci_low=cl,coverage_ci_high=ch,risk_ci_low=rl,risk_ci_high=rh,
        selective_accuracy_ci_low=1-rh if rh is not None else None,
        selective_accuracy_ci_high=1-rl if rl is not None else None,
        bootstrap_iterations=iterations,bootstrap_seed=seed,valid_risk_replicates=int(valid.sum()))

def partial_aurc(points):
    """Trapezoids only over observed attainable coverage, without invented endpoints."""
    clean=sorted((float(c),float(r)) for c,r in points if r is not None and np.isfinite(r))
    unique={}
    for c,r in clean:
        if not 0<=c<=1 or not 0<=r<=1:raise ValueError('Invalid risk/coverage')
        if c in unique and not np.isclose(unique[c],r):raise ValueError('Not a single-valued risk-coverage curve')
        unique[c]=r
    if len(unique)<2:return dict(partial_aurc=None,coverage_min=min(unique,default=None),coverage_max=max(unique,default=None))
    x=np.array(list(unique));y=np.array(list(unique.values()))
    return dict(partial_aurc=float(np.trapezoid(y,x)),coverage_min=float(x.min()),coverage_max=float(x.max()))

def decisions(frame,policy,choices=None,hybrid_threshold=.2):
    rows=[]
    for _,row in frame.iterrows():
        detector=float(row.detector_fraction)
        dual=False;repair_action=None
        if policy=='P0':action='cloudy';detect_cost=0.
        elif policy=='P1':action='cpu_auto_predicted';detect_cost=float(row.detector_latency_ms)
        elif policy=='P2':
            action=threshold_action(detector,choices[row.scene_id][0]);detect_cost=float(row.detector_latency_ms)
        elif policy=='P3':
            action=quality_action(detector,choices[row.scene_id][1]);detect_cost=float(row.detector_latency_ms)
        elif policy in ('P4','P5'):
            detect_cost=float(row.detector_latency_ms)
            dual=policy=='P4' or detector>hybrid_threshold
            action=agreement_action(row.cloudy_prediction,row.cpu_auto_predicted_prediction) if dual else 'cloudy'
        else:raise ValueError('Unknown policy')
        cost=detect_cost;calls=1
        if dual:
            calls=2;repair_action='cpu_auto_predicted'
            cost+=float(row.cloudy_latency_ms)+float(row.cpu_auto_predicted_latency_ms)+float(row.cpu_auto_predicted_repair_ms)
        elif action=='cloudy':cost+=float(row.cloudy_latency_ms)
        else:
            repair_action=action;cost+=float(row[action+'_latency_ms'])+float(row[action+'_repair_ms'])
        correct=float(row[action+'_correct']) if action!='abstain' else np.nan
        rows.append(dict(scene_id=row.scene_id,question_id=row.question_id,seed=int(row.seed),
            target_fraction=float(row.target_fraction),category=row.category,policy=policy,action=action,
            policy_correct=correct,cloudy_correct=int(row.cloudy_correct),vqa_calls=calls,
            repair_action=repair_action or '',estimated_latency_ms=cost))
    return pd.DataFrame(rows)
