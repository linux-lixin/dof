# 全新服务器完整部署步骤

更新日期：2026-10-16。

部署方式：**直接拉取 Git 仓库 → 在 Linux 服务器构建镜像 → 连接自建 MySQL 5.6 → 启动游戏和后台 → 配置 Windows 登录器。** 公网直连，不使用隧道；MySQL 原生安装，不由本项目 Compose 创建。

本文适用于 Ubuntu 22.04/24.04、x86_64/amd64 架构，MySQL 与游戏部署在同一台服务器。已有服务迁移请先阅读[自建镜像说明中的迁移注意事项](../deploy/local-images/README.md)，不要覆盖已有配置、运行目录或数据库。

构建资源从提交 `5b592fe` 起已直接纳入 Git。无需源码 ZIP、Git LFS 或 Python 资源下载脚本；基础镜像、CentOS 软件包、Maven/npm 等构建依赖仍需要联网获取。

## 1. 准备系统

除 Windows 操作和 SQL 外，以下命令均在服务器 root 终端执行：

```bash
sudo -i
apt update
apt install -y ca-certificates curl git nano openssl

uname -m
free -h
swapon --show
df -h /
```

架构应显示 `x86_64`。之前本地空载测试中，游戏、后台、MySQL 合计约占 3.1 GiB 内存；构建时的内存需求还会变化。2 GB 主机仍会依赖 swap，swap 不能提供与物理内存相同的性能。先确认内存、swap 和磁盘可用空间，再继续。

## 2. 安装 Docker 和 Compose

已经安装且 `docker compose version` 正常的，可以跳过。以下采用 [Docker 官方 Ubuntu APT 安装方式](https://docs.docker.com/engine/install/ubuntu/)，用于没有安装冲突 Docker 软件包的新系统：

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

docker version
docker compose version
```

## 3. 准备自建 MySQL

通过宝塔或自己的原生安装方式准备一个专用 MySQL 5.6 实例。已验证版本为 5.6.50、5.6.51；不要把 Ubuntu 默认的 `mysql-server` 软件包当作 MySQL 5.6，也不要直接替换为 MySQL 8 或 MariaDB。

记下 root 密码、服务器内网 IPv4 和数据库端口。以下端口按 `3306` 举例；实际配置不同就同步修改后面的 `.env`。

在宝塔 MySQL 配置中，确认 `[mysqld]` 段监听容器可访问的服务器内网地址。例如，将占位符替换成真实 IPv4 后配置：

```ini
[mysqld]
bind-address=REPLACE_WITH_SERVER_PRIVATE_IPV4
port=3306
```

修改后通过宝塔重启 MySQL，再检查：

```bash
ss -lntp | grep ':3306'
```

不能只监听 `127.0.0.1`。实例不要混放其他业务；初始化脚本需要创建多个库并配置数据库账号。

**不要提前手动创建空的 `d_taiwan`、`taiwan_cain`、`dnf_service` 等库。** 游戏初始化会检查库是否存在，空库可能导致跳过导入。此步骤只准备数据库实例，容器网段授权在第 7 步处理。

## 4. 拉取项目

全新目录执行：

```bash
git clone https://github.com/linux-lixin/dof.git /opt/dof
cd /opt/dof
git log -1 --oneline
ls -lh dnf-game/build/dnf_data/home/template/init/Script.tgz
```

`Script.tgz` 约 96 MiB。游戏程序、原始初始化 SQL、依赖库和旧配置也随仓库提供。

如果之前已经克隆且没有正在处理的本地源码修改，使用：

```bash
cd /opt/dof
git pull --ff-only
```

不要再执行旧的 `scripts/fetch_game_assets.py`，该脚本已经删除。`scripts/game-assets.lock.json` 仅保留资源来源、哈希和权限信息，用于审计。

## 5. 在服务器构建镜像

在 `/opt/dof` 下先构建游戏，成功后再构建后台：

```bash
cd /opt/dof

docker build \
  -f dnf-game/build/Centos7-DNF/Dockerfile \
  -t dnf-game:local-fix-20261015 \
  dnf-game

docker build \
  -t dnf-admin:local-fix-20261015 \
  dnf-server-public

docker image ls dnf-game
docker image ls dnf-admin
```

两个镜像都应存在。命令报错时先处理对应构建错误，不继续启动。镜像已包含数据库种子、日志表、后台 SSL 初始化等修复，不需要再挂载旧的 `fixes/` 补丁。

这里的标签是服务器本地构建的镜像，不需要执行 `docker compose pull game admin`，也不需要先导出、导入镜像 tar。

## 6. 填写部署配置

首次部署执行：

```bash
cd /opt/dof/deploy/local-images
cp .env.example .env
chmod 600 .env
nano .env
```

已有 `.env` 时直接编辑，不重新复制覆盖。填写如下字段，所有 `CHANGE_ME` 都必须替换：

```dotenv
GAME_IMAGE=dnf-game:local-fix-20261015
ADMIN_IMAGE=dnf-admin:local-fix-20261015

PUBLIC_IP=CHANGE_ME_PUBLIC_IPV4

DB_HOST=CHANGE_ME_PRIVATE_IPV4
DB_PORT=3306
DB_ROOT_PASSWORD=CHANGE_ME_EXISTING_MYSQL_ROOT_PASSWORD

GAME_DB_PASSWORD=CHANGE_ME
SUPERVISOR_PASSWORD=CHANGE_ME_RANDOM_PASSWORD
GATE_PASSWORD=CHANGE_ME_DIFFERENT_RANDOM_PASSWORD

GAME_DB_ALLOW_IP=
MYSQL_INIT_SSL_MODE=disabled
```

- `PUBLIC_IP`：新服务器公网 IPv4。
- `DB_HOST`：容器可访问的宿主机内网 IPv4，不能填 `127.0.0.1`。
- `DB_ROOT_PASSWORD`：MySQL 已有 root 密码；修改 `.env` 不会修改数据库密码。
- `GAME_DB_PASSWORD`：正好 8 位字母或数字。
- `SUPERVISOR_PASSWORD`、`GATE_PASSWORD`：分别使用独立随机值，不是后台网站管理员密码。
- `GAME_DB_ALLOW_IP`：首次留空，使用脚本探测的来源地址。
- `MYSQL_INIT_SSL_MODE=disabled`：本方案无 TLS 的旧 MySQL 客户端初始化选项；JDBC 的 `useSSL=false` 已在 Compose 中单独设置。

生成游戏数据库密码：

```bash
openssl rand -hex 4
```

其他随机密码分别运行一次：

```bash
openssl rand -hex 16
```

旧脚本对特殊字符处理不一致，本方案使用独立的随机字母数字密码。保存后检查配置：

```bash
docker compose config --quiet
```

没有报错就继续。这个检查只验证 Compose 配置，不验证数据库密码和网络是否正确。

## 7. 授权容器访问 MySQL

先创建网络和容器，不启动：

```bash
docker compose create game admin
docker network inspect dnf-local-images_default \
  --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

假设输出 `172.20.0.0/16`。进入宿主机 MySQL，宝塔通常可以使用下面路径；其他原生安装使用自己安装的 `mysql` 客户端：

```bash
/www/server/mysql/bin/mysql -uroot -p
```

输入数据库 root 密码后授权。**下面地址和掩码仅对应 `172.20.0.0/16`，必须按实际查询到的网段调整。** 密码与 `.env` 的 `DB_ROOT_PASSWORD` 保持一致：

```sql
GRANT ALL PRIVILEGES ON *.*
TO 'root'@'172.20.0.0/255.255.0.0'
IDENTIFIED BY 'CHANGE_ME_EXISTING_MYSQL_ROOT_PASSWORD'
WITH GRANT OPTION;

SHOW GRANTS FOR 'root'@'172.20.0.0/255.255.0.0';
EXIT;
```

宿主机防火墙也要允许实际 Docker 网段连接 MySQL。数据库端口不需要向玩家公网开放。删除并重建 Docker 网络后，子网可能变化，需要重新核对授权。

回到部署目录测试容器连接：

```bash
cd /opt/dof/deploy/local-images
docker compose run --rm --no-deps --entrypoint sh game -c \
'exec mysql --connect_timeout=5 -h "$MAIN_MYSQL_HOST" -P "$MAIN_MYSQL_PORT" -uroot -p -e "SELECT VERSION(), USER(), CURRENT_USER(); SHOW GRANTS;"'
```

输入数据库密码。确认连接成功，而且账号授权不是只有 `USAGE`。`USER()` 显示连接来源，`CURRENT_USER()` 显示实际匹配的授权账号；来源不符合预期时按实际结果排查。

## 8. 启动游戏

```bash
docker compose up -d game
docker compose logs --tail=100 -f game
```

首次会导入数据库、释放资源、启动频道，需要等待几分钟。`Ctrl+C` 只退出这条日志查看命令，不会停止后台容器。

检查频道状态和“五国”日志：

```bash
docker compose ps
docker compose exec game supervisorctl status \
  game:game_siroco11 game:game_siroco52

docker compose exec game sh -c \
'grep -h "GeoIP Allow Country Code" /home/neople/game/log/siroco*/Log*.init'
```

两个频道应持续运行，不能反复退出、重新启动。容器 `healthy` 只表示数据库检查通过；Supervisor 的短时 `RUNNING` 和历史日志也不能单独证明当前频道稳定，要结合后续日志观察。

默认 PVF 自动初始化到：

```text
/opt/dof/deploy/local-images/runtime/game/data/Script.pvf
```

## 9. 启动后台

游戏初始化正常后：

```bash
docker compose up -d admin
docker compose logs --tail=100 admin
docker compose exec admin test -f /app/data/.db_initialized
curl --fail http://127.0.0.1:18080/api/v1/client/version/1.0.0
```

标记检查命令没有输出且成功退出，表示初始化标记存在。尚未配置更新记录时，更新接口通常返回 `[]`。

后台会初始化 `dnf_service` 及账号表所需字段。不要重复手工导入后台 `init.sql`，也不要通过删除 `.db_initialized` 来反复初始化。失败时先查看日志，必要时用 `docker compose stop admin` 停止后台再排查。

## 10. 创建后台管理员

连接外部数据库：

```bash
docker compose exec game sh -c \
'exec mysql -h "$MAIN_MYSQL_HOST" -P "$MAIN_MYSQL_PORT" -uroot -p'
```

先检查结构与同名账号：

```sql
SHOW COLUMNS FROM d_taiwan.accounts;
SELECT UID, accountname, admin, parent_uid
FROM d_taiwan.accounts
WHERE accountname = 'admin';
```

**只有查询没有记录时才执行下面的插入。** 若已有账号，停止创建并核对来源，不覆盖原账号或重复插入。将两个密码占位符换成不同的私密 ASCII 字母数字值：

```sql
INSERT INTO d_taiwan.accounts
(accountname, password, qq, VIP, admin, parent_uid, isRobot)
VALUES
('admin', MD5('CHANGE_ME_NEW_PRIVATE_ADMIN_PASSWORD'), '', '', 1, 0, 0);

INSERT INTO dnf_service.ADMIN_TEMP_PASSWORD (id, PASSWORD)
VALUES (1, 'CHANGE_ME_DIFFERENT_PRIVATE_TEMP_SECRET')
ON DUPLICATE KEY UPDATE PASSWORD = VALUES(PASSWORD);

EXIT;
```

对应文件为 [bootstrap-admin.sql.example](../deploy/local-images/bootstrap-admin.sql.example)。管理员初始化是后台自动初始化完成后的独立操作，不要原样导入带占位符的示例。

`admin` 用于后台管理及当前默认推荐关系，不能直接用于进游戏：手工插入没有创建全部游戏关联数据。MD5 是为了匹配现有应用，并非新系统的密码设计建议。

## 11. 同步登录公钥

全新部署执行：

```bash
cp runtime/admin/data/publickey.pem runtime/game/data/publickey.pem
docker compose restart game
```

等待频道重新启动。后台私钥为 `runtime/admin/data/private.key`，需要与公钥成对保留；不能放进玩家包。已有服务应保留原来配对的密钥，不能随意覆盖。

## 12. 开放端口并配置后台

云安全组和宿主机网络规则需要允许以下端口。测试阶段可以把来源限制为测试电脑公网 IP：

| 用途 | TCP | UDP |
|---|---|---|
| 后台及登录器 API | 18080 | — |
| 游戏连接 | 7001、7300、30011、30052 | 7001、7300、31011、31052、2311–2313 |
| 可选下载服务 | 18081 | — |

Docker 发布端口的流量可能绕过 UFW 的常规规则，公网来源限制应同时在云安全组或适当的 Docker 防火墙规则中落实，参见 [Docker 防火墙说明](https://docs.docker.com/engine/install/ubuntu/#firewall-limitations)。

浏览器访问 `http://服务器公网IP:18080/login`，账号为 `admin`，密码是第 10 步设置的管理员密码。

登录后：

1. 在辅助配置／内辅管理中，将服务器地址改为游戏服务器公网 IP。
2. 等级等配置与实际客户端版本保持一致，本地 GM 功能保持关闭。
3. 第一轮保持更新列表为空。
4. 默认门户、图片、下载地址按自己的部署修改，不能直接使用作者默认地址作为自己的资源。

检查登录器获取的配置：

```bash
curl --fail http://127.0.0.1:18080/api/v1/admin/assist/config-text
```

返回的服务器地址应是你的地址。登录器使用这条匿名配置接口，不能仅因路径里有 `admin` 就在代理层一律禁止访问。

## 13. 在 Windows 编译登录器并配置客户端

WPF 登录器在 Windows 编译。安装 **.NET 10 SDK**，仅安装 Runtime 不够，参见 [微软安装说明](https://learn.microsoft.com/en-us/dotnet/core/install/windows)。

以下假设 Windows 已将同一仓库克隆到 `D:\VScodeProjects\dof`；如果没有，先在 PowerShell 执行 `git clone https://github.com/linux-lixin/dof.git D:\VScodeProjects\dof`。已有目录不要重复克隆。

```powershell
dotnet --list-sdks
dotnet publish "D:\VScodeProjects\dof\DNFLogin\DNFLogin.csproj" `
  -c Release `
  -r win-x64 `
  --self-contained true `
  -p:PublishSingleFile=true `
  -o "D:\VScodeProjects\dof\artifacts\launcher"
```

将发布目录内的全部发行文件放进配套游戏客户端根目录：

```text
客户端目录/
├─ DNF.exe
├─ Script.pvf
├─ ImagePacks2/
├─ DNFLogin.exe
├─ login.ini
└─ 其他游戏文件
```

**仓库不包含完整 Windows 游戏客户端。** 需要另外准备与服务端版本、PVF 配套的客户端。不要用 `DNFLogin.exe` 替换 `DNF.exe`。

在游戏根目录创建 UTF-8 的 `login.ini`，将地址替换成真实服务器地址：

```ini
[Login]
BaseUrl=http://REPLACE_WITH_PUBLIC_IPV4:18080
WindowTitle=我的DNF
GameVersion=1.0.0

[Credentials]
RememberPassword=False
```

`BaseUrl` 不加 `/api/v1`。`GameVersion` 对应实际采用的资源基线，不能随意标成最新版；配置缺失或错误可能回退到作者域名。

在 Windows 检查客户端 PVF：

```powershell
Get-FileHash "D:\你的客户端目录\Script.pvf" -Algorithm SHA256
```

在 Linux 检查服务端 PVF：

```bash
sha256sum /opt/dof/deploy/local-images/runtime/game/data/Script.pvf
```

两边需要使用配套资源，这里的 PVF 内容应一致。服务端能启动不代表任意客户端都能登录；客户端还需要完整的 EXE、DLL、ImagePacks2 等文件。

## 14. 测试注册、登录和进游戏

运行 `DNFLogin.exe`：

1. 注册一个新的普通测试账号，不使用后台管理员进游戏。
2. 推荐人填写 `admin`，或留空使用当前默认推荐人。
3. 当前验证码有大小写问题，字母先按小写输入。
4. 注册成功后登录。
5. 依次测试创建角色、进入频道、进入副本、退出重登。
6. 再用第二台测试电脑验证连接和组队。

登录器会从后台获取配置并写入 `DNF.toml`，服务器地址应在后台配置好，不能只改本地 TOML。API 返回凭据不代表游戏端已经接受；失败时检查游戏日志、关联账号表、密钥配对、PVF、IP 和 TCP/UDP 放行情况。

## 15. 配置完整客户端下载与自动更新

先完成正常进游戏测试，再启用下载服务：

```bash
cd /opt/dof/deploy/local-images
mkdir -p packages
docker compose --profile download up -d files
```

开放 TCP `18081`。将配套客户端打成真正的 ZIP，根目录直接放游戏文件：

```text
client-1.0.0.zip
├─ DNF.exe
├─ Script.pvf
├─ ImagePacks2/
└─ 其他游戏文件
```

不要额外套一层“客户端”目录，不要把 7z 改后缀当 ZIP，也不要包含账号密码、私钥或玩家保存的登录信息。本轮不通过这个包替换正在运行的登录器自身。

上传到：

```text
/opt/dof/deploy/local-images/packages/client-1.0.0.zip
```

确保文件服务可读：公开下载目录通常为 755、ZIP 文件为 644，不要递归放宽 `runtime` 私钥目录的权限。

在后台完整包配置中填写：

```text
版本：1.0.0
地址：http://服务器公网IP:18081/client-1.0.0.zip
```

先确认链接能下载，再用一个只放登录器发行文件及正确 `login.ini` 的空目录测试下载、解压和登录。现有更新器可能仅因发现 `Script.pvf` 就跳过完整包检查，所以要人工确认客户端文件齐全。

测试补丁时，先制作一个仅含少量资源或测试文本的小 ZIP `patch-1.0.1.zip`，放到同一个 `packages` 目录，在后台添加并启用 `1.0.1`：

```text
http://服务器公网IP:18081/patch-1.0.1.zip
```

重启登录器，检查下载、文件落盘和 `GameVersion` 更新。首次不要直接用大型 PVF 或 DNF.exe 验证更新器。

当前更新器的版本排序、完整性校验、失败恢复及登录器自更新仍有待完善。更新接口可用不代表整个下载更新流程已经验收。

## 16. 日常操作与自动启动

Compose 命令统一在部署目录执行：

```bash
cd /opt/dof/deploy/local-images
```

查看状态和日志：

```bash
docker compose ps -a
docker compose logs --tail=100 game admin
```

停止游戏和后台：

```bash
docker compose stop game admin
```

重新启动：

```bash
docker compose up -d game admin
```

使用下载服务时：

```bash
docker compose --profile download up -d files
```

修改 `.env` 后执行 `up -d` 让相关容器重新创建，普通 `restart` 不会重新读取 Compose 环境配置。数据库密码和密钥变更还需要同步对应组件，不能只改 `.env`。

后台当前默认 `restart: "no"`，便于保留首次初始化错误。部署成功后，如果需要随服务器重启恢复运行，把 `compose.yaml` 中 **admin 的这一项**改成：

```yaml
restart: unless-stopped
```

再执行：

```bash
docker compose up -d admin
```

运行配置、日志和密钥在 `deploy/local-images/runtime/` 中；数据库由宿主机 MySQL 独立管理，不在这些容器卷中。备份运行目录不能代替数据库备份。不要通过清空运行目录、删除初始化标记或删库来处理普通启动问题。

## 验收范围与相关文档

已验证镜像构建、MySQL 5.6 初始化、两个频道“五国”及短时进程/端口稳定、后台页面和 API、管理员初始化与重启保留数据。真实 Windows 客户端注册、进游戏及完整下载更新仍需在目标环境按第 14、15 步验收。

- [自建镜像说明及已有服务迁移注意事项](../deploy/local-images/README.md)
- [当前 Compose 文件](../deploy/local-images/compose.yaml)
- [环境配置模板](../deploy/local-images/.env.example)
- [管理员初始化 SQL 示例](../deploy/local-images/bootstrap-admin.sql.example)
- [验证记录](validation.md)

`deploy/external-mysql`、`deploy/test` 和旧部署指南保留了早期官方镜像方案；本流程使用 `deploy/local-images`，不要混用旧补丁挂载或内置 MySQL 命令。
