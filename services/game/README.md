# Ubuntu 游戏服务

唯一游戏镜像基于 Ubuntu 24.04，支持 ALL、CORE、GAME、P2P 四种角色，必须连接外置数据库。

| 目录 | 用途 |
|---|---|
| `docker/ubuntu` | Dockerfile、必要兼容源码和许可证 |
| `assets` | 游戏程序、模板、初始化 SQL、手动 PVF 测试包 |
| `runtime/ubuntu` | Ubuntu 入口、校验、健康检查和启动完成提示 |

在仓库根目录构建：

```bash
docker build -f services/game/docker/ubuntu/Dockerfile -t dnf-game:ubuntu24.04 services/game
```

启动脚本已直接保存为 Ubuntu 版本，不再依靠构建时剪裁旧平台脚本。
部署见 [整体](../../deploy/ubuntu/all/README.md) / [拆分](../../deploy/ubuntu/split/README.md)，依赖见 [兼容说明](../../docs/ubuntu/compatibility.md)。
`assets` 是构建输入，不是线上运行目录。实际 PVF、公钥、配置和用户 hook 保存在部署的 `runtime` 中。

## 内置 QK 配置

`assets/home/template/neople/game/` 中的三个配置随游戏模板打入镜像，启动时由现有 `bootstrap.sh`
复制到容器 `/home/neople/game/`，无需额外挂载：

| 文件 | 用途 |
|---|---|
| `qk_plugin_antonRaid.ini` | 安徒恩团本配置 |
| `qk_plugin_lukeRaid.ini` | 卢克团本配置 |
| `qk_plugin_config.ini` | 镶嵌、装备解锁等通用功能配置 |

这些文件保留提供时的配置值。部署前按实际账号和 PVF 修改 GM UID、NPC、地图及奖励道具等参数。
`init.sh` 生成的 Supervisor 配置指定游戏工作目录为 `/home/neople/game`，`start_game.sh`
在此启动 `./df_game_r`。因此这些配置与游戏程序放在一起，供按工作目录或程序目录读取配置的插件使用。
这确认了项目中的放置位置；插件是否按此规则读取、功能是否生效仍需运行验证。

文件路径：

```text
源码 assets/home/template/neople/game/qk_plugin_*.ini
  → 镜像 /home/template/neople/game/qk_plugin_*.ini
  → 启动后 /home/neople/game/qk_plugin_*.ini
```

修改后，在仓库根目录重新构建镜像，再进入所使用的部署目录重建游戏容器。例如一体部署：

```bash
docker build -f services/game/docker/ubuntu/Dockerfile -t dnf-game:ubuntu24.04 services/game
cd deploy/ubuntu/all
docker compose up -d --force-recreate game
```

拆分部署在 `deploy/ubuntu/split/game` 中重建 `game` 服务。修改源码文件或只重启旧容器不会更新镜像中的配置。
