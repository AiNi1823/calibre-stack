# Calibre-Stack rewrite — UI Bug Fix Only

> 状态：**指令文档（可执行）**
> 分支：`rewrite`
> 目标：修复 3 个 P0 UI Bug + 1 个 P1 Bug，不重新设计，不重构，不继续叠加 CSS。

---

你现在负责修复 `AiNi1823/calibre-stack` 的 `rewrite` 分支。

GitHub：

[https://github.com/AiNi1823/calibre-stack/tree/rewrite](https://github.com/AiNi1823/calibre-stack/tree/rewrite)

当前阶段不是 UI 设计，不是重新设计页面，不是继续增加 CSS。

**只解决已经存在的三个严重 UI Bug。**

必须遵守：

> 先定位根因 → 修改最少代码 → 浏览器验证 → 再提交。

禁止根据描述猜测 CSS。

---

## 一、必须先做代码调查

进入：

```text
calibre-web/
```

重点检查：

```text
cps/templates/
cps/static/
src/input.css
tailwind.config.js
```

首先找到以下页面真正使用的 template：

```text
/
/author
/category
```

然后找到：

```text
Book Detail
Author list
Category list
```

对应的 HTML DOM。

同时搜索：

```text
book detail
author
category
booklist
detail
modal
dialog
x-show
x-data
grid
flex
position
absolute
fixed
```

以及：

```text
word-break
overflow-wrap
writing-mode
white-space
transform
scale
zoom
height
min-height
max-height
position
```

---

## 二、绝对禁止

在没有找到具体 DOM 和 CSS 根因之前：

禁止：

```text
新增大量 CSS
新增 !important
新增 position:absolute
新增 transform
新增负 margin
新增固定 height
新增 min-height
修改全局 body scale
修改 html font-size
修改 Tailwind 基础 font-size
```

禁止：

```text
重新设计 Author 页面
重新设计 Category 页面
重新设计 Book Detail
```

禁止：

```text
删除原有页面重新写一个假的页面
```

必须在现有 Calibre-Web 页面结构上修复。

---

## 三、Bug 1：点击书籍后详情跑到页面底部

### 现象

在：

```text
http://localhost:8085/?sort_param=stored
```

点击一本书。

当前 Book Detail 没有出现在当前视口附近，而是跑到了整个页面内容的底部。

这是 P0 Bug。

---

## 四、先定位 Book Detail DOM

必须回答：

```text
1. 点击书籍后实际打开哪个 template/component？
2. Book Detail 的 HTML 是在哪里生成的？
3. Book Detail 是否位于 Library Grid 内部？
4. Book Detail 是否参与了正常 document flow？
5. 哪个 CSS 规则导致它出现在 Grid 后面？
```

必须在代码中找到证据。

不要直接猜。

---

## 五、Book Detail 正确结构

如果当前结构类似：

```html
<div class="book-grid">

    <div class="book-card">...</div>

    <div class="book-card">...</div>

    <div class="book-detail">...</div>

</div>
```

这是问题根源。

Book Detail 不应该成为 Book Grid 的普通子元素。

---

## 六、优先修复为独立 Overlay

Book Detail 应该脱离 Library Grid 的 document flow。

推荐：

```html
<body>

    <main>
        Library
    </main>

    <div class="book-detail-overlay">
        ...
    </div>

</body>
```

或者：

```html
<body>

    <div id="app">
        ...
    </div>

    <div id="book-detail-root">
        ...
    </div>

</body>
```

如果项目使用 Alpine.js，可以使用：

```text
x-teleport
```

或者把 Detail DOM 放到合适的 root。

---

## 七、Desktop Detail

推荐使用右侧 Drawer。

```text
┌──────────────────────────────┬─────────────────────────────┐
│                              │                         ×   │
│                              │                             │
│          Library             │      Book Detail            │
│                              │                             │
│      [Book] [Book] [Book]    │      [Cover]                │
│      [Book] [Book] [Book]    │                             │
│                              │      Title                  │
│                              │      Author                 │
│                              │                             │
│                              │      [阅读] [下载] [更多]   │
│                              │                             │
│                              │      Description            │
│                              │                             │
└──────────────────────────────┴─────────────────────────────┘
```

CSS：

```css
.book-detail-drawer {
    position: fixed;
    top: 0;
    right: 0;
    height: 100dvh;
    width: min(720px, 90vw);
    overflow-y: auto;
}
```

注意：

> 只有在确认当前 DOM 结构适合 Drawer 后才能采用。

如果当前项目已有 Modal/Dialog 机制，优先复用，不要重新造轮子。

---

## 八、Detail 必须满足

点击书籍：

```text
立即打开
```

不能：

```text
页面滚到底部
```

必须：

```text
position 脱离 Library flow
z-index 正确
overflow-y 正常
body 不产生异常高度
```

关闭后：

```text
回到原来的 Library 位置
```

不能：

```text
跳回页面顶部
```

---

## 九、特别检查 Grid/Flex

重点检查 Book Grid 是否存在：

```css
display: grid;
display: flex;
grid-template-columns;
grid-auto-rows;
align-items;
position;
```

以及 Detail 是否错误继承：

```css
grid-column
grid-row
flex
flex-basis
width
height
```

如果 Detail 当前是 Grid child：

> 从 Grid 中移除。

不要通过：

```css
grid-column: 1 / -1;
```

这种方式"修"。

---

## 十、Bug 2：/author 页面

当前：

```text
http://localhost:8085/author
```

页面初始区域出现严重异常：

> 每个字都单独换行，导致文字几乎无法阅读。

这是 P0 Bug。

---

## 十一、不要重新设计 Author

首先恢复最基本的正常 HTML 文本布局。

Author 名称必须能够正常显示：

```text
刘慈欣
江南
东野圭吾
村上春树
```

而不是：

```text
刘
慈
欣

江
南
```

---

## 十二、Author 必须检查 CSS

搜索整个项目：

```text
word-break
overflow-wrap
white-space
writing-mode
text-orientation
width
max-width
min-width
display
flex
grid
```

尤其查找：

```css
word-break: break-all;
```

```css
writing-mode: vertical-rl;
```

```css
width: 1px;
```

```css
max-width: ...
```

以及任何导致文字容器实际宽度接近一个字符的规则。

---

## 十三、确认真实 DOM

不要假设 `.author` 是问题。

使用浏览器 DevTools：

选择出现逐字换行的文字。

检查：

```text
Element
Computed
Layout
```

确认：

```text
实际 width
实际 height
display
writing-mode
word-break
overflow-wrap
white-space
```

必须找到：

> 为什么这个文字容器只有一个字符宽。

---

## 十四、正确修复

Author item 应该至少满足：

```css
.author-item {
    min-width: 0;
}

.author-name {
    font-size: 16px;
    line-height: 1.5;
    white-space: normal;
    word-break: normal;
    overflow-wrap: break-word;
}
```

但：

> 不要直接复制上述 CSS。

先确认当前 DOM。

---

## 十五、Author 页面最小目标

页面只需要正常显示：

```text
作者

刘慈欣        5
江南         25
东野圭吾      18
村上春树      12
```

不要在本轮增加：

```text
复杂 Card
Avatar
动画
渐变
大阴影
复杂筛选
新的搜索系统
```

---

## 十六、Bug 3：/category

当前：

```text
http://localhost:8085/category
```

存在和 Author 相同或更严重的布局问题。

处理原则与 Author 完全一致。

---

## 十七、Category 正确目标

最简单：

```text
分类

文学             128
科幻              56
历史              42
技术              38
小说              31
```

也可以使用简单 Grid：

```text
┌────────────────────┐
│ 文学          128  │
├────────────────────┤
│ 科幻           56  │
├────────────────────┤
│ 历史           42  │
└────────────────────┘
```

核心要求只有：

> 正常横向阅读。

---

## 十八、不要继续叠加新版 UI

如果当前 `/author` 和 `/category` 是旧模板：

可以做最小 HTML/CSS 修复。

如果之前的 UI Rewrite 已经严重破坏原始结构：

允许：

> 恢复到 Calibre-Web 原始可工作的结构。

然后再套当前 Design Token。

但是：

> 本轮不要继续设计新 UI。

---

## 十九、检查 CSS Cascade

这是本次最重要的排查。

使用 DevTools：

```javascript
getComputedStyle(element)
```

对以下元素检查：

```text
Author name
Category name
Book Detail root
Book Detail container
```

记录：

```text
display
position
width
height
min-width
max-width
font-size
line-height
word-break
overflow-wrap
white-space
writing-mode
transform
```

找到最终生效的 CSS 文件和规则。

---

## 二十、检查 Tailwind Build

项目使用：

```text
src/input.css
tailwind.config.js
```

修改后必须：

```bash
cd calibre-web
npm run build
```

确认生成：

```text
cps/static/css/tailwind.css
```

不要只修改 source CSS 然后认为已经生效。

---

## 二十一、清除浏览器缓存影响

修改完成后：

```text
Hard Reload
```

Chrome：

```text
Ctrl + Shift + R
```

必要时：

```text
Disable cache
```

重新确认。

---

## 二十二、ASIN 额外 Bug

当前出现：

```html
<a
href="https://amazon.com/dp/f66d1117-e151-4ee0-bc04-9718bc5f1b41"
>
asin
</a>
```

不要把：

```text
f66d1117-e151-4ee0-bc04-9718bc5f1b41
```

直接拼到 Amazon URL。

先检查 identifier 来源。

搜索：

```text
asin
identifiers
amazon
amazon.com/dp
```

确认：

```text
Calibre metadata
        ↓
identifier
        ↓
template
        ↓
URL
```

---

## 二十三、正确处理 ASIN

只有确定 identifier 是真实 ASIN 时：

```text
ASIN = 10-character Amazon identifier
```

才允许：

```text
https://www.amazon.com/dp/{ASIN}
```

否则：

> 只显示 metadata，不显示链接。

特别是：

```text
f66d1117-e151-4ee0-bc04-9718bc5f1b41
```

必须不能生成 Amazon URL。

---

## 二十四、这次不要删除 ASIN 字段

不要：

```text
直接隐藏 asin
```

应该：

```text
identifier 保留
错误链接取消
```

正确：

```text
ASIN
f66d1117-e151-4ee0-bc04-9718bc5f1b41
```

错误：

```text
ASIN → Amazon URL
```

---

## 二十五、最终验收必须真实浏览器完成

启动：

```text
localhost:8085
```

然后逐项验证。

---

### Test 1

打开：

```text
http://localhost:8085/?sort_param=stored
```

点击第一本书。

必须：

```text
Book Detail 立即出现在当前视口
```

不能：

```text
跑到页面底部
```

---

### Test 2

关闭 Detail。

确认：

```text
仍然停留在原来的 Library 位置
```

---

### Test 3

打开：

```text
http://localhost:8085/author
```

必须：

```text
作者名称正常横向阅读
```

不存在：

```text
刘
慈
欣
```

这种布局。

---

### Test 4

打开：

```text
http://localhost:8085/category
```

必须：

```text
分类名称正常横向阅读
```

---

### Test 5

Book Detail：

检查：

```text
ASIN
```

对于：

```text
f66d1117-e151-4ee0-bc04-9718bc5f1b41
```

不能产生 Amazon 外链。

---

## 二十六、修改策略

本次修改优先级：

```text
P0
Book Detail positioning

P0
Author text layout

P0
Category text layout

P1
ASIN URL validation
```

完成 P0 后才能处理 P1。

---

## 二十七、禁止 Agent 自由发挥

不要输出：

```text
"我建议重新设计……"
"可以考虑……"
"现代化 UI……"
```

不要创建新的设计方案。

直接：

```text
定位代码
→ 修改
→ build
→ 启动
→ 浏览器验证
→ 修复
```

---

## 二十八、最终输出

施工结束后只报告：

```text
## 修复结果

### Book Detail
- 根因：
- 修改文件：
- 修改内容：
- 浏览器验证：

### Author
- 根因：
- 修改文件：
- 修改内容：
- 浏览器验证：

### Category
- 根因：
- 修改文件：
- 修改内容：
- 浏览器验证：

### ASIN
- 根因：
- 修改文件：
- 修改内容：
- 验证结果：

### Build
- npm run build：PASS / FAIL

### 最终状态
PASS / FAIL
```

如果某问题没有实际通过浏览器验证：

> 必须标记 FAIL。

禁止声称"已修复"。
