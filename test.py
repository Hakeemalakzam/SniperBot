# test.py
from sniper_engine import analyze_single_coin

result = analyze_single_coin("BTCUSDT")
print(f"العملة: {result.symbol}")
print(f"السعر: {result.price}")
print(f"الإشارة: {result.signal}")
print(f"النقاط: {result.score}")
print(f"التفاصيل: {result.details}")