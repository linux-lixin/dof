# 已有部署升级

## 已在 deploy/ubuntu/all 或 split 运行

本轮只支持 Ubuntu，删除了旧平台构建、VPN、旧网关和未使用依赖。当前部署路径、Compose 项目名、镜像标签、外部数据库参数和密钥格式保持不变。
原有受管 `run/`、`monitor_ip/` 脚本与已验证 Ubuntu 版本保持兼容；不自动覆盖用户修改过的脚本。

在服务器仓库根目录拉取并构建：

```bash
cd /opt/dof
git pull --ff-only
docker build -f services/game/docker/ubuntu/Dockerfile -t dnf-game:ubuntu24-v1 services/game
```

然后在已有部署目录更新容器：

```bash
cd /opt/dof/deploy/ubuntu/all
docker compose up -d --force-recreate game
docker compose logs -f --tail 100 game
```

拆分部署则在原 `split/core`、`split/p2p`、`split/game` 目录分别更新对应服务。后台业务没有改变，本轮无需因此重建后台。
`restart` 不会切换镜像。保留 `.env`、`RUNTIME_ROOT`、PVF、配对密钥和自定义 hook；不要重跑后台管理员初始化，也不要删除数据库初始化标记。
更新前可按自己的运维策略保留旧镜像标签与数据恢复点；回退使用该镜像和对应配置。不要执行 `down -v`。

旧 `.env` 中 `NB_*`、`TS_*`、`GATE_PASSWORD`、`GM_*` 参数不再使用，可从部署配置删除。
非空的旧组网认证参数仍会明确报错，避免误以为隧道已启动；这只是拒绝旧配置，不是保留组网功能。
挂载目录中的历史组网状态和旧网关文件不会自动删除；尤其不要误删后台仍使用的 `runtime/admin/data/private.key`。
如果自己在 `/data/conf.d` 增加过组网/旧网关启动项，请自行移除该自定义配置，再重建容器。

## 还在旧 deploy/ubuntu 根目录运行

旧版 ALL 入口已移至 `deploy/ubuntu/all`。Git 不会搬动被忽略的 `.env` 和 `runtime/`。
将 `.env` 复制到新目录，设置 `RUNTIME_ROOT=/opt/dof/deploy/ubuntu/runtime` 指向原数据根目录，再核对 `docker compose config` 中的实际挂载。
保留原 Compose 项目名（ALL 为 `dnf-ubuntu-all`），避免新建第二套服务；不要在迁移期间让两套独立服务同时初始化同一数据库。

拆分节点同理，分别使用 `split/core`、`split/game`、`split/p2p`、`split/admin` 的入口，并将每个节点的 `RUNTIME_ROOT` 指向它自己原有数据根目录。

## 从已退役的旧平台迁移

当前仓库不再提供 CentOS Dockerfile 或部署模板。原部署说明和源码可从 Git 提交 `1ded8a2` 及更早历史查看；不要将旧平台整个数据目录作为 Ubuntu 数据卷。
先用独立 Ubuntu 目录和数据库副本验证，再按完整部署文档迁移配套 PVF、公钥和业务数据。未标记的旧目录会被入口拒绝。
目录结构变化不会自动移动你留在旧源码目录中的本地文件，不要把这些残留目录直接当垃圾删除。
