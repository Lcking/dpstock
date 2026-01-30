# aguai.net 域名和SSL部署指南

## 快速部署 (推荐)

### 1. 在服务器上克隆代码
```bash
git clone git@github.com:Lcking/dpstock.git
cd dpstock
```

### 2. 配置环境变量
```bash
cp .env.example .env
nano .env  # 填入真实的API密钥
```

### 3. 一键获取SSL证书并启动
```bash
chmod +x setup-ssl.sh
./setup-ssl.sh your-email@example.com
```

完成!访问 https://aguai.net

---

## 手动部署步骤

### 步骤1: 准备环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo apt install docker-compose-plugin -y

# 重新登录以应用Docker组权限
```

### 步骤2: 配置防火墙

```bash
# 开放必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
sudo ufw status
```

### 步骤3: 获取SSL证书

```bash
# 创建证书目录
mkdir -p certbot/www certbot/conf

# 运行Certbot获取证书
docker run --rm \
  -v $(pwd)/certbot/www:/var/www/certbot:rw \
  -v $(pwd)/certbot/conf:/etc/letsencrypt:rw \
  -p 80:80 \
  certbot/certbot certonly \
  --standalone \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d aguai.net \
  -d www.aguai.net
```

### 步骤4: 启动服务

```bash
# 使用生产配置启动
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 步骤5: 验证部署

```bash
# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 测试HTTP重定向
curl -I http://aguai.net

# 测试HTTPS访问
curl -I https://aguai.net

# 检查SSL证书
docker-compose -f docker-compose.prod.yml exec certbot certbot certificates
```

---

## 证书管理

### 查看证书信息
```bash
docker-compose -f docker-compose.prod.yml exec certbot certbot certificates
```

### 手动续期证书
```bash
docker-compose -f docker-compose.prod.yml exec certbot certbot renew
docker-compose -f docker-compose.prod.yml restart nginx
```

### 测试续期(不实际续期)
```bash
docker-compose -f docker-compose.prod.yml exec certbot certbot renew --dry-run
```

---

## 故障排查

### 问题1: 证书获取失败

**检查DNS解析**:
```bash
nslookup aguai.net
nslookup www.aguai.net
```

**检查80端口**:
```bash
sudo netstat -tulpn | grep :80
```

**检查防火墙**:
```bash
sudo ufw status
```

### 问题2: HTTPS无法访问

**检查443端口**:
```bash
sudo netstat -tulpn | grep :443
```

**查看Nginx日志**:
```bash
docker-compose -f docker-compose.prod.yml logs nginx
```

**检查证书路径**:
```bash
ls -la certbot/conf/live/aguai.net/
```

### 问题3: 应用无法访问

**检查应用容器**:
```bash
docker-compose -f docker-compose.prod.yml logs app
```

**测试应用端口**:
```bash
docker-compose -f docker-compose.prod.yml exec app curl http://localhost:8888/api/need_login
```

---

## 维护命令

### 重启服务
```bash
docker-compose -f docker-compose.prod.yml restart
```

### 查看日志
```bash
# 所有服务
docker-compose -f docker-compose.prod.yml logs -f

# 特定服务
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f app
```

### 更新代码
```bash
git pull
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

## 数据持久化（非常重要）

本项目使用 SQLite 数据库，默认路径为：`data/stocks.db`（容器内：`/app/data/stocks.db`）。

如果你在服务器上 **删除/重建代码目录**（例如重新 `git clone` 到新目录），而数据库文件保存在 `./data` 目录内，则会表现为“判断数据丢失”。

### 推荐做法：把数据目录放到仓库外

例如把数据放到 `/var/lib/aguai/data`：

```bash
sudo mkdir -p /var/lib/aguai/data
sudo chown -R $USER:$USER /var/lib/aguai/data

# 写入 .env（或直接导出环境变量）
echo "DATA_DIR=/var/lib/aguai/data" >> .env
```

之后正常部署/重建容器都不会影响数据库文件。

### 一键初始化（推荐）

项目根目录提供脚本 `setup-persistence.sh`，会自动：
- 生成并写入固定的 `JWT_SECRET_KEY`
- 写入 `DATA_DIR` / `DB_PATH`
- 迁移现有 `./data` 到外部数据目录
- 重新构建并启动容器

```bash
chmod +x setup-persistence.sh
./setup-persistence.sh
```

如果你只想写入配置但不重启：
```bash
./setup-persistence.sh --no-restart
```

## Nginx 端口映射（非常重要）

`docker-compose.yml` 已默认开放 80/443 端口，部署后可直接访问网站。

验证：
```bash
docker compose ps
```

应看到：
`0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp`

### 快速确认数据是否真的“被删了”

在服务器上执行（需要安装 sqlite3：`apt-get install -y sqlite3`）：

```bash
sqlite3 ./data/stocks.db "select count(*) as judgments_count from judgments;"
sqlite3 ./data/stocks.db "select user_id, count(*) as c from judgments group by user_id order by c desc limit 10;"
```

如果表里还有数据但前端看不到，通常是 **当前浏览器的 user_id（cookie/匿名ID/anchor）变化**导致查到的是另一个账号。

### 备份证书
```bash
tar -czf ssl-backup-$(date +%Y%m%d).tar.gz certbot/conf/
```

---

## 性能优化建议

1. **启用HTTP/2**: 已在Nginx配置中启用
2. **Gzip压缩**: 已配置
3. **静态文件缓存**: 已配置30天缓存
4. **SSL会话缓存**: 已配置10分钟缓存

---

## 安全检查清单

- [ ] SSL证书有效且自动续期
- [ ] HTTP自动重定向到HTTPS
- [ ] 安全头已配置(HSTS, X-Frame-Options等)
- [ ] 防火墙只开放必要端口
- [ ] 定期更新Docker镜像
- [ ] 定期备份数据和证书
- [ ] 监控证书过期时间

---

## 监控和告警

### SSL证书过期监控
```bash
# 添加到crontab
0 0 * * * docker-compose -f /path/to/dpstock/docker-compose.prod.yml exec certbot certbot certificates | grep "VALID"
```

### 服务健康检查
访问: https://aguai.net/health

---

## 下一步

部署完成后:
1. 访问 https://aguai.net 验证网站正常
2. 使用 https://www.ssllabs.com/ssltest/ 检查SSL配置
3. 配置监控和告警
4. 设置定期备份
