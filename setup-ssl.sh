#!/bin/bash

# SSL证书获取脚本 for aguai.net
# 使用方法: ./setup-ssl.sh your-email@example.com

set -e

DOMAIN="aguai.net"
WWW_DOMAIN="www.aguai.net"
EMAIL="${1:-admin@aguai.net}"

echo "========================================="
echo "SSL证书设置脚本 - aguai.net"
echo "========================================="
echo ""

# 检查是否提供了邮箱
if [ -z "$1" ]; then
    echo "⚠️  未提供邮箱地址，使用默认: $EMAIL"
    echo "建议用法: ./setup-ssl.sh your-email@example.com"
    echo ""
    read -p "继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 创建必要的目录
echo "📁 创建证书目录..."
mkdir -p certbot/www
mkdir -p certbot/conf

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

echo "✅ Docker运行正常"
echo ""

# 停止现有的Nginx容器(如果存在)
echo "🛑 停止现有Nginx容器..."
docker-compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true

# 获取SSL证书
echo "🔐 获取SSL证书..."
echo "域名: $DOMAIN, $WWW_DOMAIN"
echo "邮箱: $EMAIL"
echo ""

docker run --rm \
    -v $(pwd)/certbot/www:/var/www/certbot:rw \
    -v $(pwd)/certbot/conf:/etc/letsencrypt:rw \
    -p 80:80 \
    certbot/certbot certonly \
    --standalone \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN" \
    -d "$WWW_DOMAIN"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SSL证书获取成功!"
    echo ""
    echo "证书位置:"
    echo "  - 完整链: certbot/conf/live/$DOMAIN/fullchain.pem"
    echo "  - 私钥:   certbot/conf/live/$DOMAIN/privkey.pem"
    echo ""
    
    # 设置正确的权限
    echo "🔧 设置证书权限..."
    sudo chown -R $USER:$USER certbot/
    
    # 启动所有服务
    echo "🚀 启动服务..."
    docker-compose -f docker-compose.prod.yml up -d
    
    echo ""
    echo "========================================="
    echo "✅ 部署完成!"
    echo "========================================="
    echo ""
    echo "访问地址:"
    echo "  - HTTP:  http://$DOMAIN (将自动重定向到HTTPS)"
    echo "  - HTTPS: https://$DOMAIN"
    echo ""
    echo "证书信息:"
    docker-compose -f docker-compose.prod.yml exec certbot certbot certificates
    echo ""
    echo "证书将在90天后过期，Certbot会自动续期"
    echo ""
else
    echo ""
    echo "❌ SSL证书获取失败"
    echo ""
    echo "可能的原因:"
    echo "  1. DNS未正确解析到此服务器"
    echo "  2. 80端口被占用"
    echo "  3. 防火墙阻止了80端口"
    echo ""
    echo "请检查后重试"
    exit 1
fi
