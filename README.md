# DOF 部署集成与修复

集成 1995chen 游戏部署、onlyGuo 后台和 Windows 登录器，保留本地已验证的数据库与初始化修复。主流程是 **Linux 服务器 + 自建外部 MySQL 5.6 + 两个 Docker 镜像**，公网直连，不使用隧道。

## 当前完成情况

- 游戏首次导入时修复 `log_query_ref` 原始种子的编号溢出；包含有条件的旧库修复脚本。
- 定时建立本月、下月的响应日志表，支持跨年。
- 后台初始化适配旧数据库的命令行 SSL 参数；失败立即退出，成功才写初始化标记；已有库缺标记时拒绝重放 SQL；检查 RSA 密钥对是否完整。
- 修复 Windows CRLF、CentOS 7 归档软件源，以及后台 Dockerfile 引用不存在的 `libs` 目录导致的构建失败。
- 两镜像已完成本地 MySQL 5.6.51 隔离启动测试：两个频道出五国，真实进程和监听端口连续稳定 5 分钟；后台页面、更新查询接口、管理员初始化和重启保留数据均已验证。

**尚未完成真实客户端注册、登录、进游戏及自动更新下载的端到端验收。** Java/C# 业务逻辑尚未进行安全与发行功能改造，不能把“容器启动成功”等同于“已适合公开运营”。

## 获取源码和构建

```bash
git clone https://github.com/linux-lixin/dof.git
cd dof

docker build -f dnf-game/build/Centos7-DNF/Dockerfile -t dnf-game:local-fix-20261015 dnf-game
docker build -t dnf-admin:local-fix-20261015 dnf-server-public
```

构建需要 Docker 和到基础镜像、软件包依赖源的网络连接，不需要先运行 Python 下载脚本。Python 3.9+ 仅用于运行仓库测试。构建还会从基础镜像仓库、CentOS 归档、Maven/npm 等源获取依赖；`source-lock.json` 固定的是集成源码基线，不表示整个依赖链已完全可重现。

游戏构建所需的 400 个运行资源已直接纳入 Git，包括 PVF、原始 SQL 压缩包、游戏程序、库和旧配置。普通 `git clone` 后即可构建，无需 Git LFS 或额外资源下载步骤；仓库会比纯源码版本大约增加 410 MiB 未压缩文件。`scripts/game-assets.lock.json` 保留上游固定 commit、路径、大小、SHA256 和可执行权限记录，便于审计。仓库中的模板密钥是上游公开示例，不能当作生产私密凭据；实际部署应使用自己的密钥，并保持后台私钥与游戏公钥配对。

## 部署

全新服务器从这里开始：[完整部署步骤：Git 拉取、服务器构建、自建 MySQL、登录器与更新](docs/fresh-server-deployment.md)。

可选 Ubuntu 24.04 版使用独立的 [Ubuntu 构建和四角色部署说明](deploy/ubuntu/README.md)，
仅连接外部 MySQL，不包含 NetBird/Tailscale，已移除旧统一登录器网关 `tongyi_gate`，使用 onlyGuo 后台登录流程。
Ubuntu ALL/GAME 启动前必须自行放入
`deploy/ubuntu/runtime/game/data/Script.pvf`，不再自动使用内置 PVF。原 CentOS 入口仍是默认；
兼容性与实测边界见 [Ubuntu 依赖审计](docs/ubuntu-compatibility.md) 和 [Ubuntu 验收结果](docs/ubuntu-validation.md)。


使用 [自建镜像部署说明](deploy/local-images/README.md) 和 `deploy/local-images/compose.yaml`。将 `.env.example` 复制为 `.env` 后填写地址和密码，先启动 game，确认数据库及频道启动，再启动 admin。

数据库由用户独立部署；MySQL 5.6.50 曾在服务器验证，5.6.51 用于本地隔离测试。管理员账号 `admin` 按 `bootstrap-admin.sql.example` 注释单独初始化，密码自行设置。当前后台的默认推荐人也为 `admin`；已有 `123123` 的改名步骤见 Ubuntu 部署文档，更新代码不会自动改动已有账号。后台 SSL 初始化选项为 `MYSQL_INIT_SSL_MODE=disabled`，与 JDBC 的 `useSSL=false` 分开配置。

旧官方镜像的补丁挂载方案保留在 `deploy/external-mysql`、`deploy/test`，供已有部署参考。**自建镜像流程不要混用旧补丁挂载。** 已有数据卷里的启动脚本和配对密钥需核对后迁移，不能直接把新镜像当旧镜像的无差别替换。

## 验证

```bash
python tests/test_deployment_fixes.py
python tests/test_mysql56_fixes.py
python tests/test_built_images.py
python tests/test_built_images.py --cleanup
```

第一项需要 Bash（Windows 使用 Git for Windows）；后两项需要 Docker。完整镜像测试会新建临时 MySQL、游戏和后台容器，不连接已有服务器，不发布主机端口。失败时保留本次资源便于检查，完成后执行清理命令。测试输出写入被 Git 忽略的 `dist/`。

## 目录与发布范围

| 目录 | 内容 |
|---|---|
| `dnf-game` | 默认 CentOS 7、可选 Ubuntu 24.04 Dockerfile，共享模板与独立平台适配层 |
| `dnf-server-public` | 后台 Java/Vue 源码及修复后的镜像入口 |
| `DNFLogin` | 上游 Windows 登录器源码，尚未修改业务逻辑 |
| `deploy` | 自建镜像主流程与旧镜像兼容部署附件 |
| `docs` | 部署指南、兼容性分析、修复记录和验证摘要 |
| `tests` | 可重复的初始化、数据库及镜像运行验证 |
| `scripts` | 已纳入仓库的运行资源来源、校验和权限清单 |

不提交镜像 tar、构建输出、运行目录、实际 `.env`、生产密钥、数据库数据、原始运行日志、临时测试凭据、私人运维记录、原项目备用插件及等级/登录器补丁集合。

## 上游来源

- [1995chen/dnf](https://github.com/1995chen/dnf)：游戏部署部分，保留其 [LICENSE](dnf-game/LICENSE)。
- [onlyGuo/dnf-server-public](https://github.com/onlyGuo/dnf-server-public)：后台。
- [onlyGuo/DNFLogin](https://github.com/onlyGuo/DNFLogin)：登录器。

准确基线见 [source-lock.json](source-lock.json)。保留原作者署名及已有许可文件，不为未提供许可证的上游组件添加新的授权声明。
