# CentOS 7 部署目录

这里的 CentOS 指游戏镜像基础系统，宿主机仍可使用 Ubuntu x86_64。

| 目录 | 用途 |
|---|---|
| [build](build/README.md) | 服务器从源码构建镜像 |
| [all](all/README.md) | 已有自建镜像整体部署，外置 MySQL |
| [split](split/README.md) | 单独后台及角色拆分能力说明 |
| [split/admin](split/admin/README.md) | 后台单独部署 |
| [legacy/external-mysql](legacy/external-mysql/README.md) | 旧官方镜像 + 补丁挂载 + 自建 MySQL |
| [legacy/bundled-mysql](legacy/bundled-mysql/README.md) | 旧官方镜像内置 MySQL 测试方案 |

新部署完整步骤见 [CentOS 镜像部署文档](../../docs/centos/deployment.md)。
旧 `deploy/local-images` 等路径的已有服务，先看 [目录迁移](../MIGRATION.md)。
legacy 仅用于已有旧镜像维护，不与当前自建镜像方案混用。
