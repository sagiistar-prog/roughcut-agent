# Maintenance log

## 0.2.0 — 2026-09-17

- Added a versioned Codex plugin manifest with the existing Skill.
- Added validated JSON input/output, a fictional input fixture and an explicit artifact export path.
- Documented the actual offline capability and its limitations.
- Added executable contract and regression checks; see `tests/`.
- Product decision: 时间线先于渲染，风险说明先于自动执行。非法时间码不进入剪辑，反馈必须实际影响下一次片段长度。

The version labels a repository iteration, not a hosted product launch or a marketplace release.

## 2026-09-17 Product reliability release

可审核的粗剪计划。补齐产品案例、能力证据、指标契约、开源取舍与持续检查。验证范围和未验收项见 docs/validation.md。
# 0.3.0

- 实际接入本地 faster-whisper，保留原转写、词时间戳、识别信号与源哈希；移除假质量分及占位识别。
- 完整片段初选、所有排除理由、同源防重复和相邻气口约束。
- 新增本地审核台，支持试听、选择恢复、顺序、切点、撤销、会话恢复及 CSV。
- 明确审核后渲染，规范混合视频与音轨，保持原素材，拒绝覆盖。
- 增加真实媒体、ASR、桌面/手机、错误恢复和无障碍技术验收；撤下无法追溯的效果数字。
