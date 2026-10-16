# Ubuntu 24.04 游戏运行时 ABI 审计

后续 onlyGuo 清理已从 Ubuntu 运行镜像移除 `DnfGateServer` 及其启动配置；当前构建检查为
28 个游戏/模板/工具 ELF、6 个兼容库，均无未解析依赖。下文涉及旧网关的审计是历史兼容性证据，
不表示当前 Ubuntu 仍运行该组件。CentOS 兼容入口保留。

日期：2026-10-16；平台：`linux/amd64`。Ubuntu 基础镜像固定为
`ubuntu:24.04@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55`。

## 已验证的边界

所有随仓库提供的游戏 ELF 均有 Ubuntu 原生 glibc 2.39 的加载路径。无需复制旧 glibc，
无需修改系统 loader、`ld.so.conf`、`/usr/lib` 或全局 `LD_LIBRARY_PATH`。
这项结论来自 ELF 检查、`ldd -r` 重定位检查及实际启动；**不是客户端登录/进图验收**。
没有提供的玩家 DP 插件不在本次二进制审计范围内，替换插件需要重新验证。

最终构建 `dnf-game:ubuntu24-v1` 已通过：29 个游戏/模板/TeaEncrypt/STUN hook ELF，
6 个专用兼容库，均为 0 个未解析符号/依赖；网关、GeoIP 数据初始化、共享内存实际启动门禁通过。
GeoIP/共享内存修复后的镜像 ID：`sha256:fc4fe1006219b3f65c6589f1940b035f4197922ad7193e9f824b95867f91d718`。
原生工具实测 Python 3.12.3、Supervisor 4.2.5、MariaDB client 10.11.14、系统 OpenSSL 3.0.13。
镜像内未找到 gcc、python2、mysqld、netbird、tailscale、tailscaled，且未设置全局 LD 环境变量。

| 对象 | 架构 | 实际运行时路线 |
|---|---|---|
| df_game_r、核心服务、频道、relay、secsvr | i386 | Ubuntu libc6/libstdc++6/libgcc-s1/zlib1g i386 |
| bridge_hook.so、channel_hook.so、libhook.so | i386 | Ubuntu 原生 i386 libc/dl/rt/pthread/libgcc |
| libnxencryption.so | i386 | 使用现有游戏资产；固定 SHA，放入 `/opt/dnf/compat/i386` |
| libGeoIP.so.1 | i386 | Ubuntu 源包 GeoIP 1.6.12，`gcc -m32` 编译；同一专用目录 |
| liblegacy-shm.so | i386 | 本仓库源码构建，兼容已有 TSS 的目录式共享内存名 |
| STUN、forward、TeaEncrypt | amd64 | Ubuntu 原生 amd64 库；STUN hook 在构建阶段编译 |
| DnfGateServer | amd64，打包 ELF | Ubuntu 原生 libc + 专用 OpenSSL 0.9.8zh / MySQL client 5.0.95 |

Ubuntu noble 的 GeoIP 二进制包只有 amd64，不能安装 `libgeoip1t64:i386`。
这里从经 Ubuntu 签名 Sources 索引认证的原始源码构建 i386 库。

首次完整频道启动另发现数据依赖：GeoIP 1.6.12 源码不包含数据库，库虽然能加载，
`GeoIP_new` 仍因缺少默认数据失败。现在从固定的历史 GeoIP 1.4.8 归档恢复 `GeoIP.dat`，
SHA256 与旧镜像 `/usr/local/share/GeoIP/GeoIP.dat` 完全相同，安装到新库编译时的默认位置
`/opt/dnf/compat/i386/share/GeoIP/GeoIP.dat`。这是随旧系统已有的 GeoLite Country 数据，
不执行实时地理位置查询或数据库更新。This product includes GeoLite data created by MaxMind,
available from https://www.maxmind.com/ 。

实际 secagent 初始化还暴露了 glibc 行为差异：`shm_open("sec/tss_sdk_bus_1")` 在旧 glibc
可以访问 `/dev/shm/sec/tss_sdk_bus_1`，Ubuntu 原生实现因名字含目录分隔符返回 `EINVAL`。
MIT 许可的 `legacy-shm.c` 只处理 `sec/tss_sdk_bus_<数字>`（允许单个前导 `/`），
使用 `openat`/`unlinkat` 保持旧共享路径，设置 CLOEXEC，并拒绝跟随目录/文件符号链接。
其他名字调用 `RTLD_NEXT` 的原生实现。launcher 仅给 i386 游戏子进程自动前置该库，
保留既有 hook 链，Python 和 Supervisor 不加载它。修复后 secagent 日志达到
`init gamesvr channel succ`，在与 CentOS 相同配置下持续运行到测试超时。

网关是容易漏检的特例：其外层 ELF 没有动态依赖，`ldd` 回报“not a dynamic executable”，
但运行后会寻找 `libssl.so.6`、`libcrypto.so.6`、`libmysqlclient.so.15`。
初次原生启动确实因 `libssl.so.6` 缺失失败，因此 Docker 构建增加了实际启动门禁。
OpenSSL 使用真正的 0.9.8zh 源码，显式生成 SONAME 6；未把现代 OpenSSL 3 改名冒充旧 ABI。
MySQL `.15` 是已有运行镜像中的准确库，已与固定上游 RPM 重新提取的内容逐字节 SHA 校验一致。

## 隔离与构建接口

构建上下文为 `dnf-game`：

```sh
docker build -f build/Ubuntu24-DNF/Dockerfile -t dnf-game:ubuntu24-v1 .
```

`--target game` 可只构建基础镜像及 ABI 门禁；最终层复制 `ubuntu/` 到 `/opt/dnf/ubuntu/`，
执行 `prepare_image.py`。启动入口为 `/opt/dnf/ubuntu/entrypoint.sh`。
运行镜像使用 Python 3、Supervisor、socat、netcat-openbsd、MariaDB 客户端。
编译器只存在于构建层。不复制旧镜像中的操作系统、Python 2、数据库服务器或 VPN 可执行文件。
已有模板中的 netbird/tailscale 启动目录在镜像内删除。

`/opt/dnf/ubuntu/run-game` 读取目标 ELF 架构，只为最终游戏子进程配置
`LD_LIBRARY_PATH=/opt/dnf/compat/i386` 或 `amd64`。
hook 通过 `DNF_GAME_PRELOAD` 传给 launcher；它检查 ELF 位数后，在 exec 时转换成 `LD_PRELOAD`。
Python、Supervisor、socat、系统 openssl/mysql 客户端不使用这些兼容库。

原生游戏进程会直接向 stdout/stderr 输出数据库口令。launcher 在 `execve` 前创建独立
Python reader，通过两个管道按行脱敏；主进程仍直接替换为游戏 ELF，PID、退出码和信号目标不变。
reader 不加载游戏兼容库/hook，并在组停止信号时继续排空输出直到 EOF。
环境中 PASSWORD/PASS/PWD/SECRET/TOKEN/KEY 字段的非空值（包括 `DEC_GAME_PWD`）按字节替换，
仅排除表示当前工作目录的标准 shell `PWD`；
即使值不在环境中，`pw=`、`Game DB Password:`、`Auction DB Password:` 等口令字段也隐藏整行尾部。
跨 write 的完整行缓冲防止片段泄漏，超过 64 KiB 的单行整体抑制；正常日志保持 stdout/stderr 分离。
此边界只过滤进程标准输出，不改写原生程序自己打开的日志文件。

`audit/run-game-probe.c` 与 `audit/test_run_game_redaction.py` 使用合成凭据，实际编译/运行
i386 和 amd64 子进程验证两个输出流、分段写、未知口令标签、无换行 EOF、超长行、退出码 37、
原 PID、直接及进程组 SIGTERM，并检查 reader 内存映射无专用兼容库。
修复前测试观察到凭据泄漏；修复后全部通过。该测试通过只读 bind mount 使用新 launcher，
无需修改或重建正在验收的镜像。

## 可复查证据

`dnf-game/build/Ubuntu24-DNF/audit/` 保留原生依赖缺失的 `native-before.json`、
修复后的 `native-after.json`、逐程序无参数启动日志 `start-proof.json`。
`image-elf-report.json`、`image-compat-report.json`、`image-gate-start-proof.json` 与
`image-packages.tsv` 由最终构建镜像导出。
无参数启动的非零退出不等于 ABI 不兼容：df_game_r 到达公钥检查；monitor 抛出明确的
缺少参数/`server_str.xml` 配置异常；secsvr 到达自身 XML 配置检查；forward 进入监听后被限时结束。
网关到达 `invalid ini file:Config.ini`，与旧镜像相同。

每次镜像构建重新执行：

- `/opt/dnf/audit/elf-audit.py`：覆盖模板、TeaEncrypt、编译后的 STUN hook 及专用兼容库，
  记录架构、interpreter、NEEDED、符号版本、SHA256、解析路径；任何缺库/未定义符号使构建失败。
- `/opt/dnf/audit/gate-probe.py`：`LD_BIND_NOW=1` 实际运行打包网关，要求到达已知 Config.ini 检查。
- 生成 `/opt/dnf/audit/elf-report.json`、`compat-report.json`、`gate-start-proof.json`、`packages.tsv`。
- `geoip-probe.c` 在真实 i386 进程调用 `GeoIP_new` 并验证国家数据库类型；缺数据时已观察失败。
- `shm-probe.c` 验证原生及旧名称的创建、跨进程读写与删除、CLOEXEC、路径遍历及符号链接拒绝。
  原生实现已观察到旧名称失败；修复后通过，并额外在原始 `libhook.so` hook 链下通过。

额外配置边界：仓库原始 zergsvr 配置在 CentOS 和 Ubuntu 均因
`Not pull config but get ip from cfgsvr` 退出（ret=290010039）。这与 secagent 的 Ubuntu
共享内存差异是两个问题。Ubuntu 镜像层的 `ubuntu/tss_config.py` 现在选择二进制支持的
`cfgfile` 模式，只保留现有 self 30:570011 → 127.0.0.1:9000 映射，并设置
`auto_connect_num=0`，移除旧模板中指向自身的“远程 monitor”及不存在的 cfgserver 自动连接。
它验证 self 映射后才写入，配置重复执行不变；gunnersvr/安全检查/secagent 通道配置字节保持不变。
原始 CentOS 资产不修改。此适配用于本地独立部署，发行包未包含远程 TSS 配置/监控服务，
不声称集成了远程 TSS 遥测。

本地拓扑修复镜像 `sha256:c0595e55ce5e47f4ca6980e7b5bc3eea23ce20fb17d04b14752a684fdb7474fb`
已实际同时运行三个进程：zergsvr 监听 127.0.0.1:9000，gunnersvr 输出 `connect monitor succ`，
secagent 输出 `init gamesvr channel succ` 并建立 12 个游戏共享通道。
证据在 `audit/tss-start-proof.json`；完整 DB/游戏频道通信仍由整体部署验收。
零间隔并发冷启动曾触发共享 MMAP 初始化竞争；等 relay 初始化后重启 secagent 可恢复，
部署使用原有 Supervisor 顺序启动和自动重启。`tests/test_ubuntu_tss.py` 覆盖唯一 self 映射、
无错误自连接、保留安全配置、幂等以及错误 identity 时拒绝写入。

完整服务启动、数据库初始化、拆分部署和持续运行结果由部署验收报告另行记录。

### CentOS 实际解析基线与最终镜像核对

`audit/centos-baseline-elf.json` 对固定旧镜像
`sha256:b78167ea228e3a3f028827dadd0d2e075e70d2afa8e92db3f46e4f2d609b1ec1`
记录 28 个 ELF 的原始 SHA256、架构、loader、符号版本和实际依赖解析；
`centos-baseline-libraries.json` 记录 34 个解析路径的真实文件、SHA256、RPM 所属版本，
`centos-baseline-packages.tsv` 为完整 RPM 清单。
CentOS glibc 为 2.17-326.el7_9.3（i686/x86_64），libstdc++ 为 4.8.5-44.el7。
打包网关通过 `LD_TRACE_LOADED_OBJECTS=1` 查询自身 loader，揭示 readelf/ldd 静态外观隐藏的依赖。
旧镜像中的 ssl6/crypto6 实际指向 OpenSSL 1.0.2k-26.el7_9；这只是旧环境事实，
Ubuntu 使用前述真实 0.9.8zh ABI 专用构建。MySQL 客户端为 5.0.95-1.rhel5。
没有 RPM 所属的手工安装库仍记录完整路径和 SHA256，不虚构包版本。

同一脚本生成 `ubuntu-current-{elf,libraries}.json` 与 `ubuntu-current-packages.tsv`，
覆盖最终验收镜像 29 个 ELF、24 个解析路径；专用库通过 `--compat` 按架构解析。
这些清单只读取镜像，不安装软件、不启动服务。仓库根目录可复现：

```sh
audit="$PWD/dnf-game/build/Ubuntu24-DNF/audit"
centos=$(docker image inspect dnf-game:local-fix-20261015 --format '{{.Id}}')
ubuntu=$(docker image inspect dnf-game:ubuntu24-v1 --format '{{.Id}}')
docker run --rm --read-only --mount "type=bind,source=$audit,target=/audit" --entrypoint /usr/local/bin/python2.7 "$centos" /audit/runtime-inventory.py --prefix centos-baseline --image-id "$centos"
docker run --rm --read-only --mount "type=bind,source=$audit,target=/audit" --entrypoint /usr/bin/python3 "$ubuntu" /audit/runtime-inventory.py --prefix ubuntu-current --image-id "$ubuntu" --compat /opt/dnf/compat
```

最终验收镜像
`sha256:90edebbc8aa919681c7f5a8a79081e99bfb6bba1fb2f81aaa502ecc7231f9c3f`
的七份内置审计文件/资源锁已用未启动的临时容器导出并逐字节 SHA256 核对。
`audit/image-audit-verification.json` 保存文件映射与哈希；全部一致。
导出前使用只读 inspect 核对真实镜像 ID，并直接按此不可变 ID 生成库存和导出报告。
此镜像排除了宿主 Python 缓存，七份内置报告/资源锁与前一镜像逐字节不变。
重新执行库存审计仅产生镜像 ID 和 ASLR 地址变化，ELF/库哈希、解析路径和包版本不变。
标准 shell `PWD` 误判修复后，共享内存探针的两次通过记录正常保留 `/`。
当前库存无缺库或未定义符号。完整 ALL/拆分持续验收结果另见部署验收报告。

`audit/ubuntu-live-libraries.json` 补充同一最终镜像的实际进程映射证据：通过只读
`docker exec` 从 ALL、拆分 CORE/P2P/GAME 节点读取 `/proc/PID/exe` 与 `/proc/PID/maps`，
覆盖 42 个运行中的 `df_*`、gunnersvr、zergsvr、secagent、DnfGateServer 进程，
并补采实际数据库代理 `socat1` 的 117 个进程（含连接子进程）。
记录可执行文件与合计 34 个不同共享库路径的 SHA256，包括运行时加载的
`libantisvrimport.so`、BIG5 转码模块及实际 hook/私有兼容库。
相同可执行文件和库集合按数量归组，不保存 PID、环境变量或命令行。
数据库代理实际调用 socat；`forward` 是未启用的遗留工具，仅有静态 ELF 检查，
不属于此部署必需运行组件，也没有虚构它的实时映射。
这是采样时仍映射的库集合，包含实际 dlopen 结果；不声称覆盖此前卸载或未来才加载的库。

## 来源、许可证与重建限制

`build/Ubuntu24-DNF/compat-lock.json` 固定源码/二进制 URL、版本、SHA256 和提取来源。
GeoIP 与 OpenSSL 源码压缩包随构建资源保存；MySQL 客户端保存经过校验的精确库和 GPL 文本，
对应 MySQL 5.0.95 官方源码 URL 已实际下载验证 SHA。镜像中的许可证在 `/opt/dnf/licenses/`。
游戏资产沿用 `scripts/game-assets.lock.json` 的固定上游提交；不增加或假定其再分发授权。

Ubuntu 包仍从签名的 noble/noble-updates/noble-security 仓库安装，包版本清单记录在镜像内。
基础镜像与兼容资源固定不意味着 apt 仓库永久冻结；如要求逐位可重现，应保存本次构建镜像 digest
及包仓库快照。OpenSSL 0.9.8 与 MySQL 5.0 是网关强制要求的旧 ABI；它们的存在属于已知维护限制，
升级 Ubuntu 不会自动消除这些闭源程序的旧依赖。
