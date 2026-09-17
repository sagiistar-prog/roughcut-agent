# RoughCut Review · Plugin 0.2

从素材索引生成可人工复核的粗剪时间线。插件包装已有本地能力，统一输入、输出和错误约定。

## Try the fictional example

```bash
python -m pip install -r requirements-plugin.txt
python scripts/plugin_run.py --input examples/plugin-input.json
python -m unittest discover -s tests -v
```

默认仅向 stdout 返回 JSON，不写文件。保存时显式指定新的子目录：

```bash
python scripts/plugin_run.py --input examples/plugin-input.json --output-dir output/first-review
```

输出包含 `result.json`、`result.md` 和 `timeline.csv`。同名目录已存在时返回错误，不覆盖。旧命令的 `--dry-run` 表示离线演示，**仍会写入其指定的 output 文件**。

## Structure and contract

- `.codex-plugin/plugin.json`：插件身份、版本、能力说明与 Skill 路径。
- `skills/roughcut-planner/SKILL.md`：使用场景、操作流程与边界。
- `schemas/input.schema.json` / `schemas/output.schema.json`：JSON Schema 2020-12。
- `scripts/plugin_run.py`：校验输入、调用现有核心函数、校验输出。
- `examples/plugin-input.json`：可复现虚构输入。
- `tests/`：契约与缺陷回归检查。

`status: ok` 返回 `mode`、`result`、`warnings`；错误返回 `status: error` 与 `error.code/message`，进程退出 2。未知字段和超过 1MB 的输入会被拒绝。stdout 不混入运行日志。

## Capability boundary

- 仅依据输入索引和规则排序，不读取媒体、不运行 ASR、不渲染视频。
- 质量与语义分数来自输入，不代表本次进行了模型评估。

插件清单与 CLI 经本地验证；未宣称已发布到插件商店或完成 Codex App 安装验收。仓库就是插件根目录，不额外修改个人插件市场配置。

## Product decision

时间线先于渲染，风险说明先于自动执行。非法时间码不进入剪辑，反馈必须实际影响下一次片段长度。

## Next evaluation

用真实目标用户的脱敏任务验证任务完成率、结果可复核性和人工修改量。尚未采集这些用户结果，不能把本地测试通过写成用户增长、效率提升或模型质量指标。
