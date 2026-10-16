#!/bin/bash

# ================= 配置区域 =================
# 默认镜像仓库地址 (如果脚本运行时检测到是这个默认值，会提示你输入)
DEFAULT_REPO="your-docker-username/dnf-server"
IMAGE_REPO="$DEFAULT_REPO"
TAG="latest"

# 目标平台
PLATFORMS="linux/amd64,linux/arm64"
# ===========================================

# 检查是否修改了镜像名，如果没有，则提示输入
if [ "$IMAGE_REPO" == "$DEFAULT_REPO" ]; then
    echo "========================================================"
    echo "错误: 你还没有配置镜像仓库地址！"
    echo "构建多架构镜像必须推送到 Docker Hub 或私有仓库。"
    echo "--------------------------------------------------------"
    read -p "请输入你的镜像仓库地址 (例如: guoshengkai/dnf-server): " USER_INPUT_REPO

    if [ -z "$USER_INPUT_REPO" ]; then
        echo "错误: 输入不能为空。"
        exit 1
    fi
    IMAGE_REPO="$USER_INPUT_REPO"
fi

echo "准备构建多架构镜像: $PLATFORMS"
echo "目标仓库: $IMAGE_REPO:$TAG"
echo "----------------------------------------------------"
echo "要实现【对方拉取时自动识别平台】，必须将镜像 Push 到 Docker Registry (如 Docker Hub 或 阿里云)。"
echo "本地 Docker Daemon 无法同时根据一个 Tag 保存多种架构的镜像。"
echo "----------------------------------------------------"

# 检查是否登录 (简单的检查，不一定准确)
# docker login ...

read -p "是否继续构建并推送到仓库? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "已取消。"
    exit 1
fi

# 1. 准备 Buildx 环境
# 默认的 builder 可能不支持多架构 docker-container 驱动
BUILDER_NAME="my-multi-arch-builder"

if ! docker buildx inspect $BUILDER_NAME > /dev/null 2>&1; then
    echo "创建新的 Buildx Builder: $BUILDER_NAME ..."
    docker buildx create --name $BUILDER_NAME --use --bootstrap
else
    echo "使用现有的 Buildx Builder: $BUILDER_NAME"
    docker buildx use $BUILDER_NAME
fi

# 2. 构建并推送
echo "开始构建并推送..."
# --push 会自动把构建好的 manifest list 推送到远程仓库
docker buildx build --platform $PLATFORMS \
  -t "$IMAGE_REPO:$TAG" \
  --push \
  .

if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "构建并推送成功!"
    echo "你的朋友现在可以使用以下命令拉取并将自动适配其架构:"
    echo "docker pull $IMAGE_REPO:$TAG"
    echo "=========================================="
else
    echo "构建失败!"
fi
