# Video Auto Editor Skill

Use this skill when the user wants to run or improve the RoughCut Agent workflow for short videos, talking-head footage, transcript indexing, timeline generation, rough-cut rendering, subtitle configuration, or feedback-based editing preferences.

## Goal

Turn raw local talking-head or short-video footage into a reviewable rough cut through a safe, staged workflow.

## Safety Rules

1. Do not delete original media.
2. Do not upload raw media.
3. Do not process `raw_duplicates_quarantine/` unless the user explicitly asks for an audit.
4. Do not generate a video unless `timeline_review.csv` exists.
5. Do not create results that cannot be reviewed.
6. Keep intermediate files and reports for every stage.
7. Do not write local absolute paths or private data into committed files.

## Stage 1: Material Deduplication

Run:

```bash
python scripts/dedupe_raw_videos.py --raw-dir raw --output output/dedupe_report.csv
```

This computes file hashes and writes a dedupe report. By default it does not move or delete anything.

Only use quarantine mode when the user clearly wants duplicates isolated:

```bash
python scripts/dedupe_raw_videos.py --raw-dir raw --output output/dedupe_report.csv --quarantine-duplicates
```

## Stage 2: Speech Transcription

Run:

```bash
python scripts/stage1_transcribe_index.py --raw-dir raw --output output/material_index.csv
```

The script may use a local ASR dependency such as `faster-whisper` when installed. If ASR is unavailable, it should still produce a reviewable index and mark uncertainty in `risk_note`.

## Stage 3: Material Indexing

The output `material_index.csv` should include source file, segment start/end, transcript, subtitle fields, quality indicators, and risk notes.

The index is the main bridge between AI understanding and human review.

## Stage 4: Timeline Generation

Run:

```bash
python scripts/stage2_generate_timeline.py --material-index output/material_index.csv --output output/timeline_review.csv
```

The generator reads:

- `configs/editing_rules.yaml`
- `configs/user_preferences.yaml`
- `material_index.csv`

It outputs a reviewable timeline with:

- `order`
- `source_file`
- `start_time`
- `end_time`
- `duration_seconds`
- `transcript`
- `role`
- `reason`
- `risk_note`

## Stage 5: Rough Cut Rendering

Run:

```bash
python scripts/stage3_render_rough_cut.py --timeline output/timeline_review.csv --output-dir output
```

This uses FFmpeg to cut selected segments and concatenate them into `final_rough_cut.mp4`. It must not modify original media.

## Stage 6: User Feedback Learning

Run:

```bash
python scripts/apply_user_feedback.py --feedback output/feedback.csv
```

For demo data:

```bash
python scripts/apply_user_feedback.py --feedback examples/sample_feedback.csv
```

This does not train a model. It summarizes feedback into `configs/user_preferences.yaml`, so future timeline generation can reflect user preferences.

## Editing Principles

These principles must stay aligned with `configs/editing_rules.yaml`.

```yaml
editing_principles:
  rhythm:
    description: "剪辑要有节奏，不要机械拼接。"
    rules:
      - "避免把两句话硬贴在一起。"
      - "相邻片段之间如果语气变化大，需要保留呼吸空间。"
      - "优先选择表达完整、起承转合清楚的片段。"

  breathing_room:
    description: "剪切点要给人声留气口。"
    rules:
      - "裁切起点尽量不要正好卡在人声开始处。"
      - "默认把 start_time 向前延伸 0.4 到 0.6 秒。"
      - "如果前方有杂音或其他人声，则不强行前延。"
      - "裁切终点默认向后延伸 0.2 到 0.4 秒，避免句尾被切断。"

  continuity:
    description: "保证语义连续。"
    rules:
      - "不要把两个语义不连续的句子直接拼接。"
      - "如果片段之间缺少承接，需要在 risk_note 中标记。"
      - "优先保持同一主题片段内部连续。"

  quality:
    description: "保证基础可看性。"
    rules:
      - "跳过明显空白、跑题、重复、音量过低、画面严重晃动的片段。"
      - "识别文字不确定时不要强行判断，要标记人工复核。"
```

Operational rules:

- Preserve rhythm and breath.
- Do not hard-cut two unrelated sentences together.
- Avoid cutting exactly at speech onset.
- Extend `start_time` by about 0.5 seconds when safe.
- Extend `end_time` by about 0.3 seconds when safe.
- Do not force pre-roll when there is noise, overlapping speech, or unrelated content before the segment.
- Write `risk_note` for uncertain recognition, semantic jumps, or unsafe cut points.

## Preference Memory Layer

RoughCut Agent does not train a large model. It keeps a lightweight preference memory in `configs/user_preferences.yaml`:

```yaml
user_preferences:
  pacing:
    preferred_total_duration_seconds: 150
    max_single_clip_seconds: 18
    prefer_shorter_intro: true
  cut_padding:
    start_padding_seconds: 0.5
    end_padding_seconds: 0.3
  content_style:
    prefer:
      - "观点明确"
      - "信息密度高"
      - "表达完整"
      - "语气自然"
    avoid:
      - "重复铺垫"
      - "突然切入人声"
      - "句尾被切断"
      - "语义跳跃"
  learned_from_feedback:
    - date: "2026-05-14"
      feedback: "不要把两句话贴太紧，开头要留一点气口。"
      applied_rule: "所有裁切起点默认向前延伸 0.5 秒，除非前方有噪声。"
```

When applying feedback, append a new memory item instead of replacing older learning.
