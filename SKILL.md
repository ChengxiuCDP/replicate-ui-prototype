---
name: replicate-ui-prototype
description: |
  Use when coding 需求涉及 UI 布局、结构、信息层级调整或新增视觉区块。
  也适用于：需要并排多个方向变体供选择、要给没有仓库权限的人（设计师/PM/老板）看视觉效果、截图/PRD 驱动的 UI 复刻。
  不适用：单点样式微调（改一处颜色/字号/间距，直接改代码）；纯业务逻辑改动；全新组件设计、无现成风格可复刻（用 frontend-design）；真数据状态/状态机/异步流程（HTML 表达不了）。
---

# Replicate UI Prototype

## 核心原则

任何涉及 UI 布局/结构的改动，先复刻当前仓库已有的设计风格和组件，产出独立可交互的 HTML 原型快速验证效果；用户拍板后，这份 HTML 就是落地蓝图——转译时数值 1:1 保真，保证能高还原度直接翻回组件代码。

复刻必须用仓库真实的 design token、spacing、typography。数值靠猜 = 原型和工程对不上 = 拍板后逐项返工 = 原型报废。

## 触发判断

| 需求形态 | 走法 |
|-|-|
| 布局重排 / 信息层级调整 / 新增区块 / 多组件全局改动 | 本 skill：先出原型 |
| 单点微调（一处颜色/字号/间距） | 直接改代码，不出原型 |
| 全新设计、无现成实现可复刻 | frontend-design |
| 状态机 / 真数据联动 / 异步流程 | HTML 表达不了，直接改代码或走 Figma |

## 流程

1. **定位目标组件**：用户给了路径直接读；没给就 grep 组件名或界面可见文案（截图里的文字最稳）
2. **读 3 类文件，停手**：
   - 目标组件源码（结构 + class 组合 + 子区块顺序）
   - design token 源文件（`:root` + `.dark` 块，grep `--background:` 或 `:root {` 定位）
   - 项目 UI spec 文档如存在（CLAUDE.md / AGENTS.md / docs 里的 UI 章节）——spec 是凌驾于 token 的硬约束，只读 token 复刻不出项目原味
   - 不读 tailwind config 和无关文件，省 context
3. **转译严格保数值**（高还原落地的契约）：
   - token 直搬进 HTML 的 `:root` + `.dark`，不依赖任何 framework
   - Tailwind class 翻 CSS 严格保值：`px-3 py-2` = `padding:8px 12px`、`text-sm` = `font-size:14px;line-height:20px`、`gap-2` = `gap:8px`
   - 透明度语法 `xxx/40` 用 `color-mix(in srgb, var(--xxx) 40%, transparent)`
4. **变体策略——先分类需求**：
   - 探索性（开放需求、截图复刻、无精确 spec）→ 首轮并排 2-3 个整体方向变体（信息架构级差异，不是末端样式选项）
   - 执行性（精确 spec、"就照这个做"）→ 出 1 个
   - 拿不准 → 反问"想看几个方向选，还是直接按这个做？"
   - 方向选定后单线覆盖迭代，不保留旧版——被否决的旧版是噪音不是对比
5. **示例数据用真实命名**：抄界面上看得到的真实名称，不用 item-1 这类 placeholder，否则原型显假、用户分心
6. **双轨发布**：
   - 本地：写 `<component>-redesign.html`，回复带 `<media src="/绝对/路径.html"/>` 供预览和后续编辑
   - 分享：跑 `scripts/publish.sh <html文件> [id]` 上传内网拿可分享 URL。记住返回的 id，后续更新传同一 id，URL 保持不变
7. **收尾列 1-3 个你自己拍的小决策**请用户确认，不列 pros/cons

## 落地阶段

用户拍板后，把 HTML 反向转译回组件代码：CSS 数值 1:1 对回 Tailwind class / token 引用，DOM 结构对回组件层级。原型阶段严格保值就是为了这一步零 drift。

## Failure handling

- 找不到目标组件 → 直接问路径或组件名，别猜
- token 组织非常规（SCSS 变量、CSS-in-JS）→ 能转的转，转不了的写死 hex 并注释 `/* approximated, not from token */` 留用户决策
- 需求只有"美化一下" → 反问改的是结构/信息层级/颜色/间距哪个
- 组件超大（数百行）→ 只复刻用户提到的 sub-section，别全文照搬
