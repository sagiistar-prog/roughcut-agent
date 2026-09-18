# 技术验收 2026-09-18

渲染前核对所有素材、时间范围、时长与唯一序号；缺失素材拒绝整次渲染。禁止输出目录逃逸与覆盖旧成片。使用本机FFmpeg实际将4秒合成素材裁为2秒并合并，不处理私人素材。此检查不验证ASR准确率或剪辑审美。

## 复现

`python -m pip install -r requirements-plugin.txt`

`python -m unittest discover -s tests -v`

`python scripts/plugin_run.py --input examples/plugin-input.json`

所有示例为虚构测试资料。没有真实用户参与，本轮仅为技术验收。
