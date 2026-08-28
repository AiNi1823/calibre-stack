# Calibre-Web UI 升级 — Phase 4：书籍详情（Book Detail）

## 0. 目标
- 重皮肤 `detail.html`（书籍详情页）
- 保持原有功能不变：封面、元数据、操作按钮（下载/发送到 eReader / 在线阅读 / 收藏 / 编辑 / 删除）
- 封面置顶，次之元数据区，底部操作按钮区
- 阅读状态徽章与进度条（若后端提供数据）
- 侧边栏/主题状态在详情页保持同步

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/detail.html`（重写：封面居上，元数据/进度/操作按钮区域化；保留全部原有功能入口）
  - `cps/templates/include/_book-card.html`（若复用，作为 detail.html 封面小版本）
  - `cps/static/css/tailwind.css` / `input.css`（新增 detail 相关样式：`.detail-cover`、`.meta-group`、`.action-btn` 等）
  - `cps/templates/include/_status-badge.html`（复用封装状态徽章）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。`detail.html` 仅改写前端展示结构，保持所有按钮链接、数据调用完全不动。

## 2. 实施要点
1. **结构布局**：
   - `.detail-layout`：`grid grid-cols-1 gap-6`
   - `.detail-cover`：`rounded-4`、`.lazy-loading`、`.mb-4`；桌面端与 `.meta-group` 水平排列
   - `.meta-group`：含 `.title`、`.author`、`.series`、`.progress`（进度条，若后端数据存在）
   - `.action-btns`：`grid grid-cols-2`，含 `.btn`：`'阅读' / '下载' / '收藏' / '编辑' / '删除'`；每个按钮保持原有 href/action 路由

2. **状态徽章**（`_status-badge.html`复用）：
   - 若 `ub.ReadBook.read_status` 存在于模板上下文：徽章显示 `未读`/`在读`/`已读`，颜色沿用绿/蓝灰
   - 若不存在：徽章隐藏，不报错

3. **操作按钮区**：
   - `'阅读'`: `href="{{ url_for('web.read_in_browser', book_id=entry.id) }}`（或 `'read-in-browser'`）
   - `'下载'`: 下拉菜单，含所有格式 `format.format|lower`（沿用原有 format 列表）
   - `'发送到 eReader'`: `href="{{ url_for('web.send_to_ereader', ... )}}`
   - `'编辑'`: `href="{{ url_for('web.edit_book', book_id=entry.id) }}`
   - `'删除'`: `confirm` 弹窗后 `web.delete_books`；保持原有行为

4. **面包屑/返回**：
   - `.breadcrumb`：`{{_('Home')}} > {{_('Books')}} > {{entry.title}}`
   - 返回 `{{_('Back')}}` 按钮 `href="{{ url_for('web.index') }}"`

5. **Alpine 交互**：
   - 封面悬停微放大 `.detail-cover:hover { transform: scale(1.02); }`
   - 主题变量 `dark` 在此页保持生效（继承 `base.html` 的 `x-data`）

## 2. 后端改动
- 无。保持所有原有路由、按钮链接、数据调用完全不动。

## 3. 回测方法
1. **本地构建**：同上
2. **浏览器验证**：
   - 详情页布局（桌面端）：封面与元数据区横向排列，封面居左，元数据（标题/作者/系列）居右，操作按钮在封面下方或同行显示
   - 纵屏/移动端下封面全宽，元数据垂直堆叠
   - 操作按钮（阅读/下载/收藏/编辑/删除）均可点击并跳转/执行
   - 返回按钮跳转首页
   - 横屏needmobile端布局不破坏

## 3. 推进标准（进入 P5 的门禁）
- `detail.html` 在桌面端正常渲染：封面与元数据并排，操作按钮全部可用
- 封面点击跳转至阅读页/详情页正常
- 所有操作按钮功能正常（下载/阅读/收藏/编辑/删除）
- 封面圆角为 4–6px，无 `rounded-4xl`
- Alpine 无错误

## 3. 下一步门禁
- P5（Home）：重皮肤首页 `index.html`（继续阅读 / 最近 / 收藏区块）

## 3. 备注
- `detail.html` 的布局切忌过度复杂，保持「封面优先、操作明确」的原则
- 封面 `lazy-loading` 建议配合 `loading="lazy"` HTML 属性及 Tailwind `lazy` 类
- 状态徽章的后端数据查询（`ub.ReadBook`）如若不存在，前端仅显示「已读/未读」基础徽章，不报错

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P4 并经验证后，可进入 P5.