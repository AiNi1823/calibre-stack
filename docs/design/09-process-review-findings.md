# Design Doc 9: Process Review Findings (复审结论)

> 复审对象：Doc 1–8 + 现有代码 server.py / metadata-tool/src/* / nginx
> 角色：纯研究 + 文档评审 + 文档修订（不写实现、不跑管线、只改 docs/design/）
> 日期：2026-08-24

---

## 9.1 总体结论（逐文档裁决）

| 文档 | 裁决 | 主要问题 |
|------|------|----------|
| 01 安全 | **PASS-with-notes** | 逻辑正确；Redis 密码小节与 Calibre-Web 耦合未细化（仅 notes） |
| 02 任务/API | **PASS-with-notes** | STAGES 缺 `scan`；nginx `error_page` 登录跳转错位；/api 与 server.py 上限不一致 |
| 03 转换器 | **PASS-with-notes** | `remove_format_and_archive` 文本解析脆弱（见 9.3-P9）；其余正确 |
| 04 EPUB 源 | **NEEDS-REVISION→已修订** | IA 直链假设错误（已修 §4.2）；三源对非 PD 中文覆盖不足（已补 §4.7/§4.8 + AA 推荐） |
| 05 元数据/去重 | **NEEDS-REVISION→已修订** | `CalibreDB` 传目录路径（B5）；OL 不补 pubdate（B5）；tags 死分支（B5）；dedupe `_connect` 同 bug |
| 06 流水线 | **NEEDS-REVISION→已修订** | B3 `MAX(id)` 并发串号（已改为持锁解析 stdout）；MOBI→EPUB 后原格式未清（见 9.3-P8） |
| 07 全库扫描 | **NEEDS-REVISION→已修订** | `CalibreDB` 路径 bug；`get_missing_fields(dict(b))` 误判；per-book 去重无效（B7，已修） |
| 08 子代理审阅 | **PASS** | 模板本身合理；已补充本复审为其落地样例 |

> 注：B1–B4 与其余 E1–E3 决策经核查均已在对应文档一致应用，无遗漏。

---

## 9.2 端到端流程审查

### 9.2.1 主链路（上传 → … → done）是否健全
`uploaded → adding → [converting | searching_epub] → enriching → deduping → done`
- 方向正确，阶段写入 tasks.db 实时可见。
- **死路 1（已修）**：Doc 6 的 `MAX(id)` 取 book_id 在并发下会串号 → 改为 `_add_to_library` 持锁解析 `calibredb add` 的 `Added book N` 输出（见 9.3-P1 / Doc 6）。
- **死路 2（已修）**：Doc 7 逐本 `dedupe_book_group([bid])` 永远不触发跨书去重 → 改为循环后 `dd.dedupe_all()` 一次（见 9.3-P7 / Doc 7）。
- **缺口（保留建议）**：MOBI→EPUB 转换成功后，原 MOBI 格式仍留在库内（fc.process 只归档 staging 文件，未 `remove_format`），dedupe 因「不同格式都保留」不会清掉 MOBI。对 Kindle 而言多一份 MOBI 无害，但若想保持「仅 EPUB」可显式 `remove_format_and_archive(book_id,"MOBI")`（见 9.3-P8）。

### 9.2.2 模块间 API 契约一致性
| 调用方 → 被调 | 引用签名 | 核查结果 |
|-------------|----------|----------|
| Doc 5 enrich → `CalibreDB.get_missing_fields` | 入参 book dict | ✅ 但要求完整记录（已修 Doc 7 误用） |
| Doc 5 → `DoubanAPI.find_book` / `OpenLibraryAPI.find_book` | 返回 dict | ✅ 字段差异：OL 返回 `first_publish_year` 非 `pubdate`（已修 Doc 5 映射） |
| Doc 5 → `CoverDownloader.download_douban_cover/download_openlibrary_cover` | `(id|url, path)` | ✅ |
| Doc 6 → `fc.process / es.search_epub / me.enrich / dd.dedupe_book_group` | 见各 doc | ✅ 签名一致 |
| Doc 7 → `es.zlib_remaining/zlib_eta`、`dd.dedupe_all` | 见 Doc 4/5 | ✅ |
| Doc 3 → `calibredb add_format/remove_format` | CLI | ✅ |

### 9.2.3 tasks.db 状态机覆盖
- STAGES 已补 `scan`（Doc 2 §2.1）。
- STATUSES：`pending/running/success/failed/cancelled` 全覆盖；`cancelled` 定义但 UI 未提供取消按钮（无害）。
- UI 可表达所有阶段/状态，无不可表示项。

### 9.2.4 nginx auth + async-upload 集成
- `/tasks` 与 `/api/` 均接 `auth_request /_auth_check`，逻辑正确。
- **登录跳转机制（Round 3 复核修正）**：`_auth_check` 未登录返回 `302`，`auth_request` 将非 2xx/非 401/403 视作 **内部错误 → 500**（并非 401）。live nginx 的 server 级 `error_page 500 = @login_redirect;` 已正确捕获该 500 并跳转登录，覆盖 `/async-upload`、`/api/`、`/tasks`。故既往「需补 `error_page 401`」系误判（本流程 `401` 永不产生），Round 3 已在 Doc 2 §2.3 删除该死配置。
- 大小限制不一致：nginx `client_max_body_size 100M`（§2.3）vs server.py `200*1024*1024`（server.py:111），后者永不触发。建议对齐到 100M。

---

## 9.3 流程缺陷清单（P1–P9）

- **P1（严重, 已修）** Doc 6 `_latest_book_id` 的 `MAX(id)` 在释放 `CALIBRE_LOCK` 后读取，并发上传会串号。→ 改为持锁解析 `calibredb add` stdout 的 `Added book N`。
- **P2（严重, 已修）** Doc 5 metadata_enricher：`_db = CalibreDB(LIBRARY)` 传目录，但 `CalibreDB.__init__` 期望 metadata.db 路径（`sqlite3.connect`），会报 "unable to open database file"。→ 传 `os.path.join(LIBRARY,"metadata.db")`。
- **P3（严重, 已修）** Doc 7 scan：`get_missing_fields(dict(b))`，`dict(b)` 仅含 id/title/fmts，缺 isbn/has_cover，导致每本书都被误判需补元数据。→ 改用 `get_book_by_id(b["id"])`。
- **P4（中等, 已修）** Doc 5 enrich：OpenLibrary `find_book` 返回 `first_publish_year` 而非 `pubdate`，原 `src.get("pubdate")` 对 OL 源永远为空 → pubdate 不补全。→ 同时接受 `first_publish_year`。
- **P5（低, 已修）** Doc 5：`get_missing_fields` 从不返回 `"tags"`，原 `if "tags" in missing` 为死分支。→ 改为只要源有 tags 就叠加写入。
- **P6（中等, 已修）** Doc 4 IA：EPUB 直链 `{iaid}_epub.zip` 多为错误 404。→ 改查 `archive.org/metadata/{iaid}` 取真实 `.epub` 文件名。
- **P7（严重, 已修）** Doc 7 scan：per-book `dedupe_book_group([bid])` 对单本书无操作，跨书「同名重复」去重从未执行。→ 循环后统一 `dd.dedupe_all()`。
- **P8（建议）** Doc 6/3：MOBI→EPUB 成功后原 MOBI 格式残留库内。建议转换成功后 `remove_format_and_archive(book_id,"MOBI")` 保持「仅 EPUB」。当前为无害保留，列为可选项。
- **P9（建议）** Doc 3 `remove_format_and_archive` 用 `calibredb list --fields path,formats` 文本正则解析定位文件，标题含空格易错。建议仿 `deduplicator._connect` 直查 metadata.db 的 `data/path` 表。当前为设计级代码，落地前需改。

---

## 9.4 资源来源推荐表（核心交付）

> 详见 Doc 4 §4.7 / §4.8。此处为裁决摘要。

| 动作 | 源 | 用途 | EPUB 搜索优先级 |
|------|----|------|----------------|
| KEEP | Gutendex | 英文 PD EPUB | 免费层 |
| KEEP（修） | Internet Archive | PD/上传 EPUB | 免费层 |
| KEEP（降权） | z-library | 非 PD 兜底 | **末位**（10/日 + 合规风险） |
| ADD | Standard Ebooks | 英文 PD 高质量 EPUB | 免费层 |
| ADD | Wikisource(zh) | 中文 PD EPUB | 免费层 |
| ADD（升权） | **Anna's Archive** | 非 PD 畅销书（金庸等） | **z-library 之前** |
| ADD | Google Books API | 元数据（中英文，补 pubdate/ISBN/封面） | 元数据层 |
| DROP/低优先 | LibGen、鸠摩/苦瓜/书格 | 替代或手动 | 不内置 |

**核心优化**：14 本金庸 TXT 均为非 PD，免费源结构性查不到。原「免费优先→zlib」对金庸无效，
会逐日烧 10/日配额约 2 天。将 **Anna's Archive 插到 z-library 之前**（AA 无 10/日硬上限、镜像 zlib/LibGen/读秀），
可显著提速并保留 zlib 配额。E2 的 `zlib_eta` 应改为「AA 可用不计日，AA 缺才用 zlib 配额」。

---

## 9.5 合规与运营风险（用户约束落地）

> **使用性质（用户声明）**：资源仅用于家庭私人学习参考，不做任何商用或盈利活动。在此边界下，版权风险由使用性质本身规避；下文保留的是**技术/运营风险**——即与版权无关的账户、密钥、稳定性问题，须通过 Doc 10 的管理设计化解。

1. **z-library**：账户易被封；10/日为其自身限制。仅作末位兜底（见 Doc 4 §4.8 顺序）。
2. **Anna's Archive**：设计选定 **RapidAPI 形态**（D3），key 经 `Authorization: Bearer` 头传递、**不出现在下载 URL**，故此前「会员 secret 出现在 URL query 被日志/代理观测」的风险在本形态下不再成立；仍遵守 Doc 10 §10.4.2 的 `_redact()` 脱敏（对任何含 `key=/token=` 的返回 URL 兜底）+ 原始 URL 不持久化；密钥只存 `secrets.env`（chmod 600）。
3. **鸠摩搜书 / 苦瓜书盘 / 书格**：爬虫 + ToS 风险，且稳定性差。→ 列为不内置（Doc 4 §4.7.3 DROP/低优先）。
4. **合规安全源（优先）**：Gutendex、Standard Ebooks、Wikisource、Internet Archive(PD)、Google Books(仅元数据)、Douban/OpenLibrary(仅元数据) 均为合法且无账号源，已排在最前（Doc 4 §4.0 / §4.8）。
5. **反批量爬取保障**：系统仅做单标题定向检索，禁止遍历目录；每源 `min_interval` 节流；扫描仅针对缺 EPUB 的书。详见 **Doc 10 §10.5**。
6. **密钥管理交付**：需密钥源的配置模板与安全管理方案已全部设计在 **Doc 10**，用户填写 `secrets.env` / `sources_config.yaml` 后重启即启用，无需改动代码。

---

## 9.6 三大流程改进（Top 3）

1. **修 B3 并发串号（P1）**：book_id 改由 `calibredb add` stdout 持锁解析，杜绝并发上传错绑。
2. **修全库去重失效（P7）**：扫描改为循环后 `dd.dedupe_all()` 一次，真正达成「同名重复 → 去重」。
3. **引入 Anna's Archive 替代 z-library 优先级（P4.7）**：解决 14 本金庸非 PD 书的配额瓶颈，提速且降合规暴露。

---

## 9.7 落地前仍须实测项（接 Doc 4 §4.4）

- `zlibrary` 包真实签名（B2）。
- Anna's Archive 所选 API（RapidAPI / 自建爬虫 / 会员 fast-download）的可用性与 key 获取方式。
- Wikisource 条目名映射（搜索词→维基文库条目）。
- Google Books 申请 API key 以避开 `userRateLimitExceededUnreg` 限流。

---

## 9.8 本轮新增（用户指令落地，2026-08-24）

- **新增 Doc 10**：配置与密钥管理——`sources_config.yaml`（启用/调序/频控模板）、`secrets.env` 密钥段模板、日志脱敏 `_redact()`、密钥轮换步骤、反批量爬取保障表。用户填完即启用，零代码改动。
- **Doc 4 §4.0 / §4.9**：落地「无账号源优先」「仅按需检索/绝不批量爬取」「密钥脱敏」三项约束。
- **Doc 9 §9.5**：改写为「使用性质（用户声明：家庭学习参考、非商用） + 技术/运营风险（账户封禁、URL 密钥泄露）」，风险化解指向 Doc 10。
- **未做实现**：本轮仅文档规划，未写任何 .py、未改系统配置、未运行管线。

---

## 9.9 跨文档复核（新源集成 + 频控接线，2026-08-24 第二轮）

> 本轮聚焦：新源（Standard Ebooks / Wikisource / Anna's / Google Books）接入后，
> Doc 4/5/6/7 与 Doc 10 的接口一致性、Google Books 元数据缺口、Anna's 感知 ETA、频控接线。
> 本轮修复项编号 G1–G4（均为设计级文档修订，未写代码）。

### 9.9.1 发现的缺口（G1–G4）

| 缺口 | 位置 | 问题 |
|------|------|------|
| **G1 Google Books 未接入元数据** | Doc 5 §5.1 `enrich()` | 仅链 `Douban → OpenLibrary`；`enrich_google`（Doc 4 §4.8）与 Doc 10 §10.2 `metadata_order` 第 2 位均未落地 |
| **G2 annas 候选无下载通路** | Doc 4 §4.2 `download_epub` | `search_epub`（§4.8）可返回 `annas` 候选，但 `download_epub` 的 `else` 分支用 `requests.get` 直拉 md5 URL 只会 404；Doc 6/7 只调 `download_epub`，annas 下载会失败 |
| **G3 频控未接线** | Doc 4 vs Doc 10 §10.5 | Doc 10 定义每源 `min_interval`，但 Doc 4 各 `search_*` 原先未调用任何节流，Doc 6/7 也未引用 `rate_limit`，频控表悬空 |
| **G4 Anna's 未进 ETA/配额** | Doc 4 §4.6 + Doc 7 §7.2/§7.3 | Doc 4 §4.7.2 已声明「AA 可用不计 zlib 日」，但 `zlib_eta` 未改、Doc 7 `_needs_zlib` 仍只查 gutendex+IA 且按非 PD 必烧 zlib 计；与「AA 在 zlib 之前」矛盾 |

### 9.9.2 修复摘要

- **G1 已修（Doc 5 §5.1）**：新增 `_find_meta()` = `Douban → enrich_google → OpenLibrary`，与 Doc 10 顺序一致；`enrich_google` 的 `publishedDate→pubdate`、`imageLinks.thumbnail→cover_url` 已归一进通用 `src`，复用既有 `parse_pubdate` 与 `download_openlibrary_cover`；未配 key 时 `enrich_google` 返回 `None` 无缝降级。
- **G2 已修（Doc 4 §4.2 + Doc 6 §6.6）**：`download_epub` 增加 `elif cand.source == "annas": return download_annas(cand, dest_path)` 分发；明确不计入 zlib 配额；Doc 6 `_search_and_add` 改返回实际命中 `source`（供 G4 扣减判断）。
- **G3 已修（Doc 4 §4.10 + Doc 6 §6.6）**：新增 `rate_limit(source_key)` 令牌桶助手（参数读 Doc 10 §10.2）；规定每个 `search_*` 首行调用对应键；因 `search_epub` 内部串起各 `search_*`，Doc 6/7 照常调 `search_epub` 即自动获得每源节流，扫描路径亦被令牌桶守住。
- **G4 已修（Doc 4 §4.6 + Doc 7 §7.2/§7.3/§7.5）**：Doc 4 `zlib_eta` 注明 `needed` 须为「AA 感知后真正落 zlib 的书数」；Doc 7 新增 `_aa_available()` / `_needs_zlib_quota()`（免费四源 miss 且 AA 不可用才计 zlib），配额扣减改为 `used_src == "zlibrary"` 才 `-=1`，AA/免费命中不扣；金庸 14 本现优先走 AA，ETA 归零、不再强绑 2 天。

### 9.9.3 统一的源优先级 + 频控流（修复后）

```
上传/扫描触发 → es.search_epub(title)
   ├─ rate_limit("standard_ebooks")  → search_standard_ebooks   (无账号, 英文 PD)
   ├─ rate_limit("wikisource_zh")    → search_wikisource        (无账号, 中文 PD)
   ├─ rate_limit("gutendex")         → search_gutendex          (无账号, 古典中英)
   ├─ rate_limit("internet_archive") → search_ia                (无账号, PD/上传)
   └─ 免费四源全 miss 才进入非 PD 层：
        ├─ rate_limit("annas_archive") → search_annas   (需密钥, 非 PD 首选, 无 10/日硬上限)
        └─ rate_limit("zlibrary")      → search_zlibrary(需账号, 非 PD 末位, 10/日)
   命中候选 → es.download_epub(cand):
        ├─ zlibrary → 计入 zlib 配额 (_zlib_quota_inc)
        ├─ annas   → download_annas（不计 zlib 配额）
        └─ 其余    → 直链 GET
元数据（Doc 5 enrich）：_find_meta = Douban → enrich_google(rate_limit("google_books")) → OpenLibrary
日限额：zlib 10/日；AA 按 key 配额内部控（0=不限，见 Doc 10 §10.2）。
ETA：zlib_eta(needed)，needed = 免费四源 miss 且 AA 不可用/也 miss 的书数（AA 感知）。
```

### 9.9.4 剩余开放问题（待用户决策/实测）

1. **`_needs_zlib_quota` 的 AA 预探测是保守的**：它仅依「AA key 是否配置」判定，不实际调 AA 验证命中。若 AA key 已配但对某书也无果，该书仍会被乐观地排除出 zlib 配额池、并在 `search_epub` 时真正走 zlib 却未提前计 ETA——实际扣减仍正确（按 `used_src=="zlibrary"`），仅 ETA 预估值偏乐观。是否需要在预探测中真正调用一次 `search_annas`？调用代价是每次扫描多做一次 AA 检索（被 `rate_limit` 节流）。建议维持现状（不预调 AA），以「实际扣减为准」保证配额准确。
2. **Google Books key**：Doc 10 §10.3 `GOOGLE_BOOKS_API_KEY` 为空时 `enrich_google` 走未注册限流（可能 403）。是否需要本轮申请 key？属 Doc 9 §9.7 已列实测项，待用户。
3. **Anna's 实际 API 形态**（RapidAPI vs 会员 fast-download vs 自建爬虫）未定，Doc 4 §4.8 以 `search_annas`/`download_annas` 接口占位，落地前须按 Doc 9 §9.7 实测修正签名。

---

## 9.10 架构原则（Round 3 新增：精简 / 不引入额外部署 / 不用 Docker）

> 用户原则（原话）：「不要引入 Docker，原则是不引入任何可能增加服务器负担的其他部署方式，一定要保持项目的精简高效低耗稳定。」
> 本轮据此审计全部设计文档，结论如下，供 Doc 1 / Doc 10 引用。

1. **不引入 Docker / 容器化**：全栈为裸进程 + systemd，`deploy/` 下为 service 单元与补丁文件，无 Dockerfile / compose。后续任何文档**不得**提出容器化部署；若提及，须显式标注「not used, rejected by design」。
2. **不新增常驻守护进程**：仅保留三个服务——`calibre-web.service`、`calibre-async-upload.service`、`cloudflared.service`。
   - **Doc 7 §7.6 的 `calibre-scan.timer` 是 systemd 定时器 + `Type=oneshot`（`curl` 触发 `/api/scan`）**，属一次性任务、**非新守护进程**，符合精简原则，确认保留。
3. **不引入 Redis / MQ**：任务队列用 SQLite（`tasks.db`）。经核实——`/opt/calibre-web` 应用代码与 `/opt/calibre-stack`（server.py / metadata-tool/src）均**无 `import redis`**；本机 Redis 仅因其他无关用途运行。故 **Doc 1 §1.4 已标记为可选**（仅当本机其他应用实际用 Redis 才执行），对本项目属不必要开销。
4. **轻框架**：`async-upload/server.py` 保持标准库 `http.server`（已核实，无 Flask/Django/FastAPI）。任何文档不得暗示引入重框架。
5. **唯一新增运行时依赖**：`zlibrary` pip 包（Doc 4 §4.4），属单一轻量依赖，可接受；`requests` 已由 metadata-tool 提供，非新增。Doc 10 §10.1 原则中追加此条。

---

## 9.11 Round 3 复审结论（新增用户决策 D1–D3 + 两维度审计）

> 日期：2026-08-24（第三轮）。仅改 docs/design/，未写 .py、未改系统配置、未跑管线。

### 9.11.1 用户决策落地
- **D1（ETA 乐观，不预调 AA）**：已确认 Doc 7 / Doc 9 §9.9.4-① 维持「`_needs_zlib_quota` 仅按 AA key 是否配置判定、不实际调用 `search_annas` 取精确计数」的乐观行为。无需改动，本结论重申采纳。
- **D2（Google Books 免 key）**：Doc 10 §10.3 新增 §10.3.2——默认免 key 运行 `enrich_google`，遇 `403 userRateLimitExceededUnreg` 再「按需申请」Books API key 填入 `GOOGLE_BOOKS_API_KEY`；不强制 key。
- **D3（Anna's = RapidAPI 形态，但用户无账号 → DISABLED）**：
  - 设计选定 **RapidAPI `annas-archive-api`** 为唯一集成形态（最稳定、无爬取、ToS 更干净），放弃会员 secret 与自建爬虫两形态（Doc 4 §4.7.2 / §4.8）。
  - 因用户无 Anna's 账号，Doc 4（§4.1/§4.7.2/§4.7.3/§4.8）、Doc 10（§10.2/§10.3）均将 Anna's 标记为 **UNAVAILABLE/DISABLED**。
  - 明确声明（Doc 4 §4.7.2 callout、Doc 10 §10.3.1）：用户补齐 **EITHER** Anna's（RapidAPI key）**OR** z-library（邮箱+密码）前，14 本金庸等非 PD 书**无自动 EPUB 来源**（免费 PD 源结构性查不到）。

### 9.11.2 维度一：精简原则审计结果
| 审计项 | 发现 | 处置 |
|--------|------|------|
| Docker/容器 | 全栈无 Dockerfile/compose，文档无 Docker 提议 | 无违规；§9.10 立则为「rejected by design」 |
| 新守护进程 | 仅 3 个服务 + 1 个 oneshot 定时器（calibre-scan.timer） | 定时器非守护进程，符合；§9.10 确认 |
| Redis | 本栈未使用 Redis（无 import）；Doc 1 §1.4 原强制改密码 | §1.4 改标「可选/仅他应用用 Redis 才执行」；§9.10 引用 |
| 重框架 | server.py = stdlib http.server，无 Flask/Django | 无违规；§9.10 确认 |
| 新增依赖 | 仅 `zlibrary` 一个 pip 包 | 可接受；Doc 10 §10.1 注明其为唯一新增运行时依赖 |

### 9.11.3 维度二：nginx 鉴权覆盖结论
- **机制核实**：`/_auth_check` 未登录返回 `302` → `auth_request` 映射为 **500** → live nginx 第 18 行 server 级 `error_page 500 = @login_redirect;` 触发登录跳转。该 server 级配置覆盖 `/async-upload`、`/api/`、`/tasks` 全部 `auth_request` 位置。
- **新端点覆盖判定**：
  - `/tasks`（HTML，Doc 2 §2.3 待加 `auth_request /_auth_check`）✅ 设计已含。
  - `/api/tasks`、`/api/scan`、`/api/tasks/{id}/retry`、`/api/books/{id}/{action}` 均以 `/api/` 开头，由 live `/api/` location 的 `auth_request /_auth_check` 覆盖 ✅。
  - `/api/upload` 已由 live `/api/` 覆盖 ✅。
- **既往误判修正**：Doc 9 §9.2.4 称「需补 `error_page 401`」系误判（本流程不产生 401），Round 3 已在 Doc 2 §2.3 删除该死配置并说明真因。**无覆盖缺口**。
- 建议（非阻塞）：`server.py:111` 的 `200MB` 上限与 nginx `100M` 不一致，实施时对齐到 100MB。

### 9.11.4 仍待用户/实测项（开放问题）
1. **非 PD 书来源**：用户须提供 Anna's RapidAPI key 或 z-library 凭据，否则 14 本金庸仅 PD 书能自动取 EPUB（Doc 10 §10.3.1）。
2. **cloudflared 明文 token**：live `/etc/systemd/system/cloudflared.service` 仍含 `--token eyJ…` 明文（Doc 1 §1.3 方案未落到 live）。超出本轮文档范围，但提示用户按 Doc 1 §1.3 执行 `--token-file` 改造。
3. **Anna's RapidAPI 真实签名**：落地前须按 Doc 9 §9.7 实测 `search_annas`/`download_annas` 的 RapidAPI 参数与返回结构。
4. **Google Books**：先免 key 试用，仅限流时再申请 key（D2）。

---

## 9.12 Round 4 结论（域名验证调研 + 防钓鱼信任锚，新增用户决策 E1–E2）

> 日期：2026-08-24（第四轮）。仅改 docs/design/，未写 .py、未改系统配置。

### 9.12.1 调研发现：z-library / Anna's 域名频繁切换

- **z-library**：官方声明唯一正式域 `z-lib.id`（2025 年公告），SSO 登录走 `singlelogin.re / singlelogin.co`。大量仿冒镜像存在（Wikipedia 确认钓鱼站窃取凭据），常见仿域含 `z-lib.cx`、`z-library.*` 等。域名频繁更换（好读器、PNN 等来源报道）。
- **Anna's Archive**：官方镜像 `.gl / .pk / .gd`（FAQ 明确列出），FAQ 标记 `.su / .io / .is` 为欺诈。发布 **PGP 签名公告**（公钥指纹 `0D71 8B0A 3412 9CE1 AB50 42DF DB31 2C32 7E58 6040`），可验证新域名公告真实性。
- **风险**：若用户误入伪造站并输入凭据，账户即被窃取。

### 9.12.2 设计决策：域名信任锚（Doc 10 §10.7 新增）

| 决策项 | 设计 |
|--------|------|
| 信任锚 = 用户策展白名单 | `sources_config.yaml` 新增 `site_anchors`（`zlib_base_url` / `zlib_sso_url` / `annas_base_url`），由用户通过官方渠道核实后填写，系统绝不自动解析或硬编码域名 |
| TLS 证书校验永远开启 | `verify=True`（绝不 `verify=False`）；钓鱼站常持无效/自签证书 |
| 证书固定（可选） | `zlib_cert_pin` / `annas_cert_pin` 存官方域 leaf cert SHA256 指纹，握手后比对，不符则中止 + 告警 |
| 重定向拒绝 | `allow_redirects=False`；3xx 跳转到非白名单主机 → 中止 |
| 凭据发送三重检查 | (a) 主机在白名单 (b) TLS 有效且指纹匹配 (c) 登录页 URL 符合预期 SSO 模式 → 才发送；任一不满足 → 中止 + 记日志 |
| 弃用 `zlibrary` PyPI 包 | 改为自研极简客户端（仅 `requests`），只与用户确认的 `zlib_base_url` 通信 + 证书固定 + 重定向拒绝。理由：(a) 安全——包内域名解析不透明；(b) 精简——去掉一个外部依赖 |
| 操作建议 | 用户专设唯一密码；书签官方域名；填凭据前手动核对官方渠道；Anna's 可验证 PGP 签名公告确认新域名 |

### 9.12.3 已更新文档

| 文档 | 更新内容 |
|------|----------|
| Doc 10 | §10.1 新增原则 #6（域名信任锚）、#7（弃用 zlibrary 包）；新增 **§10.7 官方站点验证与防钓鱼**（威胁模型 + 白名单设计 + 硬规则 + 操作建议） |
| Doc 4 | §4.2 `search_zlibrary` / `download_epub` 改用 `zlib_client.py`（自研客户端）；§4.4 改为弃用 `zlibrary` PyPI 包、标注零新增依赖；§4.9 新增域名信任 bullet |
| Doc 9 | 本节 §9.12 记录调研发现 + 设计决策 |

### 9.12.4 仍待用户/实测项

1. **z-library 凭据 + 域名核实**：用户须提供 `ZLIB_EMAIL` / `ZLIB_PASSWORD` 并在 `sources_config.yaml` 填入经过官方渠道核实的 `zlib_base_url`，否则 14 本金庸无自动 EPUB 来源。
2. **Anna's 账号**：用户须注册 Anna's Archive 账号以获取 RapidAPI key，否则 Anna's 持续 DISABLED。
3. **Google Books**：先免 key 试用，仅限流时再申请 key（D2，Doc 10 §10.3.2）。
4. **`zlib_client.py` 实施**：落地时须用 `requests` 实现 `ZLibClient`（login / search / download_book），内部强制 `site_anchors.zlib_base_url` + 证书固定 + `allow_redirects=False`。
