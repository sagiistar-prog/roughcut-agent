---
name: RoughCut 审核台
description: 以连续转写、精确时间和可逆选择组织本地片段审核。
colors:
  paper: "#f3f4f7"
  surface: "#fff"
  ink: "#222a40"
  muted: "#596176"
  line: "#d8dce6"
  blue: "#284eab"
  purple: "#584aa3"
  selection: "#eeebf9"
  button-hover: "#e9edf7"
  button-hover-border: "#9ca8c7"
  button-disabled: "#ebeef4"
  button-disabled-text: "#667086"
  primary-hover: "#1e3f91"
  primary-disabled: "#e1e5ef"
  primary-disabled-text: "#606b83"
  error: "#9b263c"
  preview: "#e3e6ef"
  video: "#1b2131"
  text-selection: "#d8dff8"
  scrollbar: "#929bb4"
typography:
  headline:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "clamp(26px, 3.2vw, 42px)"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  title:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "19px"
    fontWeight: 650
    lineHeight: 1.6
  body:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  transcript:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.7
  utility:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
  brand:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.6
    letterSpacing: "-0.02em"
rounded:
  control: "7px"
  surface: "12px"
  row: "0"
spacing:
  tight: "4px"
  compact: "8px"
  control-gap: "10px"
  small: "12px"
  medium: "16px"
  row: "20px"
  panel: "24px"
  section: "32px"
  page: "40px"
  large: "48px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "9px 16px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-primary-disabled:
    backgroundColor: "{colors.primary-disabled}"
    textColor: "{colors.primary-disabled-text}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "9px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.button-hover}"
  button-secondary-disabled:
    backgroundColor: "{colors.button-disabled}"
    textColor: "{colors.button-disabled-text}"
  time-input:
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
    width: "100%"
  transcript-row:
    rounded: "{rounded.row}"
    padding: "20px 10px"
  transcript-row-current:
    backgroundColor: "{colors.selection}"
  preview-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
    padding: "{spacing.panel}"
  timeline-item:
    backgroundColor: "{colors.selection}"
    textColor: "{colors.purple}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 16px"
  local-error:
    textColor: "{colors.error}"
  brand-link:
    textColor: "{colors.ink}"
    typography: "{typography.brand}"
---

# Design System: RoughCut 审核台

## Overview

**Creative North Star: "字幕校对表"**

冷灰底承接连续转写，白色工作面容纳试听和切点输入；蓝色用于推进操作，紫色用于辨认当前片段。界面把文字、时间和决定放在一起，让用户逐句阅读、试听与修改。它的细节来自校对工作的对齐和留白，不模拟纸张纹理或机械设备。

系统字体、原生复选框、数字输入、视频控件和浏览器确认框构成实际交互语言，无外部字体下载。视觉状态应始终能对应真实审核状态；示例标明虚构，导出 CSV 后仍说明尚未生成视频。

**Key Characteristics:**

- 连续文本行与精确时间优先于装饰。
- 冷灰底、白色工作面、蓝色动作与紫色当前态各有职责。
- 通过色面和细线分层，没有阴影与无限动画。
- 就地反馈和可恢复操作支撑持续审核。

本记录从 `web/index.html`、`web/review.css`、`web/review.js` 提取，以最终代码为真值。具体审核台的 Operate 模式、任务路径和方向过程保留在 `docs/review-design.md`。查看过 `.impeccable/review/desktop.png` 与 `mobile.png`；截图用于核对已实现结构，不代替运行验收。`docs/design-review.md` 最终的 `ship` 仅表示初审 F1/F2/F3 已 resolved，不是整站、真实媒体、转写、渲染或发布验收。

## Colors

蓝紫是控制与定位的细节，冷灰与白色承担大面积阅读环境；具体值以 frontmatter 为准。

### Primary

- **审核蓝（blue）**：导入与导出主按钮、链接、原生复选框。`primary-hover` 加深主按钮；禁用状态使用独立的灰蓝背景与文字。

### Secondary

- **定位紫（purple）**：键盘焦点、当前时间线边框、已选带文字，以及空态点阵。
- **浅紫选择面（selection）**：当前候选行和全部已选时间线项的背景。已选带中哪一项是当前片段，由额外边框区别。

### Neutral

- **冷灰纸面（paper）与白工作面（surface）**：分别承载页面和试听容器、欢迎空态、普通按钮；`line` 分隔连续内容并描绘控件。
- **深灰正文（ink）与蓝灰辅助字（muted）**：正文和说明层级；错误消息改用 `error`，成功消息沿用普通文本而不增加绿色状态色。
- **预览灰（preview）与视频深底（video）**：前者是待关联媒体区域，后者承接原生视频画面。
- `button-hover`、`button-hover-border`、普通与主按钮的 disabled token、`text-selection` 和 `scrollbar` 保留代码中的实际交互颜色，不扩展为通用装饰色阶。

**The State Color Rule.** 蓝色表达操作，紫色表达当前定位；错误同时写出问题与恢复方式，不仅改变颜色。

Sidecar 的八级 OKLCH 色阶是查看面板用的派生色阶，未在产品中使用，不是新增的实装 token。

## Typography

全部角色使用 frontmatter 的系统 UI 字体栈。没有加载独立展示字体或等宽字体；数字对齐由 `font-variant-numeric: tabular-nums` 实现，应用于片段时间、切点输入、总时长和已选带。

- **Headline**：页标题使用弹性字号与紧凑行高；手机断点内改为固定字号（29px）。
- **Title**：区域标题和项目名称，继承正文行高。
- **Body**：正文与常规按钮；段落最大宽度（70ch）。
- **Transcript**：候选正文以更疏的行高连续阅读；长词允许换行，不用省略号隐藏待审核的正文。
- **Utility / Label**：前者承载状态和确认说明；后者承载时间、来源注释和小操作。来源文件名为独立辅助文字（13px）。
- **Brand**：仅品牌入口加重并收紧字距；手机字号降为（20px），附属“审核台”文字保持轻量。

**The Timing Rule.** 正文保持自然系统字形；需要比较的数字启用等宽数字，不把整个审核台切换成代码编辑器字体。

## Layout

页面容器与页头共用最大宽度（1360px），居中排布。桌面主区域使用上下（48px）、左右（40px）的内边距；编辑区为 `minmax(0,1.25fr) minmax(0,1fr)` 双列，列间（32px）。候选行采用复选框、可变宽正文、移动按钮三列；试听区域在桌面粘于顶部（24px），媒体保持（16:9）。

在宽度不超过（800px）时，页头和主内容改用左右（20px）的内边距，主内容上部（32px）；介绍、工具栏和导出操作改为纵向。编辑区单列、间隔（28px），试听区域取消粘附并使用（20px）内边距。DOM 的候选、试听、已选带阅读顺序不变；手机点选片段后跳转试听，提供返回当前片段的动作。

已选带在容器内横向滚动，每项 `flex: 0 0 144px`，间隔（8px）。带中文字单行省略，候选正文与源文件名允许换行。摘要、帮助和风险依据使用原生 `details` 渐进展开；无独立侧栏导航、分页或浮动工具盘。

## Elevation & Depth

没有 `box-shadow`。白色试听面与冷灰背景建立区域关系，候选之间用细线保持阅读连续性；紫色当前行和焦点描边承担定位，不模拟悬浮卡片。媒体空态点阵也出现在初始欢迎区，这是当前代码的实际复用范围。

**The Flat Surface Rule.** 层级依靠色面、分隔线与留白，当前态依靠选择底色或描边，不添加装饰阴影。

动效只用于按钮背景和边框变化（160ms）及候选行背景变化（200ms），共用 `cubic-bezier(.16,1,.3,1)`。`prefers-reduced-motion: reduce` 下关闭 transition，并将滚动行为设为 auto；没有入场动画和持续循环。

## Shapes

按钮与输入使用 `control` 圆角；试听容器、媒体区域和欢迎区使用 `surface` 圆角。候选行保持直角并以底边线连接阅读节奏；禁止把这些连续行擅自替换为分离的圆角卡片。常规边框为实线（1px）；全局 `:focus-visible` 使用紫色外描边（3px），偏移（3px）；已选带的当前项另用紫色描边（2px）、零偏移。

点阵是 CSS 径向圆点，容器（74 × 48px）、间隔（12px）、透明度（0.5）；只用于已实现的欢迎和未关联媒体空态，不表示媒体内容或分析数据。

## Components

### Buttons

明确、有边界的文字动作。主按钮使用蓝色与白字，普通按钮使用白色工作面与深色字。常规最小高度（44px）；移动按钮是紧凑辅助动作，最小高度（36px）。全局焦点样式适用于按钮与其他可聚焦元素；没有额外 `:active` 动画。

主按钮变深表示 hover；普通按钮使用浅蓝灰 hover 面与较深边框。禁用由浏览器 `disabled` 语义、文字和背景共同表达。移动按钮与正文按钮有透明背景覆盖：不要根据普通按钮规则强行给它们补不在代码中的实心底色。

### Transcript row

复选框表示是否保留，紫色行底表示正在查看，两者是独立状态；当前片段可以不入选。正文按钮用 `aria-pressed` 暴露当前状态，复选框和移动按钮有带片段编号的可访问名称。上移/下移在边界禁用；取消选择仍保留该行及原因。

桌面点开片段后，重建列表并恢复该片段正文按钮焦点；手机将焦点移到试听区，返回按钮把焦点送回对应正文。切换复选框后恢复复选框焦点，移动后聚焦移动后的正文。这里记录的是这些已实现路径，不宣称任意重绘都已完成通用焦点管理。

### Preview panel and time fields

白色容器内依次放置媒体、来源、媒体动作、局部状态、切点、转写和折叠依据。数字输入使用原生约束、秒单位与毫秒步长，边框和圆角与按钮一致；光标为紫色，焦点沿用全局描边。浏览器原生视频控件和文件选择框不被模拟。

未关联时显示灰色预览和点阵，试听禁用；正在读取显示局部等待文案；就绪后开放试听；错名、时长不符和不可播放都在媒体区域说明恢复办法。错误不删除切点。应用有效切点后的反馈留在表单下方，并提示重新试听；输入无效时就地报错。切换片段会清理前一片段的切点反馈。

### Selected timeline and export

紫色紧凑片段带表达已选顺序，当前项用 `aria-current` 和描边定位。无已选片段时给出文字空态；只有至少保留一段并勾选核对确认，才启用导出。改变选择、顺序、切点或撤销后清除核对确认，提示重新核对；加载新会话恢复“尚未渲染”说明，避免延续旧导出结果。

### Feedback and draft protection

全局状态、媒体状态、切点状态和导出说明均具备 `role="status"`；全局状态另外显式设置 `aria-live="polite"`。`notice` 同时更新内容与错误样式，正常态清掉错误类。成功不覆盖成脱离实际的“全部完成”。

有修改的草稿在打开示例或导入有效会话前通过原生确认框询问替换；取消后可继续操作并保存。保存审核会话后清除 dirty；导出 CSV 不清除 dirty。离页回调仅在 dirty 时触发浏览器原生提示；没有自动持久化，恢复会话仍需重新关联视频。

### Navigation and disclosure

页头只有品牌返回入口与本地处理说明。准备素材说明、无法加入的索引行以及当前片段的依据采用原生折叠控件；保留原生三角标记和键盘行为。未实现独立导航菜单、标签页、徽章或提示浮层，不将它们编造成已有组件。

## Do's and Don'ts

### Do:

- **Do** 让时间、正文、保留选择和来源在同一连续行中可对照。
- **Do** 沿用蓝色动作、紫色当前态和冷灰阅读环境。
- **Do** 使用离线可用的系统字体，并仅对需要对齐的数字启用 tabular-nums。
- **Do** 把媒体、切点和导出反馈留在对应操作旁，并在状态变化时清理旧提示。
- **Do** 保留原生控件、清晰焦点、可取消替换和显式保存会话。

### Don't:

- **Don't** 用独立卡片网格替换候选连续行，或用阴影与装饰转移对文字和切点的注意。
- **Don't** 把当前查看等同于已保留，或把先前导出等同于当前修改已经核对。
- **Don't** 把示例、待关联媒体、未测试的状态或 CSV 导出表现为真实成片结果。
- **Don't** 引入外部字体依赖、无限动画或未经实现验证的通用组件规则。
- **Don't** 将限定修复清单的 ship 结论扩写为整个产品已经验收。
