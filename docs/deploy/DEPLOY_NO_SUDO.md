# 无 sudo 部署（128 核共享服务器）

针对 `wang_zi_wei@123.255.66.81:39145`（主机名 `n001`）已经落地的部署方式。
不需要 root，也不占用系统 Python。

---

## 一、这台机器的实际情况（实测，2026-11-03）

| 项 | 值 | 影响 |
|---|---|---|
| 系统 | Rocky Linux 8.10 / 内核 4.18 | glibc 2.28，老版本 |
| CPU | 128 核（`nproc`） | 见第五节调优 |
| 内存 | 503 GB | 完全可以给容器 64 G |
| `/home` | NFS（`10.32.0.10:/opt/data/hpc/.home`）436 T | **SQLite 不能放这里**，锁机制不可靠 |
| `/tmp` `/` | 本地 xfs 7 T，剩 5.8 T | 临时/快速目录放这里 |
| Python | `python3` 3.13.9、`python3.11` 3.11.13、`~/anaconda3` | 够用 |
| Docker | 可用（`~/bin/docker`，无需 sudo） | 主力部署方式 |
| PyPI | **不通**（`pypi.org/simple`、清华镜像 `/simple/` 全部超时） | 不能 `pip install` |
| Docker Hub | **不通**（`registry-1.docker.io` 超时） | 不能 `docker pull` 新镜像 |
| GitHub / Cloudflare | 通 | 可以装 cloudflared |
| 对外端口 | 只有 SSH 39145 通，8800/8501 被防火墙挡 | 见第四节 |

> 两条“不通”是这台机器最关键的限制：**任何新增 Python 依赖都无法在线安装**。

---

## 二、当前部署形态

已有的 `epitoperank` 容器是 2026-10-19 构建的。本次更新没有重新 `pip install`，
而是**在旧镜像上叠一层源码**（`deploy/docker/Dockerfile.update`），依赖全部沿用旧镜像：

```
epitoperank-epitoperank:prev-20261019   ← 更新前的镜像，回滚用
epitoperank-epitoperank:latest          ← 当前运行（旧镜像 + 新代码）
```

运行结构（`docker compose ps` 可验证）：

| 进程 | 端口 | 说明 |
|---|---|---|
| `serve_ui.py --workers 8` | 8800 | FastAPI + 新 Web UI，8 个 uvicorn 进程 |
| `streamlit` | 8501 | 旧版看板，保留兼容 |
| 内置 MCP | 9100（容器内） | 8 个 worker 抢同一端口，后 7 个自动检测到已存在并复用 |

配置通过 `docker-compose.override.yml` 叠加，**原始的 `docker-compose.yml` 未改动**。

---

## 三、日常操作

全部在服务器上执行，工作目录 `~/epitoperank`：

```bash
cd ~/epitoperank

# 看状态
~/bin/docker ps | head -3
~/bin/docker compose ps

# 看日志（API）
~/bin/docker logs -f --tail 100 epitoperank

# 只看 streamlit
~/bin/docker exec epitoperank tail -f /data/streamlit.log

# 重启
~/bin/docker compose restart epitoperank

# 停止 / 启动
~/bin/docker compose stop epitoperank
~/bin/docker compose start epitoperank
```

### 更新代码（这台的专用流程）

```bash
# 本地（Windows）打包，排除大目录
tar -czf /c/Users/m1726/AppData/Local/Temp/sg_src.tar.gz \
  --exclude=venv --exclude=dist --exclude=public_datasets --exclude=runtime \
  --exclude=pdf_ppt_work --exclude=converted --exclude=out --exclude=_archive \
  --exclude=.git --exclude=__pycache__ --exclude='*.pyc' --exclude=.env .

# 上传解压
scp -P 39145 /c/Users/m1726/AppData/Local/Temp/sg_src.tar.gz wang_zi_wei@123.255.66.81:/tmp/
ssh -p 39145 wang_zi_wei@123.255.66.81 'cd ~/epitoperank && tar -xzf /tmp/sg_src.tar.gz'

# 服务器上重建镜像并只换容器（不联网、约 5 秒）
cd ~/epitoperank
~/bin/docker build -f deploy/docker/Dockerfile.update -t epitoperank-epitoperank:latest .
~/bin/docker compose up -d --no-build
```

**注意 `--no-build`**：不加的话 compose 会走 `Dockerfile` 重新 `pip install`，在这台机器上必然失败。

### 回滚

```bash
cd ~/epitoperank
~/bin/docker tag epitoperank-epitoperank:prev-20261019 epitoperank-epitoperank:latest
~/bin/docker compose up -d --no-build --force-recreate
```

---

## 四、怎么访问（外网端口被封）

8800/8501 在宿主机上是 `0.0.0.0` 监听，但防火墙只放了 SSH。无 sudo 无法改防火墙，
三条可行路径：

### 0. 当前已开的公网地址（临时隧道）

```
https://signing-viewing-uniprotkb-coalition.trycloudflare.com
```

由 `cloudflared` 快速隧道提供，进程跑在服务器上的 tmux 会话 `cloudflared` 里：

```bash
# 看状态 / 重启 / 关掉
tmux ls
tmux attach -t cloudflared                  # Ctrl-B D 退出查看
tmux kill-session -t cloudflared            # 关闭（公网地址立即失效）
~/bin/cloudflared tunnel --url http://127.0.0.1:8800 --no-autoupdate   # 重新起
```

重新启动后**域名会变**，新的地址在 `~/cloudflared.log` 里 grep `trycloudflare.com`。

> ⚠️ 这个地址是**公开且没有密码**的：拿到链接的人可以看你的全部分析结果，
> 也能消耗你的 DeepSeek 额度。用完请 `tmux kill-session -t cloudflared` 关掉。
> 不建议直接把 `EPITOPERANK_API_KEY` 打开——它只认 `X-API-Key` 请求头，
> 网页 UI 不带这个头，开了会连自己都打不开。

### 1. SSH 隧道（最稳，零依赖）


在你自己的电脑上执行，然后浏览器打开 `http://127.0.0.1:8800`：

```bash
ssh -N -L 8800:127.0.0.1:8800 -p 39145 wang_zi_wei@123.255.66.81
```

Windows 也可以用 XShell / MobaXterm 的“隧道”功能配同样的转发。
退出登录不会断（`-N` 只做端口转发），关掉窗口才断。

### 2. Cloudflare Tunnel（要一个免费公网 https 链接时）

这台机器能连 `api.trycloudflare.com`，可以装（**不需要 root**）。注意
**直接从 GitHub Releases 下载会失败**（90 秒后 `SSL unexpected eof`），要走镜像：

```bash
mkdir -p ~/bin && cd ~/bin
curl -fL -o cloudflared \
  https://gh-proxy.com/https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared
./cloudflared --version     # 已装 2026.10.7
```

`gh-proxy.com` 实测可用（返回 206），`ghfast.top` 也可作为备选。

```bash
# 临时公网地址（进程退出即失效）
~/bin/cloudflared tunnel --url http://127.0.0.1:8800 --no-autoupdate
```

它会打印一个 `https://xxx-xxx.trycloudflare.com`，任何地方都能打开。

三个必须知道的坑：

- **Cloudflare 免费版单次上传上限 100 MB**。rMATS 大表可能超，超了就是 413。
- 临时隧道每次重启换域名，且流量走 Cloudflare，数据会出国。
- **公开前务必设访问密码**，否则任何人都能用你的 DeepSeek 额度：
  ```bash
  # 在 ~/epitoperank/.env 里加
  EPITOPERANK_API_KEY=换成你自己的随机串
  ```

### 3. 请管理员开端口（一劳永逸）

```bash
# 让管理员在防火墙放行 8800（firewalld）
sudo firewall-cmd --permanent --add-port=8800/tcp && sudo firewall-cmd --reload
```

放行后可以直接用 `http://123.255.66.81:8800`，但**没有 HTTPS**，密码/数据是明文，
只建议在内网或已配好反代的情况下这么做。

---

## 五、128 核调优：为什么现在这样配

这台机器核多，但默认配置会把 128 核用成 1 核。三件事必须做：

### 1. 多进程（已做）

`run.py serve` 只有一个 uvicorn 进程，任何时刻只有 1 个核在干活。
`docker-compose.override.yml` 把启动命令换成 `serve_ui.py --workers 8`，8 个独立进程，
可以同时跑 8 个分析任务。实测 8 个 worker + streamlit 常驻内存 886 MB，128 核 / 503 G 完全吃得下。

调大：`EPITOPERANK_WORKERS=16`（每个 worker 约 300–400 MB）。

### 2. 把 BLAS 线程钉成 1（已做，最关键）

numpy/scipy 默认按核数开线程。8 个 worker × 128 线程 = 1024 个线程抢 128 个核，
**比单线程还慢**。所以 override 里显式设了：

```yaml
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
```

并行度由“进程数”提供，而不是“线程数”。

### 3. SQLite 开 WAL（已做）

8 个进程共用一个 `epitoperank.sqlite3`。WAL 让读不被写阻塞，避免分析期间刷新页面转圈。
`/data` 是本地 docker volume，WAL 安全；**如果哪天把数据目录改到 NFS，必须关掉它**
（`EPITOPERANK_SQLITE_WAL=0`），NFS 上 WAL 会损坏数据库。

### 还能再压榨的地方

- **批量分析**：CLI 支持一条命令跑一个目录，可以并行提交
  ```bash
  printf '%s\n' ~/data/*/ | xargs -P 12 -I{} \
    python run.py analyze --input {} --query "differential splicing, tumor vs normal"
  ```
  `-P 12` 对应 12 个并发项目。
- **不要在登录节点上跑重活**：`n001` 是登录/管理节点，长时间满载跑分析会被管理员盯上。
  如果能用 Slurm，把容器命令丢进 `srun`/`sbatch` 更合适。

---

## 六、数据在哪

| 内容 | 位置 | 说明 |
|---|---|---|
| 数据库 | 容器内 `/data/epitoperank.sqlite3` → 宿主机 `/var/lib/docker/volumes/epitoperank-data/_data/` | 命名卷 `epitoperank-data` |
| 项目产物（图表/报告） | 容器内 `/data/runtime/projects/<项目ID>/` | 同上卷 |
| 旧库（迁移前） | `/data/epitoperank.sqlite3` 是主库；`/data/runtime/epitoperank.sqlite3` 是备用位置 | 见 `/api/storage` |
| streamlit 日志 | `/data/streamlit.log` | |

**当前这个库几乎是空的**（60 KB，0 个项目）——你本机 `%LOCALAPPDATA%\EpitopeRank`
里那 83 个项目没有被带上来。要迁移的话见下面。

### 备份（在线安全）

```bash
cd ~/epitoperank
~/bin/docker exec epitoperank python - <<'EOF'
import sqlite3
src = sqlite3.connect('/data/epitoperank.sqlite3')
dst = sqlite3.connect('/data/backup.sqlite3')
with dst: src.backup(dst)
EOF
~/bin/docker cp epitoperank:/data/backup.sqlite3 ~/epitoperank-backup-$(date +%F).sqlite3
```

### 把本机历史项目迁上来

```bash
# 本地 Windows
cd /c/Users/m1726/AppData/Local/EpitopeRank
tar -czf /c/Users/m1726/AppData/Local/Temp/sg_data.tar.gz epitoperank.sqlite3 projects

# 上传
scp -P 39145 /c/Users/m1726/AppData/Local/Temp/sg_data.tar.gz wang_zi_wei@123.255.66.81:/tmp/

# 服务器：先停容器，解到卷里，再起
cd ~/epitoperank
~/bin/docker compose stop epitoperank
~/bin/docker run --rm -v epitoperank-data:/data -v /tmp:/in alpine sh -c \
  'cd /data && tar -xzf /in/sg_data.tar.gz'
~/bin/docker compose start epitoperank
```

迁移后 `/api/projects` 里就能看到本机的项目。注意 `artifacts.path` 里存的是绝对路径，
迁移工具不会改写它们——报告下载走 `/api/report/<id>` 的兜底逻辑，仍然可用。

---

## 七、如果换一台有网络的机器：纯用户空间方案

`deploy/userland/` 里有一套不依赖 Docker 的安装器，适合“有 PyPI、没 Docker、没 root”的机器：

```bash
tar -xzf sg_src.tar.gz -C ~/epitoperank && cd ~/epitoperank
bash deploy/userland/install.sh            # 自动选 Python/装依赖/定运行目录
bash deploy/userland/sgctl doctor          # 环境体检
bash deploy/userland/sgctl start           # 后台启动（systemd --user → tmux → nohup 自动降级）
bash deploy/userland/sgctl status
```

它会做的事：

- Python 低于 3.10 时在 `~/.epitoperank/.opt` 装 Miniconda（不碰系统 Python）
- `venv` 建在项目目录里
- **运行数据目录自动避开 NFS**：`/home` 是 NFS 时改放 `/scratch/$USER`、`/tmp/$USER` 等本地盘
- worker 数按核数自动算（128 核 → 8）
- 预先烘焙 matplotlib 字体缓存，避免多 worker 并发写坏缓存

**这台机器用不了这套**：它在第 3 步 `pip install` 会因为没有 PyPI 而失败，
除非你先在有网的机器 `pip download` 下好 wheel 再传上来。

---

## 八、故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 容器 `unhealthy` | 首次启动要合并旧库，超过 60 s | override 里已把 `start_period` 放到 180 s |
| 页面 502 / 空 | worker 全部启动失败 | `docker logs epitoperank \| grep -i error` |
| `address already in use` | 9100 端口被占 | 正常现象，后启动的 worker 会复用已有的 MCP 服务 |
| 上传大文件 413 | 走了 Cloudflare 隧道（100 MB 上限） | 改用 SSH 隧道 |
| 日志里 `Merged legacy runtime storage` | 首次启动把旧目录数据合并进新目录 | 正常，只发生一次 |
| `docker compose up --build` 卡住 | 尝试访问 Docker Hub / PyPI | 加 `--no-build`，用 `Dockerfile.update` 覆盖 |

---

相关文档：[README](README.md) · [数据与部署总览](../DATA_AND_DEPLOY.md) · [Docker 用法](DOCKER_USAGE.md)
