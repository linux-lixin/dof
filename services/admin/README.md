# onlyGuo 管理后台

前端在 `frontend/`，Java 后端在 `backend/`，后台库种子在 `database/init.sql`，
容器入口和 Nginx 模板在 `docker/`。各游戏角色共用这一套后台。

从仓库根目录构建：

```bash
docker build -f services/admin/docker/Dockerfile -t dnf-admin:local-fix-20261015 services/admin
```

Docker 构建包含前端和后端，不要求宿主机另装 Java/Node。不要只把 `docker/` 作为构建上下文。
容器中的 `/app/data`、初始化标记和密钥路径保持不变。

部署入口：[整体部署](../../deploy/ubuntu/all/README.md)、[独立后台](../../deploy/ubuntu/split/admin/README.md)。

开发操作及原上游使用说明见 [后台文档](../../docs/admin/README.md)。
