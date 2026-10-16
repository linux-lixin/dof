# 1995chen + onlyGuo：云服务器公网直连测试部署指南

> 2026-10-15 修订：上传部署目录时必须包含 fixes/，本地初始化与日志修复见 [修复说明](../../deployment-fixes-2026-10-15.md)。

日期：2026-10-14。适用目标：先不修改业务代码，在已有 Linux／云服务器上测试注册、登录和进游戏。**不使用隧道。**

**建议采用：单台 x86_64 Linux + Docker Compose；游戏和后台使用作者镜像，登录器在 Windows 编译。**

本文保留全新部署步骤。现有服务器已采用外部 MySQL 5.6.50 完成游戏/后台启动验证，修复详见配套记录；玩家进服仍待测。示例 IP `203.0.113.10` 是占位地址，必须替换。

## 1. 部署方式有几种，怎样选择

### 服务器放在哪里

| 方式 | 适用情况 | 注意点 |
|---|---|---|
| **已有 Linux／云服务器** | 你当前的选择，Windows 直接连接 | 固定可达 IP，配置安全组的 TCP/UDP |
| Windows 上的 Linux 虚拟机 | 自己或局域网测试 | 优先使用 Windows 能直达的虚拟机网络；PUBLIC_IP 填虚拟机可达地址 |
| Windows Docker Desktop／WSL2 | 熟悉 Linux 容器与 Windows 网络 | 还要验证 UDP、旧游戏二进制、卷权限，不能仅凭容器启动认定游戏兼容 |
| Linux 实体机／NAS | 局域网常开设备 | 确认 x86_64；外网还需要路由映射和公网条件 |

Docker Desktop 的 WSL2 设置参考 [Docker 官方文档](https://docs.docker.com/desktop/features/wsl/)。本次不要求 Windows 安装 Docker。

### 程序怎样安装、拆分

| 方式 | 特点 | 本轮建议 |
|---|---|---|
| docker run 逐个启动 | 简单直观，但参数容易遗漏 | 可用 |
| **Compose + 作者预构建镜像** | 配置集中、重启和复现方便 | **主方案** |
| 源码构建镜像 | 适合后续改代码 | onlyGuo 后台当前有缺 libs 目录、依赖解析待验证的问题，暂不作为“不修代码”的主路径 |
| 游戏 Docker，后台直接运行 Java/前端 | 开发调试方便 | 要自行处理构建、代理、初始化和进程管理 |
| 独立数据库、多大区、CORE/P2P/GAME 拆分 | 方便扩展 | onlyGuo 写死了部分库名且使用单数据源，需额外适配 |
| K8s | 集群编排 | 第一轮没必要增加复杂度 |

主方案是一个游戏容器（内含游戏 MySQL）、一个后台容器；测试下载时加一个文件服务。**不要另外安装 MySQL 8 来替换游戏数据库。**

参考：[1995chen 高级部署说明](https://github.com/1995chen/dnf/blob/08f724c25b12748f8eb4bf11b24a90accfc3b223/doc/OtherDeploy.md)。

## 2. 公网直连的连接关系

~~~mermaid
flowchart LR
  W["Windows 测试电脑"] -->|"HTTP 18080：注册、登录、配置"| A["onlyGuo 后台"]
  W -->|"游戏 TCP / UDP"| G["1995chen 游戏服务"]
  W -.->|"可选 HTTP 18081：ZIP 下载"| F["文件服务"]
  A -->|"Docker 内网 game:3306"| DB["游戏容器内 MySQL"]
  G --> DB
~~~

| 配置项 | 填写内容 |
|---|---|
| 登录器 BaseUrl | `http://服务器公网IP:18080` |
| 浏览器后台 | `http://服务器公网IP:18080/login` |
| 后台“服务器地址” | 游戏公网 IP，不加 http://，不填 18080 |
| 1995chen PUBLIC_IP | 同一个游戏公网 IP |
| 后台 JDBC 主机 | `game:3306`，Docker 内部服务名 |
| 游戏大区及库名 | `SERVER_GROUP=3`、`SERVER_GROUP_DB=cain` |

SSH 仅用于管理 Linux 和上传文件，没有端口隧道。Windows 的 localhost 不是云服务器。云主机如果采用公网 NAT，公网 IP 可能不出现在网卡上，端口映射仍使用模板的 0.0.0.0。

本方案不走 7600/881 的统一登录器路径。原游戏镜像内部仍可能启动统一网关，但模板不公开其端口。

## 3. 前置条件与版本

### 3.1 Linux 主机

在 Linux 执行：

~~~bash
uname -m
cat /etc/os-release
free -h
swapon --show
df -h
~~~

- 架构应为 `x86_64`。后台镜像有 ARM64 版本，不等于整套游戏服务支持 ARM。
- 建议测试起点：2–4 vCPU、8 GB 内存、足够的 swap、约 80 GB 以上可用磁盘，再按客户端体积留空间。这是联调余量建议，不是实测最低配置。
- 客户端、ZIP、解压目录、镜像和备份可能同时占空间。
- 模板保留 `shm_size: 8g`，这是共享内存上限，不等于已经分配的内存，也不是 swap。
- 宿主机不必使用 CentOS 5/7。示例可在 Ubuntu 22.04/24.04 x86_64 上准备 Docker，但旧游戏二进制与内核仍需实测。

安装 Docker Engine 和 Compose plugin，请按 [Docker 官方 Ubuntu 步骤](https://docs.docker.com/engine/install/ubuntu/) 或 [其他发行版入口](https://docs.docker.com/engine/install/) 操作。已有 Docker 的服务器先检查，不要为套教程卸载现有容器环境。

~~~bash
sudo docker version
sudo docker compose version
openssl version
~~~

Docker 必须有可用 Server，仅有 Client 不够。本指南后续 Linux 命令统一使用 sudo，避免混淆 Docker 权限。

### 3.2 Windows 本地代码与游戏客户端

源码已在：

~~~text
D:\Projects\dof
├─ dnf-game
├─ dnf-server-public
├─ DNFLogin
├─ docs
└─ dnf-stack.code-workspace
~~~

| 仓库 | 固定提交 |
|---|---|
| 1995chen/dnf | 08f724c25b12748f8eb4bf11b24a90accfc3b223 |
| onlyGuo/dnf-server-public | 4b03fe72c288e2c96db491640c7eaefe45c8c5b5 |
| onlyGuo/DNFLogin | 7f82eea909ec01b5a9cf36ada176bf373316136b |

还要准备完整 Windows 游戏客户端、配套 DOF 补丁 DNF.exe、Script.pvf、资源及运行依赖。源码仓库不等于完整客户端，不能随意混用不同包的 PVF、等级补丁和 EXE。

**第一轮用现成完整客户端验证登录，第二轮再测试空目录自动下载。**

### 3.3 本文使用的镜像

已在 2026-10-14 用 Docker CLI 读取到以下 manifest：

| 用途 | 标签 | 固定 digest |
|---|---|---|
| 游戏 | 1995chen/dnf:centos7-2.1.9.fix1 | sha256:0c2f1b8c66cce9375c07fa4501f2498659df874727ea820fc2d1ec4e48006a7a |
| 后台 | guoshengkai/dnf-server:latest | sha256:fd5fbb61aca1af13a5f55a302ce6b9bfb0e5e36dc7e211d1a64a9443989e914e |

附件按“标签 + digest”固定，防止 latest 后续变化。**manifest 查询成功不证明镜像与已审计源码完全相同**，也不证明服务能运行，所以后面还要检查入口、初始化和 API。

来源：[1995chen 镜像说明](https://github.com/1995chen/dnf/blob/08f724c25b12748f8eb4bf11b24a90accfc3b223/doc/PrepareLinux.md)、[onlyGuo Docker 指南](https://github.com/onlyGuo/dnf-server-public/blob/4b03fe72c288e2c96db491640c7eaefe45c8c5b5/DOCKER_README_CN.md)。

## 4. 先设置云安全组

**来源只允许测试电脑的实际公网 IPv4 /32**，不是服务器自己的公网 IP。多人测试分别加来源。电脑公网 IP 变化后需更新规则。

| 端口 | 协议 | 用途 | 是否放行 |
|---|---|---|---|
| 22 或实际 SSH 端口 | TCP | 管理/上传 | 管理者 IP |
| 18080 | TCP | 后台页面和客户端 API | 测试者 IP |
| 7001 | TCP、UDP | 频道入口 | 测试者 IP |
| 7300 | TCP、UDP | Relay | 测试者 IP |
| 30011、30052 | TCP | 11、52 频道 | 测试者 IP |
| 31011、31052 | UDP | 11、52 频道 | 测试者 IP |
| 2311–2313 | UDP | STUN | 测试者 IP |
| 18081 | TCP | 可选 ZIP 下载 | 测下载时才放行 |
| 3306、3000 | TCP | 数据库 | 不公开 |
| 180、2000 | TCP | Supervisor | 不公开 |
| 7600、881 | TCP | 统一登录器/网关 | 本方案不公开 |

模板用 IPv4 0.0.0.0 发布玩家端口，因此来源限制必须由安全组落实。**不要仅以 UFW 默认拒绝判断 Docker 端口已被保护**；Docker 会配置自己的转发规则。无云安全组的 Linux 服务器，要先做好适用于 Docker 转发流量的访问控制。

依据：[Docker 端口发布](https://docs.docker.com/engine/network/port-publishing/)、[防火墙限制](https://docs.docker.com/engine/install/ubuntu/#firewall-limitations)。

本轮公网 IP 直连采用 HTTP，只使用独立测试密码。长期使用时添加域名和 HTTPS；不使用隧道也能使用 HTTPS。

## 5. 上传附件，准备全新测试目录

本地附件：

~~~text
D:\Projects\dof\deploy\centos\legacy\bundled-mysql
├─ compose.yaml
├─ .env.example
├─ fixes/                   # 必须一并上传；管理员 SQL 另从 deploy/shared 复制
└─ README.md
~~~

### Windows PowerShell：上传

将 serveruser 和 IP 换成真实值：

~~~powershell
ssh serveruser@203.0.113.10 "mkdir -p ~/dnf-deploy"
scp -r "D:\Projects\dof\deploy\centos\legacy\bundled-mysql" serveruser@203.0.113.10:~/dnf-deploy/
scp "D:\Projects\dof\deploy\shared\bootstrap-admin.sql.example" serveruser@203.0.113.10:~/dnf-deploy/
~~~

SSH 非 22 端口时，ssh 用 `-p`，scp 用大写 `-P`。不需要任何 -L/-R 参数。

### Linux：准备目录和环境文件

主流程只用于**全新测试目录和新数据库**。如果 /opt/dnf-test 已存在服务数据，先停止照抄，核对已有部署，不能重复首次初始化。

~~~bash
sudo mkdir -p /opt/dnf-test
sudo cp ~/dnf-deploy/bundled-mysql/compose.yaml /opt/dnf-test/
sudo cp -r ~/dnf-deploy/bundled-mysql/fixes /opt/dnf-test/
sudo cp ~/dnf-deploy/bundled-mysql/.env.example /opt/dnf-test/.env
sudo cp ~/dnf-deploy/bootstrap-admin.sql.example /opt/dnf-test/
cd /opt/dnf-test
sudo mkdir -p runtime/game/data runtime/game/mysql runtime/game/log
sudo mkdir -p runtime/admin/data packages
sudo chmod 700 runtime/admin/data
sudo chmod 600 .env
sudo nano .env
~~~

修改：

| 变量 | 要求 |
|---|---|
| PUBLIC_IP | 实际游戏公网 IPv4 |
| DB_ROOT_PASSWORD | 独立随机数据库密码 |
| GAME_DB_PASSWORD | **恰好 8 位**字母数字 |
| SUPERVISOR_PASSWORD | 独立管理密码 |
| GATE_PASSWORD | 原统一网关测试密码，字母数字 |
| GAME_IMAGE、ADMIN_IMAGE | 首轮保留附件固定值 |

旧脚本会把部分密码插入 SQL/配置文件。测试时使用随机十六进制字符串，避免引号、美元符号、反斜杠等解析问题。分别用 `openssl rand -hex 16`、`openssl rand -hex 4`、`openssl rand -hex 12` 生成合适长度，填到相应项，不保留 CHANGE_ME。

大区 3、库名 cain、频道 11/52 已在 compose.yaml 配好。

~~~bash
sudo docker compose config --quiet
~~~

无输出表示解析通过。此命令不能验证占位 IP 是否替换、8 位密码长度、镜像兼容性或游戏能否运行。

## 6. 准备成对密钥和匹配 PVF

### 6.1 密钥

在 Linux /opt/dnf-test 检查：

~~~bash
sudo ls -l runtime/admin/data/private.key runtime/admin/data/publickey.pem
~~~

**仅在首次部署、两个文件都不存在时**执行生成；已有任意一个文件应先核对，不能重新覆盖：

~~~bash
sudo openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out runtime/admin/data/private.key
sudo openssl pkey -in runtime/admin/data/private.key -pubout -out runtime/admin/data/publickey.pem
sudo chmod 600 runtime/admin/data/private.key
sudo chmod 644 runtime/admin/data/publickey.pem
sudo cp runtime/admin/data/publickey.pem runtime/game/data/publickey.pem
~~~

后台用 private.key，游戏端只用公钥。私钥不进入玩家发行包或 packages。

核对三份公钥表示的哈希：

~~~bash
sudo openssl pkey -in runtime/admin/data/private.key -pubout -outform DER | sha256sum
sudo openssl pkey -pubin -in runtime/admin/data/publickey.pem -outform DER | sha256sum
openssl pkey -pubin -in runtime/game/data/publickey.pem -outform DER | sha256sum
~~~

三行应相同。不要删除某一个密钥来“刷新”：原后台入口在任意一个文件缺失时会重新生成整对。

### 6.2 PVF

已有配套客户端时，建议首次启动前将它对应的 Script.pvf 放到：

~~~text
/opt/dnf-test/runtime/game/data/Script.pvf
~~~

Windows 上传：

~~~powershell
scp "D:\DNF-TestClient\Script.pvf" serveruser@203.0.113.10:~/dnf-deploy/Script.pvf
~~~

Linux：

~~~bash
sudo cp ~/dnf-deploy/Script.pvf /opt/dnf-test/runtime/game/data/Script.pvf
~~~

若使用额外等级补丁，也要配套核对 df_game_r。没有提供 PVF 时，1995chen 会初始化自带 PVF，可用来检查启动，但不保证与你的客户端一致。

后台“PVF 管理”用于道具解析等功能，不能替代游戏端的这份 PVF；首次验证登录也不必先把 PVF 导入后台。

### 6.3 拉取镜像、检查入口

~~~bash
cd /opt/dnf-test
sudo docker compose pull game admin
sudo docker compose run --rm --no-deps --entrypoint sh admin -c 'ls -l /app/entrypoint.sh /app/init.sql.template; grep -n db_initialized /app/entrypoint.sh'
~~~

最后一条覆盖入口做只读检查，不执行后台初始化。如果镜像内文件或行为与文档不一致，先核对实际内容，不能继续把源码假设当作镜像事实。

拉取失败先排查网络、DNS、镜像名和 digest。官方文档有其他 registry 候选，但不能把 Docker Hub digest 直接套到另一个 registry，也不要换成不明镜像。

## 7. 先启动游戏服务

~~~bash
sudo docker compose up -d game
sudo docker compose ps
sudo docker compose logs --tail=100 game
sudo docker compose exec game supervisorctl status
~~~

首次会初始化 MySQL、游戏库和频道，耗时以日志为准。模板 healthcheck 只检查账号表与 cain 关联表可查询，**healthy 不等于可以进副本**。

交互式检查数据库：

~~~bash
sudo docker compose exec game mysql -uroot -p
~~~

输入 DB_ROOT_PASSWORD，执行：

~~~sql
SHOW DATABASES;
SELECT COUNT(*) FROM d_taiwan.accounts;
SELECT COUNT(*) FROM taiwan_cain_2nd.member_avatar_coin;
SELECT COUNT(*) FROM taiwan_login.member_login;
SELECT COUNT(*) FROM taiwan_billing.cash_cera;
EXIT;
~~~

必须有 d_taiwan、taiwan_cain、taiwan_cain_2nd、taiwan_login、taiwan_billing 等库。若没有 cain，先排查初始化和 SERVER_GROUP_DB。

查看游戏日志和进程：

~~~bash
sudo find runtime/game/log -type f -name '*.init'
sudo docker compose exec game sh -c 'ps -ef | grep "[d]f_game_r"'
~~~

目录名 siroco11/siroco52 是编号 3 大区名称，与使用 cain 数据库名不矛盾。结合对应 .init、.error 和 supervisor 状态判断，不要只看容器 Up。

## 8. 再启动后台，确认初始化成功

~~~bash
sudo docker compose up -d admin
sudo docker compose logs --tail=160 admin
sudo docker compose exec admin test -f /app/data/.db_initialized
curl --fail http://127.0.0.1:18080/api/v1/client/version/1.0.0
~~~

最后一项空更新列表通常应返回 `[]`。这里 localhost 是 Linux 本机自检，Windows 依然公网直连。

同时确认：

- 日志无 Database initialization failed。
- 成功后生成 .db_initialized。
- d_taiwan.accounts 增加了 admin、parent_uid、isRobot。
- dnf_service 存在 ASSIST_CONFIG、CLIENT_LAUNCHER_CONFIG、CLIENT_LAUNCHER_VERSION 等表。
- 客户端 API 能响应，而不仅是首页能打开。

初始化失败先停止后台：

~~~bash
sudo docker compose stop admin
~~~

不要反复删除标记或重跑 init.sql：原脚本有 ADD 列和 DROP/CREATE 表；本地修复入口在失败时退出，遇到部分初始化会阻止自动重导。网页可访问不能证明数据库准备正确。

模板把 admin 自动重启关闭，让首次初始化错误保持可见；服务器重启后需要检查并显式启动后台。本方案没有提前手工导入 init.sql，如果你已经手工导入，不能再照首次自动初始化重复执行。

## 9. 不改代码时，创建测试管理员和推荐人

普通注册不填推荐人会默认找 `admin`。为绕过这个测试阻断点，在**新测试库**创建一个名为 admin 的后台管理员，用于管理和推荐关系。这只是测试数据准备，不是长期修复。

~~~bash
sudo docker compose exec game mysql -uroot -p
~~~

先核对结构与同名账号：

~~~sql
SHOW COLUMNS FROM d_taiwan.accounts;
SELECT UID, accountname, admin, parent_uid
FROM d_taiwan.accounts WHERE accountname='admin';
~~~

若已有记录，停止创建，核对来源和权限；不要插入重复账号或直接覆盖密码。

若没有，替换密码占位符后执行：

~~~sql
INSERT INTO d_taiwan.accounts
(accountname, password, qq, VIP, admin, parent_uid, isRobot)
VALUES
('admin', MD5('CHANGE_ME_PRIVATE_ADMIN_PASSWORD'), '', '', 1, 0, 0);
~~~

选用独立随机 ASCII 字母数字密码。MD5 仅为了匹配当前应用，不是建议新系统采用这种密码设计。附件 SQL 示例需编辑并分步执行，不能原样整文件导入。

不同镜像可能预置公开授权值，也可能为空表；测试前使用下列语句新增或替换：

~~~sql
INSERT INTO dnf_service.ADMIN_TEMP_PASSWORD (id, PASSWORD)
VALUES (1, 'CHANGE_ME_DIFFERENT_PRIVATE_TEMP_SECRET')
ON DUPLICATE KEY UPDATE PASSWORD=VALUES(PASSWORD);
EXIT;
~~~

**这个管理员不要用于进游戏**：手工插入没有创建全部游戏关联行。真正的游戏账号在第 12 步由登录器注册。

Windows 浏览器打开 `http://服务器公网IP:18080/login`，账号为 admin，密码为刚设置的管理员密码。原统一网关的 GM_ACCOUNT/GM_PASSWORD 不是这个后台的账号。

## 10. 后台配置好之后再开登录器

1. 辅助配置／内辅管理：把“服务器地址”改为游戏公网 IP，保存；等级与客户端一致，本地 GM 功能保持关闭。
2. 版本管理：第一轮不添加补丁记录，保持更新列表为空。
3. 完整包配置：记录确认过的资源基线，例如 1.0.0；完整包下载放到第 14 节。
4. 图片/门户配置：按需替换作者地址；作者默认下载 URL 不能视为与你的服务已经配套。

Windows 验证：

~~~powershell
Invoke-RestMethod "http://你的服务器公网IP:18080/api/v1/client/version/1.0.0"
Invoke-WebRequest "http://你的服务器公网IP:18080/api/v1/admin/assist/config-text"
~~~

第二项返回的“服务器地址”必须是你的 IP。当前登录器依赖这条匿名配置接口，虽然路径里有 admin，也不能在代理层直接一刀切禁止后再期待登录成功。

同时检查 `/api/v1/client/full-package`。测试空目录下载前，必须替换成自己托管、确定匹配的客户端 ZIP 地址。

## 11. Windows 编译登录器、配置客户端

安装 **.NET 10 SDK**，只有 runtime 不能编译。安装器或 WinGet 方法见 [Microsoft 官方说明](https://learn.microsoft.com/en-us/dotnet/core/install/windows)。

Windows PowerShell：

~~~powershell
dotnet --list-sdks
dotnet publish "D:\Projects\dof\DNFLogin\DNFLogin.csproj" -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o "D:\Projects\dof\artifacts\launcher"
~~~

使用 WinGet 时对应 SDK 包为 `Microsoft.DotNet.SDK.10`。安装后重新打开终端。

准备独立客户端目录：

~~~text
D:\DNF-TestClient
├─ DNF.exe            配套 DOF 游戏启动程序
├─ Script.pvf
├─ ImagePacks2
├─ DNFLogin.exe       onlyGuo 登录器
├─ login.ini
└─ 其他客户端 DLL/资源
~~~

把 publish 输出的全部发行文件放到游戏根目录，保留原游戏资源。不能用 DNFLogin.exe 替换 DNF.exe，也不要漏掉发布目录中的其他依赖。

运行前创建 UTF-8 login.ini：

~~~ini
[Login]
BaseUrl=http://你的服务器公网IP:18080
WindowTitle=DNF Test
GameVersion=1.0.0

[Credentials]
RememberPassword=False
~~~

- BaseUrl 不要加 /api/v1，登录器会自己拼接。
- GameVersion 必须对应实际客户端资源，不可随便标成最新版。
- 原更新器仅检测 Script.pvf 就可能跳过完整包；必须人工确认 EXE、DLL、ImagePacks2 齐全。
- 登录器会从后台重新写 DNF.toml，地址应在后台配置，不能只改本地 TOML。
- login.ini 缺失或错误时源码可能回退到作者域名，测试期间务必核对文件。
- 玩家使用自包含发布产物无需自行编译，但仍要验证游戏本体运行依赖。

PVF 对照：

~~~powershell
Get-FileHash "D:\DNF-TestClient\Script.pvf" -Algorithm SHA256
~~~

~~~bash
sha256sum /opt/dnf-test/runtime/game/data/Script.pvf
~~~

## 12. 注册普通账号、进入游戏

1. 运行 DNFLogin.exe，完成资源检查，进入登录页。
2. 注册一个新的普通测试账号，不拿后台管理员进游戏。
3. 验证码字母按小写输入，例如图片 AB12 输入 ab12，这是现有大小写问题的临时绕行方式。
4. 推荐人可留空，默认对应已建立的 admin；也可显式填写 admin。
5. 注册成功后登录，登录器会获取凭据、写 DNF.toml、启动 DNF.exe。
6. 依次验证：角色列表 → 创建/选择角色 → 频道 → 副本 → 退出重登。
7. 然后再用第二台测试电脑验证连接和组队。

API 返回 token 仅证明后台生成了凭据，不代表游戏端已经接受。失败时核对关联表、公私钥、PVF、配套 EXE、配置 IP 和 TCP/UDP。

本文的 onlyGuo 流程不要求按统一登录器教程修改 hosts。若目标客户端另有版本特定依赖，按该客户端说明核对，不要机械混入另一套登录器配置。

## 13. 故障排查表

| 现象 | 优先检查 |
|---|---|
| 镜像拉不下来 | DNS、registry、镜像名/digest；不是先重装游戏 |
| no matching manifest / exec format error | x86_64/ARM 架构及镜像选择 |
| game 长期 unhealthy | MySQL 初始化、密码、cain 表、磁盘/内存；查看健康检查结果 |
| 容器 Up，但游戏进不去 | supervisor、df_game_r、频道初始化和错误日志 |
| Linux localhost 正常，Windows 访问失败 | 安全组来源是否为测试电脑公网 IP；18080 TCP、公网地址和宿主机规则 |
| 首页正常，API 404 | 镜像功能与源码不一致或代理路径错误；停在 API 核验步骤 |
| duplicate column | 初始化重复执行；不要删标记重试 |
| 缺 taiwan_cain 相关表 | SERVER_GROUP_DB 是否在首次初始化前设为 cain；旧数据不等于改环境变量就自动迁移 |
| 推荐人不存在 | admin 是否创建成功，显式推荐人是否拼错 |
| 验证码总不通过 | 小写输入、刷新验证码，核对实际镜像接口 |
| 无法更新配置文件 | config-text 接口能否读到文本、游戏目录是否可写 |
| 登录成功，游戏没启动 | 配套 DNF.exe、运行依赖、目录权限、DNF.toml |
| 灰频道/网络中断 | PUBLIC_IP、TOML、频道 TCP/UDP、PVF |
| GeoIP Fail | 日志中的实际源 IP、geo_allow；不要盲目放开所有来源 |
| 游戏进程立即崩溃 | 旧二进制/内核兼容、配套补丁、资源；先收集日志再决定更换镜像 |
| 更新一半失败 | 恢复备份的完整客户端；不能把进度条当成功 |
| 修改 .env 后不生效 | 运行中容器不会自动读取新环境；需协调相关组件并用 up -d 重建 |

常用命令，Linux /opt/dnf-test：

~~~bash
sudo docker compose ps -a
sudo docker compose logs --tail=150 game admin
sudo docker compose exec game supervisorctl status
sudo docker inspect --format '{{json .State.Health}}' "$(sudo docker compose ps -q game)"
free -h
swapon --show
df -h
~~~

贴日志时不要贴 .env、私钥或包含真实密码的配置输出。

## 14. 登录成功后，单独测试完整下载和小补丁

这是第二轮，可先跳过。

### 下载服务

~~~bash
cd /opt/dnf-test
sudo docker compose --profile download up -d files
~~~

安全组额外放行 TCP 18081，来源仍限测试电脑 IP。files 只读挂载 packages，不挂载密钥和数据库目录。

### 完整包

ZIP 根目录应直接是 DNF.exe、Script.pvf、ImagePacks2 等，不能外套“客户端”目录，也不能把 7z 改扩展名当 ZIP。

不要放入测试凭据、私钥、数据库、缓存或用户 login.ini，也不要借此替换正在运行的登录器自身。

上传到 `/opt/dnf-test/packages/client-1.0.0.zip`。确保文件服务可读，例如仅给 packages 目录 755、公开 ZIP 文件 644，不要递归放宽私钥目录权限。

后台完整包配置：

~~~text
版本：1.0.0
URL：http://你的服务器公网IP:18081/client-1.0.0.zip
~~~

先在 Windows 验证 URL 真能下载，再用另一个空目录，仅放登录器发布文件与正确 login.ini，验证完整包下载、解压和登录。

### 单个小补丁

从基线 1.0.0 做一个仅含少量资源或无关测试文本的小 ZIP，上传为 patch-1.0.1.zip。后台添加并启用 1.0.1 版本，URL 为：

~~~text
http://你的服务器公网IP:18081/patch-1.0.1.zip
~~~

重启登录器，确认下载、文件落盘、GameVersion 更新。第一包不建议直接替换大型 PVF 或 DNF.exe。

先做 1.0.0 → 1.0.1 是为了验证基本功能，不是认定跨版本正确。原实现的字符串排序、校验、失败恢复、断点续传、删除旧文件和登录器自更新仍待修复；后台有 md5 字段也不等于客户端实际校验它。

## 15. 停止、重启与备份

停止：

~~~bash
cd /opt/dnf-test
sudo docker compose --profile download stop
~~~

重新启动：

~~~bash
sudo docker compose up -d game
sudo docker compose up -d admin
~~~

要用下载服务，再启动 files profile。修改 .env 后应使用 up -d 使相关容器重新创建，普通 restart 不重新读取 Compose 环境；数据库密码和密钥变更还需要组件间保持一致。

首次跑通后做冷备份：

~~~bash
cd /opt/dnf-test
sudo docker compose --profile download stop
sudo tar -czf "/opt/dnf-test-backup-$(date +%Y%m%d-%H%M%S).tgz" .env compose.yaml runtime
~~~

备份含数据库、私钥和初始化标记，必须放在受控位置，不能放进 packages。恢复应选单独的新目录，恢复同一组配置/密钥/数据库/PVF，使用相同镜像核验；不要覆盖运行中的数据库。

测试流程不需要删除 MySQL 目录、删除 .db_initialized 或清空卷。

## 16. 验收与已完成范围

| 检查 | 通过标准 | 状态 |
|---|---|---|
| 主机 | x86_64，Docker Server/Compose 可用，资源足够 | 待测 |
| 游戏库 | d_taiwan、cain、login、billing 可查询 | 外部 MySQL 5.6.50 已核对 |
| 游戏服务 | 频道进程稳定、初始化日志正常 | 修复后短时观察通过，长期/玩家负载待测 |
| 后台 | 初始化标记、表结构、客户端 API 一致 | 已核对，网页/API 返回 200 |
| 公网直连 | Windows 能读后台和正确的配置 IP | 待测 |
| 注册 | 普通账号创建成功、游戏关联行齐全 | 待测 |
| 游戏 | 角色、频道、副本、重登 | 待测 |
| 第二台电脑 | 连接和组队 | 待测 |
| 下载更新 | 完整包和单个小补丁，单独验收 | 待测 |

现已准备初始化源码修复、Compose 覆盖文件、环境模板和管理员 SQL，并完成外部 MySQL 服务器启动修复。详见 deployment-fixes-2026-10-15.md；尚未修改 Java/C# 业务逻辑或完成玩家端验收。

详细已知问题另见 compatibility-audit.md。测试跑通不代表这些问题已修复。

