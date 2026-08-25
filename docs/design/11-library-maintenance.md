# Design Doc 11: 书库维护（去重 + EPUB 替换 + 封面补全 + 元数据修复）

> 角色：设计级方案，用户授权后实施
> 日期：2026-08-24
> 范围：仅改 `docs/design/`，不写 .py、不改系统配置
> 核心原则：**优先从外部源下载高质量 EPUB 替换 TXT**，非转换低质 TXT

---

## 11.1 书库现状

| 项目 | 数据 |
|------|------|
| 总书数 | 82 本（含 12 个已删 ID 空位） |
| EPUB | 53 本（64.6%） |
| TXT | 25 本（30.5%）——全部为金庸作品 |
| AZW3 | 17 本 / KFX 16 本 / AZW 9 本 / MOBI 4 本 / PDF 3 本 |
| 重复金庸 TXT | 18 条（跨 7 部作品） |
| 缺封面 | 26 本（25 金庸 + 1 证券分析） |
| 无 EPUB | 28 本（25 金庸 TXT-only + 3 词典 AZW-only + 1 PDF-only） |

---

## 11.2 去重方案

### 11.2.1 重复清单与保留决策

| 作品 | 保留 ID | 删除 ID | 保留理由 |
|------|---------|---------|----------|
| 白马啸西风 | **77** | 69, 80 | 69 首行乱码；77 与 80 相同，取较小 ID |
| 鹿鼎记 | **71** | 82, 84 | 三本相同（~2.4MB），取较小 ID |
| 侠客行 | **87** | 75, 89 | 75 截断（264KB）；87 与 89 相同（750KB），取较小 ID |
| 飞狐外传 | **76** | 86, 93 | 三本相同（~922KB），取较小 ID |
| 越女剑 | **78** | 91 | 两本相同（~34KB），取较小 ID |
| 连城诀 | **83** | 92 | 两本相同（~484KB），取较小 ID |
| 射雕英雄传 | **94** | 70 | 70 截断（447KB）；94 完整（1.9MB） |

**保留 15 本唯一金庸 TXT，删除 10 条重复**。

### 11.2.2 删除操作

```bash
# 逐本删除重复（calibredb remove 需要 --cover 等选项，这里只需删条目）
calibredb remove --library-path "$LIB" 69 80 82 84 75 89 86 93 91 92 70
```

### 11.2.3 合并碧血剑

ID 68（碧血剑）已有正确元数据但目录结构不同（`金庸/碧血剑 (68)/`），保留即可。

---

## 11.3 EPUB 获取方案（优先下载，非转换 TXT）

### 11.3.1 为什么不转换 TXT → EPUB

- TXT 编码为 GB18030，格式粗糙（无章节结构、无封面、无元数据嵌入）
- 转换后 EPUB 质量低（纯文本灌入，无排版）
- 外部源有更高质量的 EPUB（排版、章节、元数据完整）
- 用户本身就有 z-library / Anna's 账号，可直接获取优质 EPUB

### 11.3.2 免费源覆盖实测结果

对 15 本金庸逐一测试免费源（Standard Ebooks / Gutendex / OpenLibrary / Internet Archive）：

| 书名 | 免费源 EPUB | 来源 | 备注 |
|------|------------|------|------|
| 碧血剑 | 有 | IA `bixuejian0002jiny` | 9.5MB 扫描版 EPUB |
| 射雕英雄传 | 无 | IA 仅 TXT | 纯文字，非 EPUB |
| 神雕侠侣 | 无 | IA 仅 PDF | 扫描版，无 EPUB |
| 倚天屠龙记 | 无 | IA 仅 TXT | 纯文字，非 EPUB |
| 其余 11 本 | 无 | 无任何免费源 | — |

**结论：免费源仅覆盖 1/15（碧血剑），其余 14 本必须走 Anna's Archive / z-library。**

### 11.3.3 两阶段执行

#### 阶段一：立即可做（去重 + 元数据 + 封面 + 碧血剑 EPUB）

1. **去重**：删除 10 条重复（§11.2）
2. **元数据修复**：修正 15 本的标题/作者/语言（§11.4）
3. **封面补全**：从 Douban 查询 16 本封面（§11.5）
4. **碧血剑 EPUB 下载**：从 IA 下载 EPUB → 写入书库 → 删除原 TXT

#### 阶段二：需凭据后执行（14 本金庸 EPUB 替换）

用户提供 z-library 凭据（`ZLIB_EMAIL` / `ZLIB_PASSWORD`）或 Anna's RapidAPI key 后：

```
对每本金庸 TXT：
  1. search_epub(title="书名", author="金庸")  → Doc 4 管线
  2. download_epub(cand, dest)  → 下载 EPUB
  3. calibredb add --automerge overwrite "$LIB" dest.epub  → 写入书库
  4. calibredb remove_format --library-path "$LIB" <book_id> --txt  → 删除原 TXT
```

**关键**：`search_epub` 会按优先级走 6 个源（Standard Ebooks → Wikisource → Gutendex → IA → Anna's → z-library），自动跳过免费源无果的，最终由 Anna's / z-library 兜底。

### 11.3.4 待替换清单

| ID | 书名 | 当前格式 | 阶段 | 预期来源 |
|----|------|----------|------|----------|
| 68 | 碧血剑 | TXT | **阶段一** | IA `bixuejian0002jiny` |
| 77 | 白马啸西风 | TXT | 阶段二 | z-library / Anna's |
| 94 | 射雕英雄传 | TXT | 阶段二 | z-library / Anna's |
| 71 | 鹿鼎记 | TXT | 阶段二 | z-library / Anna's |
| 72 | 神雕侠侣 | TXT | 阶段二 | z-library / Anna's |
| 73 | 雪山飞狐 | TXT | 阶段二 | z-library / Anna's |
| 78 | 越女剑 | TXT | 阶段二 | z-library / Anna's |
| 79 | 笑傲江湖 | TXT | 阶段二 | z-library / Anna's |
| 83 | 连城诀 | TXT | 阶段二 | z-library / Anna's |
| 85 | 倚天屠龙记 | TXT | 阶段二 | z-library / Anna's |
| 87 | 侠客行 | TXT | 阶段二 | z-library / Anna's |
| 88 | 鸳鸯刀 | TXT | 阶段二 | z-library / Anna's |
| 90 | 书剑恩仇录 | TXT | 阶段二 | z-library / Anna's |
| 76 | 飞狐外传 | TXT | 阶段二 | z-library / Anna's |

> **降级方案**：若某本金庸在 z-library / Anna's 均无 EPUB，最终降级为 `ebook-convert` TXT→EPUB（质量较低但聊胜于无）。

---

## 11.4 元数据修复

### 11.4.1 问题

| 问题 | 影响范围 | 修复方案 |
|------|----------|----------|
| 作者为 "Unknown" | 25 本金庸 TXT（ID 68-94） | `calibredb set_metadata --field authors:"金庸"` |
| 标题含 hash 前缀 | 20 本（如 `0b7fead8_金庸 白马啸西风`） | `calibredb set_metadata --field title:"白马啸西风"` |
| 标题含多余空格 | 多本（如 `金庸 白马啸西风`） | 清理为纯书名 |
| 缺语言字段 | 全部金庸 TXT | `calibredb set_metadata --field languages:zh` |
| 缺出版信息 | 全部金庸 TXT | 从 Douban 查询补全（可选） |

### 11.4.2 修复清单

```bash
# 批量修复脚本（设计级伪代码）
for book_id in [68, 71, 72, 73, 76, 77, 78, 79, 83, 85, 87, 88, 90, 94]:
    title = clean_title(book_id)      # 去 hash 前缀、去多余空格
    calibredb set_metadata --library-path "$LIB" $book_id \
        --field authors:"金庸" \
        --field title:"$title" \
        --field languages:zh
```

### 11.4.3 标题清理映射

| ID | 原标题 | 修正标题 |
|----|--------|----------|
| 69→77 | `0b7fead8_金庸 白马啸西风` | `白马啸西风` |
| 70→94 | `e0268bba_射雕英雄传` | `射雕英雄传` |
| 71 | `d28655e7_金庸 鹿鼎记` | `鹿鼎记` |
| 72 | `29e3306e_神雕侠侣` | `神雕侠侣` |
| 73 | `e3510fa7_雪山飞狐` | `雪山飞狐` |
| 78 | `3028bf30_金庸 越女剑` | `越女剑` |
| 79 | `386c88f6_笑傲江湖` | `笑傲江湖` |
| 83 | `7dc2f881_连城诀` | `连城诀` |
| 85 | `8ec06625_倚天屠龙记` | `倚天屠龙记` |
| 87 | `938dd229_金庸 侠客行` | `侠客行` |
| 88 | `a4cb86a9_鸳鸯刀` | `鸳鸯刀` |
| 90 | `d106dc4d_书剑恩仇录` | `书剑恩仇录` |
| 94 | `ffbd23eb_射雕英雄传` | `射雕英雄传` |

---

## 11.5 封面补全

### 11.5.1 缺封面清单

| ID | 书名 | 作者 | 优先源 |
|----|------|------|--------|
| 65 | 证券分析 | 格雷厄姆 | Douban → Google Books |
| 68-94 | 金庸 15 本 | 金庸 | Douban → Google Books |

### 11.5.2 封面获取流程

```
对每本缺封面的书：
  1. Douban search(title + "金庸") → 获取 cover_url
  2. 若 Douban 无果 → Google Books(volumeQuery) → 获取 thumbnail
  3. 若均无果 → 生成纯色占位封面（calibredb 会自动生成默认封面）
  4. 下载图片 → 重命名为 cover.jpg → 放入书目目录
  5. calibredb set_metadata --field has_cover:true
```

**使用 metadata-tool 已有模块**：
- `douban.py`：`search()` → `get_detail()` → 提取 `cover` URL
- `covers.py`：`download()` → 下载到本地

---

## 11.6 执行顺序（用户授权后）

### Phase 1：去重 + 元数据 + 封面（~10 分钟，立即可做）

1. 备份数据库：`cp metadata.db metadata.db.bak`
2. 删除 10 条重复金庸 TXT（§11.2.2）
3. 批量修正 15 本元数据（§11.4）
4. Douban 查询 16 本封面并下载（§11.5）
5. 从 IA 下载碧血剑 EPUB → 写入书库 → 删除原 TXT
6. 验证：`calibredb list --fields=title,authors,formats`

### Phase 2：14 本金庸 EPUB 替换（需凭据后执行）

1. 用户提供 z-library 凭据或 Anna's RapidAPI key
2. 对每本金庸执行 `search_epub` → `download_epub` → `calibredb add` → `calibredb remove_format`
3. 验证：所有金庸书应有 EPUB 格式
4. 若某本无 EPUB → 降级为 `ebook-convert` TXT→EPUB

### 不动的

- 3 本 AZW-only 词典（ID 31/45/49）——Kindle 词典格式特殊
- 1 本 PDF-only（ID 60 艰难一日）——保留 PDF
- 53 本已有 EPUB 的书——不动

---

## 11.7 风险与边界

- **阶段二依赖凭据**：14 本金庸 EPUB 需 z-library 或 Anna's 凭据；无凭据则止步于去重+元数据+封面
- **Douban 封面**：需代理（`http://127.0.0.1:7890`）
- **IA 碧血剑**：9.5MB 扫描版，质量一般；若用户不满意，可后续从 z-library 下载更优质版本替换
- **降级路径**：若外部源无 EPUB → `ebook-convert` TXT→EPUB（质量较低但可用）
- **不删原 TXT 文件**：转换成功后仅删除数据库中的 TXT 格式条目，原文件保留在磁盘（可选清理）
- **词典格式**：3 本 AZW-only 词典（ID 31/45/49）不做转换（Kindle 词典格式特殊）
- **PDF-only**：ID 60（艰难一日）保留 PDF，不强制转 EPUB
