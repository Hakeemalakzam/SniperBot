"""
=============================================================================
  SNIPER BOT - تنبيهات سطح المكتب (Windows)
=============================================================================
"""

import os
import platform
from datetime import datetime
from config import NOTIFICATIONS_ENABLED

class Notifier:
    def __init__(self):
        self.enabled = NOTIFICATIONS_ENABLED and platform.system() == "Windows"
    
    def send(self, title: str, message: str, timeout: int = 5):
        """إرسال تنبيه Windows"""
        if not self.enabled:
            return
        
        try:
            # استخدام PowerShell لعرض التنبيه
            cmd = f'''
            powershell -Command "
                Add-Type -AssemblyName System.Windows.Forms;
                $notification = New-Object System.Windows.Forms.NotifyIcon;
                $notification.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Process -Id $pid).Path);
                $notification.BalloonTipTitle = '{title}';
                $notification.BalloonTipText = '{message}';
                $notification.Visible = $true;
                $notification.ShowBalloonTip({timeout * 1000});
                Start-Sleep -Seconds {timeout + 1};
                $notification.Dispose();
            "
            '''
            os.system(cmd)
        except Exception as e:
            print(f"❌ فشل التنبيه: {e}")

    def send_trade_signal(self, signals: list):
        """إرسال إشارة صفقة"""
        if not signals or not self.enabled:
            return
        
        top = signals[0]
        message = f"""
العملة: {top['symbol']}
الدخول: {top['entry']}
وقف الخسارة: {top['sl']}
الهدف: {top['tp1']}
نسبة RR: 1:{top['rr']}
        """.strip()
        
        self.send("🎯 إشارة شراء جديدة!", message)

    def send_summary(self, symbols_count: int, signals_count: int):
        """إرسال ملخص الجلب"""
        if not self.enabled:
            return
        
        message = f"""
📊 تم تحليل {symbols_count} عملة
✅ تم العثور على {signals_count} إشارة شراء
🕐 {datetime.now().strftime('%H:%M:%S')}
        """.strip()
        
        self.send("📊 تقرير السوق", message)

notifier = Notifier()