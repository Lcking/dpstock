
import requests
import time
import socket

def check_connection(name, headers=None):
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    # 参数模拟 akshare 的请求
    # secid=1.600519 (贵州茅台)
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "beg": "20240101",
        "end": "20500101",
        "rtntype": "6",
        "secid": "1.600519", 
        "klt": "101", # 日线
        "fqt": "1"    # 前复权
    }
    
    print(f"\n--- 测试 {name} ---")
    try:
        start_time = time.time()
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        elapsed = time.time() - start_time
        
        print(f"状态码: {resp.status_code}")
        print(f"耗时: {elapsed:.2f}s")
        if resp.status_code == 200:
            data = resp.json()
            if data.get('data'):
                lines = data['data']['klines']
                print(f"获取成功! 返回数据条数: {len(lines)}")
                print(f"第一条数据: {lines[0]}")
            else:
                print(f"响应成功但无数据: {data}")
        else:
            print(f"请求失败: {resp.text[:200]}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误 (ConnectionError): {e}")
        print("这通常意味着 IP 被封锁或 DNS 解析失败")
    except requests.exceptions.Timeout as e:
        print(f"超时 (Timeout): {e}")
    except Exception as e:
        print(f"其他错误: {type(e).__name__}: {e}")

print("开始网络诊断...")
print(f"本机主机名: {socket.gethostname()}")

# 测试 1: 无 User-Agent (默认请求)
check_connection("直连 (无 Headers)")

# 测试 2: 带浏览器 User-Agent (模拟浏览器)
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}
check_connection("模拟浏览器 (带 Headers)", headers)
