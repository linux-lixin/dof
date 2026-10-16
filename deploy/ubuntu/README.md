# Ubuntu 24.04 部署目录

Ubuntu 镜像仅连接自建外部 MySQL，使用 onlyGuo 后台；不含内置 MySQL、NetBird/Tailscale 或旧统一登录器网关。
本目录是导航入口，执行 Compose 时先进入具体部署目录。

| 目录 | 用途 |
|---|---|
| [build](build/README.md) | 从 Git 源码构建游戏与后台镜像 |
| [all](all/README.md) | 一台主机整体部署：game（ALL）+ admin |
| [split](split/README.md) | CORE → P2P → GAME → 后台，跨主机角色部署 |
| [split/core](split/core/README.md) | 核心服务，可选同机后台 |
| [split/game](split/game/README.md) | 游戏频道节点 |
| [split/p2p](split/p2p/README.md) | relay/STUN 节点 |
| [split/admin](split/admin/README.md) | 独立后台节点 |
| shared | 共享游戏 Compose 定义，不直接启动 |

每个实际部署目录都自带 `.env.example`。把它复制为该目录的 `.env`，填写后在同一目录运行
`docker compose config --quiet` 和 `docker compose up`。后台镜像与 CentOS 共用，无需再做一套后台源码。

旧版直接在 `deploy/ubuntu` 运行的用户，先看 [目录迁移说明](../MIGRATION.md)。
不要在新目录直接启动空数据栈。这里按**镜像系统**分类，宿主机同样可以是 Ubuntu。

## 端口与地址


以下对应示例大区 3、频道 11 和 52，值来源于仓库内各服务 cfg 模板及 relay/网关配置。
改大区/频道后要同时调整端口映射，不能只改 `OPEN_CHANNEL`。
在仓库根目录可运行 `python3 scripts/diagnostics/ubuntu_ports.py --group 3 --channels 11,52` 重算；
若仍位于本指南的 `deploy/ubuntu` 目录，运行 `python3 ../../scripts/diagnostics/ubuntu_ports.py --group 3 --channels 11,52`。
当前生成结果见 [角色端口表](../../docs/ubuntu/ports.md)。

| 角色 | 用途 | 协议/端口 | 来源 |
|---|---|---|---|
| CORE | 玩家频道列表 | TCP/UDP 7001 | `channel/cfg/server.cfg` |
| GAME | 玩家频道 | TCP 30011、30052；UDP 31011、31052 | `game/cfg/server.template` |
| P2P | 玩家中继 | TCP/UDP 7300 | `relay/cfg/relay.cfg` |
| P2P | STUN | UDP 2311–2313 | `stun/cfg/server.cfg` |
| CORE | 节点间 bridge | TCP/UDP 7000 | `bridge/cfg/server.cfg` |
| CORE | relay 注册 | TCP 5003 | `ubuntu/relay.py`，公式 500 + 大区 |
| CORE | monitor/guild | TCP/UDP 33303、33403 | `monitor`、`guild` cfg |
| CORE | statistic/doublecheck | UDP 33503、33703 | `statics`、`coserver` cfg |
| CORE | 拍卖/点券拍卖 | TCP/UDP 33803、33603 | `auction`、`point` cfg |
| CORE | community | TCP 33100 | `community/cfg/server.cfg` |
| CORE | 内部 dbmw/manager | 20203、20303、20403、40403 | 相应 cfg；不映射到宿主机 |
| CORE/GAME/ALL | 本地数据库代理 | TCP 127.0.0.1:3306、3307 | mysql_proxy；不映射到宿主机 |
| 全部 | Supervisor 管理 | 容器内 127.0.0.1:180 / Unix socket | supervisord；不映射到宿主机 |
| 后台 | HTTP/API | TCP 18080 → 80 | Compose |

节点间端口绑定 `NODE_BIND_IP`，仅允许可信 GAME/P2P 节点访问；玩家端口按需要放行。
容器不使用 TUN、NET_ADMIN、privileged；非空 `NB_SETUP_KEY`/`TS_AUTH_KEY` 会被拒绝。
默认 Compose 模板要求显式 `PUBLIC_IP`，仅在 `.env` 留空或添加 AUTO/DDNS 参数不能启用地址发现。
若使用运行时的自动发现功能，须先编辑当前使用的 Compose 文件及其引用的 `shared/common.yaml`：
移除该节点所有 `${PUBLIC_IP:?…}` 强制非空引用，并将以下变量透传到对应服务的 `environment`：

```yaml
PUBLIC_IP: ${PUBLIC_IP:-}
AUTO_PUBLIC_IP: ${AUTO_PUBLIC_IP:-false}
DDNS_ENABLE: ${DDNS_ENABLE:-false}
DDNS_DOMAIN: ${DDNS_DOMAIN:-}
DDNS_INTERVAL: ${DDNS_INTERVAL:-10}
```

然后在 `.env` 留空 `PUBLIC_IP`，选择 `AUTO_PUBLIC_IP=true` 或 `DDNS_ENABLE=true`，重新解析 Compose 后用 `up -d` 重建服务。
ALL 模板的 `P2P_PUBLIC_IP` 当前也引用必填 `PUBLIC_IP`，启用发现时还须改为独立、明确的玩家可达 P2P IPv4。
`CORE_PUBLIC_IP`、`MAIN_BRIDGE_IP`、`P2P_PUBLIC_IP` 及 `GAME_CHANNEL_HOSTS` 仍须按拓扑配置；
本机 PUBLIC_IP 的发现不会自动更新其他节点的这些地址。
显式 IPv4 始终优先；AUTO 模式获取一次地址，DDNS 模式持续检查。
`DDNS_DOMAIN` 非空时解析 A 记录；为空时沿用外网地址探测脚本。首次获取有时间上限，运行中变更会触发相关服务重启。

## 更新与回退

Ubuntu `/data/.dnf-ubuntu.json` 记录平台与受管脚本哈希。升级仅覆盖匹配当前或已知旧发行版哈希的脚本。
用户修改脚本时，启动列出冲突路径并退出，不覆盖修改。升级前先保存自定义改动，再根据新脚本重新合并。
PVF、密钥、用户配置、`dp/` 中的自定义 hook、`user_daily_script.sh` 不参与自动脚本升级。
新增旧发行版可升级列表时维护 `services/game/runtime/ubuntu/releases.json`，不能把任意未知哈希加入以绕过冲突。

未标记的 CentOS 数据目录会被拒绝。迁移时先创建独立 Ubuntu 目录与数据库副本；
首次启动前，数据目录中预放经核对的 `Script.pvf`、`publickey.pem`，无需旧网关 `privatekey.pem`。
不要提前放入 `Config.ini`、`dp/` 或其他自定义配置，否则未标记目录检查会拒绝启动。
完成首次初始化、确认 `.dnf-ubuntu.json` 已生成后，停止对应角色服务，再备份并按需合并必要的自定义配置、
`dp/` 内容或 `user_daily_script.sh`；不要复制旧 CentOS 的受管 `run/`、`monitor_ip/` 脚本覆盖新版本。
重新启动并验收后再决定切换。自定义 DP 插件需另行测试其 ABI；后台 RSA 私钥对仍按[整体部署第 3 节](all/README.md#3-启动后台初始化管理员配对密钥)单独保留和配对。

回退时停止 Ubuntu 测试栈，恢复原 CentOS 镜像、配置、独立运行目录和它原来使用的数据库。
本流程不改动这些资源；不能把 Ubuntu 新写入的测试数据库直接当作原业务数据库回退。
不要执行会删除业务数据卷的 `down -v`。

从含旧网关的 Ubuntu 版本升级：拉取代码并重建游戏镜像后，执行
`docker compose up -d --force-recreate game`（拆分 CORE/GAME/P2P 分别使用对应 Compose 文件）。
仅执行 restart 不会更换镜像；重建容器后旧进程和旧容器配置随之移除。
已有 `.env` 中的 `GATE_PASSWORD` 可删除。挂载目录里历史 `Config.ini`、`privatekey.pem` 不再读取或生成，
不会为清理日志而自动删除你的持久化文件。自定义 `/data/conf.d` 若另行定义了旧网关，需要自行移除该自定义启动项。
CentOS 的旧登录器兼容入口不在本次 Ubuntu 清理范围内。

## 可重复验收

从仓库根目录执行，要求 Python 3.9+、Docker 和足够内存：

```bash
python3 tests/unit/test_ubuntu_runtime.py
python3 tests/integration/test_built_images.py --ubuntu --game-image dnf-game:ubuntu24-v1 --mode all --state-file dist/ubuntu-all-state.json --stable-seconds 1800
python3 tests/integration/test_built_images.py --ubuntu --game-image dnf-game:ubuntu24-v1 --mode split --state-file dist/ubuntu-split-state.json --stable-seconds 1800
```

每个测试使用独立名称、网络、卷和随机凭据，无公网端口、不访问现有服务器。
失败保留现场；证据在对应 state 文件旁的 `*-evidence/`。state 文件含临时测试凭据，不提交、不分享。
确认结果后只清理该次资源：

```bash
python3 tests/integration/test_built_images.py --ubuntu --state-file dist/ubuntu-all-state.json --cleanup
python3 tests/integration/test_built_images.py --ubuntu --state-file dist/ubuntu-split-state.json --cleanup
```
