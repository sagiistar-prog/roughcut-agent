---
name: roughcut-planner
description: Prepare, review and render a local talking-head rough cut. Use for timestamped transcription, reversible clip selection, safe cut points, reviewed FFmpeg exports or editable subtitles aligned to a cut.
---

# RoughCut Planner

Turn local speech footage into a reviewable initial selection. Run commands from the plugin repository root. Read README for platform setup, docs/review-design.md for decision boundaries, and schemas/input.schema.json for the JSON interface.

## Choose the smallest useful entry

- User has no index: install requirements-asr.txt only when transcription is requested; FFmpeg/ffprobe must be available. Run stage1_transcribe_index.py on the user's explicitly selected directory inside this repository.
- User has a CSV: run stage2_generate_timeline.py --input <CSV> --output output/<new-session>/initial/timeline_review.csv. Do not claim to have transcribed it.
- User has structured material rows: run plugin_run.py --input <JSON> --output-dir output/<new-session>. This entry is timeline_only; it never reads media or invokes a model.
- User wants review: start review_server.py, open loopback port 8890, import generated JSON. Source video is attached per file by the user. Review the exact input/output points and context, not merely the transcript.
- User explicitly asks to render a reviewed plan: use stage3_render_rough_cut.py --timeline output/<session>/reviewed/timeline_review.csv --output-dir output/<session>/render --reviewed.

## What the stages actually do

Transcription uses faster-whisper, CPU int8 by default. First model acquisition needs network; use --local-files-only with cached models for offline operation. Preserve original transcript, word timings, language, avg_logprob and no_speech_prob. These are recognition observations, never aesthetic or semantic-quality scores. Review missing/no-speech/error source statuses before continuing.

Selection preserves source input order. It does not invent roles, quality scores or topic relevance. Complete ASR segments remain intact even if longer than preferred, with a risk note. ASR boundaries are not guaranteed sentence boundaries. Duration budget, clip-count limits, flagged duplicates and overlapping source ranges produce explicit exclusions; valid excluded candidates remain recoverable in the review UI. Padding does not consume neighboring transcript intervals.

Review supports keep/remove, restore, move, exact input/output points, local segment playback, undo, session JSON and timeline CSV export. Changes clear review acknowledgement. Saving a session does not persist media or autoplay anything.

Rendering validates ranges and real source duration, sorts contiguous order, normalizes dimensions/frame rate/audio, preserves originals and refuses overwriting old artifacts. The --reviewed flag is an acknowledgement, not proof that a human listened. Never claim it is proof.

For subtitle drafts, add `--captions-from output/<session>/material_index.asr.json` to the reviewed render command. Read `docs/captions.md` first. The original ASR source hashes must match the selected media. Word timestamps are mapped to measured rendered-segment durations in the final order. Partial-cut words, zero-duration words and missing timing remain gaps with risk records, never invented timing. SRT and VTT are sidecars, not burned-in captions; both require listening and text review. Read captions.json against schemas/captions.schema.json and report any gaps. Whole-transcript corrections in CSV or configured replacements do not propagate to original ASR words. Do not claim these drafts contain the user's corrections or have been approved.

## Protect the user's material

Never delete, upload or silently move source media. Do not read quarantine. Never generate a video without timeline_review.csv. Missing dependencies must produce an actionable setup step, not fake output. Never insert placeholder transcript segments or claim a model evaluated unmeasured properties. Record uncertainties in risk_note and preserve intermediate artifacts under output/. Only use source files the user selected; no broad user-directory scan.

Optional deduplication is report-only by default. Moving duplicates requires the user's explicit instruction. Feedback updates explicit preferences; it is not model learning.

## Verify before handoff

Check selected count, excluded reasons, duration, source preservation and actual output streams. A successful JSON schema check is not an acceptable-video judgment. Report model/setup prerequisites and any failed sources. Use the original synthetic fixture generator and tests for technical regression, not private footage or invented business results.
