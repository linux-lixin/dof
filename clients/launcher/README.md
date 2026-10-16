# Windows 登录器

本目录保留 WPF 工程 `DNFLogin.slnx` / `DNFLogin.csproj`，命名空间、资源名称和业务逻辑不因目录整理改变。
`DNFLogin/LoginConfig.cs` 处理本地登录器配置，UI 在各 `*Window.xaml` 及其 C# 文件中。
项目当前目标为 `net10.0-windows7.0`，需要匹配的 .NET 10 SDK 和 Windows 桌面构建环境。

在 Windows 仓库根目录构建：

```powershell
dotnet build clients/launcher/DNFLogin.csproj -c Release
```

依赖还原需要访问 NuGet。构建产物在本目录 `bin/`、`obj/`，不提交；发布配置位于 `Properties/PublishProfiles/`，
发布前应按实际目标检查路径，不把源码自带设置当作生产发行配置。

使用、注册、服务器地址和更新发布说明见 [登录器文档](../../docs/launcher/README.md)。
此次目录整理不代表已验证真实 Windows 客户端进游戏或自动更新。
