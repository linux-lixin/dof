# 1995chen + onlyGuo：自建 MySQL 拆分部署

> 2026-10-15 修订：实际联调 MySQL 5.6.50；镜像与源码不同。现使用 fixes/ 覆盖脚本修复已确认问题，详见 [修复说明](deployment-fixes-2026-10-15.md)。CLI 的 --skip-ssl 仅用于本方案无 TLS 的旧 MySQL。

日期：2026-10-15。用于已有 Linux／云服务器，公网直连，不用隧道，先不修改业务代码。

**当前实际部署：专用 MySQL 5.6.50。** 已完成游戏/后台启动与接口检查，尚未完成玩家进服和完整功能验收；5.0.95 是上游原始构建版本。数据库可在同机独立容器/虚拟机，也可在另一台可达内网主机，由你单独管理。

本文覆盖数据库拆分相关步骤。完整的密钥、客户端、注册和更新步骤参照附件中的 `docs/deployment-guide.md` 指定章节。**数据库地址、初始化和备份以本文为准，不要执行旧文档的内置 MySQL 操作。**

## 1. 版本为什么这样选

| 版本 | 本次判断 |
|---|---|
| **MySQL 5.0.95** | 游戏与独立 DB 构建明确安装此版本，本次匹配基线 |
| MySQL 5.6 | 5.6.50 已在现有服务器完成导入和游戏/后台启动；本地修复 SQL 用 5.6.51 隔离验证，进服仍待测 |
| MySQL 5.5 / 5.7 | 尚未完成该版本联调 |
| MySQL 8.0 / 8.4 | 原有 GRANT ... IDENTIFIED BY 等语句需要适配，不符合本轮不改代码的路线 |
| MariaDB | 不能等同于原版 MySQL；需要单独验证 |

依据：[独立数据库 Dockerfile_7](https://github.com/1995chen/dnf/blob/08f724c25b12748f8eb4bf11b24a90accfc3b223/build/Standalone-DNF-DB/Dockerfile_7)、[游戏 Dockerfile](https://github.com/1995chen/dnf/blob/08f724c25b12748f8eb4bf11b24a90accfc3b223/build/Centos7-DNF/Dockerfile)。新语法参见 [MySQL 8 GRANT 文档](https://dev.mysql.com/doc/refman/8.0/en/grant.html)。

建议旧版 MySQL 放在专用容器或虚拟机，不要把旧 RPM 直接装入现有现代宿主系统。本文不假设存在可直接拉取的 `mysql:5.0.95` 标签，也不替你安装数据库。

源码 `build/Standalone-DNF-DB/Dockerfile_7` 可作构建参考，但其入口会在每次启动时删除 mysql.user 中的全部账号，再创建 root@'%'。**不要让它操作已有共享数据库。** 若直接采用该入口，重启数据库后需要核对 root 来源权限，并重新运行游戏初始化恢复 game 账号。自行部署时应管理好账号的正常持久化。

## 2. 拆分后的关系

~~~mermaid
flowchart LR
  P["Windows 玩家"] -->|"API 18080"| A["onlyGuo 后台"]
  P -->|"游戏 TCP / UDP"| G["1995chen 游戏"]
  P -.->|"可选下载 18081"| F["文件服务"]
  A -->|"内网 DB_HOST:DB_PORT"| D["自建专用 MySQL（当前 5.6.50）"]
  G -->|"主库 + 大区库，同一实例"| D
~~~

Compose 只有 game、admin、可选 files，**没有 mysql 服务**，也不挂载 /var/lib/mysql。游戏镜像内仍有数据库程序，但外部模式跳过本地数据库启动。

这里只拆部署位置：d_taiwan、taiwan_cain 系列、taiwan_login、taiwan_billing、dnf_service 等仍在同一 MySQL 实例。onlyGuo 使用单数据源跨库访问，不能只把 dnf_service 单独放到另一台数据库。

模板已设置：

| 用途 | 配置 |
|---|---|
| 游戏主库 | MAIN_MYSQL_HOST / MAIN_MYSQL_PORT → DB_HOST / DB_PORT |
| 游戏大区库 | MYSQL_HOST / MYSQL_PORT → 同一 DB_HOST / DB_PORT |
| 两组初始化密码 | MAIN_MYSQL_ROOT_PASSWORD、DNF_DB_ROOT_PASSWORD → DB_ROOT_PASSWORD |
| onlyGuo 数据源 | jdbc:mysql://DB_HOST:DB_PORT/dnf_service |
| 大区和库名 | SERVER_GROUP=3，SERVER_GROUP_DB=cain |
| 游戏数据库用户密码 | GAME_DB_PASSWORD，恰好 8 位字母数字 |

两组游戏地址必须同时填写，不能只改 MYSQL_HOST。db_connect 表内的 127.0.0.1:3306/3307 指向游戏容器内代理，属于现有设计，不应批量改为外部数据库地址。

## 3. 先准备自建数据库

数据库本地管理终端检查：

~~~sql
SELECT VERSION();
SHOW VARIABLES LIKE 'port';
SHOW VARIABLES LIKE 'sql_mode';
SHOW ENGINES;
SHOW DATABASES;
~~~

确认 MyISAM/InnoDB 所需引擎可用。保留与原环境相容的 SQL 模式；导入有错误时先定位语句，不反复删库重试。

**首次使用没有 DNF 库的新专用实例，不要提前建立空的 d_taiwan、taiwan_cain 等库。** 原脚本常用“数据库存在”判断已初始化，空库可能导致跳过导入。

### 地址和端口

作者 `build/dnf_data/etc/my.cnf` 的 mysqld 默认端口是 **4000**；client 段为 3306，不代表服务端也是 3306。本模板 DB_PORT 默认 4000。你自行配置为 3306 就填 3306；若发布“主机内网 3306 → 数据库容器 4000”，应用连接主机侧 3306。

| 数据库位置 | DB_HOST | 数据库通常看到的来源 |
|---|---|---|
| 另一台内网主机 | 数据库内网 IPv4 | 应用宿主机内网 IP，以实际 NAT 为准 |
| 同机宿主机 MySQL | 容器可达的宿主机内网 IPv4 或桥接网关地址 | 可能是 Compose 容器网段 |
| 同机另一数据库容器 | 私网发布地址，或双方已共享网络中的地址 | 取决于网络和 NAT |

DB_HOST 不能填 127.0.0.1：那是应用容器自身。MySQL 需监听应用可达接口，不能只监听 localhost。不同 Compose 项目的服务名也不自动互通。使用 IPv4，避免旧脚本的 IPv6 限制。

### 账号和来源授权

游戏初始化脚本写死使用 root，并且会创建多个库、修改 mysql.user、给 game 授予全实例权限。因此专用实例不要混放其他业务。当前测试模板的后台也使用该实例 root。

在数据库本地管理终端，为实际应用来源授权；以下是 **MySQL 5.0 语法模板**，两个占位符必须替换，不能原样执行：

~~~sql
GRANT ALL PRIVILEGES ON *.* TO 'root'@'REPLACE_WITH_APP_SOURCE'
IDENTIFIED BY 'REPLACE_WITH_DB_ROOT_PASSWORD' WITH GRANT OPTION;
~~~

异机通常填应用宿主机内网 IP。同机可限定到确认过的 Compose 子网，例如 `172.30.95.0/255.255.255.0` 是格式示例，不能照抄地址。需同时核对已有 root@'%' 等宽泛授权。

准备 Compose 后可用 `sudo docker compose create game admin` 只创建容器，再用 `sudo docker network inspect dnf-external-mysql_default` 查看网络。默认网络删除重建后可能换网段；需同步核对授权。实际连接经过 NAT 时不能直接拿容器 IP 当数据库看到的来源。

数据库端口只允许应用来源，不向玩家开放。同机容器流量还受宿主机防火墙影响。公网玩家端口及安全组按旧指南第 4 节设置，来源限定测试者 IP；数据库例外是允许应用内网来源访问你实际配置的端口。

GAME_DB_ALLOW_IP 默认为空，使用作者脚本自动探测。启动后必须核对实际 game@host；探测错误再填数据库看到的游戏来源。不要把数据库目标 DB_HOST 当成允许来源，也不要默认填写 %。

## 4. 上传并填写模板

本地附件：`D:\Projects\dof\deploy\external-mysql`。

Windows PowerShell（替换用户和 IP）：

~~~powershell
ssh serveruser@203.0.113.10 "mkdir -p ~/dnf-deploy"
scp -r "D:\Projects\dof\deploy\external-mysql" serveruser@203.0.113.10:~/dnf-deploy/
~~~

Linux，仅用于全新目录：

~~~bash
sudo mkdir -p /opt/dnf-external-mysql
sudo cp ~/dnf-deploy/external-mysql/compose.yaml /opt/dnf-external-mysql/
sudo cp -r ~/dnf-deploy/external-mysql/fixes /opt/dnf-external-mysql/
sudo cp ~/dnf-deploy/external-mysql/.env.example /opt/dnf-external-mysql/.env
sudo cp ~/dnf-deploy/external-mysql/bootstrap-admin.sql.example /opt/dnf-external-mysql/
cd /opt/dnf-external-mysql
sudo mkdir -p runtime/game/data runtime/game/log runtime/admin/data packages
sudo chmod 700 runtime/admin/data
sudo chmod 600 .env
sudo nano .env
sudo docker compose config --quiet
~~~

填写 PUBLIC_IP、DB_HOST、DB_PORT、DB_ROOT_PASSWORD、GAME_DB_PASSWORD、SUPERVISOR_PASSWORD、GATE_PASSWORD。所有示例 IP、CHANGE_ME 值都要替换。数据库密码必须与已部署的专用 MySQL 一致；不要以为修改 .env 会自动改 root 密码。

密码用独立随机字母数字，避免旧脚本的 SQL/shell 插值问题。GAME_DB_PASSWORD 用 `openssl rand -hex 4` 生成 8 位，其他密码可用 `openssl rand -hex 16`。首次保留 GAME_IMAGE、ADMIN_IMAGE 固定值；其 manifest 在 2026-10-14 查询过，但未验证镜像与源码完全等同。

## 5. 密钥、PVF 和只读预检

先按旧指南第 6 节准备成对 RSA 密钥、配套 PVF、拉取游戏/后台镜像并检查入口。**把该节所有 /opt/dnf-test 替换为 /opt/dnf-external-mysql。** 已有密钥不能覆盖；私钥不进玩家包。

在应用目录，用游戏镜像的旧版客户端验证数据库，不执行游戏入口：

~~~bash
sudo docker compose run --rm --no-deps --entrypoint sh game -c 'exec mysql --connect_timeout=5 -h "$MAIN_MYSQL_HOST" -P "$MAIN_MYSQL_PORT" -uroot -p -e "SELECT VERSION(), USER(), CURRENT_USER();"'
~~~

交互输入数据库密码。临时容器与正式容器同网段、IP 可能不同；这是网络/网段授权预检，正式服务启动后还需核对。

后台镜像也要独立验证，替换地址、端口：

~~~bash
sudo docker compose run --rm --no-deps --entrypoint sh admin -c 'exec mysql --skip-ssl --connect_timeout=5 -h REPLACE_WITH_DB_HOST -P REPLACE_WITH_DB_PORT -uroot -p -e "SELECT VERSION(), USER(), CURRENT_USER();"'
~~~

任一连接失败，先定位监听、端口、防火墙、授权或客户端认证兼容性，不继续执行自动初始化。

## 6. 先游戏，再后台

~~~bash
sudo docker compose up -d game
sudo docker compose ps
sudo docker compose logs --tail=100 game
sudo docker compose exec game supervisorctl status
~~~

首次会在外部 MySQL 创建并导入游戏库、配置 game 账号。healthcheck 查询外部实例中的账号表和 cain 关联表；healthy 不代表已能进副本。

**本版所有交互数据库操作统一用这个命令**，替代旧指南的无主机参数 mysql 命令：

~~~bash
sudo docker compose exec game sh -c 'exec mysql -h "$MAIN_MYSQL_HOST" -P "$MAIN_MYSQL_PORT" -uroot -p'
~~~

在 SQL 中检查：

~~~sql
SELECT VERSION(), USER(), CURRENT_USER();
SHOW DATABASES;
SELECT COUNT(*) FROM d_taiwan.accounts;
SELECT COUNT(*) FROM taiwan_cain_2nd.member_avatar_coin;
SELECT COUNT(*) FROM taiwan_login.member_login;
SELECT COUNT(*) FROM taiwan_billing.cash_cera;
SELECT User,Host FROM mysql.user WHERE User='game';
EXIT;
~~~

确认库和 game 来源正确，再启动后台：

~~~bash
sudo docker compose up -d admin
sudo docker compose logs --tail=160 admin
sudo docker compose exec admin test -f /app/data/.db_initialized
curl --fail http://127.0.0.1:18080/api/v1/client/version/1.0.0
~~~

核对 dnf_service 表、accounts 新增列、初始化标记与 API，参照旧指南第 8 节。后台失败时停止 admin；不要删除 .db_initialized 或重复导入带 DROP/ADD 列的 init.sql。

之后按旧指南：

1. 第 9 节：用本文的外部数据库连接命令创建测试管理员 admin、替换临时授权密码。附件 SQL 要编辑并分步执行。
2. 第 10–12 节：配置后台游戏公网 IP、编译登录器、准备 login.ini、注册普通账号并验证角色/频道/副本。
3. 第 14 节：首次进游戏成功后才测试完整包下载与单个小补丁；目录改为 /opt/dnf-external-mysql。
4. 现有更新器的版本排序、校验、失败恢复、自更新限制仍未修复，不能承诺完整生产级自动更新。

## 7. 常见问题

| 现象 | 检查 |
|---|---|
| Connection refused / timeout | DB_HOST 是否从容器可达，实际端口是否 4000，监听和防火墙 |
| Access denied for root | 数据库看到的来源与 root@host、密码是否匹配 |
| Access denied for game | GAME_DB_ALLOW_IP 探测结果、game@host 与 8 位密码 |
| game unhealthy，但数据库能连接 | 空库跳过导入、缺表、SQL 模式或导入错误 |
| 后台启动后网页有了，但注册失败 | init.sql 失败、游戏关联库不全、默认推荐人不存在 |
| 数据库重启后 game 登录失败 | 是否使用作者每次清空账号的独立 DB 入口 |
| db_connect 是 127.0.0.1 | 游戏内部代理设计；先检查代理进程和目标配置 |
| 修改 .env 不生效 | 需 up -d 重建容器；restart 不重新加载 Compose 配置 |

## 8. 停止与独立备份

停止应用：

~~~bash
cd /opt/dnf-external-mysql
sudo docker compose --profile download stop
~~~

保存应用文件：

~~~bash
sudo tar -czf "/opt/dnf-app-backup-$(date +%Y%m%d-%H%M%S).tgz" .env compose.yaml runtime
~~~

**这不包含数据库。** 保持应用停止，在数据库所在机器使用与 MySQL 5.0 相容的 mysqldump 单独备份专用实例（按实际端口替换 4000）：

~~~bash
umask 077
mysqldump -h 127.0.0.1 -P 4000 -uroot -p --all-databases --lock-all-tables --routines > "dnf-db-$(date +%Y%m%d-%H%M%S).sql"
~~~

检查退出状态和输出文件，失败导出不能当备份。游戏含 MyISAM 表，不能只用 --single-transaction 保证一致性。全库备份含 mysql 系统库与账号权限，只用于同版本专用实例的受控恢复，不能覆盖共享实例或直接导入新版。

数据库备份和同一时点应用备份配对保存，均含敏感信息，不能放入 packages。隔离恢复时先恢复数据库和权限，再恢复对应密钥、PVF、配置及初始化标记，最后启动应用验证。

重新启动：

~~~bash
sudo docker compose up -d game
sudo docker compose up -d admin
~~~

需要下载再执行 `sudo docker compose --profile download up -d files`。Compose 不管理外部 MySQL 的启动、停止与重启。

## 9. 本次验证范围

已依据固定源码核查环境变量、MySQL 版本、权限脚本、端口和后台数据源。模板已通过 Compose 解析及结构检查：没有 MySQL 服务或本地数据库挂载，主库、大区库、后台均指向外部实例，健康检查也查询外部实例。现已在真实 MySQL 5.6.50 上完成导入、游戏启动及后台初始化/API 检查。已修改本地初始化脚本与部署覆盖文件，Java/C# 业务逻辑未改；注册、进游戏和自动更新仍待实测。

上线前的功能验收仍是：数据库直连 → 游戏库导入 → 后台初始化 → 注册 → 登录 → 角色与副本 → 第二台电脑/组队 → 下载与小补丁。

