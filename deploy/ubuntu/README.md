# Ubuntu 24.04 独立部署入口

Ubuntu 是可选版本，原 `deploy/local-images` 的 CentOS 默认部署不变。
仅支持 amd64 和外部 MySQL；本轮验收基线为 MySQL 5.6.51。后台与登录器沿用现有版本。
实际测试范围和未验收项见 [Ubuntu 验收报告](../../docs/ubuntu-validation.md)，
依赖来源见 [兼容库审计](../../docs/ubuntu-compatibility.md)。

Docker 管理容器生命周期；本版保留 Supervisor 管理角色内部的多个旧服务进程。
日常用 `docker compose up/stop/logs`，排障或单独重启内部服务时才用容器内的 `supervisorctl`。
宿主机不需要安装 Supervisor。子进程退出由 Supervisor 恢复；健康检查失败本身不会触发 Docker 重启容器。
每个内部服务各用一个容器、移除 Supervisor 属于后续架构改造，不在本版范围。

## 1. 从 Git 获取源码，在服务器构建

准备已安装 Docker Engine/Compose 的 Linux amd64 服务器，以及独立管理的 MySQL 5.6 实例。
构建需要访问 Docker 镜像仓库、Ubuntu APT、Maven/npm 源；游戏资源与兼容依赖源码已在 Git 内。
不需要单独下载游戏资源、运行资源下载脚本或下载源码 ZIP。

```bash
git clone https://github.com/linux-lixin/dof.git
cd dof
docker build --platform linux/amd64 -f dnf-game/build/Ubuntu24-DNF/Dockerfile -t dnf-game:ubuntu24-v1 dnf-game
docker build --platform linux/amd64 -t dnf-admin:local-fix-20261015 dnf-server-public
cd deploy/ubuntu
cp .env.example .env
chmod 600 .env
nano .env
```

填写真实 `PUBLIC_IP`、`DB_HOST`、`DB_PORT` 和各密码。`203.0.113.*` 仅是文档示例。
`GAME_DB_PASSWORD` 恰好 8 位字母/数字，可用 `openssl rand -hex 4` 生成。
其余密码使用独立随机字母/数字值，例如 `openssl rand -hex 16`。
本套旧 SQL/配置模板不支持任意标点密码，入口会明确拒绝不符合要求的值，不会静默截断。

数据库必须是专用测试实例，或专用测试副本；初始化会管理多个 schema 和 `game` 用户。
ALL/CORE 使用的数据库 root 需要全局权限及 GRANT OPTION。按实际容器出口 IP 授权，
不要把 `127.0.0.1` 当作容器可达的宿主机数据库地址。同机原生 MySQL 使用宿主机内网 IP。
MySQL 监听、防火墙、用户 host 授权必须允许所有游戏节点与后台节点连接。
不要同时让 CentOS 和 Ubuntu 测试栈初始化同一个业务数据库。

`MYSQL_INIT_SSL_MODE=disabled` 为旧数据库 CLI 关闭 TLS；`auto` 保留 MariaDB 客户端默认行为。
后台 JDBC 的 `useSSL=false` 是独立选项。这里使用 MariaDB **客户端**连接外部 MySQL，镜像中没有数据库服务端。

## 2. ALL 单机启动

始终使用新的 `deploy/ubuntu/runtime/`，不要复制整个旧 CentOS `/data` 进来。
ALL/GAME 首次启动前必须自行上传与客户端匹配的 `Script.pvf`，文件名大小写必须一致。
镜像不再自动提供默认 PVF；缺少文件、文件为空或误建成目录时，会在连接和修改数据库之前退出。
CORE/P2P 不需要该文件。现有数据目录中的 PVF 会保留，不自动覆盖。

```bash
mkdir -p runtime/game/data
# 将你自己的 Script.pvf 上传到当前目录下的 runtime/game/data/Script.pvf
test -s runtime/game/data/Script.pvf
```

挂载关系为 `./runtime/game/data:/data`，无需另外增加单文件挂载。公钥可预放配对版本。
替换已有 PVF 时先执行 `docker compose stop game`，上传完成后再 `docker compose up -d game`。
文件检查只能确认存在且非空，版本是否匹配仍需实际启动和客户端验证。

```bash
docker compose config --quiet
docker compose up -d game
docker compose logs -f --tail 100 game
```

`Ctrl+C` 只退出日志跟随。另一个终端验证：

```bash
docker compose ps
docker compose exec game python3 /opt/dnf/ubuntu/health.py
docker compose exec game bash -c 'grep -h "GeoIP Allow Country Code" /home/neople/game/log/siroco*/Log*.init'
```

健康检查包含真实子进程、角色端口、外部数据库和 P2P 注册；Supervisor 的 RUNNING 字样不足以判定完成。
每个依赖阶段最多等 600 秒，单次 TCP 探测最多 2 秒。错误信息会指出失败依赖。

## 3. 启动后台、初始化管理员、配对密钥

```bash
docker compose up -d admin
docker compose logs -f --tail 100 admin
```

后台首次启动会初始化 `dnf_service`；失败不写成功标记。已有库但没有标记时拒绝重放破坏性初始化。
打开 `http://你的服务器地址:18080`。管理员仍需单独初始化：

```bash
cp ../external-mysql/bootstrap-admin.sql.example bootstrap-admin.sql
chmod 600 bootstrap-admin.sql
nano bootstrap-admin.sql
mysql -h 你的数据库内网IP -P 3306 -uroot -p < bootstrap-admin.sql
rm bootstrap-admin.sql
```

初始化账号为 `admin`，普通玩家未填写推荐人时也默认使用 `admin`。管理员密码由你填写，没有固定默认密码。
先修改 SQL 中两个占位密码，按注释核对已有账号，避免重复创建。不要提交编辑后的 SQL 或把密码粘贴到日志。

已有库升级不会自动改名。如果之前创建了 `123123`，先查询：

```sql
SELECT UID, accountname, admin FROM d_taiwan.accounts
WHERE accountname IN ('123123', 'admin');
```

仅当 `admin` 不存在且 `123123` 确为需要改名的管理员时，执行：

```sql
UPDATE d_taiwan.accounts SET accountname = 'admin'
WHERE accountname = '123123' AND admin = 1;
```

这会保留 UID、密码和基于 UID 的推荐关系；若 `admin` 已存在，应先核对其身份，不能覆盖或重复插入。
重建并更新后台镜像后，玩家未填推荐人才会使用新的默认值。已有库不要重放后台初始化 SQL。
后台生成自己的 RSA 密钥对后，将公钥同步给游戏端：

```bash
docker compose cp admin:/app/data/publickey.pem ./runtime/game/data/publickey.pem
docker compose restart game
docker compose exec game python3 /opt/dnf/ubuntu/health.py
```

后台 `/app/data/private.key` 保持私密。所有 GAME 节点都需要与后台私钥对应的公钥。
内置旧网关私钥是另一套配置，不能把后台私钥随意复制到旧网关路径。

用新建的管理员账号登录后台，在辅助配置／内辅管理中设置“服务器地址”：ALL 填玩家可达的本机地址，
拆分部署填玩家可达的 CORE 频道入口地址。容器的 `PUBLIC_IP` 不会自动写入后台配置；
不修改时后台仍可能下发上游示例地址。保持本地 GM 关闭，等级等配置与客户端/PVF 一致，首轮更新列表保持为空。
在后台所在主机核验实际下发内容：

```bash
curl --fail http://127.0.0.1:18080/api/v1/admin/assist/config-text
```

确认返回的“服务器地址”为自己的玩家入口，且玩家可访问后台 API 和下文列出的游戏端口。
完整的后台配置、客户端包、登录器配置和更新发布步骤见 [完整部署文档第 12–15 步](../../docs/fresh-server-deployment.md#12-开放端口并配置后台)。
本轮没有验证真实 Windows 客户端注册、登录、进副本、组队与自动更新下载。

## 4. CORE / P2P / GAME 跨主机拆分

每台主机均 Git 拉取并构建 Ubuntu 镜像，使用各自新的运行目录。三台主机共享同一个外部测试数据库实例。
需要后台的 CORE 主机同时构建后台镜像。

拆分时 CORE 的 `GAME_DB_ALLOW_IP` **必须填写**覆盖 CORE 和所有 GAME 节点数据库连接来源的地址模式，
例如可信内网 `10.2.4.%`。以 MySQL 实际看到的来源 IP 为准，容器跨主机连接可能经过宿主机 NAT。
留空自动识别只适用于 ALL；拆分模板会拒绝留空，GAME 也会使用 `game` 账号检查实际权限后才启动。
若节点不在一个可安全授权的网段内，应由数据库管理员逐个建立对应的 `game@host` 授权，
CORE 中仍填写它自身匹配的授权地址；不要为了省事默认开放 `%`。

CORE 另需设置 `GAME_CHANNEL_HOSTS`，例如 `11=10.2.4.11,52=10.2.4.11`。
左侧为频道号，右侧为 CORE 能到达的 GAME 主机内网 IPv4；覆盖 CORE 的全部 `OPEN_CHANNEL`，不允许重复或遗漏。
频道位于不同主机时分别填写地址。该映射用于 statics/coserver 的服务器间 UDP 路由，不能填 CORE 自身地址。
GAME 主机必须放行并映射对应频道 UDP 端口（例：31011、31052），允许 CORE 访问。
ALL 自动把自己的频道映射到容器 loopback，无需填写此映射。

多个 GAME 主机必须分别配置自己的频道子集。`common.yaml` 的 `OPEN_CHANNEL` 当前固定为 `11,52`，
只在 `.env` 添加 `OPEN_CHANNEL` 不会改变它；在每台 GAME 主机的现有 `compose.game.yaml` 中，
向 `services.game.environment` 添加 `OPEN_CHANNEL` 覆盖继承值，并编辑该服务的 `ports` 列表。
例如在 `10.2.4.11` 主机上保留其他已有字段，将相应部分设为：

```yaml
services:
  game:
    environment:
      OPEN_CHANNEL: "11"
    ports:
      - "30011:30011/tcp"
      - "31011:31011/udp"
```

这是现有服务的局部编辑示例，不是完整 Compose 文件。另一台 `10.2.4.12` 主机设置 `OPEN_CHANNEL: "52"`，
其端口列表只保留 TCP 30052 和 UDP 31052。CORE 保留全部频道 `OPEN_CHANNEL: "11,52"`，
并在 CORE 的 `.env` 中设置 `GAME_CHANNEL_HOSTS=11=10.2.4.11,52=10.2.4.12`。
每个频道只由一台 GAME 主机启动；新增频道时同时更新 CORE 的频道全集、映射及对应 GAME 的频道子集/端口。
编辑后在各主机运行相应的 `docker compose -f ... config --quiet` 和 `up -d` 使配置生效。

公网通告地址可与容器网卡不同。Ubuntu 为 auction/point 使用 `0.0.0.0` 监听，
manager/DBMW 的本机 CORE 路由使用 loopback；玩家通告仍使用原 PUBLIC_IP，协议和端口不变。

| 主机 | 启动文件 | 本机 PUBLIC_IP | 其他地址 |
|---|---|---|---|
| CORE | `compose.core.yaml` | 玩家可达的 CORE 地址 | `NODE_BIND_IP` 为 CORE 主机真实内网 IP |
| P2P | `compose.p2p.yaml` | 玩家可达的 P2P 地址 | `CORE_IP`、`BRIDGE_IP` 为 CORE 内网 IP |
| GAME | `compose.game.yaml` | 玩家可达的 GAME 地址 | `CORE_IP`、`BRIDGE_IP` 为 CORE 内网 IP；`P2P_IP` 为玩家可达 P2P 地址 |

P2P 的 Compose 文件不读取或传入数据库凭据；只需 GAME_IMAGE、PUBLIC_IP、CORE_IP、BRIDGE_IP、P2P_RELAY_INDEX。
同一主机上的多个角色也必须使用不同的运行目录，不能把 CORE 与 GAME 的 `/data` 指向同一个目录。
示例每个主机只运行一个角色，不能把三个文件直接合并后共用目录。

先在 CORE 主机执行：

```bash
docker compose -f compose.core.yaml config --quiet
docker compose -f compose.core.yaml up -d core
docker compose -f compose.core.yaml logs -f --tail 100 core
docker compose -f compose.core.yaml exec core python3 /opt/dnf/ubuntu/health.py
```

CORE 完成数据库初始化后，在 P2P 主机执行：

```bash
docker compose -f compose.p2p.yaml config --quiet
docker compose -f compose.p2p.yaml up -d p2p
docker compose -f compose.p2p.yaml exec p2p python3 /opt/dnf/ubuntu/health.py
```

等待注册完成，再在 GAME 主机执行：

```bash
docker compose -f compose.game.yaml config --quiet
docker compose -f compose.game.yaml up -d game
docker compose -f compose.game.yaml exec game python3 /opt/dnf/ubuntu/health.py
```

最后回 CORE 主机启动后台并按上节初始化：

```bash
docker compose -f compose.core.yaml up -d admin
```

从 CORE 后台取出公钥，安全复制到 GAME 主机的 `runtime/game/data/publickey.pem`，再重启 GAME。
CORE 和 P2P 互通使用内网实际 IP；Docker 服务名不能用于不同主机之间的连接。
网关注册内部消息保持 `ip,index,port` 格式，Ubuntu relay 适配层使用有超时的 TCP 收发及确认，避免旧 nc 的 EOF 等待差异。

## 5. 端口与地址

以下对应示例大区 3、频道 11 和 52，值来源于仓库内各服务 cfg 模板及 relay/网关配置。
改大区/频道后要同时调整端口映射，不能只改 `OPEN_CHANNEL`。
在仓库根目录可运行 `python3 scripts/ubuntu_port_matrix.py --group 3 --channels 11,52` 重算；
若仍位于本指南的 `deploy/ubuntu` 目录，运行 `python3 ../../scripts/ubuntu_port_matrix.py --group 3 --channels 11,52`。
当前生成结果见 [角色端口表](../../docs/ubuntu-ports.md)。

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
| CORE/ALL | 旧网关 | TCP 7600、881 | `init/Config.ini`；onlyGuo 流程不默认映射 |
| CORE/GAME/ALL | 本地数据库代理 | TCP 127.0.0.1:3306、3307 | mysql_proxy；不映射到宿主机 |
| 全部 | Supervisor 管理 | 容器内 127.0.0.1:180 / Unix socket | supervisord；不映射到宿主机 |
| 后台 | HTTP/API | TCP 18080 → 80 | Compose |

节点间端口绑定 `NODE_BIND_IP`，仅允许可信 GAME/P2P 节点访问；玩家端口按需要放行。
容器不使用 TUN、NET_ADMIN、privileged；非空 `NB_SETUP_KEY`/`TS_AUTH_KEY` 会被拒绝。
默认 Compose 模板要求显式 `PUBLIC_IP`，仅在 `.env` 留空或添加 AUTO/DDNS 参数不能启用地址发现。
若使用运行时的自动发现功能，须先编辑当前使用的 Compose 文件及其引用的 `common.yaml`：
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

## 6. 更新与回退

Ubuntu `/data/.dnf-ubuntu.json` 记录平台与受管脚本哈希。升级仅覆盖匹配当前或已知旧发行版哈希的脚本。
用户修改脚本时，启动列出冲突路径并退出，不覆盖修改。升级前先保存自定义改动，再根据新脚本重新合并。
PVF、密钥、用户配置、`dp/` 中的自定义 hook、`user_daily_script.sh` 不参与自动脚本升级。
新增旧发行版可升级列表时维护 `dnf-game/ubuntu/releases.json`，不能把任意未知哈希加入以绕过冲突。

未标记的 CentOS 数据目录会被拒绝。迁移时先创建独立 Ubuntu 目录与数据库副本；
首次启动前，数据目录中只可预放经核对的 `Script.pvf`、`publickey.pem` 及需要保留的旧网关 `privatekey.pem`。
不要提前放入 `Config.ini`、`dp/` 或其他自定义配置，否则未标记目录检查会拒绝启动。
完成首次初始化、确认 `.dnf-ubuntu.json` 已生成后，停止对应角色服务，再备份并按需合并必要的自定义配置、
`dp/` 内容或 `user_daily_script.sh`；不要复制旧 CentOS 的受管 `run/`、`monitor_ip/` 脚本覆盖新版本。
重新启动并验收后再决定切换。自定义 DP 插件需另行测试其 ABI；后台 RSA 私钥对仍按第 3 节单独保留和配对。

回退时停止 Ubuntu 测试栈，恢复原 CentOS 镜像、配置、独立运行目录和它原来使用的数据库。
本流程不改动这些资源；不能把 Ubuntu 新写入的测试数据库直接当作原业务数据库回退。
不要执行会删除业务数据卷的 `down -v`。

## 7. 可重复验收

从仓库根目录执行，要求 Python 3.9+、Docker 和足够内存：

```bash
python3 tests/test_ubuntu_runtime.py
python3 tests/test_built_images.py --ubuntu --game-image dnf-game:ubuntu24-v1 --mode all --state-file dist/ubuntu-all-state.json --stable-seconds 1800
python3 tests/test_built_images.py --ubuntu --game-image dnf-game:ubuntu24-v1 --mode split --state-file dist/ubuntu-split-state.json --stable-seconds 1800
```

每个测试使用独立名称、网络、卷和随机凭据，无公网端口、不访问现有服务器。
失败保留现场；证据在对应 state 文件旁的 `*-evidence/`。state 文件含临时测试凭据，不提交、不分享。
确认结果后只清理该次资源：

```bash
python3 tests/test_built_images.py --ubuntu --state-file dist/ubuntu-all-state.json --cleanup
python3 tests/test_built_images.py --ubuntu --state-file dist/ubuntu-split-state.json --cleanup
```
