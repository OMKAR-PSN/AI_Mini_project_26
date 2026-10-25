"""Observed-data-only summaries and figures; no accuracy plots without predictions."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from PIL import Image
from .manifests import write_csv, atomic_json
from .metrics import transitions, normalize_answer
from .statistics import scene_bootstrap

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,
                    'axes.spines.right':False,'pdf.fonttype':42,'savefig.dpi':250})

def records(folder, kind):
    return pd.DataFrame([json.loads(p.read_text()) for p in sorted((folder/'records'/kind).glob('*.json'))])

def save(fig, folder, name):
    fig.tight_layout()
    fig.savefig(folder/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(folder/(name+'.png'),bbox_inches='tight',dpi=250)
    plt.close(fig)

def grouped(frame, keys):
    return frame.groupby(keys,dropna=False,sort=True)

def paired_table(predictions, before_condition, after_condition):
    keys=['scene_id','question_id','seed','target_fraction','generator','partition']
    after=predictions[predictions.condition==after_condition]
    before=predictions[predictions.condition==before_condition]
    if before_condition=='clean': keys=['scene_id','question_id','generator','partition']
    if before.duplicated(keys).any() or after.duplicated(keys if before_condition!='clean' else keys+['seed','target_fraction']).any():
        raise ValueError('Duplicate paired identity')
    pairs=after.merge(before[keys+['correct','prediction_normalized','input_digest']],on=keys,
        suffixes=('_after','_before'),validate='many_to_one' if before_condition=='clean' else 'one_to_one')
    if before_condition=='cloudy' and not (pairs.cloudy_digest==pairs.input_digest_before).all():
        raise ValueError('Repair and baseline used different cloudy inputs')
    return pairs

def analyze(folder):
    folder=Path(folder)
    manifest=json.loads((folder/'experiment_manifest.json').read_text())
    cfg=manifest['config']; bs=cfg['bootstrap']
    e0=records(folder,'e0'); predictions=records(folder,'predictions'); repairs=records(folder,'repairs')
    report={'vlm_results_available':not predictions.empty,'claims':'Pilot/experimental results only; no validated repair policy'}
    if not e0.empty:
        summary=[]
        for (generator,partition,target),frame in grouped(e0,['generator','partition','target_fraction']):
            tp,fp,fn,tn=(int(frame[col].sum()) for col in ['tp','fp','fn','tn'])
            summary.append(dict(generator=generator,partition=partition,target_fraction=target,
                n_scenes=frame.scene_id.nunique(),n_conditions=len(frame),tp=tp,fp=fp,fn=fn,tn=tn,
                achieved_fraction=float(frame.achieved_fraction.mean()),detector_fraction=float(frame.detector_fraction.mean()),
                precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
                f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,iou=tp/(tp+fp+fn) if tp+fp+fn else None,
                undefined_f1=int(frame.f1.isna().sum()),false_positive_coverage=fp/(tp+fp+fn+tn),
                mean_absolute_target_error=float(abs(frame.achieved_fraction-target).mean())))
        write_csv(folder/'e0_summary.csv',summary)
        s=pd.DataFrame(summary)
        fig,ax=plt.subplots(figsize=(5,3.3))
        for (gen,part),frame in grouped(s,['generator','partition']):
            for metric,marker in [('precision','o'),('recall','s'),('f1','^')]:
                ax.plot(frame.achieved_fraction,frame[metric],marker=marker,label=f'{metric} ({gen}, {part})')
        ax.set(xlabel='Achieved coverage (opacity ≥ declared threshold)',ylabel='Pooled pixel metric',ylim=(0,1.05))
        ax.legend(fontsize=6);save(fig,folder,'fig_e0_detection_quality')
        fig,ax=plt.subplots(figsize=(4.5,3.3))
        ax.scatter(e0.achieved_fraction,e0.detector_fraction,s=16,alpha=.6,label='Scene / seed conditions')
        ax.plot([0,1],[0,1],'k--',lw=.8,label='Equal coverage');ax.legend(fontsize=7)
        ax.set(xlabel='Achieved reference coverage',ylabel='Detector-measured coverage',xlim=(0,1),ylim=(0,1))
        save(fig,folder,'fig_e0_coverage_scatter')
        failure=folder/'e0_failure_cases';failure.mkdir(exist_ok=True)
        for name,metric in [('false_positive','fp'),('false_negative','fn')]:
            row=e0.sort_values(metric,ascending=False).iloc[0]
            if int(row[metric])==0: continue
            fig,axes=plt.subplots(1,4,figsize=(8,2.4))
            for ax,key,title in zip(axes,['original_path','cloudy_path','reference_path','predicted_path'],
                                    ['Original observation','Synthetic cloudy','Reference opacity mask','RGB predicted mask']):
                ax.imshow(Image.open(folder/row[key]),cmap='gray');ax.set_title(title,fontsize=8);ax.axis('off')
            fig.suptitle(f'{name.replace("_"," ")}: {int(row[metric])} pixels; achieved {row.achieved_fraction:.3f}',fontsize=9)
            save(fig,failure,name)
        # Representative input chosen by stable scene ID, closest achieved coverage to 0.4.
        sid=sorted(e0.scene_id.unique())[0]; rows=e0[e0.scene_id==sid]
        row=rows.iloc[np.argmin(abs(rows.achieved_fraction.to_numpy()-.4))]
        entries=[('Original observation',row.original_path),('Synthetic cloudy',row.cloudy_path),
                 ('Predicted mask',row.predicted_path),('Reference mask',row.reference_path)]
        if not repairs.empty:
            match=repairs[(repairs.scene_id==sid)&(repairs.seed==row.seed)&
                (repairs.target_fraction==row.target_fraction)&(repairs.variant=='telea_predicted')]
            if not match.empty: entries.append(('Telea estimate',match.iloc[0].input_path))
        fig,axes=plt.subplots(1,len(entries),figsize=(10,2.5))
        for ax,(title,path) in zip(axes,entries):
            ax.imshow(Image.open(folder/path),cmap='gray');ax.set_title(title,fontsize=8);ax.axis('off')
        save(fig,folder,'fig_image_gallery')
        report['cpu_conditions']=len(e0)
        report['cpu_generation_detection_seconds']=float(e0.generation_detection_ms.sum()/1000)
        report['repair_seconds']=float(repairs.repair_latency_ms.sum()/1000) if not repairs.empty else 0
    if predictions.empty:
        report['vqa_note']='E1/E2 accuracy and repair-benefit figures not generated: no model predictions'
        report['crossover']='Not evaluated; no VQA evidence'
        atomic_json(folder/'analysis_report.json',report)
        return report
    accuracy=[]
    for (condition,target),frame in grouped(predictions,['condition','target_fraction']):
        for category,subset in [('overall',frame)]+list(frame.groupby('category')):
            interval=scene_bootstrap(subset.scene_id,subset.correct,**bs)
            numeric=subset[subset.category=='numeric']
            accuracy.append(dict(condition=condition,target_fraction=target,category=category,
                achieved_fraction=float(subset.achieved_fraction.mean()),**interval,
                mean_latency_ms=float(subset.inference_latency_ms.mean()),numeric_n=len(numeric),
                numeric_parseable_n=int(numeric.numeric_absolute_error.notna().sum()),
                numeric_mae=float(numeric.numeric_absolute_error.mean()) if numeric.numeric_absolute_error.notna().any() else None))
    write_csv(folder/'accuracy_by_category.csv',accuracy)
    paired=[]; pair_audit=[]
    for before,after in [('clean','cloudy')]+[('cloudy',v) for v in sorted(set(predictions.condition)-{'clean','cloudy'})]:
        table=paired_table(predictions,before,after)
        pair_audit.append(dict(before=before,after=after,available_after=int((predictions.condition==after).sum()),
            matched=len(table),excluded_unmatched=int((predictions.condition==after).sum())-len(table)))
        if table.empty: continue
        # Completeness is explicit; incomplete results cannot support the prospective claim.
        for level,frame in list(table.groupby('target_fraction'))+[('all_nonzero',table[table.target_fraction>0])]:
            if frame.empty: continue
            for category,subset in [('overall',frame)]+list(frame.groupby('category')):
                delta=subset.correct_after-subset.correct_before
                pair_stats=transitions(subset.correct_before,subset.correct_after)
                paired.append(dict(before=before,after=after,target_fraction=level,category=category,
                    achieved_fraction=float(subset.achieved_fraction.mean()),
                    **pair_stats,clean_correct_cloudy_wrong=pair_stats['damaged'] if before=='clean' else None,
                    clean_wrong_cloudy_correct=pair_stats['recovered'] if before=='clean' else None,
                    **scene_bootstrap(subset.scene_id,delta,**bs),
                    prediction_change_rate=float((subset.prediction_normalized_before!=subset.prediction_normalized_after).mean())))
    write_csv(folder/'paired_comparisons.csv',paired)
    write_csv(folder/'pairing_completeness.csv',pair_audit)
    development=pd.read_csv(folder/'roster_all.csv',keep_default_na=False)
    development=development[development.partition=='development']
    baseline=[]
    for category in ['yes_no','categorical']:
        labels=development[development.category==category].answer.map(normalize_answer)
        if labels.empty: continue
        counts=labels.value_counts(); majority=sorted(counts[counts==counts.max()].index)[0]
        clean=predictions[(predictions.condition=='clean')&(predictions.category==category)]
        baseline.append(dict(category=category,development_majority=majority,development_n=len(labels),
            evaluation_n=len(clean),accuracy=float((clean.answer_normalized==majority).mean()) if len(clean) else None))
    write_csv(folder/'majority_baseline.csv',baseline)
    a=pd.DataFrame(accuracy); p=pd.DataFrame(paired)
    fig,ax=plt.subplots(figsize=(5,3.3))
    for condition,frame in a[(a.category=='overall')&a.condition.isin(['clean','cloudy'])].groupby('condition'):
        frame=frame.sort_values('achieved_fraction')
        ax.errorbar(frame.achieved_fraction,frame.estimate,
            yerr=np.maximum(0,np.array([frame.estimate-frame.ci_low,frame.ci_high-frame.estimate],dtype=float)),
            marker='o',capsize=3,label=condition)
    ax.set(xlabel='Achieved cloud coverage',ylabel='Exact-match accuracy',ylim=(0,1.05));ax.legend()
    save(fig,folder,'fig_e1_accuracy')
    if not p.empty:
        repair_rows=p[(p.before=='cloudy')&(p.category=='overall')&(p.target_fraction!='all_nonzero')]
        if not repair_rows.empty:
            fig,ax=plt.subplots(figsize=(6,3.5))
            for condition,frame in repair_rows.groupby('after'):
                frame=frame.sort_values('achieved_fraction')
                ax.errorbar(frame.achieved_fraction,frame.estimate,
                    yerr=np.maximum(0,np.array([frame.estimate-frame.ci_low,frame.ci_high-frame.estimate],dtype=float)),
                    marker='o',capsize=2,label=condition)
            ax.axhline(0,color='black',ls='--',lw=.8);ax.set(xlabel='Achieved cloud coverage',ylabel='Paired accuracy difference')
            ax.legend(fontsize=7);save(fig,folder,'fig_e2_repair_difference')
            totals=p[(p.before=='cloudy')&(p.category=='overall')&(p.target_fraction=='all_nonzero')]
            fig,ax=plt.subplots(figsize=(6,3.5));x=np.arange(len(totals))
            ax.bar(x-.18,totals.recovered,.36,label='Recovered',color='.35')
            ax.bar(x+.18,totals.damaged,.36,label='Damaged',color='.8',edgecolor='black',hatch='//')
            ax.set_xticks(x,totals.after,rotation=20,ha='right');ax.set_ylabel('Answers across fixed cloud seeds');ax.legend()
            save(fig,folder,'fig_e2_recovered_damaged')
    report.update(crossover='No confirmatory crossover analysis: per-level intervals are exploratory and pointwise',
        primary_criterion='CPU auto predicted vs cloudy, all nonzero levels: lower scene-bootstrap 95% CI > 0 on complete held-out test only',
        completeness=pair_audit)
    atomic_json(folder/'analysis_report.json',report)
    return report
