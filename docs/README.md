# 文档索引

部署目录选择见 [部署导航](../deploy/README.md)，已有用户先看 [目录迁移](../deploy/MIGRATION.md)。
项目全貌见 [架构与目录](architecture.md)，开发流程见 [CONTRIBUTING](../CONTRIBUTING.md)。

| 系统/范围 | 文档 |
|---|---|
| 后台开发及业务入口 | [后台文档](admin/README.md) |
| Windows 登录器 | [构建与使用](launcher/README.md) |
| 测试与工具 | [tests](../tests/README.md)、[scripts](../scripts/README.md)、[metadata](../metadata/README.md) |
| 本轮目录整理验证 | [构建、文件核对与启动回归](project-layout-validation.md) |
| Ubuntu 整体部署 | [从 Git、构建到启动](../deploy/ubuntu/all/README.md) |
| Ubuntu 单独部署 | [CORE / GAME / P2P / 后台](../deploy/ubuntu/split/README.md) |
| Ubuntu 构建与运维 | [平台入口](../deploy/ubuntu/README.md) |
| Ubuntu 依赖、端口、验证 | [兼容性](ubuntu/compatibility.md)、[端口](ubuntu/ports.md)、[验收记录](ubuntu/validation.md) |
| CentOS 整体部署 | [完整流程](centos/deployment.md)、[镜像验收](centos/validation.md) |
| CentOS 旧镜像维护 | [外置 MySQL](centos/legacy/external-mysql.md)、[内置 MySQL](centos/legacy/bundled-mysql.md) |
| 共同背景 | [兼容性分析](history/compatibility-audit.md)、[早期修复记录](history/deployment-fixes-2026-10-15.md) |

`ubuntu/validation/`、`centos/validation/` 保留各自历史测试报告。历史报告中的提交与镜像 ID 对应测试时版本，
目录整理不代表重新执行整套游戏运行验收。真实 Windows 客户端体验尚未完成端到端验收。
