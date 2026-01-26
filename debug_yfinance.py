
import yfinance as yf
import pandas as pd
import time

def test_yfinance(code, name):
    print(f"\n--- 测试 YFinance 获取 {name} ({code}) ---")
    try:
        start_time = time.time()
        ticker = yf.Ticker(code)
        # 获取最近1个月数据
        df = ticker.history(period="1mo")
        elapsed = time.time() - start_time
        
        print(f"耗时: {elapsed:.2f}s")
        
        if not df.empty:
            print(f"获取成功! 返回数据条数: {len(df)}")
            print("最后一条数据:")
            print(df.tail(1)[['Open', 'High', 'Low', 'Close', 'Volume']])
            return True
        else:
            print("获取失败: 返回数据为空")
            return False
            
    except Exception as e:
        print(f"发生错误: {e}")
        return False

print("开始 YFinance连通性测试...")

# 测试沪市 (贵州茅台)
test_yfinance("600519.SS", "贵州茅台(沪)")

# 测试深市 (平安银行)
test_yfinance("000001.SZ", "平安银行(深)")

# 测试美股 (Apple) - 作为基准对比
test_yfinance("AAPL", "Apple(美)")
