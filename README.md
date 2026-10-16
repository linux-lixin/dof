# DOF · Ubuntu 部署

集成 1995chen 游戏资源、onlyGuo 后台和 Windows 登录器。游戏镜像只维护 **Ubuntu 24.04 / x86_64**，数据库使用你自建的 MySQL（隔离验收基线 5.6.51），公网或内网直连。

| 场景 | 入口 |
|---|---|
| 一台服务器运行游戏和后台 | [完整部署步骤](deploy/ubuntu/all/README.md) |
| CORE、GAME、P2P 分主机 | [拆分部署](deploy/ubuntu/split/README.md) |
| 后台单独部署 | [独立后台](deploy/ubuntu/split/admin/README.md) |
| 登录器、客户端和更新包 | [客户端配置](docs/launcher/deployment.md) |

默认按全新服务器、全新运行目录和专用数据库部署，管理员账号统一为 `admin`，密码在初始化时自行设置。

## 拉取和构建

```bash
git clone https://github.com/linux-lixin/dof.git /opt/dof
cd /opt/dof
docker build -f services/game/docker/ubuntu/Dockerfile -t dnf-game:ubuntu24.04 services/game
docker build -f services/admin/docker/Dockerfile -t dnf-admin:latest services/admin
```

镜像命名统一为 `dnf-game:ubuntu24.04` 和 `dnf-admin:latest`：前者标识游戏基础系统，后者表示本次源码构建的后台镜像。部署使用本地镜像，不会自动拉取同名远端镜像。

Git 已包含游戏资源和必要兼容源码，无需额外下载脚本或 Git LFS。构建仍需连接镜像仓库、APT、Maven/npm 软件源。
接着按完整部署文档配置 `.env`、手动放置 `Script.pvf`、检查数据库连接，再启动游戏和后台。仓库里的 `services/game/assets/home/template/init/Script.tgz` 可手动解压用于配套测试，不会在启动时自动覆盖你的 PVF。

启动完成后 `docker compose logs game` 会打印 `[启动完成] 游戏服务已全部就绪`。看到容器 Up 不等于游戏频道已经就绪。

## 项目结构

| 目录 | 内容 |
|---|---|
| `services/game` | Ubuntu 镜像、游戏资源和启动源码 |
| `services/admin` | Java 后端、Vue 前端及后台镜像 |
| `clients/launcher` | Windows WPF 登录器 |
| `deploy/ubuntu` | 构建、整体及拆分部署入口 |
| `deploy/shared` | 公共后台定义和管理员 SQL 示例 |
| `docs` | 使用、维护、兼容性和验收说明 |
| `tests`、`scripts` | 回归测试、诊断和发布工具 |
| `metadata` | 上游提交及保留资源的 SHA256 清单 |

详见 [项目结构](docs/architecture.md)、[文档索引](docs/README.md)、[开发说明](CONTRIBUTING.md) 和 [测试入口](tests/README.md)。

## 当前边界

- 已删除 CentOS 构建/部署入口、内置数据库初始化、NetBird/Tailscale、旧统一登录器网关及其专用依赖；不会申请 TUN、NET_ADMIN 或 privileged。
- Relay/STUN 是游戏联机服务，仍保留；保留公网/内网直连、显式地址、自动公网 IP 探测与 DDNS。
- Docker 管理容器，Supervisor 管理容器内旧游戏进程；游戏和后台分别使用一个镜像，拆分节点复用游戏镜像。
- MySQL 由用户独立管理。默认后台管理员名为 `admin`，密码自行设置；私钥和公钥必须配对，私钥不能发给玩家。
- 真实 Windows 客户端注册、进图、组队和自动更新仍需独立验收。当前测试范围见 [验收记录](docs/ubuntu/validation.md)。

源码不包含完整 Windows 游戏客户端。实际 `.env`、运行目录、私钥、数据库数据、镜像 tar 和测试凭据均不提交。

## 来源

- [1995chen/dnf](https://github.com/1995chen/dnf)：游戏部署与资源，保留 [LICENSE](services/game/LICENSE)。
- [onlyGuo/dnf-server-public](https://github.com/onlyGuo/dnf-server-public)：后台。
- [onlyGuo/DNFLogin](https://github.com/onlyGuo/DNFLogin)：登录器。

来源基线见 [metadata/source-lock.json](metadata/source-lock.json)，保留资源见 [metadata/game-assets.lock.json](metadata/game-assets.lock.json)。历史审计只是当时的证据，不是已删除功能的部署入口；不为上游未授权的资源添加新的授权声明。
