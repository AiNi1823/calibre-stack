# Design Doc 4: EPUB Sources (Phase 2)

> 前置：Phase 1
> 产出：epub_sources.py（仅依赖 requests，零新增外部包）
> 外部：Gutendex / Standard Ebooks / Wikisource / Internet Archive（均**无需账号**）
>       Anna's Archive / z-library（**需密钥/账号**，见 Doc 10）

---

## 4.0 用户约束落地（重要）

依据用户指令，资源获取遵循：

1. **无账号源优先**：免费无账号源（Standard Ebooks / Wikisource / Gutendex / IA / Google Books 元数据）排在最前；仅当免费源无果，才动用需密钥的 Anna's Archive / z-library（见 §4.8 新 `search_epub` 顺序）。**注意（Round 3 / D3）：用户当前无 Anna's 账号，且设计选定 RapidAPI 形态需其 key，故 Anna's 标记为 UNAVAILABLE/DISABLED（见 §4.7.2 / §4.8 / Doc 10）；在用户补齐 Anna's 凭据或 z-library 凭据前，14 本金庸非 PD TXT 书无自动 EPUB 来源（免费 PD 源结构性查不到，详见 §4.7.2）。**
2. **仅按需检索，绝不批量爬取**：系统只对「具体书名」做定向搜索（上传一本查一本 / 扫描仅针对缺 EPUB 的书）。**禁止**枚举或分页遍历任何源站完整目录。频控与反爬保障见 Doc 10 §10.5。
3. **密钥管理**：需密钥的源一律读 `secrets.env`（用户填写，chmod 600），代码零明文；日志中 URL 含密钥/会员 secret 须脱敏（Doc 10 §10.4.2）。配置模板见 **Doc 10**。
4. **使用性质**：资源仅用于家庭私人学习参考，不做商用或盈利。

---

## 4.1 已验证事实

| 源 | 可达性 | 中文 | 认证 | 备注 |
|----|--------|------|------|------|
| Gutendex | ✅ via proxy | 仅古典(三國) | 无 | `/books?search=&languages=zh` |
| Internet Archive | ✅ via proxy | 有 | 无 | `advancedsearch.php?q=title:射雕` |
| z-library | ⚠ 需凭据(未装包) | 强 | 邮箱+密码 | 10下载/日 |
| Anna's Archive | ⛔ **需账号，当前 UNAVAILABLE/DISABLED** | 强(非PD) | RapidAPI key（设计选定形态，见 §4.7.2） | 按 key 配额 |

> **z-library 客户端**：自研极简实现（`zlib_client.py`），不引入 `zlibrary` PyPI 包。
> 域名信任锚 + 证书固定见 Doc 10 §10.7。

Proxy: `http://127.0.0.1:7890`（所有外网请求必须走代理）。

## 4.2 接口设计

```python
# /opt/calibre-stack/async-upload/epub_sources.py
import os, requests, logging, json, time, re
from datetime import date

log = logging.getLogger("epub_sources")
PROXY = os.environ.get("HTTP_PROXY", "http://127.0.0.1:7890")
PROXIES = {"http": PROXY, "https": PROXY}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
TIMEOUT = 20

ZLIB_QUOTA_FILE = "/opt/calibre-stack/async-upload/zlib_quota.json"

class Candidate:
    def __init__(self, source, title, author, url, fmt="epub"):
        self.source, self.title, self.author = source, title, author
        self.url, self.fmt = url, fmt

def _title_ok(query, found):
    q = re.sub(r"[（(].*?[)）]", "", query).strip()
    f = re.sub(r"[（(].*?[)）]", "", found).strip()
    return q in f or f in q or q == f

# ---- Gutendex ----
def search_gutendex(title, author=""):
    try:
        r = requests.get("https://gutendex.com/books",
                         params={"search": title, "languages": "zh"},
                         proxies=PROXIES, timeout=TIMEOUT)
        out = []
        for b in r.json().get("results", []):
            if _title_ok(title, b["title"]):
                ep = b["formats"].get("application/epub+zip")
                if ep: out.append(Candidate("gutendex", b["title"], "", ep))
        return out
    except Exception as e:
        log.warning("gutendex: %s", e); return []

# ---- Internet Archive ----
def search_ia(title, author=""):
    q = f'title:{title} mediatype:texts'
    try:
        r = requests.get("https://archive.org/advancedsearch.php",
                          params={"q": q, "output": "json", "rows": 10},
                          proxies=PROXIES, timeout=TIMEOUT)
        out = []
        for d in r.json()["response"]["docs"]:
            if _title_ok(title, d.get("title", "")):
                iaid = d["identifier"]
                # B3-IA：必须查 metadata 接口拿真实文件名，
                # 不能假设 {iaid}_epub.zip（多半 404）。
                m = requests.get(f"https://archive.org/metadata/{iaid}",
                                 proxies=PROXIES, timeout=TIMEOUT)
                ep = None
                for f in m.json().get("files", []):
                    if f.get("name", "").lower().endswith(".epub"):
                        ep = f"https://archive.org/download/{iaid}/{f['name']}"
                        break
                if ep:
                    out.append(Candidate("ia", d["title"], d.get("creator",""), ep))
        return out
    except Exception as e:
        log.warning("ia: %s", e); return []

# ---- z-library ----
def _zlib_quota():
    try:
        d = json.load(open(ZLIB_QUOTA_FILE))
        if d.get("date") != str(date.today()):
            d = {"date": str(date.today()), "used": 0, "daily_limit": 10}
    except Exception:
        d = {"date": str(date.today()), "used": 0, "daily_limit": 10}
    return d

def _zlib_quota_inc():
    d = _zlib_quota(); d["used"] += 1
    json.dump(d, open(ZLIB_QUOTA_FILE, "w"))

def zlib_remaining():
    """今日剩余配额"""
    return max(0, _zlib_quota()["daily_limit"] - _zlib_quota()["used"])

def zlib_eta(needed):
    """预计还需几天（按每日配额 10 铺开，ceil 估算）"""
    if needed <= 0: return 0
    return (needed + 9) // 10

def search_zlibrary(title, author=""):
    """自研客户端，只与 site_anchors.zlib_base_url 通信 + 证书固定（Doc 10 §10.7）"""
    d = _zlib_quota()
    if d["used"] >= d["daily_limit"]:
        log.info("zlib quota exhausted today"); return []
    try:
        email = os.environ.get("ZLIB_EMAIL"); pwd = os.environ.get("ZLIB_PASSWORD")
        if not email: return []
        from zlib_client import ZLibClient  # 自研极简客户端（§4.4 / Doc 10 §10.7）
        z = ZLibClient()
        z.login(email, pwd)
        results = z.search(title, limit=5)
        out = []
        for b in results:
            if _title_ok(title, b.get("title","")):
                out.append(Candidate("zlibrary", b["title"],
                                     b.get("authors",""), b.get("id")))
        return out
    except Exception as e:
        log.warning("zlibrary: %s", e); return []

# ---- 统一入口 ----
def search_epub(title, author=""):
    """按优先级返回候选列表（已过滤标题匹配）"""
    cands = []
    cands += search_gutendex(title, author)
    cands += search_ia(title, author)
    cands += search_zlibrary(title, author)
    return cands

def download_epub(cand, dest_path):
    """下载候选到 dest_path，成功返回 True；统一入口，按来源分发到具体下载器"""
    try:
        if cand.source == "zlibrary":
            from zlib_client import ZLibClient  # 自研极简客户端（Doc 10 §10.7）
            z = ZLibClient()
            z.login(os.environ.get("ZLIB_EMAIL"), os.environ.get("ZLIB_PASSWORD"))
            z.download_book(cand.url, dest_path)
            _zlib_quota_inc()
        elif cand.source == "annas":
            # G2 整合：search_epub（§4.8）可能返回 annas 候选，本统一入口须能下载之，
            # 否则 Doc 6/7 调用 es.download_epub 对 annas 候选只会走 else 分支而 404。
            # 不计入 zlib 配额（AA 自身配额由 download_annas 内部控，见 Doc 10 §10.5）。
            return download_annas(cand, dest_path)
        else:
            # standard_ebooks / wikisource / gutendex / ia 均为直链 GET
            r = requests.get(cand.url, proxies=PROXIES, timeout=60, headers={"User-Agent": UA})
            if r.status_code == 200 and len(r.content) > 1000:
                open(dest_path, "wb").write(r.content)
            else:
                return False
        return os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000
    except Exception as e:
        log.warning("download %s: %s", cand.source, e); return False
```

## 4.3 使用约定

`post_process.py` 在 `searching_epub` 阶段：
```python
cands = epub_sources.search_epub(title, author)
for c in cands:
    if epub_sources.download_epub(c, epub_tmp):
        calibredb add_format book_id epub_tmp
        break
```

## 4.4 安装依赖（弃用 zlibrary PyPI 包，改用自研客户端，Doc 10 §10.7）

**不再引入 `zlibrary` PyPI 包**。该包内部域名解析不透明，可能把凭据发往伪造域；且属额外依赖，违反精简原则。改为**自研极简客户端**（仅用 `requests`），只与用户确认的 `zlib_base_url` 通信 + 证书固定 + 重定向拒绝。详见 Doc 10 §10.7。

```bash
# 无需额外安装；requests 已存在于项目依赖中
# 自研客户端代码在 async-upload/zlib_client.py（实施时新建，仅几行）
```

> 凭据由用户提供后填入 `secrets.env` 的 `ZLIB_EMAIL` / `ZLIB_PASSWORD`。
> 未提供前，`search_zlibrary` 因 `email` 为空直接返回 `[]`，不影响 Gutendex/IA 路径。

## 4.5 验证

```python
python3 -c "
import epub_sources as e
c = e.search_epub('三國志演義')
print('gutendex hits:', len(c))
"  # 期望 >=1
```

## 4.6 边界

- z-library 配额按日历日重置，落 JSON 文件（`used` / `daily_limit`）
- **E2（AA 感知，本轮修订）**：`zlib_eta(needed)` 仍按 `ceil(needed/10)` 估算天数，供 /tasks 页展示「还需 N 天」。
  但 **`needed` 必须是「真正落到 zlib 的书数」**——即免费四源无果**且** Anna's 也无果/未配 key 的书。
  因 `search_epub`（§4.8）已把 AA 排在 zlib **之前**，非 PD 书优先由 AA 满足，只有 AA 也缺时才烧 zlib 10/日；
  故 `zlib_eta` 的入参 `needed` 由 Doc 7 的 AA 感知逻辑计算（见 Doc 7 §7.3 修订），本函数只负责按 zlib 配额换算天数。
- 所有外网请求强制走 proxy
- 标题不匹配则丢弃（避免错误下载）
- 下载失败不影响后续候选

---

## 4.7 资源来源评估与推荐（复审修订）

> 复审结论：原 §4.1 三源选型对「中文畅销书（金庸等）」覆盖严重不足，
> 且 IA 的 EPUB 直链假设错误（已修 §4.2）。以下为重新评估与推荐。

### 4.7.1 当前三源对本案的适用性

| 源 | 内容性质 | 中文畅销书（金庸等） | 自动化友好度 | 风险 |
|----|----------|----------------------|--------------|------|
| Gutendex | 公有领域（PD）英文为主，少量古典中文（三國等） | ❌ 金庸非 PD（2009 年逝世，版权约至 2070s），永不命中 | ✅ 干净 REST JSON，无需认证 | 无（合法 PD） |
| Internet Archive | PD + 用户上传混合；`title:` 需近似精确匹配，对中文模糊标题召回差 | ⚠ 偶发，但非畅销书主力 | ⚠ 需二次查 metadata 拿真实文件名（已修） | 低（多为 PD/已授权） |
| z-library | 盗版库，含非 PD 畅销书 | ✅ 有金庸等，但需账户 + 10 本/日上限 + ToS/法律风险 | ⚠ 需凭据、自研客户端（Doc 10 §10.7） | 高（版权 + 账户封禁） |

**关键事实**：14 本金庸 TXT 均为非 PD 作品，Gutendex/IA 免费源**结构性**查不到。
原「免费源优先 → z-library 兜底」策略在金庸场景会逐日烧掉 zlib 的 10/日配额，
约 2 天才能补齐 14 本（见 Doc 7 §7.3）。这是方案的瓶颈。

### 4.7.2 候选增补源评估

**EPUB 下载：**
- **Standard Ebooks**（https://standardebooks.org/feeds/opds）：精选 PD 英文经典，
  质量极高（排版/元数据），OPDS feed 或解析 HTML 均可，无密钥。→ 英文 PD 最佳，**合法**。
  缺点：仅英文 PD，无金庸。
- **Wikisource**（ws-export 工具 https://ws-export.wmcloud.org）：PD 内容，**含中文维基文库**，
  可导出 EPUB（及 MOBI）。接口：`?lang=zh&title=...&format=epub-3`。→ 中文 PD 古典可用，**合法**。
  缺点：仅 PD，无畅销书；部分条目未完成校对。
- **Anna's Archive**（annas-archive.org）：镜像 z-lib + LibGen + 读秀(duxiu) + IA 等，
   覆盖非 PD 畅销书（含金庸）。**设计选定集成形态（Round 3 / D3）：RapidAPI `annas-archive-api`**
   （Bearer key，限流，可按 `source` 过滤 zLibraryChinese/libgen 等）。理由：最稳定、无爬取、
   ToS 更干净；**放弃**自建爬虫（scrape 搜索页取 md5）与会员 secret key 两种形态（已评估为稳定性/合规更差）。
   **无 zlib 那种 10/日硬上限**（按 key 配额内部控）。→ 解决金庸瓶颈的优选。
   缺点：⚠ **ToS/版权风险同 z-lib**；且 **用户当前无 Anna's 账号 → 本源标记为 UNAVAILABLE/DISABLED**，
   在补齐 RapidAPI key 前 `search_annas` 静默跳过（见 §4.8 / Doc 10「需要你提供」）。

   > **⚠ 非 PD 书无自动来源声明（Round 3 / D3）**：14 本金庸 TXT 均为非 PD 作品，Gutendex / Standard Ebooks /
   > Wikisource / Internet Archive 等免费 PD 源**结构性无法返回**它们。因此——在用户**补齐 EITHER
   > Anna's 账号（RapidAPI key）OR z-library 凭据（邮箱+密码）之前**，这 14 本非 PD 书**没有任何自动化 EPUB 来源**，
   > 流水线对它们只能停在「未找到 EPUB 替代源」。仅 PD 书可自动得到 EPUB。
- **LibGen**：含大量小说 EPUB，但**无干净 API**（FTP/SQL dump 或 libgen.is OPDS），自动化成本高。→ 低优先。
- **中文聚合站**（鸠摩搜书 jiumodiary.com、苦瓜书盘、书格 shuge.org）：
  鸠摩是搜索聚合、返回直链，但需爬 `init_hubs.php`/`ajax_fetch_hubs.php`；书格仅为 PD 古籍（非畅销）。
  → 可选但**爬虫 + ToS 风险**，稳定性差，列为低优先/可选。

**元数据：**
- **Google Books API**（https://www.googleapis.com/books/v1/volumes?q=...）：**无需密钥**（未注册会被限流 403，建议申请 key），
  返回标题/作者/ISBN/出版年/简介/封面，中英文均好。→ **强烈建议增补**为元数据第 3 源，
  尤其补 OpenLibrary 缺的 `pubdate`（见 Doc 5 缺陷）。
- 现有 Douban（中文最佳）、OpenLibrary（英文）保留。

### 4.7.3 推荐结论（keep / add / drop + 优先级）

| 动作 | 源 | 用途 | 优先级（EPUB 搜索顺序） |
|------|----|------|------------------------|
| KEEP | Gutendex | 英文 PD EPUB | 免费层 |
| KEEP（修 URL） | Internet Archive | PD/上传 EPUB | 免费层 |
| KEEP（降权） | z-library | 非 PD 兜底 | **末位**（10/日，合规风险） |
| ADD | Standard Ebooks | 英文 PD EPUB（高质量） | 免费层 |
| ADD | Wikisource(zh) | 中文 PD EPUB | 免费层 |
| ADD（升权，⛔ 当前 DISABLED 待账号） | **Anna's Archive**（RapidAPI 形态） | 非 PD 畅销书（金庸） | **z-library 之前**（启用后） |
| ADD | Google Books API | 元数据（中英文，补 pubdate/ISBN/封面） | 元数据层 |
| DROP/低优先 | LibGen、鸠摩/苦瓜/书格 | 替代或可选 | 不内置，按需手动 |

**对 14 本金庸书的优化**：把 Anna's Archive 插到 z-library **之前**，
金庸类非 PD 书优先走 AA（配额更宽松），仅 AA 也缺时才烧 zlib 10/日。
原「免费优先→zlib」对金庸无效（免费源必空），故插入 AA 是核心提速点。

**E2 需同步调整**：`zlib_eta` 仅统计 zlib 配额；引入 AA 后应为
「AA 可用则不计日，AA 缺才用 zlib 配额」——见 §4.8 `search_epub` 新优先级。

---

## 4.8 新增源客户端（设计级接口，非生产代码）

```python
# 设计层接口：实际实现前需按 §4.4 方式实测各 API 签名
class SourceClient:
    name = ""
    def search(self, title, author="") -> list[Candidate]: ...
    def download(self, cand: Candidate, dest: str) -> bool: ...

# ---- Standard Ebooks（OPDS / HTML，无密钥）----
def search_standard_ebooks(title):
    # GET https://standardebooks.org/feeds/opds 或解析 /ebooks 列表
    # 命中后取 /ebooks/<author>/<slug>/downloads/<slug>.epub
    ...

# ---- Wikisource（ws-export 工具）----
def search_wikisource(title, lang="zh"):
    # GET https://ws-export.wmcloud.org/api/export?lang=zh&title=<title>&format=epub-3
    # 返回 EPUB 字节流；标题需是维基文库条目名，需先 search 取条目
    ...

# ---- Anna's Archive（设计选定形态：RapidAPI `annas-archive-api`，⛔ 当前 UNAVAILABLE/DISABLED）----
# Round 3 / D3：用户无 Anna's 账号，故本源暂停。仅当 secrets.env 提供 ANNAS_RAPIDAPI_KEY 才启用。
# 设计选定 RapidAPI（最稳定、无爬取、ToS 更干净）；已放弃自建爬虫与会员 secret 两种形态。
def search_annas(title, ext="epub", source="zLibraryChinese"):
    # 仅当 ANNAS_RAPIDAPI_KEY 已配置时调用（否则由 search_epub 守卫跳过）
    # RapidAPI：GET anna.tribestick.com ... Bearer key, limit<=50, source 过滤 zLibraryChinese/libgen
    # 返回 Candidate(source="annas", url=<下载直链>, ...)
    ...
def download_annas(cand, dest):
    # RapidAPI 返回的下载直链 GET 即可；配额记入 AA 自身限额（非 10/日），不计 zlib 配额
    ...

# ---- Google Books（元数据，无需密钥）----
def enrich_google(title, author=""):
    # GET https://www.googleapis.com/books/v1/volumes?q=intitle:<t>+inauthor:<a>&maxResults=5
    # 返回 isbn / publishedDate / description / imageLinks.thumbnail
    # 注入到 metadata_enricher 的 src 候选（见 Doc 5 §5.1 增补）
    ...

# ---- 修订后的统一入口（E2 感知 AA）----
def _free_hit_for(title, author=""):
    """免费无账号源是否已有命中（命中则无需动用需密钥源）"""
    return (search_standard_ebooks(title)
            or search_wikisource(title)
            or search_gutendex(title)
            or search_ia(title))

def search_epub(title, author=""):
    """优先级：免费 PD 源 → Anna's Archive(非PD) → z-library(末位)
    仅按书名定向检索，绝不批量遍历目录（见 Doc 10 §10.5 频控保障）。"""
    cands = []
    cands += search_standard_ebooks(title)      # 英文 PD（无账号）
    cands += search_wikisource(title)           # 中文 PD（无账号）
    cands += search_gutendex(title)             # 古典中英（无账号）
    cands += search_ia(title)                   # 上传/PD（无账号）
    if not _free_hit_for(title):                # 免费源无果 → 才动用非 PD 源
        cands += search_annas(title)            # 非 PD 优先 AA（需密钥，Doc 10）
        cands += search_zlibrary(title)         # zlib 末位兜底（需账号，10/日）
    return cands
```

---

## 4.9 合规、频控与密钥管理（用户约束落地，详见 Doc 10）

- **无账号优先**：§4.8 的 `search_epub` 已将四个无账号源（Standard Ebooks / Wikisource / Gutendex / IA）置于最前，Anna's / z-library（需密钥）仅在免费源无果时启用——契合「无需账号即可完成的资源库优先使用」。
- **绝不批量爬取**：所有 `search_*` 均为单标题检索；配置 `sources_config.yaml` 的 `rate_limit.min_interval` 做全局节流；扫描路径（`POST /api/scan`）只对「缺 EPUB」的书发起检索，且尊重每源最小间隔。具体保障表见 **Doc 10 §10.5**。
- **密钥与脱敏**：Anna's 会员 secret / RapidAPI key、z-library 凭据只存 `secrets.env`（用户填写，chmod 600），代码零明文；下载 URL 中的 `?key=/?secret=/?md5=` 在写日志前由 `_redact()` 剥离（Doc 10 §10.4.2）。原始 URL 不持久化进 tasks.db。
- **使用性质**：资源仅用于家庭私人学习参考，不做商用或盈利（Doc 10 §10.1）。
- **域名信任锚 / 防钓鱼**：z-library / Anna's 频繁换域名，伪造镜像盛行。系统绝不自动解析域名；信任锚 = 用户策展的 `site_anchors` 白名单（Doc 10 §10.7）+ TLS 校验 + 证书固定 + 重定向拒绝 + 凭据发送三重检查。z-library 客户端为自研极简实现（`zlib_client.py`），不引入 `zlibrary` PyPI 包。
- **配置由用户填写**：启用/调序/频控见 `sources_config.yaml` 模板；密钥填写见 `secrets.env` 模板——均在 **Doc 10**，用户填完重启服务即生效，无需改代码。

---

## 4.10 频控接线（rate_limit 落地 Doc 10 §10.5）

> **G3 整合（频控接线缺口，本轮新增）**：Doc 10 §10.2/§10.5 定义了每源 `min_interval`，但 Doc 4 各 `search_*` 原先**未调用任何节流**，Doc 6/7 也未引用 `rate_limit`。若不接线，频控表只是一纸空文。本节将节流**接到真实调用点**。

### 4.10.1 节流助手（令牌桶，读 Doc 10 配置）

```python
# 频控参数与 Doc 10 §10.2 rate_limit 完全一致；实现层从 sources_config.yaml 读取，
# 此处给出默认映射，便于无配置文件时退化运行。
_RATE_CFG = {"standard_ebooks":2,"wikisource_zh":2,"gutendex":1,
             "internet_archive":2,"annas_archive":3,"zlibrary":5,"google_books":1}
_RATE = {k: {"last": 0.0, "lock": threading.Lock()} for k in _RATE_CFG}

def rate_limit(source_key):
    """在每次外部检索前调用；阻塞至距上次同源自调用 >= min_interval 秒。
    source_key 对应 Doc 10 §10.2 的 epub_search_order / metadata_order 键。"""
    cfg = _RATE_CFG.get(source_key, 1)
    st = _RATE.get(source_key, {"last":0.0,"lock":threading.Lock()})
    with st["lock"]:
        wait = cfg - (time.time() - st["last"])
        if wait > 0:
            time.sleep(wait)
        st["last"] = time.time()
```

### 4.10.2 接线点（每个 `search_*` 开头）

- **每个 `search_*` 在函数体首行调用 `rate_limit(<对应键>)`**：
  - `search_standard_ebooks` → `rate_limit("standard_ebooks")`
  - `search_wikisource` → `rate_limit("wikisource_zh")`
  - `search_gutendex` → `rate_limit("gutendex")`
  - `search_ia` → `rate_limit("internet_archive")`
  - `search_annas` → `rate_limit("annas_archive")`
  - `search_zlibrary` → `rate_limit("zlibrary")`
  - `enrich_google`（Doc 5 调用）→ `rate_limit("google_books")`
- 因 `search_epub`（§4.8）内部依次调用上述各 `search_*`，**Doc 6 `_search_and_add` / Doc 7 `scan_library` 只需照常调用 `search_epub` 即可自动获得每源节流**，无需在编排层额外接线。
- 扫描路径（Doc 7）尊重 `min_interval`：单本书的外部检索自然落在 `search_epub` 内的节流之后；循环本身不额外 sleep，但每源已被令牌桶守住，**不会**出现「只对 zlib 限 10/日却高频打其他源」的漏控。
- 退避：某源超时/429 → `log.warning` 跳下一源（Doc 10 §10.5），`rate_limit` 仍按 `min_interval` 放行，避免重试轰炸。


