# 游戏服务

`docker/centos` 和 `docker/ubuntu` 提供两个基础系统版本；`assets` 共享程序、配置与 SQL；
`runtime/ubuntu` 负责 Ubuntu 的启动适配。仓库里的公开模板密钥不代表你的生产密钥。

在仓库根目录执行（二选一）：

```bash
docker build -f services/game/docker/ubuntu/Dockerfile -t dnf-game:ubuntu24-v1 services/game
docker build -f services/game/docker/centos/Dockerfile -t dnf-game:local-fix-20261015 services/game
```

运行入口使用 [Ubuntu 部署](../../deploy/ubuntu/README.md) 或 [CentOS 部署](../../deploy/centos/README.md)。
不直接在源码目录执行 Compose，不在源码中填写实际密码。

默认 PVF 存档位于 `assets/home/template/init/Script.tgz`。Ubuntu 仍需按部署文档手动解压或上传匹配客户端的 PVF；
整理目录不会恢复自动解压行为。共享游戏文件的来源及哈希见 [资源清单](../../metadata/game-assets.lock.json)。
兼容库来源、许可证和构建哈希位于 `docker/ubuntu/compat-lock.json` 及同目录的版权文件。

CentOS 原有功能保持原样，Ubuntu 启动仍使用 `/opt/dnf/ubuntu/entrypoint.sh`，容器内部路径不变。
系统依赖、初始化和运维边界见 [Ubuntu 文档](../../docs/ubuntu/README.md) 与 [项目结构](../../docs/architecture.md)。
