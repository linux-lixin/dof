# 旧目录迁移到按系统分类的目录

## 本轮完整项目重组

部署目录仍沿用 `deploy/centos`、`deploy/ubuntu`，本轮源码从 `dnf-game` 移到 `services/game`，
`dnf-server-public` 移到 `services/admin`，`DNFLogin` 移到 `clients/launcher`。
游戏构建文件为 `services/game/docker/<系统>/Dockerfile`，后台为 `services/admin/docker/Dockerfile`。
后端、前端分别在 `services/admin/backend`、`services/admin/frontend`；资源清单迁至 `metadata`，测试按用途分组。
完整结构见 [项目说明](../docs/architecture.md)。

已完成上一轮部署目录迁移的服务器，本轮 `git pull --ff-only` 后继续在原 `deploy/...` 目录管理容器即可。
运行数据路径、镜像标签、容器内路径不变，单纯目录整理无需重建在运行的容器。
以后构建镜像使用更新后的 [Ubuntu](ubuntu/build/README.md) / [CentOS](centos/build/README.md) 命令；不要继续使用旧源码目录。
如果曾把实际文件放在旧源码目录（例如旧后台的 data 或本地客户端产物），Git 不会自动搬走它们；
按实际配置核对并迁移，不能把残留目录一律删除。

## 上一轮部署入口迁移

这是宿主机部署文件的目录调整，不是 CentOS 数据迁移到 Ubuntu。不要混用两种镜像的数据目录。
游戏镜像、后台镜像、协议和数据库内容未因本次整理发生变化，已有镜像无需为本次目录调整重新构建。
Git 不移动被忽略的 `.env`、`runtime/` 或下载包；直接进入新目录启动会得到一个空运行目录。

| 旧入口 | 新入口 | Compose 项目名 |
|---|---|---|
| `deploy/local-images` | `deploy/centos/all` | `dnf-local-images`（保留） |
| `deploy/ubuntu/compose.yaml` | `deploy/ubuntu/all/compose.yaml` | `dnf-ubuntu-all`（保留） |
| `deploy/ubuntu/compose.core.yaml` | `deploy/ubuntu/split/core/compose.yaml` | `dnf-ubuntu-core`（保留） |
| `deploy/ubuntu/compose.game.yaml` | `deploy/ubuntu/split/game/compose.yaml` | `dnf-ubuntu-game`（保留） |
| `deploy/ubuntu/compose.p2p.yaml` | `deploy/ubuntu/split/p2p/compose.yaml` | `dnf-ubuntu-p2p`（保留） |
| `deploy/external-mysql` | `deploy/centos/legacy/external-mysql` | `dnf-external-mysql`（保留） |
| `deploy/test` | `deploy/centos/legacy/bundled-mysql` | `dnf-test`（保留） |

## 已有 Ubuntu 整体部署：保留原运行目录

以下假设仓库为 `/opt/dof`，原文件位于 `deploy/ubuntu/.env`、`deploy/ubuntu/runtime/`。
如果此前用了其他路径或 `-p` 自定义项目名，以原容器实际配置为准并继续使用相同项目名。
先记录挂载，避免误建空数据栈：

```bash
docker ps --filter label=com.docker.compose.project=dnf-ubuntu-all
# 把下面的容器名替换为上一条输出中的真实名称：
docker inspect dnf-ubuntu-all-game-1 --format '{{json .Mounts}}'
```

拉取后把旧 `.env` 复制到新入口，并指定旧运行根目录；保留旧数据原位即可：

```bash
cd /opt/dof
git pull --ff-only
cp -n deploy/ubuntu/.env deploy/ubuntu/all/.env
chmod 600 deploy/ubuntu/all/.env
nano deploy/ubuntu/all/.env
```

在新 `.env` 中设置一条（已有该变量时修改原行，避免重复）：

```dotenv
RUNTIME_ROOT=/opt/dof/deploy/ubuntu/runtime
```

新配置仍挂载原来的 `runtime/game/data`、`runtime/game/log`、`runtime/admin/data`。
在新目录检查路径，输出只包含项目名、镜像和挂载，不显示环境密码：

```bash
cd /opt/dof/deploy/ubuntu/all
docker compose config --quiet
docker compose config --format json | python3 -c 'import json,sys; c=json.load(sys.stdin); print(c["name"]); [print(n,s.get("image"),s.get("volumes",[])) for n,s in c["services"].items()]'
docker compose up -d --force-recreate game
docker compose logs -f --tail 100 game
```

看到 `[启动完成]`，退出日志跟随后执行 `docker compose up -d --force-recreate admin`。
后台初始化标记、密钥、PVF 和游戏配置仍来自原目录；不要重放数据库或管理员初始化 SQL。
以后都在 `deploy/ubuntu/all` 操作。旧 runtime 路径继续由 `RUNTIME_ROOT` 引用，不能当废目录删除。

## 其他部署迁移

- **CentOS 自建整体部署**：复制 `deploy/local-images/.env` 到 `deploy/centos/all/.env`，设置
  `RUNTIME_ROOT=/opt/dof/deploy/local-images/runtime`。项目名仍为 `dnf-local-images`，核对原挂载后重建 game/admin。
  如果使用下载服务，把旧 `packages/` 复制到新部署目录的 `packages/`，再启动 files；数据库与密钥不重置。
- **Ubuntu GAME / P2P**：分别复制旧配置到新角色目录的 `.env`，设置 `RUNTIME_ROOT` 为原来的绝对 runtime 根目录。
  GAME 保持 `game/data`、`game/log`，P2P 保持 `p2p/data`。原项目名保留，用新目录的默认 Compose 操作。
- **Ubuntu CORE**：旧模板把 CORE 数据存在 `runtime/game/`，新模板为 `runtime/core/`。
  先停止旧 CORE 容器，将原 `runtime/game/` 完整复制到新 `split/core/runtime/core/`；
  同机后台的 `runtime/admin/` 完整复制到新 `split/core/runtime/admin/`，旧 `.env` 复制到新目录。
  此方式不设置指向旧根目录的 `RUNTIME_ROOT`。核对复制内容和原项目名后，使用新目录重建 core/admin。
  不要同时运行两套 CORE 写同一数据库。
- **legacy 旧官方镜像**：将原 `.env`、`runtime/`、`packages/` 完整迁移到对应的新 legacy 目录。
  `fixes/` 已随 Git 移动；挂载需要同时包括新 fixes 和原数据，不能只复制 Compose 文件。

任何已有自定义 Compose 改动都需与新文件合并；不能用示例覆盖自己的参数。
独立 admin 目录用于新分离部署，不会自动接管 ALL/CORE 的后台。若移动后台，先停原 admin，
复制原后台数据（包括 `.db_initialized`、RSA 私钥和公钥），再启动独立 admin。

## 全新部署与回退

全新部署从 [导航](README.md) 选目录，使用新的 `.env` 和 `runtime/`，不需要上面的路径复用设置。
本次整理没有自动连接或修改服务器。回退时保留原镜像、旧配置及数据路径；不要执行 `down -v` 或删除数据库。
