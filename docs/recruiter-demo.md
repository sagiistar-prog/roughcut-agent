# 不使用私人素材的演示

安装 requirements-plugin.txt 后运行：

```bash
python scripts/review_server.py
```

打开本地 8890 端口，点击“打开示例”，选择/恢复片段、调整顺序和切点，尝试撤销与保存会话。示例仅为虚构索引，没有视频；不要声称试听过它。

命令行也可查看规划结果：

```bash
python scripts/stage2_generate_timeline.py --input examples/sample_material_index.csv --dry-run
```

dry-run 只打印规划与排除理由，不写文件、不读取视频。生成实体文件必须选择 output/ 中的新路径。

需要复现真实媒体技术测试时，先安装 FFmpeg 和 requirements-asr.txt；Windows 使用系统 TTS，Linux 需 espeak：

```bash
python scripts/create_acceptance_media.py --directory output/demo-media
python scripts/stage1_transcribe_index.py --raw-dir output/demo-media --output output/demo-media/material_index.csv --model tiny.en --language en
python scripts/asr_acceptance.py --report output/demo-media/material_index.asr.json --output output/demo-media/acceptance.json
python scripts/stage2_generate_timeline.py --input output/demo-media/material_index.csv --output output/demo-media/initial/timeline_review.csv
```

导入 JSON 到审核台后，关联刚生成的视频、试听和调整，再按 README 导出和渲染。生成器先写 timeline_review.csv，再生成自己创作的测试视频；不使用、扫描或复制私人媒体。
