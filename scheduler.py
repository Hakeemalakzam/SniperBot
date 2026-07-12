"""
=============================================================================
  SNIPER BOT - جدولة المهام التلقائية (كل ساعة)
=============================================================================
"""

import time
import threading
from datetime import datetime, timedelta
from sniper_engine import analyze_single_coin, get_top_symbols
from database import db
from notifier import notifier
from config import FETCH_INTERVAL_HOURS, TOP_COINS_COUNT, TOP_TRADES_TO_SEND, MIN_SCORE

try:
    from whatsapp import whatsapp
    WHATSAPP_AVAILABLE = True
except ImportError:
    WHATSAPP_AVAILABLE = False
    print("⚠️ واتساب غير متوفر")

SCHEDULER_RUNNING = False

def fetch_and_analyze():
    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"🚀 بدء جلب البيانات - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    symbols = get_top_symbols(TOP_COINS_COUNT)
    if not symbols:
        print("❌ فشل في جلب قائمة العملات")
        return
    
    print(f"📊 عدد العملات: {len(symbols)}")
    signals = []
    total_coins = len(symbols)
    
    for i, symbol in enumerate(symbols, 1):
        try:
            progress = f"[{i}/{total_coins}]"
            result = analyze_single_coin(symbol)
            
            data = {
                'price': result.price,
                'score': result.score,
                'signal': result.signal,
                'rsi': result.rsi,
                'trend': result.trend,
                'support': result.support,
                'resistance': result.resistance,
                'entry': result.entry,
                'sl': result.sl,
                'tp1': result.tp1,
                'rr': result.rr,
                'whale_score': result.whale_score,
                'tech_score': result.tech_score,
                'details': result.details
            }
            
            try:
                db.save_market_data(symbol, data)
            except Exception as e:
                print(f"  ⚠️ {symbol}: خطأ في حفظ البيانات - {e}")
                continue
            
            if result.signal == 'شراء' and result.score >= MIN_SCORE:
                signals.append({
                    'symbol': symbol,
                    'score': result.score,
                    'entry': result.entry,
                    'sl': result.sl,
                    'tp1': result.tp1,
                    'rr': result.rr
                })
                print(f"  {progress} تحليل {symbol}... ✅ شراء! (نقاط: {result.score})")
            else:
                print(f"  {progress} تحليل {symbol}... ⚪ {result.signal} (نقاط: {result.score})")
            
            time.sleep(0.1)
        except Exception as e:
            print(f"  {progress} تحليل {symbol}... ❌ خطأ: {str(e)[:50]}")
    
    signals.sort(key=lambda x: x['score'], reverse=True)
    top_signals = signals[:TOP_TRADES_TO_SEND]
    
    print(f"\n{'─'*60}")
    print(f"📊 ملخص التحليل:")
    print(f"  ✅ إشارات شراء: {len(signals)}")
    if top_signals:
        print(f"  📈 أفضل {len(top_signals)} إشارة:")
        for i, s in enumerate(top_signals, 1):
            print(f"    {i}. {s['symbol']} - نقاط: {s['score']} - RR: 1:{s['rr']}")
    print(f"{'─'*60}")
    
    if top_signals:
        try:
            notifier.send_trade_signal(top_signals)
            print(f"🔔 تم إرسال {len(top_signals)} إشارة إلى سطح المكتب")
        except Exception as e:
            print(f"⚠️ فشل إرسال تنبيه سطح المكتب: {e}")
    
    try:
        notifier.send_summary(len(symbols), len(signals))
    except Exception as e:
        print(f"⚠️ فشل إرسال ملخص سطح المكتب: {e}")
    
    if WHATSAPP_AVAILABLE and top_signals:
        try:
            whatsapp.send_trade_signals(top_signals)
            print(f"📱 تم إرسال {len(top_signals)} إشارة إلى واتساب")
        except Exception as e:
            print(f"⚠️ فشل إرسال واتساب: {e}")
    
    try:
        db._clean_old_data()
        print("🧹 تم تنظيف البيانات القديمة")
    except Exception as e:
        print(f"⚠️ فشل تنظيف البيانات: {e}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"{'='*60}")
    print(f"✅ اكتمل الجلب - {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ استغرق: {duration:.1f} ثانية")
    print(f"{'='*60}\n")

def scheduled_task():
    fetch_and_analyze()
    next_run = datetime.now() + timedelta(hours=FETCH_INTERVAL_HOURS)
    print(f"⏰ المهمة التالية: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    timer = threading.Timer(FETCH_INTERVAL_HOURS * 3600, scheduled_task)
    timer.daemon = True
    timer.start()

def start_scheduler():
    global SCHEDULER_RUNNING
    if SCHEDULER_RUNNING:
        return
    SCHEDULER_RUNNING = True
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║  🚀 SNIPER BOT SCHEDULER                                       ║
║                                                                  ║
║  ⏰ الجلب كل: {FETCH_INTERVAL_HOURS} ساعة                      ║
║  📊 عدد العملات: {TOP_COINS_COUNT}                            ║
║  🎯 الحد الأدنى للنقاط: {MIN_SCORE}                          ║
║  🔔 تنبيهات Windows: {'مفعلة' if notifier.enabled else 'معطلة'}║
║  📱 واتساب: {'مفعل' if WHATSAPP_AVAILABLE else 'معطل'}        ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    scheduled_task()