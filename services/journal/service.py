"""
Journal Service
判断记录服务 - PRD 3.3 判断记录与到期复盘
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from database.db_factory import DatabaseFactory
from schemas.watchlist import WatchlistItemSummary
from services.journal.evaluator import evaluate_journal_conditions
from services.journal.failure_reasons import (
    failure_reason_label,
    normalize_failure_reason,
)
from services.watchlist import watchlist_service
from services.user_service import UserService
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
        self.user_service = UserService()

    def get_journal_state(self, user_id: str) -> Dict[str, Any]:
        is_temporary = self.user_service.is_temporary_user(user_id)
        return {
            "is_temporary": is_temporary,
            "trial_message": "当前判断日记仅临时保存在本设备，绑定后可长期追踪与复盘。" if is_temporary else None,
        }
    
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
            "status": "active",
            **self.get_journal_state(user_id),
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

    def delete_record(self, record_id: str, user_id: str) -> bool:
        """删除判断记录（硬删除）"""
        if not record_id or not user_id:
            return False
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM judgments WHERE id = ? AND user_id = ?",
                (record_id, user_id),
            )
            deleted = cursor.rowcount > 0
            conn.commit()
        return deleted

    def get_records_count(self, user_id: str) -> int:
        """获取用户记录数量"""
        if not user_id:
            return 0
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM judgments WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        if not row:
            return 0
        try:
            return int(row["c"])
        except Exception:
            return int(row[0])

    def get_single_anchor_id(self) -> Optional[str]:
        """若仅存在一个 anchor，则返回其 ID，否则返回 None"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT anchor_id FROM anchors ORDER BY created_at DESC LIMIT 2"
            )
            rows = cursor.fetchall()
        if not rows or len(rows) != 1:
            return None
        row = rows[0]
        try:
            return row["anchor_id"]
        except Exception:
            return row[0]

    def migrate_user_records(self, from_user_id: str, to_user_id: str) -> int:
        """
        Migrate journal records from one user_id to another.

        This is used to merge anonymous records into an anchor account.
        Idempotent: safe to call multiple times.
        """
        if not from_user_id or not to_user_id or from_user_id == to_user_id:
            return 0

        now = datetime.utcnow().isoformat() + 'Z'
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE judgments
                SET user_id = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (to_user_id, now, from_user_id),
            )
            updated = cursor.rowcount
            conn.commit()

        if updated > 0:
            logger.info(f"[Journal] Migrated {updated} records: {from_user_id[:8]}... -> {to_user_id[:8]}...")

        return updated

    def get_review_stats(self, user_id: str, limit: int = 30) -> Dict[str, Any]:
        """Return a compact review scorecard for the user's recent judgments."""
        limit = min(max(int(limit or 30), 1), 200)
        outcome_counts = {"supported": 0, "falsified": 0, "uncertain": 0}
        selected_candidate_counts: Dict[str, int] = {}
        actual_path_counts: Dict[str, int] = {}
        failure_reason_counts: Dict[str, int] = {}
        reviewed_count = 0
        pending_count = 0

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, candidate, status, review, created_at
                FROM judgments
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()

        for row in rows:
            candidate = str(row.get("candidate") or "").upper()
            if candidate:
                selected_candidate_counts[candidate] = selected_candidate_counts.get(candidate, 0) + 1

            if row.get("status") != "reviewed":
                pending_count += 1
                continue

            review = self._parse_review(row.get("review"))
            if not review:
                pending_count += 1
                continue

            outcome = review.get("outcome")
            if outcome not in outcome_counts:
                outcome = "uncertain"
            outcome_counts[outcome] += 1
            reviewed_count += 1

            system_evaluation = review.get("system_evaluation") or {}
            actual_path = system_evaluation.get("actual_path")
            if actual_path:
                actual_key = str(actual_path).upper()
                actual_path_counts[actual_key] = actual_path_counts.get(actual_key, 0) + 1

            failure_reason = normalize_failure_reason(review.get("failure_reason"))
            if failure_reason:
                failure_reason_counts[failure_reason] = failure_reason_counts.get(failure_reason, 0) + 1

        support_rate = None
        if reviewed_count > 0:
            support_rate = round(outcome_counts["supported"] / reviewed_count * 100, 2)

        return {
            "limit": limit,
            "sample_size": len(rows),
            "reviewed_count": reviewed_count,
            "pending_count": pending_count,
            "outcome_counts": outcome_counts,
            "support_rate": support_rate,
            "selected_candidate_counts": selected_candidate_counts,
            "actual_path_counts": actual_path_counts,
            "most_common_actual_path": self._most_common_key(actual_path_counts),
            "failure_reason_counts": failure_reason_counts,
            "most_common_failure_reason": self._most_common_key(failure_reason_counts),
            "most_common_failure_reason_label": failure_reason_label(
                self._most_common_key(failure_reason_counts)
            ),
        }

    def _parse_review(self, raw_review: Any) -> Optional[Dict[str, Any]]:
        if not raw_review:
            return None
        if isinstance(raw_review, dict):
            return raw_review
        if isinstance(raw_review, str):
            try:
                return json.loads(raw_review)
            except Exception:
                try:
                    import ast
                    parsed = ast.literal_eval(raw_review)
                    return parsed if isinstance(parsed, dict) else None
                except Exception:
                    return None
        return None

    def _most_common_key(self, counts: Dict[str, int]) -> Optional[str]:
        if not counts:
            return None
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    
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
                if isinstance(row['review'], str):
                    try:
                        review = json.loads(row['review'])
                    except Exception:
                        import ast
                        review = ast.literal_eval(row['review'])
                else:
                    review = row['review']
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
            "evaluation_preview": constraints.get("evaluation_preview") if isinstance(constraints, dict) else None,
            "review": review
        }
    
    def run_due_check(self) -> int:
        """
        检查到期记录并更新状态
        
        将已过验证期的 active 记录标记为 due
        """
        now = datetime.utcnow()
        now_iso = now.isoformat() + 'Z'

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM judgments
                WHERE status = 'active' AND validation_date < ?
                """,
                (now_iso,),
            )
            rows = cursor.fetchall()

            updated = 0
            for row in rows:
                record_id = row.get("id")
                cursor.execute(
                    """
                    UPDATE judgments
                    SET status = 'due', updated_at = ?
                    WHERE id = ? AND status = 'active'
                    """,
                    (now_iso, record_id),
                )
                if cursor.rowcount > 0:
                    updated += 1
            conn.commit()

        for row in rows:
            try:
                self._ensure_evaluation_preview(row)
            except Exception as e:
                logger.warning(f"[Journal] Failed to pre-evaluate due record {row.get('id')}: {e}")
        
        if updated > 0:
            logger.info(f"[Journal] Marked {updated} records as due")
        
        return updated

    def force_due_record(self, record_id: str) -> Dict[str, Any]:
        """
        Admin-only helper: force an active judgment record into due status.

        This is intentionally narrow for production testing of the review loop:
        it never reopens reviewed/archived records.
        """
        now = datetime.utcnow()
        forced_validation_date = (now - timedelta(seconds=1)).isoformat() + 'Z'
        updated_at = now.isoformat() + 'Z'

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, status, validation_date FROM judgments WHERE id = ?",
                (record_id,),
            )
            row = cursor.fetchone()

            if not row:
                return {"ok": False, "error": "Record not found"}

            previous_status = row.get("status")
            if previous_status != "active":
                return {
                    "ok": False,
                    "id": record_id,
                    "status": previous_status,
                    "previous_status": previous_status,
                    "reason": "Only active records can be forced due",
                }

            cursor.execute(
                """
                UPDATE judgments
                SET status = 'due', validation_date = ?, updated_at = ?
                WHERE id = ? AND status = 'active'
                """,
                (forced_validation_date, updated_at, record_id),
            )
            conn.commit()

        return {
            "ok": True,
            "id": record_id,
            "status": "due",
            "previous_status": previous_status,
            "validation_date": forced_validation_date,
        }
    
    def review_record(
        self,
        record_id: str,
        user_id: str,
        notes: Optional[str] = None,
        lesson: Optional[str] = None,
        failure_reason: Optional[str] = None,
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
        row = self._get_record_row(record_id, user_id)
        
        if not row:
            return {"error": "Record not found"}
        
        # 自动评估：优先使用到期时生成的系统预判卷，避免重复拉取行情。
        preview = self._get_evaluation_preview(row)
        if preview:
            system_evaluation = preview
            outcome = system_evaluation.get("outcome", "uncertain")
            triggers = self._evaluation_to_triggers(system_evaluation)
        else:
            outcome, triggers, system_evaluation = self._auto_evaluate(row)
        
        review = {
            "reviewed_at": now.isoformat() + 'Z',
            "outcome": outcome,
            "triggers": triggers,
            "system_evaluation": system_evaluation,
            "notes": notes,
            "lesson": lesson,
            "failure_reason": normalize_failure_reason(failure_reason),
        }
        
        # 更新记录
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE judgments
                SET status = 'reviewed', review = ?, updated_at = ?
                WHERE id = ?
            """, (json.dumps(review, ensure_ascii=False), now.isoformat() + 'Z', record_id))
            conn.commit()
        
        return {
            "id": record_id,
            "status": "reviewed",
            "review": review
        }

    def evaluate_record(self, record_id: str, user_id: str) -> Dict[str, Any]:
        """Preview the system evaluation without marking the record as reviewed."""
        row = self._get_record_row(record_id, user_id)
        if not row:
            return {"error": "Record not found"}

        preview = self._get_evaluation_preview(row)
        if preview:
            return preview

        _outcome, _triggers, system_evaluation = self._auto_evaluate(row)
        return system_evaluation

    def _get_record_row(self, record_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM judgments
                WHERE id = ? AND user_id = ?
            """, (record_id, user_id))
            return cursor.fetchone()

    def _ensure_evaluation_preview(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self._get_evaluation_preview(row):
            return self._get_evaluation_preview(row)

        _outcome, _triggers, evaluation = self._auto_evaluate(row)
        evaluation = dict(evaluation)
        evaluation.setdefault("outcome", _outcome)
        evaluation["evaluated_at"] = datetime.utcnow().isoformat() + 'Z'

        constraints = self._parse_constraints(row.get("constraints"))
        constraints["evaluation_preview"] = evaluation

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE judgments
                SET constraints = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(constraints, ensure_ascii=False),
                    datetime.utcnow().isoformat() + 'Z',
                    row.get("id"),
                ),
            )
            conn.commit()

        return evaluation

    def _get_evaluation_preview(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        constraints = self._parse_constraints(row.get("constraints"))
        preview = constraints.get("evaluation_preview")
        return preview if isinstance(preview, dict) else None

    def _parse_constraints(self, raw_constraints: Any) -> Dict[str, Any]:
        if isinstance(raw_constraints, dict):
            return dict(raw_constraints)
        if isinstance(raw_constraints, str) and raw_constraints.strip():
            try:
                parsed = json.loads(raw_constraints)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}
    
    def _auto_evaluate(self, row: Dict) -> tuple:
        """
        自动评估
        
        返回 (outcome, triggers)
        """
        import json
        from services.stock_data_provider import StockDataProvider

        constraints = self._parse_constraints(row.get('constraints'))

        candidate_descriptions = self._extract_candidate_descriptions(constraints)
        if not candidate_descriptions:
            system_evaluation = {
                "outcome": "uncertain",
                "summary": "缺少候选条件原文，无法自动判卷。之后保存的新判断会记录 A/B/C 条件用于验证。",
                "actual_path": None,
                "selected_condition": {"status": "missing_condition"},
                "candidate_results": {},
            }
            return "uncertain", [], system_evaluation

        try:
            stock_code = self._normalize_stock_code(row.get('stock_code', ''))
            start_date = self._date_to_yyyymmdd(constraints.get('snapshot_time') or row.get('created_at'))
            end_date = self._date_to_yyyymmdd(row.get('validation_date') or datetime.utcnow().isoformat())
            price_data = StockDataProvider()._get_stock_data_sync(
                stock_code,
                market_type='A',
                start_date=start_date,
                end_date=end_date,
            )
            evaluation = evaluate_journal_conditions(
                selected_candidate=row.get('candidate'),
                candidate_descriptions=candidate_descriptions,
                price_data=price_data,
            )
        except Exception as e:
            logger.error(f"[Journal] Auto evaluation failed for {row.get('id')}: {e}")
            evaluation = {
                "outcome": "uncertain",
                "actual_path": None,
                "summary": f"自动判卷失败：{str(e)}",
                "selected_condition": {"status": "evaluation_error"},
                "candidate_results": {},
            }

        triggers = self._evaluation_to_triggers(evaluation)
        return evaluation.get("outcome", "uncertain"), triggers, evaluation

    def _extract_candidate_descriptions(self, constraints: Dict[str, Any]) -> Dict[str, str]:
        candidates = constraints.get("candidates")
        if isinstance(candidates, dict):
            return {
                str(option_id).upper(): str(description)
                for option_id, description in candidates.items()
                if option_id and description
            }
        if isinstance(candidates, list):
            result = {}
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                option_id = candidate.get("option_id") or candidate.get("id")
                description = candidate.get("description")
                if option_id and description:
                    result[str(option_id).upper()] = str(description)
            return result
        return {}

    def _evaluation_to_triggers(self, evaluation: Dict[str, Any]) -> List[Dict[str, str]]:
        triggers = []
        selected = evaluation.get("selected_condition") or {}
        price = selected.get("price") or {}
        volume = selected.get("volume") or {}
        if price:
            triggers.append({
                "check_id": "price_condition",
                "result": "triggered" if price.get("triggered") else "passed",
                "detail": self._format_price_trigger(price),
            })
        if volume:
            triggers.append({
                "check_id": "volume_condition",
                "result": "triggered" if volume.get("triggered") else "passed",
                "detail": self._format_volume_trigger(volume),
            })
        return triggers

    def _format_price_trigger(self, price: Dict[str, Any]) -> str:
        trigger_type = price.get("type")
        if trigger_type == "breakout":
            return f"突破价 {price.get('threshold')}，最高价 {price.get('max_price')}"
        if trigger_type == "breakdown":
            return f"跌破价 {price.get('threshold')}，最低价 {price.get('min_price')}"
        if trigger_type == "range":
            return f"区间 {price.get('lower')}-{price.get('upper')}，要求 {price.get('required_days')} 个交易日"
        return "价格条件"

    def _format_volume_trigger(self, volume: Dict[str, Any]) -> str:
        if volume.get("type") == "above_ma20":
            return f"量能要求 {volume.get('required_consecutive_days')} 日高于 20 日均量 {volume.get('multiple')} 倍，最高 {volume.get('max_ratio')} 倍"
        if volume.get("type") == "within_ma20":
            return f"量能要求回落至 20 日均量 {volume.get('lower')}-{volume.get('upper')} 倍"
        return volume.get("reason") or "量能条件"

    def _normalize_stock_code(self, stock_code: str) -> str:
        return str(stock_code or "").split(".")[0]

    def _date_to_yyyymmdd(self, value: Any) -> str:
        if not value:
            return datetime.utcnow().strftime("%Y%m%d")
        if hasattr(value, "strftime"):
            return value.strftime("%Y%m%d")
        text = str(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text).strftime("%Y%m%d")
        except Exception:
            return text[:10].replace("-", "")
    
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
