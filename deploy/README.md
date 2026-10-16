# 部署目录导航

先选游戏镜像系统，再选部署方式。`all` 表示整体部署，`split` 表示单独部署；自建 MySQL 始终由你管理。
CentOS/Ubuntu 是**镜像**系统，和宿主机系统名称不必相同。

```text
deploy/
├── centos/
│   ├── README.md
│   ├── build/                 构建说明
│   ├── all/                   game(ALL) + admin，外置 MySQL
│   ├── split/
│   │   ├── README.md          CentOS 拆分能力范围
│   │   └── admin/             独立后台
│   └── legacy/
│       ├── external-mysql/    旧官方镜像 + 外置 MySQL + 补丁
│       └── bundled-mysql/     旧官方镜像内置 MySQL 测试
├── ubuntu/
│   ├── README.md
│   ├── build/                 构建说明
│   ├── all/                   game(ALL) + admin，外置 MySQL
│   ├── split/
│   │   ├── README.md          跨主机地址与启动顺序
│   │   ├── core/              核心服务 + 可选同机后台
│   │   ├── game/              游戏频道
│   │   ├── p2p/               relay / STUN
│   │   └── admin/             独立后台
│   └── shared/                Ubuntu 游戏服务公共配置
└── shared/
    ├── admin.yaml             两种系统共用的后台定义
    └── bootstrap-admin.sql.example
```

每个可执行部署目录都包含 `compose.yaml`、`.env.example`、`README.md`。
在该目录复制 `.env.example` 为 `.env`，填写真实值，再执行 Compose 命令。
`build/` 和 `shared/` 不直接运行 Compose。运行后生成 `runtime/`，不提交 Git。
Ubuntu 和独立后台模板通过相对路径引用 shared 文件，服务器应保留 Git 仓库的完整层级，不能只复制叶子目录。

| 场景 | 从这里开始 |
|---|---|
| Ubuntu 单机游戏 + 后台 | [Ubuntu 整体部署](ubuntu/all/README.md) |
| Ubuntu 核心、频道、P2P 分机器 | [Ubuntu 拆分部署](ubuntu/split/README.md) |
| CentOS 保持原自建镜像流程 | [CentOS 完整部署](../docs/centos/deployment.md) |
| Ubuntu 后台放到单独机器 | [Ubuntu 独立后台](ubuntu/split/admin/README.md) |
| CentOS 后台放到单独机器 | [CentOS 独立后台](centos/split/admin/README.md) |
| 已按旧目录启动过 | [先迁移配置和运行路径](MIGRATION.md) |

源码保持一份：`services/game/` 为两个平台的游戏镜像构建及共享资源，`services/admin/` 为共享后台，
`clients/launcher/` 为 Windows 登录器。后台不因游戏基础镜像不同而复制两套源码。

CentOS 的 CORE/GAME/P2P 跨主机拆分未提供已验收模板，详见其 split 说明。
本次整理不改游戏协议、数据库内容、镜像标签或线上服务。玩家客户端实机验收仍是独立步骤。

## 目录整理验证（2026-10-16）

9 个部署入口均通过实际 `docker compose config` 解析：检查角色、项目名、独立挂载目录、已有数据路径覆盖、
独立后台不依赖游戏环境参数，以及文档链接。7 套原有 Compose 与整理前配置比对，除预期的宿主机路径外一致。
5 项目录测试、30 项 Ubuntu 离线测试、9 项初始化修复测试通过。本次没有修改运行时代码，
没有重新构建镜像、启动线上服务或重跑 30 分钟游戏稳定性；原运行验收见 [文档索引](../docs/README.md)。
