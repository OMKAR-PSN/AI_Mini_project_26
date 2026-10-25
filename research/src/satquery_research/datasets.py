"""Pinned HF dataset ingestion and scene-grouped, auditable rosters."""
from pathlib import Path
import numpy as np
from .manifests import image_digest, atomic_json, write_csv
from .metrics import answer_category, numeric_value
from .scene_split import split_scenes, select_roster

def prepare(config, folder):
    from datasets import load_dataset
    folder = Path(folder)
    spec = config['dataset']
    data = load_dataset(spec['id'], revision=spec['revision'], split=spec['split'],
                        cache_dir=config['cache_dir'], token=False)
    required = {'image', 'question', 'answer'}
    if not required.issubset(data.column_names):
        raise ValueError(f'Missing dataset columns: {required-set(data.column_names)}')
    rows, images = [], {}
    for index, item in enumerate(data):
        image = item['image'].convert('RGB')
        array = np.array(image)
        sid = 'scene_' + image_digest(array)
        path = folder / 'originals' / (sid + '.png')
        if sid not in images:
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path)
            images[sid] = path.relative_to(folder).as_posix()
        native_id = item.get('question_id', item.get('id'))
        qid = str(native_id) if native_id is not None else f"{spec['revision']}:{spec['split']}:{index}"
        rows.append(dict(scene_id=sid, question_id=qid, native_question_id=native_id,
            row_index=index, question=str(item['question']), answer=str(item['answer']),
            category=answer_category(item['answer']), original_path=images[sid],
            width=image.width, height=image.height))
    if len({r['question_id'] for r in rows}) != len(rows):
        raise ValueError('Question identifiers are not unique')
    split = split_scenes(images, config['split_seed'], config['development_fraction'])
    for row in rows: row['partition'] = split[row['scene_id']]
    selection = config['selection']
    selected = select_roster(rows, selection['partition'], selection['max_scenes'],
                             selection['questions_per_scene'], config['roster_seed'])
    if not selected: raise ValueError('Empty selected roster')
    write_csv(folder/'roster_all.csv', rows)
    write_csv(folder/'roster_selected.csv', selected)
    audit = [dict(r, review_status='unreviewed; label retained') for r in rows
             if numeric_value(r['answer']) is not None and abs(numeric_value(r['answer'])) >= 100]
    write_csv(folder/'annotation_review.csv', audit)
    atomic_json(folder/'dataset_audit.json', dict(dataset=spec, columns=data.column_names,
        rows=len(rows), unique_scenes=len(images), selected_scenes=len({r['scene_id'] for r in selected}),
        selected_questions=len(selected), sizes=sorted({(r['width'],r['height']) for r in rows}),
        partitions={p:sum(v==p for v in split.values()) for p in ['development','test']},
        roster_origin='New experimental roster; previous pilot CSV not found',
        id_policy='Native ID if present; otherwise pinned revision:split:row index',
        suspected_numeric_annotations=len(audit), exclusion_policy='No labels altered or excluded'))
    return rows, selected
