# Design Doc 10: 配置与密钥管理（用户填写 + 安全管理）

> 角色：仅设计配置模板与安全管理方案，由用户填写后启用；不写实现代码、不改系统
> 关联：Doc 4（资源源）/ Doc 1（secrets.env 基础）
> 日期：2026-08-24

---

## 10.1 设计原则（来自用户指令）

1. **无账号源优先**：Gutendex / Standard Ebooks / Wikisource / Internet Archive / Google Books(元数据) 均无需账号，排在最前。仅当免费源无果，才动用需密钥的 Anna's Archive / z-library。
2. **仅按需检索，绝不批量爬取**：系统只对「具体书名」做定向搜索（上传一本查一本 / 扫描仅针对缺 EPUB 的书）。禁止枚举、分页遍历任何资源站的完整目录。
3. **密钥代码零明文**：所有密钥只存 `secrets.env`（chmod 600），由 systemd `EnvironmentFile` 注入；代码只读环境变量。
4. **日志脱敏**：任何含密钥/会员 secret 的下载 URL 在写日志前必须剥离 query 参数（见 §10.4）。
5. **使用性质声明**：资源仅用于家庭私人学习参考，不做任何商用或盈利。此声明记录于本文件，作为使用边界。
6. **官方站点验证 / 防钓鱼（域名信任锚）**：z-library / Anna's 频繁换域名，伪造镜像盛行（Wikipedia 确认 z-lib 仿站窃取凭据；Anna's FAQ 标记 `.su/.io/.is` 为欺诈）。系统**绝不**自动解析或跟随跳转到未经验证的域名；信任锚 = 用户策展的**精确域名白名单**（填前须通过官方渠道核实），并强制 TLS 校验 + 证书固定。详见 **§10.7**。
7. **弃用 `zlibrary` PyPI 包**：该包内部域名解析不透明，可能把凭据发往伪造域，且属额外依赖。改为**自研极简客户端**（仅 `requests`），只与用户确认的 `zlib_base_url` 通信 + 证书固定。符合"精简低耗"原则（见 §10.7 / Doc 4 §4.4）。

---

## 10.2 sources_config.yaml（模板，用户启用/调序）

```yaml
# /opt/calibre-stack/async-upload/sources_config.yaml
# 启用开关 + 搜索优先级（自上而下）+ 每源频控
# 改动后重启 calibre-async-upload.service 生效

epub_search_order:
  - standard_ebooks     # 无账号，英文 PD 高质量
  - wikisource_zh       # 无账号，中文 PD
  - gutendex            # 无账号，古典中英
  - internet_archive    # 无账号，PD/上传
  - annas_archive       # 需密钥(RapidAPI，设计选定形态)；⛔ 当前 DISABLED 待 ANNAS_RAPIDAPI_KEY
  - zlibrary            # 需账号，非 PD 末位（10/日）

metadata_order:
  - douban              # 无账号，中文最佳
  - google_books        # 可选 API key，中英文补 pubdate/ISBN/封面
  - open_library        # 无账号，英文

rate_limit:
  # 每个源两次调用之间的最小间隔（秒），防止高频被封
  standard_ebooks: 2
  wikisource_zh: 2
  gutendex: 1
  internet_archive: 2
  annas_archive: 3
  zlibrary: 5
  google_books: 1

daily_cap:
  zlibrary: 10          # z-library 自身限制
  annas_archive: 0      # 0 = 不限（按 key 自身配额），由 AA 客户端内部控
```

> 用户只需：确认启用顺序、按需调 `rate_limit`。其余保持默认即可。

---

## 10.3 secrets.env 模板（新增密钥段，用户填写）

在 Doc 1 已创建的 `/opt/calibre-stack/secrets.env` 末尾追加：

```bash
# ---- 资源源密钥（按需填写，留空则该源自动跳过）----

# z-library（非 PD 末位兜底；提供后 14 本金庸等书才有自动 EPUB 来源之一）
ZLIB_EMAIL=
ZLIB_PASSWORD=

# Anna's Archive（非 PD 首选，⛔ 当前 UNAVAILABLE/DISABLED：用户暂无账号）
# 设计选定集成形态：RapidAPI `annas-archive-api`（最稳定、无爬取、ToS 更干净）。
# 已放弃「会员 secret」「自建爬虫」两种形态。补齐下面 key 后本源才启用。
ANNAS_RAPIDAPI_KEY=          # RapidAPI anna.tribestick.com 的 Bearer key

# Google Books（元数据，可选 key）
# 默认【免 key 运行】；若遇 403 userRateLimitExceededUnreg 限流，再按需申请 key（见 §10.3 末尾说明）。
GOOGLE_BOOKS_API_KEY=
```

**填写规则**：
- 不填 → 对应源在 `search_epub` 中静默跳过，不影响免费源路径（已在 Doc 4 各 `search_*` 中以 `if not key: return []` 守卫）。
- 填错 → 该源抛异常被 `log.warning` 吞掉，降级到下一源，不阻断流水线。

### 10.3.1 ⚠ 需要你提供（非 PD 书自动 EPUB 的前提，Round 3 / D3）

当前仅有 **免费 PD 源**（Gutendex / Standard Ebooks / Wikisource / Internet Archive）可自动化取 EPUB。
**非 PD 书（如 14 本金庸 TXT）免费 PD 源结构性查不到**，必须有「需密钥/账号」源才能自动获取 EPUB：

| 你要提供的 | 填到 | 效果 |
|-----------|------|------|
| **Anna's Archive RapidAPI key**（`ANNAS_RAPIDAPI_KEY`） | §10.3 | 非 PD 书优先走 AA（无 10/日硬上限），14 本金庸可自动化 EPUB。**但用户当前无 Anna's 账号 → 本项暂无** |
| **z-library 邮箱+密码**（`ZLIB_EMAIL`/`ZLIB_PASSWORD`） | §10.3 | 非 PD 兜底（10/日），启用后金庸书按 zlib 配额逐日补齐 |

> **结论**：在用户补齐 **EITHER** Anna's 凭据（RapidAPI key）**OR** z-library 凭据之前，
> 14 本金庸等非 PD 书**没有任何自动化 EPUB 来源**，流水线对它们止步于「未找到 EPUB 替代源」。
> 仅 PD 书会自动得到 EPUB。此限制是数据源性质决定的，非实现缺陷（详见 Doc 4 §4.7.2）。

### 10.3.2 Google Books：免 key 运行 + 按需申请（Round 3 / D2）

- **默认免 key 运行**：`enrich_google` 在未配 `GOOGLE_BOOKS_API_KEY` 时仍可调 Google Books 未注册接口，
  命中即补元数据，未命中/限流则 `log.warning` 降级到 OpenLibrary（不阻断流水线，见 Doc 5 §5.1 / Doc 9 §9.9.2 G1）。
- **按需申请**：若日志频繁出现 `403 userRateLimitExceededUnreg`（未注册限流），再去
  https://console.cloud.google.com 申请 **Books API** key 填入 `GOOGLE_BOOKS_API_KEY` 即可提额。
  **不强制要求 key**，先免 key 试用。

---

## 10.4 安全管理

### 10.4.1 文件权限与注入
- `secrets.env`：`chmod 600`、`chown calibreweb:calibreweb`、`.gitignore` 排除（Doc 1 已做）。
- `sources_config.yaml`：同目录，权限 644 即可（无密钥）。
- systemd 单元：`EnvironmentFile=/opt/calibre-stack/secrets.env`，**不**在 `ExecStart` 写任何密钥。

### 10.4.2 日志脱敏（实现要点，设计级）
所有 `log.info/warning` 输出 URL 前，统一过一道脱敏：

```python
import re
_SENSITIVE = re.compile(r"([?&](?:key|secret|md5|token)=)[^&]+", re.I)
def _redact(url):
    return _SENSITIVE.sub(r"\1***", url)   # 仅日志用，下载仍用原 URL
# 用法：log.info("download %s", _redact(cand.url))
```
- Anna's（RapidAPI 形态）下载直链或 key 经 `Authorization: Bearer` 头传递；若任何返回 URL 含 `key=/token=` 查询参数，同样被 `_redact` 脱敏为 `***`（日志绝不出现明文密钥）。
- 下载动作本身使用原始 URL（不脱敏），但**原始 URL 不持久化**到 tasks.db 的 `detail` 字段（只存 `已下载EPUB: annas` 这类摘要）。

### 10.4.3 密钥轮换步骤（用户日后操作手册）
1. 编辑 `secrets.env`，替换对应值。
2. `systemctl restart calibre-async-upload.service`。
3. 验证：`curl -b cookie -X POST .../api/scan` 单本测试目标源是否恢复。

---

## 10.5 频控 / 反批量爬取保障（设计级）

| 保障项 | 设计 |
|--------|------|
| 检索粒度 | 仅 `search_epub(title)` 单标题检索；**禁止** `while` 翻页遍历源站 catalog |
| 全局节流 | 每源 `min_interval`（见 §10.2）用令牌桶实现，两次调用至少间隔 N 秒 |
| 上传主路径 | 用户上传一本 → 搜一本；天然不批量 |
| 扫描路径 | `POST /api/scan` 用户手动触发；循环内每本书尊重 `min_interval`；且只对「缺 EPUB」的书发起外部检索 |
| 退避 | 某源超时/429 → `log.warning` 跳下一源，不重试轰炸 |
| 日限额 | zlib 10/日（Doc 4 `zlib_quota.json`）；AA 按 key 配额内部控 |

> 以上确保「只是对上传书籍做资源获取」，不构成对资源站的批量爬取。

---

## 10.6 用户启用清单（填完即可）

- [ ] `sources_config.yaml` 确认顺序/频控（默认即可）
- [ ] `secrets.env` 按需填 `ZLIB_*` / `ANNAS_RAPIDAPI_KEY`（⛔ 暂无账号则留空，非 PD 书暂无法自动取 EPUB，见 §10.3.1）/ `GOOGLE_BOOKS_API_KEY`（免 key 可留空，见 §10.3.2）
- [ ] `systemctl restart calibre-async-upload.service`
- [ ] 单本上传测试，观察 `/tasks` 各源命中情况

---

## 10.7 官方站点验证与防钓鱼（域名信任锚）

### 10.7.1 威胁模型

z-library / Anna's Archive 频繁更换域名，催生大量伪造镜像：
- **z-library**：Wikipedia 确认存在大量钓鱼仿站（phishing clones），冒充 z-lib 窃取账户凭据。官方声明仅有 **z-lib.id** 为唯一正式域（2025 年公告）；SSO 登录走 **singlelogin.re / singlelogin.co**。
- **Anna's Archive**：官方镜像为 **annas-archive.gl / .pk / .gd**（其 FAQ 明确列出）。FAQ 同时标记 `.su / .io / .is` 为欺诈。`.org` 已非官方。Anna's 还发布 **PGP 签名公告**（公钥指纹 `0D71 8B0A 3412 9CE1 AB50 42DF DB31 2C32 7E58 6040`），用于验证新域名公告的真实性——这是验证新域名最权威的方式。

若用户访问伪造站并输入凭据，账户即被窃取。

### 10.7.2 信任锚设计：用户策展域名白名单

系统**绝不**硬编码或自动解析站点域名。信任锚 = 用户在 `sources_config.yaml` 中填写的**精确域名白名单**。

**sources_config.yaml 新增字段**：

```yaml
# 站点信任锚（必须由你手动核实后填写，绝不自动解析）
site_anchors:
  zlib_base_url: "https://z-lib.id"           # 当前官方主域（2025 年公告）；填前须核实
  zlib_sso_url: "https://singlelogin.re"      # z-library SSO 登录页
  annas_base_url: "https://annas-archive.gd"  # 当前官方镜像之一；填前须核实

  # 证书固定（可选但强烈建议）：官方域的 leaf certificate SHA256 指纹
  # 获取方法：curl -v https://z-lib.id 2>&1 | grep "SHA256 Fingerprint"
  zlib_cert_pin: ""
  annas_cert_pin: ""
```

> **用户操作**：填写前，通过官方渠道核实当前域名：
> - z-library：访问其官方公告 / singlelogin 页面确认主域
> - Anna's：打开任一已知官方镜像 → FAQ「What are your official mirrors?」核对；或验证 PGP 签名公告

### 10.7.3 硬规则：系统行为

1. **仅连接白名单主机**：所有 `requests.get/post` 只发往 `site_anchors` 中列出的精确主机名。
2. **TLS 证书校验永远开启**：`verify=True`（绝不 `verify=False`）。钓鱼站常持无效/自签证书。
3. **证书固定**：若 `site_anchors` 中配置了 `cert_pin`，握手后比对 leaf cert SHA256；不符 → 中止 + 告警。
4. **拒绝跟随重定向到非白名单主机**：`allow_redirects=False`；若 3xx 跳转到非白名单主机 → 中止。
5. **凭据发送三重检查**：仅当 (a) 主机在白名单 (b) TLS 有效且指纹匹配 (c) 登录页 URL 符合预期 SSO 模式 → 才发送凭据。任一不满足 → 中止 + 记日志。

### 10.7.4 弃用 `zlibrary` PyPI 包

该包内部域名解析不透明，可能把凭据发往非官方域。改为**自研极简客户端**（仅用 `requests`），只与用户确认的 `zlib_base_url` 通信 + 证书固定 + 重定向拒绝。

**优势**：
- 安全：域名解析由用户白名单控制，不经第三方包
- 精简：去掉一个外部依赖（符合「精简低耗」原则）
- 可审计：代码仅几行，逻辑完全透明

### 10.7.5 操作建议

- **专设密码**：z-library / Anna's 使用独立密码，绝不复用重要账户密码。
- **书签官方域名**：核实后添加浏览器书签，不点搜索广告 / 社媒链接。
- **域名变更时**：仅在官方渠道（PGP 签名公告 / 官方 FAQ）确认新域名后，才更新白名单。
