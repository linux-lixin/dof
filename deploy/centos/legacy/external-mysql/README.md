# DNF 测试部署附件

修复说明：[2026-10-15 部署修复](../../../../docs/deployment-fixes-2026-10-15.md)。

必须上传整个目录，包括 fixes/。Compose 通过只读挂载修复固定镜像的入口和日志维护；只上传 compose.yaml 不够。

external-mysql 使用自建外部数据库，本次实际服务器版本为 MySQL 5.6.50；bundled-mysql 使用游戏镜像内置数据库。不要混用两套数据库配置。

按 .env.example 填写地址和独立密码。MYSQL_INIT_SSL_MODE=disabled 用于当前无 TLS 的专用旧 MySQL 测试实例。先启动 game 并检查频道，再启动 admin。

[共享管理员 SQL](../../../shared/bootstrap-admin.sql.example) 需替换占位密码并分步执行；admin 是后台管理员/默认推荐人，不是完整游戏账号。已有服务器不要重复初始化数据库或覆盖密钥。
默认推荐人改为 admin 需要使用当前源码重建的后台镜像；旧上游镜像仍可能默认使用 123123，此时注册时须显式填写推荐人 admin。

游戏启动、后台数据库与 HTTP 接口已在现有服务器验证；玩家进服和更新功能仍需实际客户端验证。源码和部署回归测试见 [tests](../../../../tests/README.md)。

完整步骤见 [旧镜像部署文档](../../../../docs/centos/legacy/external-mysql.md)。
