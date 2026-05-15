# Workflow

RoughCut Agent 使用分阶段工作流。每个阶段都生成可复查文件，避免直接产出无法解释的视频结果。

## 目录约定

- `raw/`：本地原始素材，不提交。
- `raw_duplicates_quarantine/`：重复素材隔离目录，不提交。
- `work/`：临时文件，不提交。
- `output/`：运行结果，不提交。
- `configs/`：剪辑规则和用户偏好。
- `examples/`：脱敏示例数据。

## 阶段一：素材去重

```bash
python scripts/dedupe_raw_videos.py --raw-dir raw --output output/dedupe_report.csv
```

脚本会计算视频哈希并输出重复报告。默认只报告，不移动、不删除原始素材。

如需隔离重复项，需要显式传入：

```bash
python scripts/dedupe_raw_videos.py --raw-dir raw --output output/dedupe_report.csv --quarantine-duplicates
```

隔离是移动重复副本，不是硬删除。脚本不会处理 `raw_duplicates_quarantine/` 中已有文件。

## 阶段二：语音转写与素材索引

```bash
python scripts/stage1_transcribe_index.py --raw-dir raw --output output/material_index.csv
```

如果本地安装了 `faster-whisper`，脚本会尝试使用它做语音识别。没有安装时，脚本仍会生成可复查索引，并在 `risk_note` 中标注需要补齐转写。

素材索引用于记录：

- 来源视频。
- 视频总时长。
- 片段开始和结束时间。
- 转写文本。
- 中英字幕字段。
- 质量分。
- 语义分。
- 噪音、重叠人声、跑题等风险。

## 阶段三：时间线生成

```bash
python scripts/stage2_generate_timeline.py --material-index output/material_index.csv --output output/timeline_review.csv
```

脚本会读取：

- `output/material_index.csv`
- `configs/editing_rules.yaml`
- `configs/user_preferences.yaml`

并输出：

- `order`
- `source_file`
- `start_time`
- `end_time`
- `duration_seconds`
- `transcript`
- `role`
- `reason`
- `risk_note`

剪切点会按气口规则调整：默认 `start_time` 向前扩展 0.5 秒，`end_time` 向后扩展 0.3 秒，同时不小于 0，也不超过原视频时长。

## 阶段四：粗剪合成

```bash
python scripts/stage3_render_rough_cut.py --timeline output/timeline_review.csv --output-dir output
```

脚本必须先读取 `timeline_review.csv`，再调用 FFmpeg 裁切和拼接。它不会修改原始素材。

输出：

- `output/final_rough_cut.mp4`
- `output/edit_report.md`
- `output/segments/` 中间片段

## 阶段五：用户反馈学习

```bash
python scripts/apply_user_feedback.py --feedback output/feedback.csv
```

如果只是体验示例，可以运行：

```bash
python scripts/apply_user_feedback.py --feedback examples/sample_feedback.csv
```

脚本会把反馈归纳追加到 `configs/user_preferences.yaml`。下一次运行 `stage2_generate_timeline.py` 时，会读取这些偏好并影响排序和剪切点。

