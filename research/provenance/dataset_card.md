---
license: cc-by-4.0
configs:
- config_name: default
  data_files:
  - split: validation
    path: data/validation-*
dataset_info:
  features:
  - name: image
    dtype: image
  - name: question
    dtype: string
  - name: answer
    dtype: string
  splits:
  - name: validation
    num_bytes: 174133383
    num_examples: 2000
  download_size: 174052999
  dataset_size: 174133383
task_categories:
- visual-question-answering
tags:
- remote-sensing
- rsvqa
- vqa
size_categories:
- 1K<n<10K
language:
- en
---
A 2k subset of the validation split of the RSVQA LR dataset ported to HF for ease-of-use in quick remote sensing VQA evaluation.
For more information and attribution please refer to the original dataset: https://rsvqa.sylvainlobry.com/#dataset