# 判断追踪系统 v0.1 - 快速启动指南

## 🚀 快速启动

### 1. 数据库初始化
```bash
cd /Users/ck/Desktop/Project/stock-scanner-baseline
sqlite3 data/stocks.db < migrations/001_create_judgments_tables.sql
```

### 2. 启动后端
```bash
python3 web_server.py
# 访问: http://localhost:8888/docs
```

### 3. 启动前端
```bash
cd frontend
npm run dev
# 访问: http://localhost:5173
```

---

## 📝 测试清单

### 后端测试

```bash
# 1. 单元测试
python3 -m pytest tests/test_judgment_verifier.py -v

# 2. 导入测试
python3 -c "from services.verification_cache import verification_cache; print('✓ OK')"

# 3. API 测试（需先启动服务器）
# 保存判断
curl -c cookies.txt -X POST http://localhost:8888/api/v1/judgments \
  -H "Content-Type: application/json" \
  -d '{"snapshot": {...}}'

# 获取判断列表
curl -b cookies.txt http://localhost:8888/api/v1/me/judgments

# 获取判断详情
curl http://localhost:8888/api/v1/judgments/{judgment_id}
```

### 前端测试

1. **保存判断**
   - 分析股票 → 点击"保存判断" → 查看提示

2. **查看列表**
   - 导航栏 → "我的判断" → 查看列表

3. **查看详情**
   - 列表 → "查看详情" → 查看弹窗

---

## 📊 验收标准

| 类别 | 通过率 |
|------|--------|
| A. 身份与数据落库 | 3/3 ✅ |
| B. API 正确性 | 3/3 ✅ |
| C. 验证逻辑 | 3/3 ✅ |
| D. 缓存与性能 | 1/1 ✅ |
| E. 前端闭环 | 3/3 ✅ |
| F. 防跑偏检查 | 2/2 ✅ |
| **总计** | **15/15 (100%)** ✅ |

---

## 📁 关键文件

**后端:**
- `routes/judgments.py` - API 路由
- `services/judgment_service.py` - CRUD 服务
- `services/judgment_verifier.py` - 验证逻辑
- `services/verification_cache.py` - 缓存服务

**前端:**
- `components/MyJudgments.vue` - 判断列表
- `components/StockCard.vue` - 保存按钮
- `services/api.ts` - API 客户端

**文档:**
- `docs/judgment_api_examples.md` - API 示例
- `docs/judgment_verifier_quick_ref.md` - 验证器参考

---

## ✅ 完成状态

所有功能已实现并通过验收！可以开始使用。
