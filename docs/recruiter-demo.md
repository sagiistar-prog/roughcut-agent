# Recruiter Demo: Safe Timeline Generation

This demo shows how to inspect RoughCut Agent's timeline generation logic without using any real video assets.

## What This Demo Does

- Reads only the desensitized sample index in `examples/sample_material_index.csv`.
- Reads the public editing rules in `configs/editing_rules.yaml`.
- Reads the lightweight preference memory in `configs/user_preferences.yaml`.
- Generates a reviewable timeline CSV at `examples/generated_timeline_review.csv`.

## What This Demo Does Not Do

- It does not read `raw/`.
- It does not read `work/`, `output/`, `.venv/`, or `raw_duplicates_quarantine/`.
- It does not render video.
- It does not generate `final_rough_cut.mp4`.
- It does not require real private media files.

## Run the Safe Demo

```bash
python scripts/stage2_generate_timeline.py --input examples/sample_material_index.csv --output examples/generated_timeline_review.csv --rules configs/editing_rules.yaml --preferences configs/user_preferences.yaml --dry-run
```

## What to Review

Open `examples/generated_timeline_review.csv` and check:

- selected clip order
- adjusted `start_time` and `end_time`
- `duration_seconds`
- transcript text
- clip role
- selection reason
- `risk_note` for uncertain or unsafe cuts

This is the safest way for a recruiter or interviewer to understand the Agent's decision logic without receiving real video material.