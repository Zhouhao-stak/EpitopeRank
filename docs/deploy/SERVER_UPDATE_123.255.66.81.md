# 123.255.66.81 增量更新手册（不重建镜像）

> 适用主机：`wang_zi_wei@123.255.66.81 -p 39145`，项目目录 `~/splicegaip`。
> 结论：**不要 `docker build`**。该主机无法访问 PyPI / Docker Hub，
> 但依赖已经全部装在现有镜像 `splicegaip-splicegaip:latest` 里，
> 代码更新只需要「同步源码 → 重建容器（不 build）」。

## 为什么不能按常规方式发布

| 约束 | 实测 |
|---|---|
| 出网 | PyPI / Docker Hub 被集群防火墙阻断 |
| 镜像 | `splicegaip-splicegaip:latest`，1.07 GB，Python 3.11.17 |
| 依赖 | pandas / numpy / scipy / openai / httpx / fastapi / streamlit 等已装 |
| 代码位置 | 镜像内 `/app`，原来**没有**源码 bind mount |
| 数据 | docker volume `splicegaip-data` → `/data`，SQLite 877 MB / 180 万事件 |
| 资源 | 128 核 / 503 GB 内存，容器限额 64 核 / 64 GB |
| 端口 | 8800（FastAPI + 新 Web UI）、8501（旧 Streamlit） |

所以发布模型是：**把源码目录挂进容器，覆盖镜像里的 `/app`**。
以后每次更新 = 覆盖文件 + `docker compose up -d --no-build`，几秒完成。

## 目录与 compose 组合

```
~/splicegaip/
├── splicegaip/                 # 包源码（含 peptide/reference 数据）
├── run.py  serve_ui.py         # 入口
├── deploy/docker/entrypoint.sh # 容器 entrypoint
├── docker-compose.yml          # 基础
├── docker-compose.override.yml # 多核 / 8 workers / WAL
├── docker-compose.server.yml   # 本机专用：./:/app:ro + 肽缓存 + TZ
├── .env                        # MODEL_API_KEY + COMPOSE_FILE
└── .backup-*/                  # 每次更新的回滚包
```

`.env` 里由更新脚本维护一行：

```
COMPOSE_FILE=docker-compose.yml:docker-compose.override.yml:docker-compose.server.yml
```

因此在该目录直接 `docker compose ps / logs / up -d` 就会自动带上三层配置。

## 更新步骤

### 一键发布（Windows，推荐）

```powershell
$env:SSHPASS = '服务器密码'      # 不想用 sshpass 可省略，随后手动输入
.\deploy\server\push-from-windows.ps1
```

脚本会打包、上传到 `~/splicegaip/.upload/`、在服务器执行
`deploy/server/update-container.sh`（备份 → 解包 → 预检 → 重建容器 → 健康检查）。
只上传不部署：`.\deploy\server\push-from-windows.ps1 -SkipUpdate`。

### 手动更新（等价步骤）

#### 1. 本地打包（Windows，项目根目录）

```powershell
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
tar -czf "dist\splicegaip-server-$ts.tar.gz" `
  --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' `
  splicegaip deploy docs examples scripts tests `
  run.py serve_ui.py desktop_ui.py pytest.ini README.md requirements.txt requirements-dev.txt
```

不要打包：`venv/`、`dist/`、`public_datasets/`、`out/`、`config/`（服务器配置以线上为准）。

### 2. 上传

```powershell
scp -P 39145 "dist\splicegaip-server-$ts.tar.gz" `
  wang_zi_wei@123.255.66.81:~/splicegaip/.upload/
```

### 3. 服务器执行

```bash
cd ~/splicegaip
./deploy/server/update-container.sh            # 自动选最新 bundle
# 或显式：./deploy/server/update-container.sh .upload/splicegaip-server-XXXX.tar.gz
```

脚本做七件事：

1. 备份 `splicegaip/ run.py serve_ui.py deploy docs examples scripts tests` + compose + `.env` 到 `.backup-<ts>/`
2. 解包
3. 清理 `__pycache__` / `*.pyc`
4. 确保 `.env` 有 `COMPOSE_FILE`
5. `docker compose config -q` 校验
6. **预检**：用现有镜像 + 新源码跑 `import splicegaip.api.app, splicegaip.peptide, splicegaip.agent.copilot`
7. `docker compose up -d --no-build`，等 `/api/health`，打印 copilot/peptide 能力

预检失败时容器不会被动，线上仍是旧版本。

### 4. 验证

```bash
curl -s localhost:8800/api/health
curl -s localhost:8800/api/copilot/tools | head -c 300
curl -s localhost:8800/api/peptide/capabilities | head -c 300
docker compose logs --tail 50 splicegaip
```

浏览器打开 `http://123.255.66.81:8800/`，确认左侧导航出现「🤖 AI 助手」和「肽预测」。

### 5. 回滚

```bash
cd ~/splicegaip
./deploy/server/rollback-container.sh .backup-20261104-010203
```

回滚只恢复源码和 compose，不动 `/data` 数据库。镜像从未被修改，所以最坏情况也只是回到上一版代码。

## 本机专属适配点

| 适配 | 原因 |
|---|---|
| `./:/app:ro` 目录挂载 | 单文件挂载在 `tar -x` 后 inode 变化，容器仍读旧文件；目录挂载没有这个问题 |
| `PYTHONDONTWRITEBYTECODE=1` | 源码只读，避免 Python 尝试写 `__pycache__` |
| `SPLICEGAIP_PEPTIDE_CACHE=/data/runtime/peptide_cache` | NFS home 上不放缓存；肽预测缓存跟随本地 volume |
| `SPLICEGAIP_PEPTIDE_TIMEOUT=120` / `RETRIES=1` | 该网络访问 IEDB 冷请求实测 30–90 s；给足超时，避免超时后重试叠加 |
| `TZ=Asia/Shanghai` | 报告/日志时间与操作者一致 |
| 8 workers + SQLite WAL | 已有 `docker-compose.override.yml`；877 MB 库已建好查询索引，启动不会全表扫描 |
| 依赖零变更 | 新增模块只用标准库 + 已安装的 `openai/httpx`，无需联网装包 |

## 已知边界

- **8800 端口无鉴权**：目前是公网直连。需要的话在 `splicingnexus-proxy` 加 Basic Auth 或只监听 127.0.0.1 再由 nginx 转发。
- **8501 Streamlit 是旧界面**：新 Web UI 在 8800 `/`。确认无人使用后可把 `SPLICEGAIP_ENABLE_STREAMLIT=0`，省一个进程。
- **`.env` 含真实密钥**：不要提交、不要打包、不要发群。
- **数据库 877 MB**：`/data/splicegaip.sqlite3`；更新不会重建它，但也不做备份。需要时先 `docker run --rm -v splicegaip-data:/data alpine cp /data/splicegaip.sqlite3 /data/backup.sqlite3`。
- **镜像更新仍需外网**：如果未来新增 Python 依赖，必须在一台能出网的机器上 `docker build` + `docker save` / `docker load`，本机不能直接 build。

## 本次部署验证（2026-11-04）

| 项 | 结果 |
|---|---|
| 镜像 | `splicegaip-splicegaip:latest` 未重建（1.07 GB） |
| 挂载 | `/home/wang_zi_wei/splicegaip -> /app (ro)`；`/data` volume 保留 |
| 进程 | 8 个 uvicorn worker + Streamlit :8501 |
| 路由 | `/api/health`、`/api/copilot/tools`、`/api/peptide/capabilities`、`/api/projects`、`/docs`、`/` 全部 200 |
| UI | 页面含「AI 助手」「肽预测」「模型配置」 |
| 大模型 | `mode=llm`，`list_projects` 工具调用成功，4643 tokens，数字溯源 `ok` |
| 肽预测 | IEDB 实测：冷请求 33.2 s，命中缓存后 **2.4 ms**；`NLVPMVATV / HLA-A*02:01` percentile 0.06 |
| 数据 | 83 个项目 / 1,805,145 事件 / 14 个索引，未重建 |
| 测试 | 本地 318 passed；容器内 copilot+peptide 52 passed |
| 回滚点 | `.backup-20261104-010511`（最新） |

**冷请求慢是网络位置问题，不是代码问题**：同一请求第二次走 `/data/runtime/peptide_cache`，实测 2.4 ms。首次批量预测请给浏览器/网关留 ≥120 s。

## 上线后仍需注意

1. **首次调用 IEDB 会慢**：服务端到 IEDB 的 RTT 很高。批量预测建议一次提交、复用缓存；不要把超时改回 45 s。
2. **旧项目路径**：数据库里有早期 Windows 产生的项目（`source_dir` 为 `E:\...`），它们的文件类工具在服务器上不可用；新建项目不受影响。
3. **8800 无鉴权**：如需公开长期使用，建议在 `splicingnexus-proxy` 加 Basic Auth，或改为只监听 `127.0.0.1:8800` 再由 nginx 转发。
4. **`docker compose` 必须带三层文件**：已在 `.env` 写入 `COMPOSE_FILE`，直接用 `docker compose ps/logs/up` 即可；手动指定时别漏掉 `docker-compose.server.yml`，否则会丢失源码挂载。
5. **不要 `docker compose down -v`**：`splicegaip-data` 里是 877 MB 的分析库，删卷等于清空历史项目。
