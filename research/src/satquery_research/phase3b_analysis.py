"""Failure analysis and exploratory E4 preparation from immutable saved predictions."""
import json
from decimal import Decimal,InvalidOperation
from pathlib import Path
import re
import textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from .phase3b_integrity import METHODS,KEY,pair,transitions,normalized
from .phase3b_policies import (THRESHOLDS,grouped_choices,decisions,metrics,cluster_intervals,partial_aurc,
                              fit_threshold,fit_quality)
from .statistics import scene_bootstrap
from .manifests import atomic_json

def csv(path,frame):frame.to_csv(path,index=False,float_format='%.12g',lineterminator='\n')

def numeric_sensitivity(value):
    text=normalized(value)
    words='zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty'.split()
    if text in words:text=str(words.index(text))
    if re.fullmatch(r'[+-]?\d{1,3}(,\d{3})+(\.\d+)?',text):text=text.replace(',','')
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)',text):return None
    try:return Decimal(text)
    except InvalidOperation:return None

def build_failure_table(p,e,rep):
    rows=[];emap=e.set_index(['scene_id','seed','target_fraction']);rmap=rep.set_index(['scene_id','seed','target_fraction','variant'])
    clean=p[p.condition=='clean'].set_index('question_id').prediction_normalized
    for method in METHODS:
        joined=pair(p,method)
        for _,row in joined.iterrows():
            env=emap.loc[(row.scene_id,row.seed,row.target_fraction)]
            repaired=rmap.loc[(row.scene_id,row.seed,row.target_fraction,method)]
            b=int(row.correct_cloudy);a=int(row.correct_repair)
            outcome={(0,1):'recovered',(1,0):'damaged',(1,1):'preserved',(0,0):'unrecovered'}[b,a]
            rows.append(dict(scene_id=row.scene_id,question_id=row.question_id,question=row.question_cloudy,
                answer=row.answer_cloudy,category=row.category_cloudy,seed=int(row.seed),target_fraction=float(row.target_fraction),
                achieved_fraction=float(env.achieved_fraction),detector_fraction=float(env.detector_fraction),
                detector_f1=float(env.f1) if pd.notna(env.f1) else None,
                false_negative_fraction=float(env.fn/(env.tp+env.fn)) if env.tp+env.fn else None,
                detector_coverage_error=float(env.detector_fraction-env.achieved_fraction),
                method=method,mask_source=repaired.mask_source,radius=float(repaired.radius),algorithm=repaired.repair_algorithm,
                cloudy_prediction_raw=row.prediction_raw_cloudy,repaired_prediction_raw=row.prediction_raw_repair,
                cloudy_prediction=row.prediction_normalized_cloudy,repaired_prediction=row.prediction_normalized_repair,
                clean_prediction=clean.loc[row.question_id],
                cloudy_correct=b,repaired_correct=a,transition=outcome,correctness_change=a-b,
                original_path=env.original_path,cloudy_path=env.cloudy_path,reference_path=env.reference_path,
                predicted_path=env.predicted_path,repaired_path=repaired.input_path,
                cloudy_digest=env.cloudy_digest,mask_digest=repaired.mask_digest,
                repair_latency_ms=float(repaired.repair_latency_ms)))
    return pd.DataFrame(rows).sort_values(['scene_id','question_id','seed','target_fraction','method']).reset_index(drop=True)

def policy_frame(p,e,rep):
    direct=p[(p.condition=='cloudy')&(p.target_fraction>0)].copy()
    columns=KEY+['question','answer','category','partition']
    result=direct[columns].copy()
    for method in ['cloudy']+METHODS:
        selected=p[(p.condition==method)&(p.target_fraction>0)]
        selected=selected[KEY+['correct','prediction_normalized','inference_latency_ms']].rename(columns={
            'correct':method+'_correct','prediction_normalized':method+'_prediction','inference_latency_ms':method+'_latency_ms'})
        result=result.merge(selected,on=KEY,validate='one_to_one')
        if method!='cloudy':
            timing=rep[rep.variant==method][['scene_id','seed','target_fraction','repair_latency_ms']].rename(columns={'repair_latency_ms':method+'_repair_ms'})
            result=result.merge(timing,on=['scene_id','seed','target_fraction'],validate='many_to_one')
    result=result.merge(e[['scene_id','seed','target_fraction','detector_fraction','detector_latency_ms']],
                        on=['scene_id','seed','target_fraction'],validate='many_to_one')
    return result.sort_values(KEY).reset_index(drop=True)

def analyze(source,output,p,e,rep,roster):
    output=Path(output);(output/'figures').mkdir(exist_ok=True);(output/'case_studies').mkdir(exist_ok=True)
    m=source.json('experiment_manifest.json')
    configuration=dict(schema_version=1,source_run=m['run_id'],source_configuration_hash=m['configuration_hash'],
        evaluation='Exploratory development only; primary policy evaluation excludes target zero',
        bootstrap=dict(seed=314159,iterations=2000,cluster='scene; retain questions, levels and fixed seeds',
            limitation='OOF bootstrap conditional on selected fold actions; does not capture full policy-selection uncertainty'),
        P0='Direct cloudy answer; one VQA call',P1='CPU auto predicted-mask repair; one VQA call plus detector/repair',
        P2=dict(threshold_candidates=list(THRESHOLDS),rule='repair iff detector fraction > threshold',selection='leave-one-scene-out training accuracy; ties favor fewer repairs and larger threshold'),
        P3=dict(bins=[.1,.3],actions=['cloudy','telea_predicted','ns_predicted'],selection='Training-bin accuracy in LOSO; ties favor direct then Telea; empty bins direct'),
        P4='Run direct and auto repair; abstain on normalized disagreement; two VQA calls',
        P5=dict(repair_trigger=.2,rule='Direct below/equal trigger; above trigger run both, abstain on disagreement',sensitivity_thresholds=[0,.1,.2,.3,.4,.5]),
        label_access='Labels used only for development fitting and retrospective scoring, never decision functions',
        oracle_masks='Excluded from all operational policies',
        latency='Sum of saved condition inference, detector and repair times; serial estimate, not measured policy execution; per-question no image-stage amortization',
        preregistration='Candidate rules fixed for this analysis, after pilot collection; not a registration before the GPU run',
        experiment_numbering=dict(E0='Cloud detection',E1='Cloud-affected VQA',E2='Reconstruction versus no reconstruction',E3='Bi-temporal change analysis',E4='Abstention and risk-coverage',E5='Dynamic tool-injection ablation'))
    atomic_json(output/'policy_configuration.json',configuration)
    failures=build_failure_table(p,e,rep);csv(output/'failure_cases.csv',failures)
    nonzero=failures[failures.target_fraction>0]
    comparisons=[]
    for method,g in nonzero.groupby('method',sort=True):
        comparisons.append(dict(method=method,cloudy_accuracy=float(g.cloudy_correct.mean()),
            repaired_accuracy=float(g.repaired_correct.mean()),**transitions(g.cloudy_correct,g.repaired_correct),
            **scene_bootstrap(g.scene_id,g.correctness_change)))
    comparison=pd.DataFrame(comparisons);csv(output/'repair_comparison.csv',comparison)
    level_rows=[]
    for (method,level,category),g in failures.groupby(['method','target_fraction','category'],sort=True):
        level_rows.append(dict(method=method,target_fraction=level,category=category,n_records=len(g),
            **transitions(g.cloudy_correct,g.repaired_correct),accuracy_difference=float(g.correctness_change.mean())))
    csv(output/'transitions_by_level_category.csv',pd.DataFrame(level_rows))
    scene=nonzero.groupby(['scene_id','method'],sort=True).agg(n=('question_id','size'),
        cloudy_accuracy=('cloudy_correct','mean'),repaired_accuracy=('repaired_correct','mean'),
        accuracy_difference=('correctness_change','mean'),damaged=('transition',lambda x:int((x=='damaged').sum())),
        recovered=('transition',lambda x:int((x=='recovered').sum()))).reset_index()
    csv(output/'scene_level_summary.csv',scene)
    repeat=nonzero.groupby(['scene_id','question_id','question','method'],sort=True).agg(
        damaged_conditions=('transition',lambda x:int((x=='damaged').sum())),
        recovered_conditions=('transition',lambda x:int((x=='recovered').sum()))).reset_index()
    csv(output/'repeated_question_failures.csv',repeat)
    associations=[]
    image_units=nonzero.groupby(['scene_id','seed','target_fraction','method'],sort=True).agg(
        delta=('correctness_change','mean'),fn_fraction=('false_negative_fraction','first'),
        achieved=('achieved_fraction','first'),coverage_error=('detector_coverage_error','first'),radius=('radius','first')).reset_index()
    for method,g in image_units.groupby('method'):
        for variable in ['fn_fraction','achieved','coverage_error']:
            value=g[variable].corr(g.delta,method='spearman') if g.delta.nunique()>1 and g[variable].nunique()>1 else None
            associations.append(dict(method=method,signal=variable,spearman_rho=value,n_scene_conditions=len(g),
                interpretation='Descriptive association; repeated scenes/levels, no causal or significance claim'))
    csv(output/'exploratory_associations.csv',pd.DataFrame(associations))
    numeric=p[p.category=='numeric'].copy()
    numeric['sensitivity_prediction']=numeric.prediction_raw.map(numeric_sensitivity)
    numeric['sensitivity_answer']=numeric.answer.map(numeric_sensitivity)
    numeric['secondary_numeric_equal']=[a is not None and b is not None and a==b for a,b in zip(numeric.sensitivity_prediction,numeric.sensitivity_answer)]
    numeric['large_reference_count']=numeric.answer.map(lambda x:float(x)>=100)
    numeric['review_status']='Original answer retained; visual inspection cannot verify exact count'
    csv(output/'numeric_diagnostics.csv',numeric.sort_values(['question_id','condition','seed','target_fraction']))
    numeric_summary=numeric.groupby('condition').agg(n=('correct','size'),exact_accuracy=('correct','mean'),
        secondary_numeric_accuracy=('secondary_numeric_equal','mean')).reset_index()
    csv(output/'numeric_summary.csv',numeric_summary)
    frame=policy_frame(p,e,rep);choices,folds=grouped_choices(frame)
    csv(output/'grouped_validation.csv',pd.DataFrame(folds))
    summaries=[];all_decisions=[]
    for policy in ['P0','P1','P2','P3','P4','P5']:
        result=decisions(frame,policy,choices);all_decisions.append(result)
        row=dict(policy=policy,**metrics(result),**cluster_intervals(result),evaluation='LOSO out-of-fold' if policy in ['P2','P3'] else 'Fixed development baseline')
        if row['coverage']==1:
            interval=scene_bootstrap(result.scene_id,result.policy_correct-result.cloudy_correct)
            row.update(accuracy_difference_vs_direct=interval['estimate'],difference_ci_low=interval['ci_low'],difference_ci_high=interval['ci_high'])
        summaries.append(row)
    policies=pd.DataFrame(summaries);csv(output/'policy_comparison.csv',policies)
    all_decisions=pd.concat(all_decisions,ignore_index=True);csv(output/'policy_decisions.csv',all_decisions)
    strata=[]
    for (policy,category),g in all_decisions.groupby(['policy','category']):strata.append(dict(policy=policy,category=category,**metrics(g),**cluster_intervals(g)))
    csv(output/'policy_by_category.csv',pd.DataFrame(strata))
    risk=[]
    for threshold in configuration['P5']['sensitivity_thresholds']:
        result=decisions(frame,'P5',hybrid_threshold=threshold)
        risk.append(dict(family='P5 fixed-gate sensitivity',threshold=threshold,**metrics(result),**cluster_intervals(result)))
    risk=pd.DataFrame(risk);csv(output/'risk_coverage.csv',risk)
    aurc=partial_aurc(list(zip(risk.coverage,risk.selective_risk)))
    targets=[]
    for target in [.1,.2,.3,.4,.5]:
        eligible=risk[risk.selective_risk<=target];conservative=risk[risk.risk_ci_high<=target]
        targets.append(dict(target_risk=target,observed_max_coverage=float(eligible.coverage.max()) if len(eligible) else None,
            max_coverage_upper_ci_within_target=float(conservative.coverage.max()) if len(conservative) else None,
            limitation='Development descriptive attainable points only; not a guaranteed future risk'))
    csv(output/'coverage_at_target_risk.csv',pd.DataFrame(targets))
    agreement=frame.cloudy_prediction==frame.cpu_auto_predicted_prediction
    agreement_report=dict(agree_n=int(agreement.sum()),false_agreement_n=int((agreement&(frame.cloudy_correct==0)).sum()),
        agree_correct_n=int((agreement&(frame.cloudy_correct==1)).sum()),disagree_n=int((~agreement).sum()))
    frozen=dict(recommended_operational_change=False,baseline='P0 direct answer',
        candidate_for_held_out_comparison='P5 with fixed 0.20 measured-fraction gate; exploratory only, no safety claim',
        P2_full_development_threshold=fit_threshold(frame),P3_full_development_mapping=fit_quality(frame),
        restriction='Do not deploy or tune on held-out labels. No conclusion that agreement implies correctness.')
    atomic_json(output/'candidate_freeze.json',frozen)
    report=dict(source_run=m['run_id'],clean_accuracy=float(p[p.condition=='clean'].correct.mean()),
        cloudy_nonzero_accuracy=float(frame.cloudy_correct.mean()),auto_nonzero_accuracy=float(frame.cpu_auto_predicted_correct.mean()),
        agreement=agreement_report,partial_risk_coverage=aurc,
        numeric_clean_n=int(((p.condition=='clean')&(p.category=='numeric')).sum()),
        numeric_exact_correct=int(numeric.correct.sum()),numeric_sensitivity_correct=int(numeric.secondary_numeric_equal.sum()),
        selection_uncertainty='Ten scenes only. OOF cluster intervals condition on fold selections; not full selection uncertainty.',
        radius_limitation='Auto radius10 changes algorithm above 0.30; comparisons with radius3 cannot isolate a radius causal effect.',
        missing_signals='No calibrated confidence, token probabilities, independent annotations or task-relevant object masks saved.',
        source_files_unchanged=all(__import__('hashlib').sha256(source.read(n)).hexdigest()==h for n,h in source.hashes.items()))
    atomic_json(output/'analysis_summary.json',report)
    figures(source,output,failures,comparison,scene,image_units,policies,risk)
    write_notes(output,report,comparison,policies,numeric_summary,repeat,folds)
    print(json.dumps(report,indent=2),flush=True)

def figures(source,output,failures,comparison,scene,image_units,policies,risk):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    names={'cloudy':'Direct','cpu_auto_predicted':'CPU auto','telea_predicted':'Telea predicted','ns_predicted':'NS predicted','telea_oracle':'Telea reference'}
    cases=[]
    with PdfPages(output/'phase3b_figures.pdf',metadata={'Title':'SatQuery Phase 3B — exploratory development pilot','CreationDate':None,'ModDate':None}) as book:
        def save(fig,name,case=False):
            fig.tight_layout()
            folder=output/('case_studies' if case else 'figures')
            fig.savefig(folder/(name+'.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None})
            fig.savefig(folder/(name+'.png'),bbox_inches='tight',dpi=300)
            book.savefig(fig,bbox_inches='tight');plt.close(fig)
        fig,ax=plt.subplots(figsize=(6.8,3.1));x=np.arange(len(comparison))
        ax.errorbar(x,100*comparison.estimate,yerr=100*np.array([comparison.estimate-comparison.ci_low,comparison.ci_high-comparison.estimate]),fmt='ko',capsize=4)
        ax.axhline(0,color='.5',ls='--');ax.set_xticks(x,[names[v] for v in comparison.method],rotation=12)
        ax.set_ylabel('Repair minus direct accuracy (percentage points)');ax.set_title('E2: 10 development scenes; scene-bootstrap 95% intervals')
        save(fig,'accuracy_difference')
        fig,ax=plt.subplots(figsize=(6.8,3))
        ax.bar(x-.18,comparison.recovered,.36,color='.3',label='Recovered');ax.bar(x+.18,comparison.damaged,.36,color='.8',edgecolor='black',hatch='//',label='Damaged')
        ax.set_xticks(x,[names[v] for v in comparison.method],rotation=12);ax.set_ylabel('Question-condition counts');ax.legend();save(fig,'recovered_damaged')
        matrix=scene.pivot(index='scene_id',columns='method',values='accuracy_difference').sort_index()
        fig,ax=plt.subplots(figsize=(6.8,4));im=ax.imshow(matrix.to_numpy()*100,cmap='RdBu',vmin=-40,vmax=40,aspect='auto')
        ax.set_yticks(range(len(matrix)),[f'S{i+1}: '+s[6:14] for i,s in enumerate(matrix.index)])
        ax.set_xticks(range(len(matrix.columns)),[names[v] for v in matrix.columns],rotation=15)
        for i in range(len(matrix)):
            for j in range(len(matrix.columns)):ax.text(j,i,f'{matrix.iloc[i,j]*100:.1f}',ha='center',va='center',fontsize=7)
        fig.colorbar(im,ax=ax,label='Accuracy difference (percentage points)');save(fig,'scene_level_performance')
        fig,ax=plt.subplots(figsize=(6.8,3.2))
        for method,marker in zip(METHODS,['o','s','^','x']):
            g=image_units[image_units.method==method];ax.scatter(g.fn_fraction,g.delta*100,label=names[method],marker=marker,s=20,alpha=.6)
        ax.axhline(0,color='.6',lw=.6);ax.set(xlabel='Detector FN / reference-positive pixels',ylabel='Mean question accuracy change (pp)')
        ax.legend(fontsize=7);ax.set_title('Repeated scene conditions; descriptive, not a causal relationship');save(fig,'false_negatives_vs_outcomes')
        fig,ax=plt.subplots(figsize=(6.8,3.6));g=risk.sort_values('coverage').drop_duplicates('coverage')
        ax.plot(g.coverage,g.selective_risk,'k.-',label='P5 gate sensitivity; observed points')
        for _,row in policies.iterrows():
            ax.scatter(row.coverage,row.selective_risk,label=row.policy,s=40,marker={'P0':'o','P1':'s','P2':'^','P3':'v','P4':'D','P5':'x'}[row.policy])
        ax.set(xlabel='Coverage (answered fraction)',ylabel='Selective risk (error among answered)',xlim=(0,1.04),ylim=(0,1))
        ax.legend(fontsize=7,ncol=2);ax.set_title('Exploratory E4 preparation: no interpolation beyond observed coverage');save(fig,'risk_coverage')
        f=failures[failures.target_fraction>0]
        selectors=[('01_damaged',f[(f.method=='cpu_auto_predicted')&(f.transition=='damaged')], 'Already correct; repair damages the answer'),
            ('02_recovered',f[(f.method=='cpu_auto_predicted')&(f.transition=='recovered')], 'Counterexample: repair recovers the answer'),
            ('03_mask_false_negatives',f[f.method=='cpu_auto_predicted'].sort_values('false_negative_fraction',ascending=False,kind='stable'), 'High missed reference-cloud fraction; task relevance not independently labelled'),
            ('04_reference_wrong',f[(f.method=='telea_oracle')&(f.repaired_correct==0)],'Reference-mask repair still wrong'),
            ('05_large_mask',f[f.method=='cpu_auto_predicted'].sort_values('detector_fraction',ascending=False,kind='stable'),'Large-mask classical estimate; inspect structural distortion'),
            ('06_stable',f[(f.cloudy_prediction==f.repaired_prediction)&(f.cloudy_prediction==f.clean_prediction)&(f.transition=='preserved')].sort_values('target_fraction',ascending=False,kind='stable'), 'Counterexample: correct answer stable from clean through cloud and repair')]
        for name,subset,title in selectors:
            if subset.empty:continue
            row=subset.iloc[0];cases.append(dict(case=name,scene_id=row.scene_id,question_id=row.question_id,method=row.method,target_fraction=row.target_fraction,transition=row.transition))
            fig,axes=plt.subplots(1,5,figsize=(7.2,3.3))
            for ax,key,label in zip(axes,['original_path','cloudy_path','reference_path','predicted_path','repaired_path'],
                ['Original','Synthetic cloudy','Reference mask','Predicted mask','Repair estimate']):
                ax.imshow(source.array(row[key]),cmap='gray',vmin=0,vmax=255);ax.set_title(label,fontsize=8);ax.axis('off')
            fig.suptitle(title,fontsize=9,y=.99)
            caption=f"Question: {row.question}\nReference answer: {row.answer} | Cloudy: {row.cloudy_prediction_raw} | Repaired: {row.repaired_prediction_raw}\n{names[row.method]} | {row.transition} | achieved {row.achieved_fraction:.3f}, measured {row.detector_fraction:.3f} | scene {row.scene_id[6:18]}"
            fig.text(.03,.02,'\n'.join(textwrap.fill(line,115) for line in caption.splitlines()),fontsize=8,va='bottom')
            fig.subplots_adjust(top=.82,bottom=.35)
            # Explicit rectangle preserves caption space when tight_layout runs.
            fig.tight_layout(rect=(0,.30,1,.90))
            # save without a second automatic layout to preserve the text region.
            dest=output/'case_studies'/name
            fig.savefig(dest.with_suffix('.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None});fig.savefig(dest.with_suffix('.png'),bbox_inches='tight',dpi=300)
            book.savefig(fig,bbox_inches='tight');plt.close(fig)
    csv(output/'case_studies/selection.csv',pd.DataFrame(cases))

def write_notes(output,report,comparison,policies,numeric_summary,repeat,folds):
    numeric_text='''# Numeric-answer diagnostic and review checklist

Primary exact-match labels and predictions are unchanged. Secondary sensitivity only recognizes standalone number words zero–twenty, properly grouped thousands commas and equivalent decimal numerals. It does not extract numbers from prose or accept arbitrary tolerance.

All ten selected numeric questions use counting language, so this pilot shows no obvious category error from the answer-form heuristic. The shared prompt asks for a short answer; it does not request yes/no. Whether this short-answer wording affects counting needs a separately approved prompt experiment, not a causal claim from these records.

The selected reference labels include 409 buildings and 89 roads. A 256×256 RGB observation does not independently establish object counts, object use or directional relation annotations. Counts may reflect geographic annotation semantics. Do not relabel them based on this inspection.

Review checklist: recover original RSVQA geographic/vector annotation provenance; verify patch extent and relation wording; check object-category definitions; independently double-annotate an agreed subset; record ambiguity rather than silently exclude; freeze any exclusion/normalization protocol before held-out testing; retain original exact match alongside any sensitivity result.

'''
    numeric_text+=numeric_summary.to_string(index=False)+'\n'
    (output/'numeric_diagnostic_report.md').write_text(numeric_text,encoding='utf-8')
    (output/'README.md').write_text('''# Phase 3B exploratory analysis

Run `python research/scripts/analyze_phase3b.py --results PATH_TO_ZIP_OR_RUN_DIRECTORY --output research/analysis/phase3b` from repository root. No model weights, GPU or dataset download is used. The input is read only. Integrity failure returns exit code2 and blocks policy selection. Use `--integrity-only` for validation alone.

Primary policy comparison uses nonzero cloud levels (180 repeated question-conditions from10 scenes and30 distinct questions); the complete failure table also includes target zero. P2/P3 choices use leave-one-scene-out development folds, not random question splits. All results remain exploratory. CIs cluster by scene and retain repeated conditions, and condition on selected fold actions. No method is deployed.

Read policy_configuration.json before interpreting cost or risk. P4/P5 agreement may be confidently wrong: inspect false agreement in analysis_summary.json. Zero coverage has undefined selective risk. Risk–coverage integration is limited to the observed attainable interval of the nested P5 gate family; it is not full AURC and must not be compared to a full-domain AURC. Separate policies are plotted as points, never connected into an invented ranking curve.

Images and predictions retain the original run's relative paths; resolve them inside the supplied ZIP/run, not against this output folder. source_file_hashes.json records every input file. CSV rows and figure selection are deterministic. Figure metadata timestamps are omitted; rendering may vary across Matplotlib versions.

E0 cloud detection; E1 cloud-affected VQA; E2 reconstruction versus no reconstruction; E3 bi-temporal change; E4 abstention/risk–coverage; E5 dynamic tool-injection ablation. Phase3B prepares E4 and does not replace E3.
''',encoding='utf-8')
