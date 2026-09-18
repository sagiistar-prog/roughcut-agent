# 开源选择

选择依据是任务匹配、可测试性、许可证和维护成本。未以 star 数量替代质量判断。2026-09-18 查阅官方仓库和接口。

| 上游 | 采用方式 | 理由与边界 |
|---|---|---|
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 实际依赖 1.2.1，MIT | CTranslate2 本地 CPU int8、VAD、词时间戳；每批复用模型。ASR 信号不当作剪辑质量分。 |
| [FFmpeg](https://ffmpeg.org/ffmpeg-filters.html#concat) | 调用用户安装的 CLI | 拼接前显式统一分辨率、帧率、像素格式和音轨。未分发二进制；FFmpeg 构建及 libx264 许可证需由分发者按实际构建遵守。 |
| [Playwright](https://github.com/microsoft/playwright) | 测试依赖，Apache-2.0 | 真实浏览器播放、输入恢复、下载、手机宽度回归。 |
| [axe-core](https://github.com/dequelabs/axe-core) | 测试依赖，MPL-2.0 | 自动无障碍检查；不等于完整认证。 |
| [jsonschema](https://github.com/python-jsonschema/jsonschema) | 实际依赖，MIT | 宿主输入输出校验；不替代语义审核。 |

审核台使用原生 video、File API 与本地静态服务，未复制其他编辑器 UI。保留/撤销借鉴非破坏性剪辑的通用交互，避免为少量操作引入完整剪辑器框架。Impeccable 指导字幕校对表式的信息层级、蓝紫灰与可逆状态设计。

上游代码、模型能力和本项目贡献分别标明。本项目贡献是用户任务定义、阶段边界、审核体验、规则约束、集成与可复现验收；不称 Whisper 为自研模型。完整模型文件、源媒体和运行输出不提交。
