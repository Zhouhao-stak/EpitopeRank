# EpitopeRank Web UI 访问指南

## ✅ 部署状态

**服务已成功启动！**

- **容器状态**: Up & Healthy ✓
- **API 服务**: http://0.0.0.0:8800 ✓
- **Web UI**: http://0.0.0.0:8800/ ✓（页面由 API 在 `/` 直接渲染）
- **端口映射**: 8800 (API + Web UI) ✓

## 🌐 访问方式

### 方式一：直接访问（如果服务器端口开放）

在浏览器中打开以下任一地址：

```
http://123.255.66.81:8800        # Web UI
http://123.255.66.81:8800/docs   # API 文档（Swagger UI）
```

### 方式二：SSH 隧道（推荐，更安全）

在你的本地机器上运行以下命令（Windows PowerShell 或 CMD）：

```bash
ssh -L 8800:localhost:8800 -p 39145 wang_zi_wei@123.255.66.81
```

保持 SSH 会话打开，然后在浏览器中访问：

```
http://localhost:8800        # Web UI
http://localhost:8800/docs   # API 文档
```

**参数说明**：
- `-L 8800:localhost:8800`：将服务器的 8800 端口转发到本地的 8800 端口
- `-p 39145`：服务器 SSH 端口
- `wang_zi_wei@123.255.66.81`：服务器用户名和地址

## 📱 Web UI 功能

Web UI 提供以下功能（9 个页面：仪表盘 / AI 流水线 / 事件浏览器 / 可视化 / 基因浏览器 / 报告 / 剪接候选新抗原 / 肽预测 / 设置）：

1. **项目管理**：查看、创建和管理剪接分析项目
2. **数据上传**：上传 rMATS 结果（JC 事件表或厂商逐样本导出）
3. **可视化**：查看剪接事件的 PSI 值、差异分析图表
4. **报告生成**：生成包含候选基因排序、功能富集、文献证据的科研报告
5. **设置**：配置模型密钥、调用 MCP 工具

## 🔧 API 测试

通过 Swagger UI 测试 API：

1. 访问 http://localhost:8800/docs
2. 点击任意 API 端点展开
3. 点击 "Try it out" 按钮
4. 填写参数并执行请求

常用端点：
- `GET /api/health` - 健康检查
- `GET /api/projects` - 列出所有项目
- `POST /api/analyze` - 提交新分析任务

## 🔑 API Key 配置

当前已配置的 DeepSeek API Key：
```
MODEL_API_KEY=sk-your-api-key-here
```

如需更换，编辑服务器上的 `.env` 文件：
```bash
ssh -p 39145 wang_zi_wei@123.255.66.81
cd /home/wang_zi_wei/epitoperank
nano .env
# 修改 MODEL_API_KEY
docker compose restart
```

## 📊 监控和维护

### 查看容器状态
```bash
ssh -p 39145 wang_zi_wei@123.255.66.81
docker ps | grep epitoperank
```

### 查看实时日志
```bash
docker compose logs -f
```

### 重启服务
```bash
docker compose restart
```

### 查看资源使用
```bash
docker stats epitoperank
```

## ⚠️ 注意事项

1. **保持 SSH 会话打开**：如果使用 SSH 隧道方式，需要保持 SSH 会话一直打开
2. **防火墙设置**：确保服务器防火墙允许 8800 端口访问（或直接使用 SSH 隧道）
3. **API Key 安全**：不要公开分享你的 DeepSeek API Key
4. **数据持久化**：分析数据存储在 Docker volume `epitoperank-data` 中，即使容器删除也不会丢失

## 🆘 故障排查

### UI 无法访问
```bash
# 检查容器是否运行
docker ps | grep epitoperank

# 查看日志
docker logs epitoperank --tail 50
```

### API 无响应
```bash
# 测试健康检查
curl http://localhost:8800/api/health

# 查看进程
docker exec epitoperank ps aux
```

### 重新构建和启动
```bash
cd /home/wang_zi_wei/epitoperank
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

**祝你使用愉快！** 🎉

如有问题，请查看日志或联系技术支持。
