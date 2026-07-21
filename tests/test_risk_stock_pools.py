"""风险股池扩展：连续涨跌停 / 5%·9%涨幅池 / 创业板大波动 / ST征兆。"""
import json
import sqlite3
from pathlib import Path

import pandas as pd

from database.db_factory import DatabaseFactory
from scripts.run_migrations import run_migrations
from services.risk_stock_collector import RiskStockCollector, is_chinext
from services.risk_stock_service import RiskStockService


def _run_all_migrations(db_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DB_PATH", str(db_path))
    run_migrations()


# ------------------------------------------------------------------
# 分类规则
# ------------------------------------------------------------------

def test_two_day_limit_up_or_down_is_high_risk():
    service = RiskStockService.__new__(RiskStockService)

    up2 = service._classify_row(
        "20260721",
        {"ts_code": "002001.SZ", "name": "二连板示例", "limit_up_days": 2},
        source="unit-test",
    )
    assert up2 is not None
    assert up2["risk_level"] == "high"
    assert "连续涨停" in up2["tags"]
    assert "三连板" not in up2["tags"]

    down2 = service._classify_row(
        "20260721",
        {"ts_code": "002002.SZ", "name": "二连跌停示例", "limit_down_days": 2},
        source="unit-test",
    )
    assert down2 is not None
    assert down2["risk_level"] == "high"
    assert "连续跌停" in down2["tags"]
    assert down2["limit_down_days"] == 2

    one_day = service._classify_row(
        "20260721",
        {"ts_code": "002003.SZ", "name": "单日涨停", "limit_up_days": 1},
        source="unit-test",
    )
    assert one_day is None


def test_gain_pools_and_chinext_swing_classification():
    service = RiskStockService.__new__(RiskStockService)

    gain5 = service._classify_row(
        "20260721",
        {
            "ts_code": "600100.SH",
            "name": "涨5示例",
            "pct_chg": 5.6,
            "pools": ["5%涨幅池"],
            "pool_reasons": ["当日涨幅 5.60%，达到 5% 档"],
        },
        source="unit-test",
    )
    assert gain5["risk_level"] == "low"
    assert "5%涨幅池" in gain5["tags"]
    assert gain5["pct_chg"] == 5.6

    gain9 = service._classify_row(
        "20260721",
        {
            "ts_code": "600200.SH",
            "name": "涨9示例",
            "pct_chg": 9.4,
            "pools": ["9%涨幅池"],
            "pool_reasons": ["当日涨幅 9.40%，达到 9% 档"],
        },
        source="unit-test",
    )
    assert gain9["risk_level"] == "medium"
    assert "9%涨幅池" in gain9["tags"]

    cx = service._classify_row(
        "20260721",
        {
            "ts_code": "300300.SZ",
            "name": "创业板大波动示例",
            "pct_chg": -16.2,
            "pools": ["创业板大波动"],
            "pool_reasons": ["创业板当日涨跌幅 -16.20%，波动达 ±15%"],
        },
        source="unit-test",
    )
    assert cx["risk_level"] == "medium"
    assert "创业板大波动" in cx["tags"]

    omen = service._classify_row(
        "20260721",
        {
            "ts_code": "600300.SH",
            "name": "征兆示例",
            "pools": ["ST征兆"],
            "pool_reasons": ["最近年报业绩预告为「续亏」（2025年报）"],
        },
        source="unit-test",
    )
    assert omen["risk_level"] == "medium"
    assert "ST征兆" in omen["tags"]
    assert "续亏" in omen["reason"]


# ------------------------------------------------------------------
# 回落移除（替换式刷新）
# ------------------------------------------------------------------

def test_refresh_removes_stocks_that_fell_out_of_pools(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_pool_fallback.db"
    _run_all_migrations(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    service = RiskStockService(db_path=str(db_path))

    service.refresh_from_rows(
        "20260721",
        [
            {"ts_code": "600100.SH", "name": "涨5示例", "pct_chg": 5.6,
             "pools": ["5%涨幅池"], "pool_reasons": ["当日涨幅 5.60%，达到 5% 档"]},
            {"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0},
        ],
        source="unit-test",
    )
    codes = {item["ts_code"] for item in service.get_items(trade_date="20260721")}
    assert codes == {"600100.SH", "600001.SH"}

    # 第二次刷新：涨5示例回落到 4%，不再进池 → 应被移除
    service.refresh_from_rows(
        "20260721",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="unit-test",
    )
    codes = {item["ts_code"] for item in service.get_items(trade_date="20260721")}
    assert codes == {"600001.SH"}


def test_refresh_with_empty_rows_keeps_existing_data(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_pool_empty_guard.db"
    _run_all_migrations(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    service = RiskStockService(db_path=str(db_path))
    service.refresh_from_rows(
        "20260721",
        [{"ts_code": "600001.SH", "name": "ST示例", "limit_up_days": 0}],
        source="unit-test",
    )
    # 数据源故障时返回空行，不应清空当日已有数据
    service.refresh_from_rows("20260721", [], source="unit-test")
    assert len(service.get_items(trade_date="20260721")) == 1


# ------------------------------------------------------------------
# 收集器
# ------------------------------------------------------------------

def _spot_df():
    return pd.DataFrame(
        [
            {"代码": "600100", "名称": "涨5示例", "涨跌幅": 5.6},
            {"代码": "600200", "名称": "涨9示例", "涨跌幅": 9.4},
            {"代码": "300300", "名称": "创业板暴涨", "涨跌幅": 16.8},
            {"代码": "301400", "名称": "创业板暴跌", "涨跌幅": -15.3},
            {"代码": "000500", "名称": "普通股票", "涨跌幅": 2.1},
            {"代码": "300500", "名称": "创业板普通", "涨跌幅": 7.2},
        ]
    )


def test_collector_builds_spot_pools(monkeypatch):
    collector = RiskStockCollector.__new__(RiskStockCollector)
    monkeypatch.setattr(RiskStockCollector, "_fetch_spot", lambda self, d=None: _spot_df())

    rows = collector._collect_spot_pool_rows()
    by_code = {row["ts_code"]: row for row in rows}

    assert by_code["600100.SH"]["pools"] == ["5%涨幅池"]
    assert by_code["600200.SH"]["pools"] == ["9%涨幅池"]
    # 创业板暴涨 16.8%：同时命中大波动 + 9% 档
    assert set(by_code["300300.SZ"]["pools"]) == {"创业板大波动", "9%涨幅池"}
    # 创业板暴跌 -15.3%：只命中大波动
    assert by_code["301400.SZ"]["pools"] == ["创业板大波动"]
    # 未达标的不进池
    assert "000500.SZ" not in by_code
    # 创业板 7.2% 只进 5% 档
    assert by_code["300500.SZ"]["pools"] == ["5%涨幅池"]


def test_collector_limit_down_rows(monkeypatch):
    dt_df = pd.DataFrame(
        [
            {"代码": "600900", "名称": "二连跌停", "连续跌停": 2, "所属行业": "地产"},
            {"代码": "600901", "名称": "单日跌停", "连续跌停": 1, "所属行业": "地产"},
        ]
    )
    collector = RiskStockCollector.__new__(RiskStockCollector)
    monkeypatch.setattr(RiskStockCollector, "_fetch_dt_pool", lambda self, d: dt_df)

    rows = collector._collect_limit_down_rows("20260721")
    assert len(rows) == 1
    assert rows[0]["ts_code"] == "600900.SH"
    assert rows[0]["limit_down_days"] == 2


def test_collector_limit_up_threshold_is_two(monkeypatch):
    zt_df = pd.DataFrame(
        [
            {"代码": "000600", "名称": "二连板", "连板数": 2, "所属行业": "电子"},
            {"代码": "000601", "名称": "首板", "连板数": 1, "所属行业": "电子"},
        ]
    )
    collector = RiskStockCollector.__new__(RiskStockCollector)
    monkeypatch.setattr(RiskStockCollector, "_fetch_zt_pool", lambda self, d: zt_df)

    rows = collector._collect_limit_up_rows("20260721")
    assert len(rows) == 1
    assert rows[0]["ts_code"] == "000600.SZ"
    assert rows[0]["limit_up_days"] == 2


def test_spot_eastmoney_pages_stop_at_thresholds(monkeypatch):
    """排序分页：涨幅侧跌破 5% 即停，跌幅侧回到 -15% 以内即停。"""
    desc_pages = [
        [
            {"f12": "300643", "f14": "万通智控", "f3": 20.03},
            {"f12": "600200", "f14": "涨9示例", "f3": 9.4},
        ],
        [
            {"f12": "600100", "f14": "涨5示例", "f3": 5.6},
            {"f12": "000500", "f14": "普通股票", "f3": 4.9},  # 跌破 5% → 停止
        ],
        [
            {"f12": "999999", "f14": "不应到达", "f3": 4.0},
        ],
    ]
    asc_pages = [
        [
            {"f12": "301400", "f14": "创业板暴跌", "f3": -15.3},
            {"f12": "600900", "f14": "普通下跌", "f3": -9.9},  # 回到 -15% 以内 → 停止
        ],
    ]
    calls = {"desc": 0, "asc": 0}

    def fake_page(self, session, page, ascending):
        if ascending:
            calls["asc"] += 1
            return asc_pages[page - 1] if page <= len(asc_pages) else []
        calls["desc"] += 1
        return desc_pages[page - 1] if page <= len(desc_pages) else []

    monkeypatch.setattr(RiskStockCollector, "_fetch_spot_page", fake_page)
    monkeypatch.setattr(RiskStockCollector, "SPOT_PAGE_SIZE", 2)
    collector = RiskStockCollector.__new__(RiskStockCollector)
    df = collector._fetch_spot_eastmoney()

    codes = set(df["代码"])
    assert codes == {"300643", "600200", "600100", "301400"}
    assert calls["desc"] == 2  # 第 2 页触发早停，不翻第 3 页
    assert calls["asc"] == 1


def test_spot_falls_back_to_sina_when_eastmoney_fails(monkeypatch):
    """服务器上东财 push2 常被拒连，必须回退新浪而不是让涨幅池静默为空。"""
    sina_desc = [
        [
            {"code": "300643", "name": "万通智控", "changepercent": 20.03},
            {"code": "600200", "name": "涨9示例", "changepercent": 9.4},
            {"code": "830001", "name": "北交所示例", "changepercent": 9.0},  # 应被过滤
            {"code": "600100", "name": "涨5示例", "changepercent": 5.6},
            {"code": "000500", "name": "普通股票", "changepercent": 4.9},
        ],
    ]
    sina_asc = [
        [
            {"code": "301400", "name": "创业板暴跌", "changepercent": -15.3},
            {"code": "600900", "name": "普通下跌", "changepercent": -9.9},
        ],
    ]

    def boom(self):
        raise ConnectionError("push2 refused")

    def fake_sina_page(self, session, page, ascending):
        pages = sina_asc if ascending else sina_desc
        return pages[page - 1] if page <= len(pages) else []

    monkeypatch.setattr(RiskStockCollector, "_fetch_spot_eastmoney", boom)
    monkeypatch.setattr(RiskStockCollector, "_fetch_sina_page", fake_sina_page)

    collector = RiskStockCollector.__new__(RiskStockCollector)
    df = collector._fetch_spot()

    codes = set(df["代码"])
    assert codes == {"300643", "600200", "600100", "301400"}
    assert "830001" not in codes  # 北交所过滤

    # 走标准入口验证池子归属
    monkeypatch.setattr(RiskStockCollector, "_fetch_spot", lambda self, d=None: df)
    pool_rows = collector._collect_spot_pool_rows()
    pools = {row["ts_code"]: row["pools"] for row in pool_rows}
    assert pools["600200.SH"] == ["9%涨幅池"]
    assert pools["600100.SH"] == ["5%涨幅池"]
    assert "创业板大波动" in pools["301400.SZ"]


def test_spot_falls_back_to_tushare_daily_when_web_sources_fail(monkeypatch):
    """东财+新浪都失败时，收盘后用 tushare daily 兜底（积分接口，最稳）。"""
    daily_df = pd.DataFrame(
        [
            {"ts_code": "600200.SH", "pct_chg": 9.44},
            {"ts_code": "600100.SH", "pct_chg": 5.61},
            {"ts_code": "301400.SZ", "pct_chg": -15.33},
            {"ts_code": "000500.SZ", "pct_chg": 2.1},
            {"ts_code": "830001.BJ", "pct_chg": 9.9},  # 北交所过滤
        ]
    )

    class FakeTushare:
        is_available = True

        def ensure_initialized(self, log_missing_token=True):
            return None

        def query(self, api, **kwargs):
            assert api == "daily"
            assert kwargs.get("trade_date") == "20260721"
            return daily_df

    def boom(self, *args, **kwargs):
        raise ConnectionError("web source down")

    monkeypatch.setattr(RiskStockCollector, "_fetch_spot_eastmoney", boom)
    monkeypatch.setattr(RiskStockCollector, "_fetch_spot_sina", boom)
    monkeypatch.setattr("services.tushare.client.tushare_client", FakeTushare())
    monkeypatch.setattr(RiskStockCollector, "_build_name_map", lambda self: {"600200": "涨9示例"})

    collector = RiskStockCollector.__new__(RiskStockCollector)
    df = collector._fetch_spot("20260721")

    codes = set(df["代码"])
    assert "830001" not in codes
    by_code = df.set_index("代码")
    assert float(by_code.loc["600200", "涨跌幅"]) == 9.44
    assert by_code.loc["600200", "名称"] == "涨9示例"
    # 快照缺名时用代码兜底，不丢数据
    assert by_code.loc["600100", "名称"] == "600100"

    monkeypatch.setattr(RiskStockCollector, "_fetch_spot", lambda self, d=None: df)
    pool_rows = collector._collect_spot_pool_rows("20260721")
    pools = {row["ts_code"]: row["pools"] for row in pool_rows}
    assert pools["600200.SH"] == ["9%涨幅池"]
    assert pools["600100.SH"] == ["5%涨幅池"]
    assert "创业板大波动" in pools["301400.SZ"]
    assert "000500.SZ" not in pools


def test_is_chinext():
    assert is_chinext("300001") is True
    assert is_chinext("301151") is True
    assert is_chinext("002129") is False
    assert is_chinext("688001") is False


def test_st_omen_rows_follow_delisting_warning_rules(monkeypatch):
    import services.risk_stock_collector as mod

    collector = RiskStockCollector.__new__(RiskStockCollector)

    yjbb_df = pd.DataFrame(
        [
            # 主板：亏损且营收 2 亿 < 3 亿 → 命中
            {"股票代码": "600300", "股票简称": "亏损小营收", "净利润-净利润": -5e7, "营业总收入-营业总收入": 2e8},
            # 主板：亏损但营收 10 亿 → 不命中
            {"股票代码": "600301", "股票简称": "亏损大营收", "净利润-净利润": -5e7, "营业总收入-营业总收入": 1e9},
            # 创业板：亏损且营收 0.8 亿 < 1 亿 → 命中
            {"股票代码": "300400", "股票简称": "创业板亏损", "净利润-净利润": -1e7, "营业总收入-营业总收入": 8e7},
            # 创业板：亏损但营收 2 亿（主板阈值以下，但创业板阈值以上）→ 不命中
            {"股票代码": "300401", "股票简称": "创业板营收过线", "净利润-净利润": -1e7, "营业总收入-营业总收入": 2e8},
            # 盈利 → 不命中
            {"股票代码": "600302", "股票简称": "盈利示例", "净利润-净利润": 5e7, "营业总收入-营业总收入": 1e8},
            # 已戴帽 → 排除
            {"股票代码": "600305", "股票简称": "*ST已帽", "净利润-净利润": -5e7, "营业总收入-营业总收入": 1e8},
        ]
    )
    basic_df = pd.DataFrame(
        [
            {"ts_code": "600303.SH", "pb": -0.5},
            {"ts_code": "600304.SH", "pb": 1.2},
        ]
    )

    monkeypatch.setattr(RiskStockCollector, "_fetch_yjbb", lambda self, period: yjbb_df)
    monkeypatch.setattr(
        RiskStockCollector,
        "_fetch_daily_basic_with_fallback",
        lambda self, trade_date: basic_df,
    )
    monkeypatch.setattr(
        RiskStockCollector,
        "_build_name_map",
        lambda self: {"600303": "负资产示例"},
    )
    mod._st_omen_cache.clear()

    rows = collector._build_st_omen_rows("20260721")
    by_code = {row["ts_code"]: row for row in rows}

    assert "600300.SH" in by_code
    assert by_code["600300.SH"]["pools"] == ["ST征兆"]
    assert "净利润为负" in by_code["600300.SH"]["pool_reasons"][0]
    assert "600301.SH" not in by_code  # 营收超阈值
    assert "300400.SZ" in by_code  # 创业板 1 亿阈值
    assert "300401.SZ" not in by_code
    assert "600302.SH" not in by_code  # 盈利
    assert "600305.SH" not in by_code  # 已戴帽排除
    assert "600303.SH" in by_code
    assert "净资产为负" in by_code["600303.SH"]["pool_reasons"][0]
    assert "600304.SH" not in by_code


def test_latest_disclosed_annual_period():
    from datetime import datetime

    # 7 月：2025 年报已披露完毕
    assert RiskStockCollector._latest_disclosed_annual_period(datetime(2026, 7, 21))[0] == "20251231"
    # 3 月：2025 年报还没披露完，用 2024 年报
    assert RiskStockCollector._latest_disclosed_annual_period(datetime(2026, 3, 1))[0] == "20241231"


def test_st_omen_rows_cached_per_day(monkeypatch):
    import services.risk_stock_collector as mod

    collector = RiskStockCollector.__new__(RiskStockCollector)
    calls = []

    def fake_build(self, trade_date):
        calls.append(trade_date)
        return [{"ts_code": "600300.SH", "name": "示例", "market": "主板",
                 "pools": ["ST征兆"], "pool_reasons": ["r"]}]

    monkeypatch.setattr(RiskStockCollector, "_build_st_omen_rows", fake_build)
    mod._st_omen_cache.clear()

    rows1 = collector._collect_st_omen_rows("20260721")
    rows2 = collector._collect_st_omen_rows("20260721")
    assert len(calls) == 1  # 当日只真正构建一次
    assert rows1 == rows2
    # 返回副本，调用方修改不污染缓存
    rows1[0]["name"] = "被改了"
    rows3 = collector._collect_st_omen_rows("20260721")
    assert rows3[0]["name"] == "示例"


# ------------------------------------------------------------------
# 自选提醒过滤
# ------------------------------------------------------------------

def test_low_risk_pool_items_do_not_create_watchlist_alerts(tmp_path, monkeypatch):
    import uuid
    from datetime import datetime

    from services.watchlist_risk_alert_service import WatchlistRiskAlertService

    db_path = tmp_path / "risk_pool_alert_filter.db"
    _run_all_migrations(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    service = RiskStockService(db_path=str(db_path))
    service.refresh_from_rows(
        "20260721",
        [
            {"ts_code": "600100.SH", "name": "涨5示例", "pct_chg": 5.6,
             "pools": ["5%涨幅池"], "pool_reasons": ["当日涨幅 5.60%，达到 5% 档"]},
        ],
        source="unit-test",
    )

    user_id = "user_pool_filter"
    now = datetime.utcnow().isoformat() + "Z"
    watchlist_id = f"wl_{uuid.uuid4().hex[:8]}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO watchlists (id, user_id, name, created_at, updated_at) VALUES (?, ?, '默认自选', ?, ?)",
            (watchlist_id, user_id, now, now),
        )
        conn.execute(
            "INSERT INTO watchlist_items (watchlist_id, ts_code, name, added_at) VALUES (?, ?, ?, ?)",
            (watchlist_id, "600100.SH", "涨5示例", now),
        )
        conn.commit()

    result = WatchlistRiskAlertService(db_path=str(db_path)).sync_alerts_for_trade_date("20260721")
    assert result["created"] == 0


def test_refresh_persists_pool_fields(tmp_path, monkeypatch):
    db_path = tmp_path / "risk_pool_fields.db"
    _run_all_migrations(db_path, monkeypatch)
    DatabaseFactory.initialize(str(db_path))

    service = RiskStockService(db_path=str(db_path))
    service.refresh_from_rows(
        "20260721",
        [
            {"ts_code": "600900.SH", "name": "二连跌停", "limit_down_days": 2, "pct_chg": -9.98},
        ],
        source="unit-test",
    )

    item = service.get_items(trade_date="20260721")[0]
    assert item["limit_down_days"] == 2
    assert item["pct_chg"] == -9.98
    tags = json.loads(item["tags_json"])
    assert "连续跌停" in tags
    assert item["risk_level"] == "high"
