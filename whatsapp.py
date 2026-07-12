"""
=============================================================================
  SNIPER BOT - إرسال رسائل واتساب (CallMeBot)
=============================================================================
"""

import requests
import urllib.parse
from datetime import datetime
from config import WHATSAPP_NUMBER, WHATSAPP_API_KEY, WHATSAPP_ENABLED, FETCH_INTERVAL_HOURS

class WhatsAppSender:
    def __init__(self):
        self.number = WHATSAPP_NUMBER
        self.api_key = WHATSAPP_API_KEY
        self.enabled = WHATSAPP_ENABLED
    
    def send_message(self, message: str):
        """إرسال رسالة عبر CallMeBot"""
        if not self.enabled:
            print("📱 واتساب غير مفعل")
            return False
        
        try:
            # ترميز الرسالة للـ URL
            encoded_msg = urllib.parse.quote(message)
            
            url = f"https://api.callmebot.com/whatsapp.php?phone={self.number}&text={encoded_msg}&apikey={self.api_key}"
            
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                print("✅ تم إرسال الرسالة إلى واتساب")
                return True
            else:
                print(f"❌ فشل الإرسال: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ خطأ في الإرسال: {e}")
            return False
    
    def send_trade_signals(self, signals: list):
        """إرسال إشارات الصفقات"""
        if not signals or not self.enabled:
            return
        
        # ترتيب حسب النقاط
        signals.sort(key=lambda x: x['score'], reverse=True)
        top = signals[:3]
        
        message = f"""
🎯 *SNIPER BOT - أفضل {len(top)} صفقات*
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}
{'─' * 30}
"""
        
        for i, s in enumerate(top, 1):
            message += f"""
*{i}. {s['symbol']}*
  📍 الدخول: {s['entry']}
  🔴 وقف الخسارة: {s['sl']}
  🟢 الهدف: {s['tp1']}
  ⚖️ RR: 1:{s['rr']}
  ⭐ النقاط: {s['score']}
{'─' * 30}
"""
        
        message += """
📊 *للتفاصيل:* افتح تطبيق Sniper Bot
        """
        
        self.send_message(message)
    
    def send_summary(self, symbols_count: int, signals_count: int):
        """إرسال ملخص الجلب"""
        if not self.enabled:
            return
        
        message = f"""
📊 *تقرير السوق - Sniper Bot*
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}
{'─' * 30}
📈 تم تحليل: {symbols_count} عملة
🎯 إشارات شراء: {signals_count}
{'─' * 30}
*انتظر التحديث التالي بعد {FETCH_INTERVAL_HOURS} ساعة*
        """
        
        self.send_message(message)

# إنشاء نسخة وحيدة
whatsapp = WhatsAppSender()