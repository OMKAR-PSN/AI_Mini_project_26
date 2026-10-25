# Real-cloud annotation intake (no labels supplied)
Place RGB observations in images/ and aligned binary uint8 PNG masks (0 clear, 255 cloud) in masks/.
Maintain annotations.csv with scene_id,image_path,mask_path,annotator,reviewer,source_license,acquired_at,mask_policy,uncertainty_notes.
Record ambiguous boundaries and independent review. Never substitute synthetic masks for real labels.
This intake is separate from the synthetic E0 runner; no real-cloud evaluation is claimed.
