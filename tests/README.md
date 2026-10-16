# 部署修复回归测试

游戏资源已随仓库提供。在 dof 根目录直接运行：

```text
python tests/test_deployment_fixes.py
python tests/test_mysql56_fixes.py
```

前者需要 Python 3 和 bash（Windows 使用 Git for Windows），模拟初始化命令，不连接数据库。
后者需要本地 Docker，拉取固定的 mysql:5.6 digest，在无网络、无公开端口的临时容器内执行实际 SQL，结束删除该测试容器和匿名卷。需要 Docker 能访问该镜像；不连接服务器，不读取实际 .env 或凭据。

部署覆盖文件与源码保持同步：后台入口复制到 deploy/*/fixes/admin-entrypoint.sh；游戏 seed/repair/daily_job/response_time 脚本复制到同一 fixes 目录。修改后应复测并核对副本一致性。
