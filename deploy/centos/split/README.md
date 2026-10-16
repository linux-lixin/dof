# CentOS 单独部署范围

可以在 [all](../all/README.md) 中仅运行 `docker compose up -d game`，将后台放在
[admin](admin/README.md) 的独立主机。游戏容器仍使用 ALL 角色；两个目录使用同一个自建 MySQL。
不要再启动 all 目录中的 admin，公钥需要从后台主机复制到游戏主机。

CentOS 原程序存在 CORE/GAME/P2P 角色，但当前仓库没有通过跨主机验收的 CentOS 角色拆分模板。
例如 statics/coserver 仍把全部频道路由替换为同一个 MONITOR_PUBLIC_IP，不能照搬 Ubuntu 的 GAME_CHANNEL_HOSTS。
本次目录整理保留原运行行为，不把 Ubuntu 适配层套到 CentOS 镜像上。
需要 CORE、GAME、P2P 分主机时，使用 [Ubuntu 拆分部署](../../ubuntu/split/README.md)。
