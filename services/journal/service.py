"""
Journal Service
判断记录服务 - PRD 3.3 判断记录与到期复盘
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from database.db_factory import DatabaseFactory
from schemas.watchlist import WatchlistItemSummary
from services.watchlist import watchlist_service
from utils.logger import get_logger

logger = get_logger()


class JournalService:
    """
    判断记录服务
    
    职责:
    - 创建判断记录 (snapshot)
    - 查询判断记录
    - 到期检查
    - 自动评估 (supported/falsified/uncertain)
    - 复盘/归档
    """
    
    def __init__(self):
        self.db = DatabaseFactory()
    
    def create_record(
        self,
        user_id: str,
        ts_code: str,
        selected_candidate: str,
        selected_premises: List[str],
        selected_risk_checks: List[str],
        constraints: Dict[str, Any],
        validation_period_days: int = 7
    ) -> Dict[str, Any]:
        """
        创建判断记录
        
        PRD 3.2.2: JudgementRecord 包含 snapshot
        """
        now = datetime.utcnow()
        asof = now.strftime('%Y-%m-%d')
        due_at = now + timedelta(days=validation_period_days)
        
        record_id = f"jr_{uuid.uuid4().hex[:12]}"
        
        # 生成快照
        try:
            summary = watchlist_service._generate_single_summary(ts_code, asof)
            snapshot = {
                "watchlist_summary": summary.model_dump(),
                "enhancements_key": self._extract_enhancements_key(summary)
            }
        except Exception as e:
            logger.error(f"Failed to create snapshot for {ts_code}: {e}")
            snapshot = {"error": str(e)}
        
        # 插入记录 (使用现有 judgments 表)
        try:
            import json
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO judgments (
                        id, user_id, stock_code, candidate, 
                        selected_premises, selected_risk_checks,
                        constraints, snapshot,
                        validation_date, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_id,
                    user_id,
                    ts_code,
                    selected_candidate,
                    json.dumps(selected_premises, ensure_ascii=False),
                    json.dumps(selected_risk_checks, ensure_ascii=False),
                    json.dumps(constraints, ensure_ascii=False),
                    json.dumps(snapshot, ensure_ascii=False),
                    due_at.isoformat() + 'Z',
                    'active',
                    now.isoformat() + 'Z',
                    now.isoformat() + 'Z'
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to insert judgment record: {e}")
            logger.error(f"Data types: premises={type(selected_premises)}, risks={type(selected_risk_checks)}")
            raise e
        
        return {
            "id": record_id,
            "ts_code": ts_code,
            "candidate": selected_candidate,
            "validation_period_days": validation_period_days,
            "due_at": due_at.isoformat() + 'Z',
            "status": "active"
        }
    
    def _extract_enhancements_key(self, summary: WatchlistItemSummary) -> Dict:
        """提取关键增强数据"""
        return {
            "excess_20d": summary.relative_strength.excess_20d_vs_000300,
            "flow_label": summary.capital_flow.label,
            "event_count_30d": summary.events.event_count_30d
        }
    
    def get_records(
        self,
        user_id: str,
        status: Optional[str] = None,
        ts_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """获取判断记录列表"""
        conditions = ["user_id = ?"]
        params = [user_id]
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if ts_code:
            conditions.append("stock_code = ?")
            params.append(ts_code)
        
        offset = (page - 1) * page_size
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM judgments
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, params + [page_size, offset])
            rows = cursor.fetchall()
        
        return [self._row_to_record(row) for row in rows]
    
    def _row_to_record(self, row: Dict) -> Dict[str, Any]:
        """转换数据库行为记录"""
        import json
        
        validation_date = row.get('validation_date')
        days_left = None
        
        if validation_date:
            try:
                val_dt = datetime.fromisoformat(validation_date.replace('Z', '+00:00'))
                days_left = (val_dt.replace(tzinfo=None) - datetime.utcnow()).days
                if days_left < 0:
                    days_left = 0
            except:
                pass
        
        # Parse JSON fields
        selected_premises = []
        selected_risk_checks = []
        constraints = {}
        snapshot = {}
        review = None
        
        try:
            if row.get('selected_premises'):
                selected_premises = json.loads(row['selected_premises'])
        except:
            pass
        
        try:
            if row.get('selected_risk_checks'):
                selected_risk_checks = json.loads(row['selected_risk_checks'])
        except:
            pass
        
        try:
            if row.get('constraints'):
                constraints = json.loads(row['constraints'])
        except:
            pass
            
        try:
            if row.get('snapshot'):
                snapshot = json.loads(row['snapshot'])
        except:
            pass
            
        try:
            if row.get('review'):
                review = eval(row['review']) if isinstance(row['review'], str) else row['review']
        except:
            review = row.get('review')
        
        return {
            "id": row.get('id'),
            "user_id": row.get('user_id'),
            "ts_code": row.get('stock_code'),
            "candidate": row.get('candidate'),
            "selected_premises": selected_premises,
            "selected_risk_checks": selected_risk_checks,
            "constraints": constraints,
            "snapshot": snapshot,
            "validation_date": validation_date,
            "days_left": days_left,
            "status": row.get('status'),
            "created_at": row.get('created_at'),
            "review": review
        }
    
    def run_due_check(self) -> int:
        """
        检查到期记录并更新状态
        
        将已过验证期的 active 记录标记为 due
        """
        now = datetime.utcnow().isoformat() + 'Z'
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE judgments
                SET status = 'due', updated_at = ?
                WHERE status = 'active' AND validation_date < ?
            """, (now, now))
            
            updated = cursor.rowcount
            conn.commit()
        
        if updated > 0:
            logger.info(f"[Journal] Marked {updated} records as due")
        
        return updated
    
    def review_record(
        self,
        record_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        复盘判断记录
        
        PRD 3.3 自动评估规则:
        - 任一关键失效检查触发 → falsified
        - 满足检查比例>=60%且无关键失效 → supported
        - 否则 → uncertain
        """
        now = datetime.utcnow()
        
        # 获取记录
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM judgments
                WHERE id = ? AND user_id = ?
            """, (record_id, user_id))
            row = cursor.fetchone()
        
        if not row:
            return {"error": "Record not found"}
        
        # 自动评估
        outcome, triggers = self._auto_evaluate(row)
        
        review = {
            "reviewed_at": now.isoformat() + 'Z',
            "outcome": outcome,
            "triggers": triggers,
            "notes": notes
        }
        
        # 更新记录
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE judgments
                SET status = 'reviewed', review = ?, updated_at = ?
                WHERE id = ?
            """, (str(review), now.isoformat() + 'Z', record_id))
            conn.commit()
        
        return {
            "id": record_id,
            "status": "reviewed",
            "review": review
        }
    
    def _auto_evaluate(self, row: Dict) -> tuple:
        """
        自动评估
        
        返回 (outcome, triggers)
        """
        # 简化实现：暂时返回 uncertain
        # TODO: 实现完整的评估逻辑
        triggers = []
        outcome = "uncertain"
        
        # 检查是否有关键失效
        # 这需要获取当前价格与判断时的快照进行对比
        
        return outcome, triggers
    
    def get_due_count(self, user_id: str) -> int:
        """获取待复盘记录数量"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM judgments
                WHERE user_id = ? AND status = 'due'
            """, (user_id,))
            row = cursor.fetchone()
        
        return row.get('cnt', 0) if row else 0
    
    def get_active_for_stock(self, ts_code: str) -> Optional[Dict]:
        """获取标的的活跃判断"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM judgments
                WHERE stock_code = ? AND status IN ('active', 'pending')
                ORDER BY created_at DESC
                LIMIT 1
            """, (ts_code,))
            row = cursor.fetchone()
        
        if row:
            return self._row_to_record(row)
        return None


# 单例
journal_service = JournalService()
