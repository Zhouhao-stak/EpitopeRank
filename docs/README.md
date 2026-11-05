# EpitopeRank 文档索引

根目录只保留 [`README.md`](../README.md) 作为入口，其余文档按用途归档在这里。

## 概览

| 文档 | 说明 |
| --- | --- |
| [手把手教程.html](手把手教程.html) | **零基础图文教程：从启动、新建分析、看剪接结果，一路走到生成候选肽 + HLA 预测，全程用真实数据、带 12 张界面截图和实跑数字** |
| [USER_GUIDE.md](USER_GUIDE.md) | **完整使用手册：输入数据格式（rMATS 五类 JC 表 / 样本元数据 / CDS 对照表）、生成肽三条路线、API 速查、FAQ** |
| [QUICKSTART.md](QUICKSTART.md) | 三步跑通第一个分析 |
| [DATA_AND_DEPLOY.md](DATA_AND_DEPLOY.md) | **数据存在哪 · 部署到服务器 · 免费域名与 HTTPS** |
| [智能体的手册.md](智能体的手册.md) | 平台能力全清单：哪些已上线、哪些实验性、边界在哪 |
| [NEOANTIGEN.md](NEOANTIGEN.md) | 剪接新抗原流程：moPepGen / pVACsplice / 结果解读注意事项 |
| [PEPTIDE.md](PEPTIDE.md) | **肽预测层：MHC-I/II 结合、加工、稳定性、MHC-NP、已知表位查询、novelty 过滤、综合评分、CLI/API/MCP 用法** |
| [DATASETS.md](DATASETS.md) | **可用数据集目录：PRELP rMATS / TCGA PanCan / GSE319608 / HCC1395 / splice2neo 的边界与加载方式，以及肽参考数据来源** |
| [BIOGAIP_COMPARISON.md](BIOGAIP_COMPARISON.md) | 与 BioGAIP 的能力对照与改进记录（历史快照） |
| [prompts/](prompts/) | Agent 提示词草稿 |

## 部署（`deploy/`）

> 先看 [DATA_AND_DEPLOY.md](DATA_AND_DEPLOY.md) —— 它把数据目录、Docker 部署、免费域名三件事一次讲完。
> 下面是特定场景的细节文档，部分内容写于更早版本，路径与域名示例请以新文档为准。

| 文档 | 场景 |
| --- | --- |
| [DEPLOY_COOLIFY.md](deploy/DEPLOY_COOLIFY.md) | Coolify 面板部署（推荐，带自动 HTTPS） |
| [COOLIFY_QUICKSTART.md](deploy/COOLIFY_QUICKSTART.md) | Coolify 最快路径 |
| [DEPLOYMENT_WORKFLOW.md](deploy/DEPLOYMENT_WORKFLOW.md) | 各部署方式的取舍对比 |
| [DEPLOY_NO_SUDO.md](deploy/DEPLOY_NO_SUDO.md) | **128 核共享服务器、无 sudo、内网无外网端口**（当前 123.255.66.81 的实际做法） |
| [DEPLOY_NO_ROOT.md](deploy/DEPLOY_NO_ROOT.md) | 无 root 权限服务器（通用流程） |
| [DEPLOY_123.255.66.81.md](deploy/DEPLOY_123.255.66.81.md) | 现有测试机部署记录 |
| [SERVER_UPDATE_123.255.66.81.md](deploy/SERVER_UPDATE_123.255.66.81.md) | **123.255.66.81 增量更新：源码 bind mount、不重建镜像、一键脚本、回滚与实测结果** |
| [COMPLETE_DEPLOY_GUIDE.md](deploy/COMPLETE_DEPLOY_GUIDE.md) | 完整手把手部署 |
| [MANUAL_DEPLOY_STEPS.md](deploy/MANUAL_DEPLOY_STEPS.md) | 手工部署步骤 |
| [QUICK_DEPLOY.md](deploy/QUICK_DEPLOY.md) | 最简部署命令 |
| [WINSCP_DEPLOY_GUIDE.md](deploy/WINSCP_DEPLOY_GUIDE.md) / [WINSCP_ONE_CLICK.md](deploy/WINSCP_ONE_CLICK.md) | WinSCP 图形化上传 |
| [DOCKER_USAGE.md](deploy/DOCKER_USAGE.md) / [README_DOCKER.md](deploy/README_DOCKER.md) | Docker 使用与镜像说明 |

部署脚本仍在仓库根目录：`deploy-to-coolify.sh`、`deploy-to-server.sh`、`deploy-to-123.255.66.81.sh`、`build-on-server.sh`、`check-deploy-status.sh`。

## 开发（`dev/`）

| 文档 | 说明 |
| --- | --- |
| [BUILD_GUIDE.md](dev/BUILD_GUIDE.md) | PyInstaller / Docker 打包 |
| [TESTING.md](dev/TESTING.md) | 测试策略与覆盖率门槛 |
| [TESTING_QUICKSTART.md](dev/TESTING_QUICKSTART.md) | 跑测试的最短路径 |
| [TEST_SUMMARY.md](dev/TEST_SUMMARY.md) | 测试补强记录 |
| [API_CONFIG.md](dev/API_CONFIG.md) | 大模型 / API 配置项 |
| [WEB_UI_ACCESS_GUIDE.md](dev/WEB_UI_ACCESS_GUIDE.md) | Web UI 访问方式 |
