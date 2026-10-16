# 文档索引

部署目录选择见 [部署导航](../deploy/README.md)，已有用户先看 [目录迁移](../deploy/MIGRATION.md)。

| 系统/范围 | 文档 |
|---|---|
| Ubuntu 整体部署 | [从 Git、构建到启动](../deploy/ubuntu/all/README.md) |
| Ubuntu 单独部署 | [CORE / GAME / P2P / 后台](../deploy/ubuntu/split/README.md) |
| Ubuntu 构建与运维 | [平台入口](../deploy/ubuntu/README.md) |
| Ubuntu 依赖、端口、验证 | [兼容性](ubuntu/compatibility.md)、[端口](ubuntu/ports.md)、[验收记录](ubuntu/validation.md) |
| CentOS 整体部署 | [完整流程](centos/deployment.md)、[镜像验收](centos/validation.md) |
| CentOS 旧镜像维护 | [外置 MySQL](centos/legacy/external-mysql.md)、[内置 MySQL](centos/legacy/bundled-mysql.md) |
| 共同背景 | [兼容性分析](compatibility-audit.md)、[早期修复记录](deployment-fixes-2026-10-15.md) |

`ubuntu/validation/`、`centos/validation/` 保留各自历史测试报告。历史报告中的提交与镜像 ID 对应测试时版本，
目录整理不代表重新执行整套游戏运行验收。真实 Windows 客户端体验尚未完成端到端验收。
