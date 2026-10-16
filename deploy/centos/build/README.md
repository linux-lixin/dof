# Centos 镜像构建

在 Linux x86_64 服务器执行。源码、游戏资源和兼容依赖由同一 Git 仓库提供；构建仍需访问软件源。

```bash
git clone https://github.com/linux-lixin/dof.git /opt/dof
cd /opt/dof
docker build -f dnf-game/build/Centos7-DNF/Dockerfile -t dnf-game:local-fix-20261015 dnf-game
docker build -t dnf-admin:local-fix-20261015 dnf-server-public
```

已有仓库时用 `cd /opt/dof` 和 `git pull --ff-only` 代替 clone。构建标签须与部署 `.env` 一致。
Dockerfile 和共享资源保留在 `dnf-game/`，后台源码保留在 `dnf-server-public/`，不复制两份。
构建完成按 [平台入口](../README.md)选择整体或单独部署目录。
