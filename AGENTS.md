# AGENTS.md

本项目是 RoughCut Agent，一个面向短视频和口播素材的 AI 粗剪工作流 Agent。Codex 在本仓库中工作时，请遵守以下规则。

## 默认沟通

1. 默认使用中文解释。
2. 面向用户时优先说明产品逻辑、处理结果和风险点，避免不必要的底层细节。

## 素材安全

1. 所有脚本都必须保护 `raw/` 原始素材。
2. 禁止硬删除素材。
3. 不上传、不复制、不提交真实视频、音频、字幕原件或隐私数据。
4. 不处理 `raw_duplicates_quarantine/` 隔离目录中的素材，除非用户明确要求做审计。
5. 不在文档或示例中写入用户本地绝对路径。

## 剪辑逻辑

1. 修改剪辑逻辑时，先更新 `configs/editing_rules.yaml` 和相关文档，再改脚本。
2. 任何生成视频的操作都必须先有 `timeline_review.csv`。
3. 遇到识别不确定、语义跳跃、噪音、重叠人声或剪切点风险时，写入 `risk_note`，不要伪造确定判断。
4. 不生成无法复查的结果。每一步都要保留中间文件或报告。

## 输出位置

1. 所有运行产物都写入 `output/` 目录。
2. 临时处理文件写入 `work/` 目录。
3. `raw/`、`raw_duplicates_quarantine/`、`work/`、`output/` 均不应提交到 GitHub。
## 作品集审查规则

1. 以后检查作品集时，优先运行 `scripts/portfolio_audit.ps1`。
2. 禁止扫描项目目录之外的文件。
3. 禁止扫描整个用户目录。
4. 禁止读取 `raw/`、`work/`、`output/`、`.venv/`、`raw_duplicates_quarantine/`。
5. 禁止把 token、真实素材、`output/` 成片提交到 GitHub。
6. 审查脚本必须只基于 `git ls-files` 返回的已跟踪文件做隐私和大文件检查。
