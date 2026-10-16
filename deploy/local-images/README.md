# 本地构建镜像包（2026-10-15）

这套镜像从 `dnf-game` 和 `dnf-server-public` 当前工作区构建，包含本地修复。它不是旧的 `centos7-2.1.9.fix1` 官方镜像改标签；当前游戏源码的 Supervisor 分组、启动脚本和 P2P 配置与旧镜像有区别。

全新服务器直接拉取 Git、在服务器构建镜像，请按[完整部署步骤](../../docs/fresh-server-deployment.md)操作。下面的 tar 加载方式仅适用于已有镜像包的情况。

## 文件与加载

把 `dist` 中两个 tar 文件传到 Linux 服务器，执行：

```bash
docker load -i dnf-game-local-fix-20261015.tar
docker load -i dnf-admin-local-fix-20261015.tar
```

镜像标签分别是 `dnf-game:local-fix-20261015`、`dnf-admin:local-fix-20261015`。`SHA256SUMS` 校验下载完整性；`image-test-report.json` 记录本次测试镜像 ID 和检查结果。只加载 tar 不会改变正在运行的容器。

## 首次部署（外置、自建 MySQL）

使用本目录的 `compose.yaml`，不要混用旧部署目录里的 `fixes` 挂载。修复脚本已经在镜像内。数据库仍由你独立部署；镜像不包含你的云服务器地址、数据库密码、管理员密码或生产 RSA 密钥。

1. 将本目录复制到新的服务器目录，执行 `cp .env.example .env`，填写公网 IP、可从容器访问的数据库地址、端口和各项密码。游戏数据库密码正好 8 个字母或数字。MySQL 5.6 使用 `MYSQL_INIT_SSL_MODE=disabled`；JDBC 的 `useSSL=false` 已在 Compose 内独立配置。
2. 给数据库账号配置容器网段访问权限。使用专用游戏数据库实例。首次启动会建立整套游戏库，不能把任意已有业务数据库当空库初始化。
3. 执行 `docker compose up -d game`，查看 `docker compose logs --tail=100 game`。数据库健康检查通过只代表库可查询，还需检查频道进程及游戏日志。
4. 执行 `docker compose up -d admin`，查看 `docker compose logs --tail=100 admin`。首次成功初始化后，`runtime/admin/data/.db_initialized` 会生成。网页默认端口为 18080。
5. 在数据库里先检查账号 `admin` 是否已存在，再按照 `bootstrap-admin.sql.example` 的注释填写新密码并执行。它是独立的管理员初始化步骤，不会把固定管理员密码烘焙进镜像，也不要在已有账号上整份重复执行。
6. 首次使用 onlyGuo 登录认证时，保证后台与游戏公钥匹配：

```bash
cp runtime/admin/data/publickey.pem runtime/game/data/publickey.pem
docker compose restart game
```

后台私钥为 `runtime/admin/data/private.key`，应与该公钥成对保留。以上复制用于全新部署；已有服务应沿用已经配对的密钥。

后台启动和更新接口可用，并不意味着已发布客户端更新包。登录器服务器地址、推荐人/注册设置、版本记录和下载地址仍需要配置。未进行真实 Windows 客户端进游戏及自动更新下载的端到端验收。

## 镜像带上的修复

- 游戏首次导入前修复原始 `taiwan_login.log_query_ref` 的已知编号溢出种子，保留 394 条原记录。
- 游戏定时任务自动建立本月和下月 `log_response_time_YYYYMM` 表。
- 镜像包含 `repair_existing_log_ref.sh`，用于符合条件的旧库修复；它不会自动改动已有数据库，必须先停频道并按脚本要求操作。
- 后台初始化支持独立的命令行客户端 SSL 参数；SQL 失败立即退出，成功后才写标记；防止缺失标记时重放破坏性 SQL；检查 RSA 密钥是否完整。
- 本次构建还修复后台 Dockerfile 引用不存在的 `libs` 目录、游戏 Windows CRLF 换行和过期 CentOS HTTP 软件源问题。

## 已有服务切换

不要直接删除运行目录、数据库或初始化标记。旧游戏卷里的 `/data/run/*.sh` 会被保留，可能继续执行旧版本脚本；把镜像换成新标签并不能保证这些持久化脚本同步更新。应单独安排现有数据迁移、密钥保留和脚本差异核对。本次打包测试使用全新临时数据卷，不会改动云服务器正在运行的环境。

## 重新构建与测试

游戏构建所需资源已随 Git 仓库提供，无需额外下载脚本。在仓库根目录直接执行：

```bash
docker build --platform linux/amd64 -f dnf-game/build/Centos7-DNF/Dockerfile -t dnf-game:local-fix-20261015 dnf-game
docker build --platform linux/amd64 -t dnf-admin:local-fix-20261015 dnf-server-public
python tests/test_built_images.py
# Optional independent process/port observation before cleanup:
python tests/verify_game_ready.py
python tests/test_built_images.py --cleanup
```

测试仅创建名称以 `dnf-image-test-` 开头的临时资源，数据库和后台均不发布主机端口，HTTP 检查在隔离网络内部进行。失败时保留本次资源以便排查；清理命令仅清理 `dist/image-test-state.json` 记录的资源。该状态文件包含临时测试密码，不属于交付包。
