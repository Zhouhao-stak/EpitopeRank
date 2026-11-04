#!/usr/bin/env bash
# EpitopeRank — install on a shared Linux server WITHOUT root.
#
#   bash deploy/userland/install.sh                  # auto-detect everything
#   bash deploy/userland/install.sh --workers 8      # pin the worker count
#   bash deploy/userland/install.sh --mirror tsinghua
#   bash deploy/userland/install.sh --runtime-root /scratch/$USER/sg
#
# Everything lands inside the project directory or $HOME. Nothing touches /etc,
# system packages, or the system Python.
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$APP_DIR/deploy/userland"
SG_ENV="$HERE/sg.env"
OPT_DIR="$APP_DIR/.opt"
STATE_DIR="$APP_DIR/.state"

WORKERS=""
PORT="8800"
RUNTIME_ROOT=""
MIRROR="auto"

C_RESET=''; C_DIM=''; C_OK=''; C_WARN=''; C_ERR=''
if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_DIM=$'\033[2m'; C_OK=$'\033[32m'
  C_WARN=$'\033[33m'; C_ERR=$'\033[31m'
fi
step()  { printf '%s==>%s %s\n' "$C_OK" "$C_RESET" "$*"; }
info()  { printf '    %s\n' "$*"; }
dim()   { printf '    %s%s%s\n' "$C_DIM" "$*" "$C_RESET"; }
warn()  { printf '%s[!]%s %s\n' "$C_WARN" "$C_RESET" "$*"; }
die()   { printf '%s[x]%s %s\n' "$C_ERR" "$C_RESET" "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --workers)      WORKERS="${2:-}"; shift 2 ;;
    --port)         PORT="${2:-}"; shift 2 ;;
    --runtime-root) RUNTIME_ROOT="${2:-}"; shift 2 ;;
    --mirror)       MIRROR="${2:-}"; shift 2 ;;
    -h|--help)      sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)              die "未知参数: $1（用 --help 查看用法）" ;;
  esac
done

[ "$(uname -s)" = "Linux" ] || warn "本脚本按 Linux 编写，当前是 $(uname -s)，部分步骤可能不适用"

mkdir -p "$OPT_DIR" "$STATE_DIR"

CORES="$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)"
MEM_GB=$(( $(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 8000000) / 1048576 ))

# ---------------------------------------------------------------- 1. Python 3.10+
python_ok() { [ -n "${1:-}" ] && "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; }

find_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && python_ok "$candidate"; then
      command -v "$candidate"
      return 0
    fi
  done
  # A conda already on PATH is fine too.
  for candidate in "$HOME/miniconda3/bin/python" "$HOME/anaconda3/bin/python" "$OPT_DIR/miniconda3/bin/python"; do
    if [ -x "$candidate" ] && python_ok "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

miniconda_url() {
  local arch url_cn url_org
  case "$(uname -m)" in
    x86_64|amd64)  arch="Linux-x86_64" ;;
    aarch64|arm64) arch="Linux-aarch64" ;;
    ppc64le)       arch="Linux-ppc64le" ;;
    *)             arch="Linux-x86_64" ;;
  esac
  url_cn="https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-${arch}.sh"
  url_org="https://repo.anaconda.com/miniconda/Miniconda3-latest-${arch}.sh"
  if [ "$MIRROR" = "aliyun" ]; then
    url_cn="https://mirrors.aliyun.com/anaconda/miniconda/Miniconda3-latest-${arch}.sh"
  fi
  if [ "$MIRROR" = "pypi" ] || [ "$MIRROR" = "none" ]; then
    printf '%s\n' "$url_org"
  else
    printf '%s\n' "$url_cn"
  fi
}

install_miniconda() {
  local url installer prefix
  prefix="$OPT_DIR/miniconda3"
  url="$(miniconda_url)"
  installer="$OPT_DIR/miniconda.sh"
  warn "系统 Python 低于 3.10，改为在用户目录安装 Miniconda（不需要 root）"
  info "下载: $url"
  if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 3 --connect-timeout 20 -o "$installer" "$url" || die "下载失败，请检查网络；可用 --mirror pypi 走官方源"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$installer" "$url" || die "下载失败，请检查网络"
  else
    die "服务器上没有 curl 也没有 wget，无法自动安装 Python 3.10+"
  fi
  bash "$installer" -b -p "$prefix" >/dev/null 2>&1 || die "Miniconda 安装失败"
  rm -f "$installer"
  printf '%s\n' "$prefix/bin/python"
}

step "[1/6] 查找 Python >= 3.10"
if PYTHON="$(find_python)"; then
  info "使用 $PYTHON  ($("$PYTHON" -V 2>&1))"
else
  PYTHON="$(install_miniconda)"
  info "已安装 $PYTHON  ($("$PYTHON" -V 2>&1))"
fi

# --------------------------------------------------------------------- 2. venv
step "[2/6] 创建虚拟环境 venv/"
VENV_PY="$APP_DIR/venv/bin/python"
if [ -x "$VENV_PY" ] && python_ok "$VENV_PY"; then
  info "已存在，复用"
else
  rm -rf "$APP_DIR/venv"
  if "$PYTHON" -m venv "$APP_DIR/venv" >/dev/null 2>&1 && [ -x "$VENV_PY" ]; then
    info "已创建（$("$VENV_PY" -V 2>&1)）"
  else
    # Debian/Ubuntu without python3-venv: bootstrap virtualenv, or fall back to conda.
    warn "系统 Python 缺少 venv 模块（常见于未装 python3-venv 的机器），改用备用方案"
    if [ -x "$OPT_DIR/miniconda3/bin/python" ]; then
      "$OPT_DIR/miniconda3/bin/python" -m venv "$APP_DIR/venv" || "$OPT_DIR/miniconda3/bin/conda" create -y -p "$APP_DIR/venv" python=3.11
    elif "$PYTHON" -m pip install --user virtualenv >/dev/null 2>&1; then
      "$PYTHON" -m virtualenv "$APP_DIR/venv"
    else
      die "无法创建虚拟环境。请让管理员执行：apt install python3-venv（或 python3.11-venv）"
    fi
    [ -x "$VENV_PY" ] || die "虚拟环境创建后仍找不到 $VENV_PY"
    info "已创建"
  fi
fi

# ------------------------------------------------------------------- 3. 依赖
index_url() {
  case "$MIRROR" in
    tsinghua) printf 'https://pypi.tuna.tsinghua.edu.cn/simple' ;;
    aliyun)   printf 'https://mirrors.aliyun.com/pypi/simple' ;;
    pypi|none) printf '' ;;
    *)
      # Auto: Chinese hosts get the Tsinghua mirror, everything else goes direct.
      if [ -n "${EPITOPERANK_PIP_INDEX:-}" ]; then printf '%s' "$EPITOPERANK_PIP_INDEX"
      elif [ -n "${TZ:-}" ] && [ "${TZ#Asia/}" != "$TZ" ]; then printf 'https://pypi.tuna.tsinghua.edu.cn/simple'
      elif curl -fsS --max-time 4 -o /dev/null https://pypi.org/simple/ 2>/dev/null; then printf ''
      else printf 'https://pypi.tuna.tsinghua.edu.cn/simple'; fi
      ;;
  esac
}

PIP_ARGS=(--disable-pip-version-check)
IDX="$(index_url)"
if [ -n "$IDX" ]; then PIP_ARGS+=(-i "$IDX"); fi

step "[3/6] 安装 Python 依赖"
info "索引: ${IDX:-PyPI 官方}"
"$VENV_PY" -m pip install "${PIP_ARGS[@]}" --upgrade pip setuptools wheel >/dev/null || warn "pip 自身升级失败，继续"
if ! "$VENV_PY" -m pip install "${PIP_ARGS[@]}" -r "$APP_DIR/requirements.txt"; then
  die "依赖安装失败。常见原因：网络、磁盘配额、缺少编译工具（本项目的依赖都提供预编译 wheel，通常不需要 gcc）"
fi
info "依赖就绪"

# --------------------------------------------------- 4. 运行目录（避开 NFS）
fstype_of() { df -PT "$1" 2>/dev/null | awk 'NR==2 {print $2}'; }
is_network_fs() {
  case "$1" in
    nfs*|cifs|smb*|smbfs|afs|lustre|gpfs|glusterfs|ceph|fuse*|9p) return 0 ;;
    *) return 1 ;;
  esac
}
writable() { mkdir -p "$1" 2>/dev/null && [ -w "$1" ]; }

pick_runtime_root() {
  if [ -n "$RUNTIME_ROOT" ]; then printf '%s\n' "$RUNTIME_ROOT"; return; fi
  if [ -n "${EPITOPERANK_RUNTIME_ROOT:-}" ]; then printf '%s\n' "$EPITOPERANK_RUNTIME_ROOT"; return; fi

  local home_fs candidate
  home_fs="$(fstype_of "$HOME")"
  if ! is_network_fs "$home_fs"; then
    printf '%s\n' "$HOME/.local/share/epitoperank"
    return
  fi
  # Home is on NFS/SMB: SQLite locking and WAL are unsafe there, and analysis
  # writes tens of thousands of small files. Look for local scratch space.
  for candidate in "${EPITOPERANK_LOCAL_DISK:-}" /scratch/"$USER" /scratch /local/"$USER" /work/"$USER" /data/"$USER" /tmp/"$USER"; do
    [ -n "$candidate" ] || continue
    if writable "$candidate" && ! is_network_fs "$(fstype_of "$candidate")"; then
      printf '%s\n' "$candidate/epitoperank"
      return
    fi
  done
  printf '%s\n' "$HOME/.local/share/epitoperank"
}

step "[4/6] 选择运行数据目录"
HOME_FS="$(fstype_of "$HOME")"
RUN_ROOT="$(pick_runtime_root)"
mkdir -p "$RUN_ROOT/projects" "$RUN_ROOT/logs"
[ -w "$RUN_ROOT" ] || die "运行目录不可写: $RUN_ROOT"
if is_network_fs "$HOME_FS" && is_network_fs "$(fstype_of "$RUN_ROOT")"; then
  warn "主目录和运行目录都在网络文件系统（$HOME_FS）上"
  warn "SQLite 在网络盘上容易锁冲突甚至损坏，强烈建议指定本地盘：--runtime-root /scratch/$USER/sg"
  WAL="0"
else
  WAL="1"
fi
info "运行目录: $RUN_ROOT  (fstype=$(fstype_of "$RUN_ROOT"))"
if [ "$HOME_FS" = "nfs" ] || [ "$HOME_FS" = "nfs4" ]; then
  dim "主目录是 NFS，已把数据放到本地盘"
fi

# --------------------------------------------------- 5. worker 数与线程上限
if [ -z "$WORKERS" ] || [ "$WORKERS" -lt 1 ] 2>/dev/null; then
  WORKERS=$(( CORES / 16 ))
  if [ "$WORKERS" -lt 1 ]; then WORKERS=1; fi
  if [ "$WORKERS" -gt 8 ]; then WORKERS=8; fi
fi

step "[5/6] 生成配置"
{
  printf '# 由 install.sh 生成，sgctl 会读取本文件。手工改完执行 sgctl restart 生效。\n'
  printf 'APP_DIR=%q\n' "$APP_DIR"
  printf 'VENV_PY=%q\n' "$VENV_PY"
  printf 'RUNTIME_ROOT=%q\n' "$RUN_ROOT"
  printf 'HOST=%q\n' "0.0.0.0"
  printf 'PORT=%q\n' "$PORT"
  printf 'WORKERS=%q\n' "$WORKERS"
  printf 'CORES=%q\n' "$CORES"
  printf 'SQLITE_WAL=%q\n' "$WAL"
} > "$SG_ENV"
chmod 600 "$SG_ENV"

export MPLCONFIGDIR="$STATE_DIR/mpl"
mkdir -p "$MPLCONFIGDIR"
umask 022

if [ ! -f "$APP_DIR/.env" ]; then
  if [ -f "$APP_DIR/.env.example" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    warn "已从模板生成 .env —— 打开它填入 MODEL_API_KEY，否则只能做离线确定性分析"
  fi
fi

# Matplotlib builds its font cache on first use. With several worker processes
# that race corrupts the cache, so warm it once here, single-threaded.
info "预热 matplotlib 字体缓存（多 worker 同时构建会损坏缓存）"
"$VENV_PY" - "$MPLCONFIGDIR" <<'PY' >/dev/null 2>&1 || warn "字体缓存预热失败（不影响使用）"
import os, sys, tempfile
os.environ.setdefault("MPLCONFIGDIR", sys.argv[1])
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig = plt.figure(figsize=(1, 1)); fig.text(0.2, 0.5, "warm"); 
buf = os.path.join(tempfile.gettempdir(), f"sg-warm-{os.getpid()}.png")
fig.savefig(buf); os.unlink(buf)
PY

# ------------------------------------------------------------- 6. 自检
step "[6/6] 自检"
"$VENV_PY" - <<'PY' || die "Python 环境自检失败"
import sys
sys.path.insert(0, ".")
import fastapi, uvicorn, pandas, numpy, matplotlib, reportlab  # noqa: F401
import epitoperank
from epitoperank.storage import storage_info
print(f"    Python      {sys.version.split()[0]}")
print(f"    FastAPI     {fastapi.__version__}")
print(f"    pandas      {pandas.__version__}")
print(f"    numpy       {numpy.__version__}")
info = storage_info()
print(f"    数据目录    {info['runtime_root']}")
PY

FD_LIMIT="$(ulimit -n 2>/dev/null || echo unknown)"
if [ "$FD_LIMIT" != "unknown" ] && [ "$FD_LIMIT" -lt 4096 ] 2>/dev/null; then
  warn "文件描述符上限只有 $FD_LIMIT，sgctl 启动时会尝试提到 65535"
fi

cat <<EOF

$(printf '%s安装完成%s' "$C_OK" "$C_RESET")

  机器        ${CORES} 核 / 约 ${MEM_GB} GB 内存
  Python      $("$VENV_PY" -V 2>&1)
  运行目录    $RUN_ROOT
  worker 数   $WORKERS   （并发分析数上限，可用 sgctl set workers N 调整）

下一步：

  cd "$APP_DIR"
  bash deploy/userland/sgctl doctor     # 再看一眼环境是否正常
  bash deploy/userland/sgctl start      # 后台启动
  bash deploy/userland/sgctl status

端口 ${PORT} 的访问方式见 docs/deploy/DEPLOY_NO_SUDO.md（SSH 隧道 / Cloudflare Tunnel）。
EOF
