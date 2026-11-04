# 数据存放 · 服务器部署 · 免费域名

这一页回答三个问题：**数据存在哪**、**怎么放到服务器上**、**怎么弄一个不花钱的域名和 HTTPS**。
内容与本仓库当前代码一致（`epitoperank/storage.py`、`Dockerfile`、`docker-compose.yml`）。

---

## 一、数据存在哪

EpitopeRank 的全部"业务数据"都在**一个运行根目录**里，三样东西：

| 内容 | 说明 |
| --- | --- |
| `epitoperank.sqlite3` | 项目表、事件表（百万级）、候选、富集、图表登记、流程日志、解读 |
| `literature.sqlite3` | 文献证据缓存 |
| `projects/<项目ID>/` | 该项目的图（PNG/SVG）、`report.html`、`report.pdf`、中间表 |
| `epitoperank_upload_*` | 上传的原始输入副本（分析完成后可删） |

### 各运行方式的路径

| 你怎么跑 | 运行根目录 | 主数据库 |
| --- | --- | --- |
| 桌面版 exe | `%LOCALAPPDATA%\EpitopeRank` | 同目录 `epitoperank.sqlite3` |
| 源码 / `serve_ui.py` / `run.py` | 同上 | 同上 |
| Docker / 服务器 | 容器内 `/data/runtime` | `/data/epitoperank.sqlite3`（挂载在命名卷 `epitoperank-data`） |
| 自定义 | 环境变量 `EPITOPERANK_RUNTIME_ROOT` | 可再加 `EPITOPERANK_MEMORY_DB`、`EPITOPERANK_LITERATURE_DB` |

> **为什么改过位置**：旧版本把数据写在 `%TEMP%\epitoperank`，Windows 的存储感知 / 磁盘清理会把整个 `%TEMP%` 删掉，历史项目就这么没了。现在固定在上面这张表的位置，系统清理和更新 exe 都不会碰它。
>
> 旧目录（`%TEMP%\epitoperank`、exe 同级的 `epitoperank_runtime`、`/var/tmp/epitoperank`）在首次启动时会**自动合并**到新目录，数据库逐表 `INSERT OR IGNORE` 合并、项目文件夹复制、图表/报告路径重写。执行结果可以在 `GET /api/storage` 里看到。

### 备份 / 恢复 / 换机器

```bash
# 备份（先退出程序，保证 SQLite 没有写入）
# Windows PowerShell
Copy-Item "$env:LOCALAPPDATA\EpitopeRank" "D:\backup\EpitopeRank-$(Get-Date -f yyyyMMdd)" -Recurse

# 服务器 / Docker
docker compose stop
docker run --rm -v epitoperank-data:/data -v "$PWD:/backup" alpine \
    tar czf /backup/epitoperank-data.tar.gz -C /data .
docker compose start
```

恢复就是反向操作：把目录（或卷）放回去。**`docker compose down -v` 会删掉命名卷**，历史会一起消失，别顺手加 `-v`。

### 想自己看/查数据库

```bash
sqlite3 "$LOCALAPPDATA/EpitopeRank/epitoperank.sqlite3" \
  "select project_id,name,source_format,created_at from projects order by created_at desc limit 10;"
```

---

## 二、部署到服务器

### 方案 A：Docker Compose（推荐，任意云主机）

前提：一台 Linux 服务器（1 核 2G 就能跑，8G 更舒服），装好 Docker + Compose 插件。

```bash
# 1. 把代码传上去
rsync -av --exclude venv --exclude .git --exclude dist --exclude _archive \
      ./ user@your-server:/opt/epitoperank/

# 2. 在服务器上
cd /opt/epitoperank
cat > .env <<'EOF'
MODEL_API_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
MODEL_API_KEY=sk-你的密钥
# 对外开放时强烈建议加这两行：
EPITOPERANK_API_KEY=自己编一个长随机串
EPITOPERANK_RATE_LIMIT=60
EOF

# 3. 启动
docker compose up -d --build
curl http://127.0.0.1:8800/api/health   # {"status":"ok",...}
```

访问 `http://服务器IP:8800/`。数据落在命名卷 `epitoperank-data`，容器重建也不丢。

**镜像体积和构建时间**是第一次部署最大的坑：`requirements.txt` 里有 gseapy（要 rust）、matplotlib、reportlab，Alpine 上编译通常 8–20 分钟。国内服务器建议保留 Dockerfile 里的清华源。

### 方案 B：不用 Docker，直接跑源码

```bash
python3.11 -m venv venv && ./venv/bin/pip install -r requirements.txt
EPITOPERANK_RUNTIME_ROOT=/opt/epitoperank-data \
EPITOPERANK_API_KEY=随机串 \
./venv/bin/python serve_ui.py --host 0.0.0.0 --port 8800 --no-browser
```

配 systemd 守护：

```ini
[Unit]
Description=EpitopeRank
After=network.target

[Service]
WorkingDirectory=/opt/epitoperank
Environment=EPITOPERANK_RUNTIME_ROOT=/opt/epitoperank-data
Environment=EPITOPERANK_API_KEY=随机串
ExecStart=/opt/epitoperank/venv/bin/python serve_ui.py --host 0.0.0.0 --port 8800 --no-browser
Restart=always

[Install]
WantedBy=multi-user.target
```

### 方案 C：反向代理 + 已有 HTTPS

仓库自带 `nginx.conf`（Coolify 风格，示例域名 `epitoperank.your-domain.com`），把 `server_name`、证书路径换掉即可。**注意上传体积**：nginx 默认只放行 1 MB，rMATS 表动辄几十 MB，必须在 `server {}` 里加

```nginx
client_max_body_size 2048m;
```

（`nginx.conf` 已加。）API 长任务超时也调过：`proxy_read_timeout 300s`。

### 部署后进不去 / 分析卡住，先查这几个

| 现象 | 原因 |
| --- | --- |
| 502 Bad Gateway | 容器没起来或端口不对，`docker compose logs --tail=100` |
| 上传报 413 | 就是上面 `client_max_body_size` |
| 分析跑一会儿就失败 | 内存不够。百万事件项目加载约 2–4 GB，Docker 默认可能不够，`deploy.resources.limits.memory` 调到 8G |
| 历史项目全空 | 卷没挂上，或换了 `EPITOPERANK_RUNTIME_ROOT`，旧数据在另一个目录 |
| 大模型解读不可用 | `.env` 里 `MODEL_API_KEY` 没读到；打开「AI 助手 → 模型配置」也能现场粘贴 |

---

## 三、免费域名与 HTTPS

分两种情形：

### 情形 1：服务器有公网 IP，但没域名 / 没钱买

| 方案 | 域名形态 | 成本 | 说明 |
| --- | --- | --- | --- |
| **nip.io / sslip.io** | `1.2.3.4.nip.io` | 免费、免注册 | 把 IP 直接当域名用，需 80/443 对公网开放 |
| **DuckDNS** | `xxx.duckdns.org` | 免费、需注册 | 动态 DNS，家宽换 IP 也能跟上；配 certbot 拿真证书 |
| **FreeDNS (afraid.org)** | `xxx.mooo.com` 等 | 免费 | 二级域名多，界面糙 |
| **EU.org** | `xxx.eu.org` | 免费 | 审核排队几周，过了就很香 |

配 HTTPS 一条命令（以 DuckDNS 为例）：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d xxx.duckdns.org
```

### 情形 2：家里/内网的机器，没有公网 IP（最常见）

**Cloudflare Tunnel 是这里唯一正解**：免费、不用开端口、不用公网 IP、自动给你 HTTPS。

```bash
# 服务器上
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared

# 临时公网地址（30 秒搞定，适合先给合作者看一眼）
cloudflared tunnel --url http://127.0.0.1:8800
# 输出里会给你一个 https://xxxx-xxxx.trycloudflare.com
```

`trycloudflare.com` 地址**每次重启都会变**，只适合临时演示。要固定地址：把域名（哪怕是 nip.io 之外自己买的几十块的）托管到 Cloudflare，然后

```bash
cloudflared tunnel login
cloudflared tunnel create epitoperank
cloudflared tunnel route dns epitoperank splice.your-domain.com
cloudflared tunnel run --url http://127.0.0.1:8800 epitoperank
```

Cloudflare 的 CDN/SSL 本身免费，所以"免费域名 + 免费 HTTPS + 免公网 IP"这一套是能跑通的；真正要花钱的只有域名本身（`.top`/`.xyz` 首年常年在 10 元上下）。

### 情形 3：连服务器都不想买

| 平台 | 免费额度 | 适配度 |
| --- | --- | --- |
| **Oracle Cloud Always Free** | ARM 4 核 24G + 200G 盘，永久免费 | ⭐ 最推荐，跑 Docker Compose 毫无压力 |
| **Fly.io** | 少量免费额度 | 需要挂 volume 存 SQLite，配置略麻烦 |
| **Koyeb / Render** | 有免费层 | Render 免费实例会休眠，长分析会被打断 |
| **Hugging Face Spaces** | Docker Space 免费 CPU | 需把端口改成 7860，且默认公开；只适合演示 |

> 公开到公网前务必设置 `EPITOPERANK_API_KEY` 和 `EPITOPERANK_RATE_LIMIT`。这两个变量会让所有 `/api/*`（除 `/api/health`）要求请求头带密钥并限流；否则任何人都能用你的服务器和大模型额度。

---

## 四、历史项目在哪看

启动后打开 Web UI：

- **仪表盘 → 历史项目**：按时间倒序列出全部项目，显示输入格式、事件数、显著事件数；搜索框可按项目名 / ID / 查询词过滤。
- **点任意一个项目**：右侧「历史项目详情」展开——样本分组、事件类型分布、图表缩略图（点击放大）、候选事件 Top 10、最近流程日志，以及 HTML 报告 / PDF 下载 / 浏览全部事件 / 删除项目。
- **事件浏览器**：服务端分页（每页 50 条），可按基因名或事件 ID 搜索、按事件类型筛选、"仅显著事件"、按 FDR / |ΔPSI| / 基因名排序。百万事件项目也不会把浏览器撑爆。

对应接口：

```text
GET    /api/projects                        项目列表（含 event_count / significant_count）
GET    /api/status/{id}                     项目详情（计数走 SQL，不拉全表）
GET    /api/projects/{id}/events?page=&size=&q=&event_type=&significant_only=&order_by=
GET    /api/report/{id}?format=html|pdf     报告（先找登记路径，再找项目目录）
GET    /api/figure/{id}/{name}              图表
GET    /api/storage                         数据目录、库体积、迁移记录
DELETE /api/projects/{id}                   删除项目（库记录 + 项目目录）
```
