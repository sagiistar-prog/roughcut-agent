# 插件使用

插件清单位于 .codex-plugin/plugin.json，入口 Skill 为 roughcut-planner。安装到支持该插件清单的宿主后，由宿主读取 Skill 并调用仓库内脚本；本地 CLI 与网页无需插件宿主即可使用。未声称所有宿主安装都已验证。

```bash
python -m pip install -r requirements-plugin.txt
python scripts/plugin_run.py --input examples/plugin-input.json --output-dir output/plugin-01
python scripts/review_server.py
```

将 output/plugin-01/result.json 导入审核台。输入/输出 JSON Schema 位于 schemas/。兼容 schema_version 1.0，并新增 candidates，涵盖初选和未选候选及源时长；timeline 只包含初选。错误返回结构化 JSON 和非零退出码。CLI 不进行模型推理或媒体读取。

需转写和渲染时，按 README 逐阶段运行。转写另外安装 requirements-asr.txt；渲染要求 FFmpeg、已审核 CSV 与 --reviewed。浏览器导出不是渲染完成。技能名称中的 Planner 表示负责组织和审核工作流，不声称能够自动评判视频审美。
