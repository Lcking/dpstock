# Aguai 线上运维速查表

适用场景：`aguai.net` 生产环境日常更新、健康检查、数据备份、证书续签、故障排查。

默认部署目录示例：`/root/dpstock`

---

## 1. 日常更新

### 标准更新流程
```bash
cd /root/dpstock
git pull --ff-only origin main
docker compose -f docker-compose.prod.yml up -d --build app
docker compose -f docker-compose.prod.yml up -d nginx
docker compose -f docker-compose.prod.yml ps
```

### 如果改了 Nginx 配置
建议直接重建 `nginx` 容器，避免旧容器继续加载旧配置：

```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml stop nginx
docker compose -f docker-compose.prod.yml rm -f nginx
docker compose -f docker-compose.prod.yml up -d nginx
docker compose -f docker-compose.prod.yml ps
```

---

## 2. 快速健康检查

### 容器状态
```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml ps
```

期望状态：
- `app` 为 `healthy`
- `nginx` 为 `healthy`
- `certbot` 为 `Up`

### 本机健康检查
```bash
curl -s http://127.0.0.1/health
curl -s https://aguai.net/api/need_login
curl -s "https://aguai.net/api/search_global?keyword=600519&market_type=A"
```

期望结果：
- `http://127.0.0.1/health` 返回 `healthy`
- `api/need_login` 返回 JSON
- A 股搜索返回带股票名称的结果，例如 `贵州茅台 (600519)`

---

## 3. 常用日志命令

### 查看最近日志
```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml logs --tail=100 app
docker compose -f docker-compose.prod.yml logs --tail=100 nginx
docker compose -f docker-compose.prod.yml logs --tail=100 certbot
```

### 实时跟日志
```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml logs -f app
docker compose -f docker-compose.prod.yml logs -f nginx
```

---

## 4. 数据与配置备份

建议在大版本更新前执行一次完整备份。

```bash
cd /root/dpstock
TS=$(date +%F-%H%M%S)
BACKUP_DIR="$HOME/backups/aguai/$TS"
mkdir -p "$BACKUP_DIR"

tar -czf "$BACKUP_DIR/data-backup.tar.gz" data
tar -czf "$BACKUP_DIR/nginx-certbot-backup.tar.gz" nginx certbot
cp -f .env "$BACKUP_DIR/.env.backup"
cp -f docker-compose.prod.yml "$BACKUP_DIR/docker-compose.prod.yml.backup"
git rev-parse HEAD > "$BACKUP_DIR/current_git_commit.txt"
git log -1 --oneline > "$BACKUP_DIR/current_git_commit_oneline.txt"
```

重点保护目录：
- `data/`
- `certbot/conf/`
- `.env`

---

## 5. 证书检查与续签

### 查看当前证书
```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml exec certbot certbot certificates
```

### 验证自动续签链路
```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml exec certbot certbot renew --dry-run
```

如果输出包含：
```text
Congratulations, all simulated renewals succeeded
```
说明续签链路正常。

### 手动续签并 reload nginx
```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml exec -T certbot certbot renew --webroot -w /var/www/certbot --quiet
docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload
```

---

## 6. cron 兜底任务

建议保留宿主机层的兜底续签任务。

### 查看 cron 状态
```bash
sudo systemctl status cron
crontab -l
```

### 推荐 crontab
```bash
15 3 * * * cd /root/dpstock && docker compose -f docker-compose.prod.yml exec -T certbot certbot renew --webroot -w /var/www/certbot --quiet && docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload >> /var/log/aguai-cert-renew.log 2>&1
```

作用：
- 每天凌晨 3:15 尝试续签
- 成功后 reload nginx
- 将日志写入 `/var/log/aguai-cert-renew.log`

---

## 7. 常见故障排查

### 站点打不开
按顺序检查：

```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 nginx
docker compose -f docker-compose.prod.yml logs --tail=100 app
docker compose -f docker-compose.prod.yml exec certbot certbot certificates
```

常见原因：
- `nginx` 容器未启动
- 证书目录丢失
- `nginx` 配置未重载
- 80/443 端口未正常监听

### 搜索只有代码没有名称
先检查：

```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml exec app env | grep TUSHARE
docker compose -f docker-compose.prod.yml logs --tail=100 app
curl -s "https://aguai.net/api/search_global?keyword=600519&market_type=A"
```

关注日志关键词：
- `akshare 获取A股列表失败`
- `Tushare Client initialized successfully`
- `tushare 成功加载`

### 数据增强显示“数据不可用”
高优先级检查：

```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml exec app env | grep TUSHARE
grep TUSHARE_TOKEN .env
```

如果 `.env` 有值但容器里没有，说明 `docker-compose.prod.yml` 没有透传 `TUSHARE_TOKEN`。

### nginx 显示 unhealthy
先检查：

```bash
curl -s http://127.0.0.1/health
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=50 nginx
```

如果业务正常但容器 unhealthy，优先怀疑健康检查路径和实际 Nginx 配置不一致。

---

## 8. 配置一致性检查

### 检查生产 compose 是否透传关键环境变量
```bash
grep -n "TUSHARE_TOKEN" docker-compose.prod.yml
grep -n "DB_PATH" docker-compose.prod.yml
grep -n "DATA_DIR" .env
```

### 检查 Nginx 当前加载配置
```bash
cd /root/dpstock
grep -n "location = /health" nginx/nginx.conf
docker compose -f docker-compose.prod.yml exec nginx sh -c 'sed -n "1,40p" /etc/nginx/conf.d/default.conf'
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```

---

## 9. 回滚最小步骤

如果更新后出现明显问题：

```bash
cd /root/dpstock
git log --oneline -5
git checkout <上一稳定提交>
docker compose -f docker-compose.prod.yml up -d --build app
docker compose -f docker-compose.prod.yml up -d nginx
docker compose -f docker-compose.prod.yml ps
```

如果涉及数据或证书问题，再从最近的备份目录恢复：
- `data-backup.tar.gz`
- `nginx-certbot-backup.tar.gz`

---

## 10. 当前已验证项

本手册对应的环境已验证通过：
- `app` 健康检查正常
- `nginx` 健康检查正常
- HTTPS 正常访问
- A 股搜索返回股票名称
- `TUSHARE_TOKEN` 成功透传到生产容器
- `certbot renew --dry-run` 成功
- 手动 `renew + nginx reload` 成功

---

## 11. 低优先级待整理项

当前不影响业务，但后续可以优化：
- 将 `listen 443 ssl http2;` 升级为新版 Nginx 推荐写法
- 评估是否保留 `ssl_stapling` 配置，减少非阻塞 warning

