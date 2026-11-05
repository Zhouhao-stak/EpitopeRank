# EpitopeRank 一键部署命令（复制粘贴版）

> 当你的网络连接稳定时，直接复制这些命令到 Git Bash 或 WSL 执行

---

## 🚀 完整部署（一条命令搞定）

打开 **Git Bash** 或 **WSL**，复制粘贴以下所有命令：

> 下面的 `ssh` 命令会逐条提示输入密码（仓库不再保存密码）。想省掉反复输入，先执行一次
> `ssh-copy-id -p 39145 wang_zi_wei@123.255.66.81` 配置密钥。

```bash
# ===== 第1步：设置变量 =====
SERVER="wang_zi_wei@123.255.66.81"
PORT="39145"
REMOTE_DIR="/home/wang_zi_wei/epitoperank"

# ===== 第2步：创建远程目录 =====
ssh -o StrictHostKeyChecking=no -p $PORT $SERVER "mkdir -p $REMOTE_DIR"

# ===== 第3步：上传文件（使用 tar 管道）=====
cd /e/EpitopeRank
tar czf - \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='node_modules' \
  --exclude='htmlcov' \
  --exclude='dist' \
  --exclude='build' \
  . | ssh -o StrictHostKeyChecking=no -p $PORT $SERVER "cd $REMOTE_DIR && tar xzf -"

echo "✅ Files uploaded!"

# ===== 第4步：配置环境变量 =====
ssh -o StrictHostKeyChecking=no -p $PORT $SERVER "
cd $REMOTE_DIR
if [ ! -f .env ]; then
    cp .env.production.example .env
    echo '️  Please edit .env and add your API key!'
fi
"

# ===== 第5步：启动服务 =====
ssh -o StrictHostKeyChecking=no -p $PORT $SERVER "
cd $REMOTE_DIR
echo 'Starting EpitopeRank...'
docker compose pull
docker compose up -d --build
echo ''
echo 'Container status:'
docker compose ps
echo ''
echo 'Waiting for service...'
sleep 15
curl -s http://localhost:8800/api/health || echo 'Service starting, check logs with: docker compose logs -f'
"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo "Web UI + API: http://123.255.66.81:8800"
```

---

## ⚙️ 配置 API Key（必须）

部署成功后，SSH 登录服务器配置 API Key：

```bash
# SSH 登录
ssh -p 39145 wang_zi_wei@123.255.66.81
# 密码: 手动输入（仓库不保存）

# 编辑配置文件
cd ~/epitoperank
vim .env

# 添加这一行（按 i 进入编辑模式）：
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# 保存退出（按 Esc，然后输入 :wq 回车）

# 重启服务
docker compose restart

# 查看日志
docker compose logs -f
```

---

## 🔄 更新部署

以后每次代码更新后，只需重新运行上面的**第3步和第5步**。

或者创建一个更新脚本 `update-server.sh`：

```bash
#!/bin/bash
SERVER="wang_zi_wei@123.255.66.81"
PORT="39145"
REMOTE_DIR="/home/wang_zi_wei/epitoperank"

echo "Updating EpitopeRank..."

# Upload files
cd /e/EpitopeRank
tar czf - --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' --exclude='node_modules' --exclude='htmlcov' --exclude='dist' --exclude='build' . | \
  ssh -o StrictHostKeyChecking=no -p $PORT $SERVER "cd $REMOTE_DIR && tar xzf -"

# Restart
ssh -o StrictHostKeyChecking=no -p $PORT $SERVER "
cd $REMOTE_DIR
docker compose up -d --build
docker compose ps
"

echo "✅ Update complete!"
```

使用方式：
```bash
chmod +x update-server.sh
./update-server.sh
```

---

## 🔍 验证部署

```bash
# 测试 API
curl http://123.255.66.81:8800/api/health

# 期望输出
{"status":"ok","version":"0.1.0"}

# 查看日志
ssh -p 39145 wang_zi_wei@123.255.66.81 "cd ~/epitoperank && docker compose logs -f"
```

---

## 💡 如果网络不稳定

### 方案 A：使用 WinSCP 图形界面上传

1. 下载 WinSCP: https://winscp.net
2. 连接信息：
   - 主机: `123.255.66.81`
   - 端口: `39145`
   - 用户: `wang_zi_wei`
   - 密码: 登录时手动输入（仓库不保存）
3. 将 `E:\EpitopeRank\` 文件夹拖拽到服务器的 `/home/wang_zi_wei/epitoperank/`
4. 然后 SSH 登录执行第5步（启动服务）

### 方案 B：分批上传

如果大文件传输失败，可以分批次上传关键文件：

```bash
# 先上传核心代码
tar czf - epitoperank/*.py requirements.txt Dockerfile docker-compose*.yml | \
  ssh -p $PORT $SERVER "cd $REMOTE_DIR && tar xzf -"

# 再上传子目录
for dir in agent analysis api interface llm splicing; do
    tar czf - epitoperank/$dir/ | \
      ssh -p $PORT $SERVER "cd $REMOTE_DIR && tar xzf -"
    echo "Uploaded $dir"
done
```

---

##  常见问题

**Q: Connection timed out**
A: 检查网络连接，稍后再试。服务器可能暂时不可用。

**Q: Permission denied**
A: 确认密码正确，或者联系管理员确认你的账户权限。

**Q: Docker command not found**
A: 服务器上 Docker 未安装，需要管理员安装。

**Q: Port already in use**
A: 修改 `docker-compose.coolify.yml` 中的端口映射，例如改为 `9800:8800`。

---

**祝你部署顺利！** 遇到问题随时告诉我具体的错误信息。
