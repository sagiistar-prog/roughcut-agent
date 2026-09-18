# 把转写带到剪完的时间线上

剪辑者调换片段顺序、缩短入出点后，原始字幕的时间不再对应成片。0.4 增加可选字幕交付，使用已有 ASR 词时间戳，不重复识别或翻译，不把整段转写均匀铺满切片。

先按 README 完成转写和时间线审核，再运行：

```bash
python scripts/stage3_render_rough_cut.py --timeline output/session-01/reviewed/timeline_review.csv --output-dir output/session-01/render-with-captions --reviewed --captions-from output/session-01/material_index.asr.json
```

得到 MP4、同名 SRT 和 VTT、`captions.json`、原有渲染报告。字幕以独立文件交给后续剪辑工具修改，不烧进画面。没有合格词时不生成空字幕假装成功；报告列明缺口。

## 规则与取舍

- 先校验 ASR 源文件摘要与当前素材一致，再使用词时间戳。旧视频换了内容必须重新转写。
- 按审核 CSV 的顺序，利用每个实际渲染片段的容器时长累计偏移，而不是假设所有切片恰好等于输入秒数。成片与映射保留在 `render.json`。
- 切点穿过一个词时，省略这个词并记录源时间与原因；不显示只剩半个发音的完整词。保留完全处于选定区间的词。
- 没有词时间戳时留空并报告，不用整段文字伪造精确时间。零时长词也省略并报告。
- 默认按停顿、句尾、42 字符或 4 秒分组；单个过长的词不机械切开，记录可读性风险。阈值来自 `configs/editing_rules.yaml`，属于启发式，未经过用户效果验证。
- 字幕使用原始词识别结果；CSV 中的整段转写修改与规则替换不自动套到词级。每次字幕导出都标记 `needs_review`，需逐段试听校对；`--reviewed` 仅确认时间线。

## 开源依据

复用 [faster-whisper 的词时间戳](https://github.com/SYSTRAN/faster-whisper#word-level-timestamps) 和 [FFmpeg concat 的时长与时间戳规则](https://ffmpeg.org/ffmpeg-formats.html#concat)。本项目新增的是源文件校验、剪辑时间映射、字幕分组和可复查风险记录，没有自研语音识别模型。

技术验证使用原创合成媒体与确定性边界样例。自然中文识别质量、真实剪辑者效率与专业字幕可读性仍未验证。

## 2026-09-18 技术验收

- 30 项 Python 测试通过，包含 10 项字幕边界用例，以及真实 FFmpeg 混合素材渲染、源摘要检查、SRT 解析和禁止覆盖。
- 实际执行 faster-whisper 1.2.1 / tiny.en / CPU int8，识别两段原创英文合成语音。倒序剪辑后得到 18.203333 秒视频和 8 条字幕，SRT 与 VTT 的 8 个解析包都与映射时间一致，原始素材摘要不变。
- 一处模型输出的零时长词被省略，并在风险清单中保留。这是可见缺口，不算识别完整性通过。
- 本轮未修改审核台视觉；既有浏览器验收由发布 CI 回归。自然中文、多说话人、实际业务素材与剪辑者效果未验收。

[结构契约](../schemas/captions.schema.json) | [真实模型技术记录](caption-acceptance-04.json)

重跑原创合成素材联调：

```bash
python scripts/create_acceptance_media.py --directory output/caption-demo
python scripts/stage1_transcribe_index.py --raw-dir output/caption-demo --output output/caption-demo/material_index.csv --model tiny.en --language en
python scripts/caption_acceptance.py --asr output/caption-demo/material_index.asr.json --output-dir output/caption-check
```

联调脚本按倒序构造测试时间线，适用于生成器的两段固定原创测试素材，不替代真实素材的人工作品审核。
