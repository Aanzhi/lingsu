# AI 工具台设计 QA

## Source visual truth

- 用户参考图：`/var/folders/8l/njfts9y953j44s0vckdvdpg80000gn/T/codex-clipboard-d9aba22c-2e6a-486a-83af-246df20f04bd.png`，1236 × 1236；它定义 AI 工具台的主内容区，不覆盖现有学生工作台的顶部栏和左侧导航。
- 已确认线框：`/Users/anzhi/.codex/visualizations/2026/08/28/01a047c4-9722-7ed0-8eaf-901efa840855/ai-workbench-wireframe.html`。
- 线框截图：`/Users/anzhi/.codex/visualizations/2026/08/28/01a047c4-9722-7ed0-8eaf-901efa840855/wireframe-source.png`。

## Implementation evidence

- 主视图：`frontend/src/pages/shared/AICenter.vue`。
- 输入面板：`frontend/src/components/ai/AIWorkbenchComposer.vue`。
- 模式文案契约：`frontend/src/stores/aiWorkbenchModel.ts`。
- 开题空状态截图：`/Users/anzhi/.codex/visualizations/2026/08/28/01a047c4-9722-7ed0-8eaf-901efa840855/style-opening-clean-1203.png`。
- 研究态截图：`/Users/anzhi/.codex/visualizations/2026/08/28/01a047c4-9722-7ed0-8eaf-901efa840855/style-research-clean-1203.png`。
- 已有对话状态截图：`/Users/anzhi/.codex/visualizations/2026/08/28/01a047c4-9722-7ed0-8eaf-901efa840855/style-active-clean-1203.png`。

## Comparison setup

- 统一对比输入：`/Users/anzhi/.codex/visualizations/2026/08/28/01a047c4-9722-7ed0-8eaf-901efa840855/qa-style-comparison-clean-full.png`；生成页面为 `qa-comparison.html`，线框、开题实现、研究态和已有对话实现在同一比较画布中呈现。
- 桌面复核 viewport：1203 × 998 CSS px；干净实现截图为 1203 × 998，未发现水平溢出。
- 状态：开题、研究、成果表达三种新建态、已有对话状态（14 条消息）、模式切换、快捷提示填充、历史对话展开/选择。
- 密度：默认浏览器像素密度，无额外缩放。

## Mandatory comparison passes

### Fonts and typography

- 保留工作台既有 `--sans` 字体 token；标题、说明、模式标签、快捷提示和输入辅助文案形成清晰的层级。
- 线框的粗体中文标题层级在实现中对应到 `研究工作台 / 灵思 AI / 从一个问题开始`；窄屏时说明文案允许换行，不再截断或挤压相邻控件。
- 结论：通过。操作系统字体渲染和线框截图存在正常的抗锯齿差异，未形成可用性问题。

### Spacing and layout

- 实现使用单一 `.ai-workbench-canvas` 承载标题、模式切换、空状态和 composer，保持线框的纵向阅读路径与统一边界。
- 新建态与对话态共用画布边界；对话态将消息流和输入 dock 放入同一表面，避免状态切换时出现第二套容器语言。
- 在不改变 DOM 顺序和区域布局的前提下，画布、模式卡、空状态和 composer 改用全站 `paper-card` 视觉语言：12px 圆角、轻阴影、细边框、常规字号。
- 桌面 1203 px 下无水平溢出；各内容表面的左右边界一致。
- 结论：通过。

### Viewport resilience

- 1203 × 998：三段模式导航、三种模式内容模块和输入区均可用，`document.scrollWidth === clientWidth`。
- 本轮不新增移动端适配要求，保留现有媒体查询，不以移动端作为本轮验收标准。
- 结论：通过。

### Colors and tokens

- 内容区统一映射到现有 paper/ink/moss/sage/line token；画布、边框、激活态、主按钮和禁用态保持同一绿色纸张系统。
- 空状态和对话态使用同样的白色画布与深绿边界，主按钮只在可发送时进入强调态。
- 结论：通过。

### Image quality and asset fidelity

- 参考图和线框没有要求新增照片、插画或栅格图；实现未添加占位图片、CSS 艺术或伪造头像。
- 品牌标识和现有导航图标继续复用产品已有组件/图标系统。
- 结论：通过。

### Copy and content

- 开题说明更新为“直接说出要处理的研究问题，不需要先填写表格。”，与参考图和空状态语境一致。
- 模式副标题统一为“整理观察，形成研究问题 / 推进当前项目的研究任务 / 整理摘要和答辩表达”。
- composer placeholder 与参考图统一为“写下你的问题或研究想法...”。
- 结论：通过。

### Icons, states, and accessibility

- 发送按钮的箭头使用现有 Element Plus 图标；历史、新建、模式和快捷提示均为语义化按钮。
- 已复核新建态、对话态、历史抽屉展开/关闭、模式切换和快捷提示填充；未执行发送，避免产生后端副作用。
- 开发浏览器控制台 error/warning：0 条。
- 结论：通过。

## Findings

- P0：无。
- P1：无。
- P2：无。
- P3：不同操作系统的字体抗锯齿、窄屏下中文换行位置与线框截图会有轻微像素差异，不影响层级、阅读或操作，暂不需要修复。

## Comparison history

1. 线框落地后的第一版使用了 AI 专属的大字号、大圆角和厚边框，视觉上偏离学生工作台现有语言。
2. 本轮保留原有 DOM 和区域布局，仅将背景、标题尺度、模式卡、快捷按钮、composer、边框和阴影切回全站 token。
3. 根据反馈再次收紧桌面端字号、间距和 composer 高度，并让研究/成果表达复用开题下方的内容模块；蓝色批注标记未纳入产品视觉判断。

## Verification

- AI 相关测试：6 个测试文件，59 个测试通过。
- 全量测试：296/298 通过；剩余 2 个失败属于本次范围外、工作区原有的项目邀请页旧契约（`src/remainingPageParity.test.ts`、`src/pageContentContracts.test.ts`），未修改无关页面。
- 生产构建：`npm --prefix frontend run build` 通过；仅有现有 Rollup 注释和大 chunk 警告。
- `git diff --check`：通过。

final result: passed
