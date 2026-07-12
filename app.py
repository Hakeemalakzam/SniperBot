"""
=============================================================================
  SNIPER BOT - خادم الويب الرئيسي (نسخة متكاملة)
=============================================================================
"""

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import json
import threading
import time
import os
import sys
from datetime import datetime
from sniper_engine import analyze_single_coin, get_top_symbols
from database import db
from config import PORT, DEBUG, HOST, FETCH_INTERVAL_HOURS, TOP_COINS_COUNT, MIN_SCORE

app = Flask(__name__)
CORS(app)

SELECTED_TRADES = []
MAX_SELECTED_TRADES = 10
AUTO_TRADE_RESULTS = []

# ========== HTML ==========

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 SNIPER BOT</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a0f; color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; min-height: 100vh; }
        .container { max-width: 1400px; margin: 0 auto; display: flex; gap: 20px; }
        .main { flex: 1; min-width: 0; }
        .sidebar { width: 320px; min-width: 320px; max-height: 90vh; position: sticky; top: 20px; overflow-y: auto; background: rgba(255,255,255,0.03); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); padding: 15px; }
        .sidebar h3 { color: #ffd700; font-size: 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .sidebar h3 span { background: rgba(255,215,0,0.15); padding: 2px 10px; border-radius: 12px; font-size: 12px; color: #ffd700; }
        .sidebar .empty { color: #555; text-align: center; padding: 30px 0; font-size: 14px; }
        .trade-card { background: rgba(0,0,0,0.3); border-radius: 10px; padding: 12px; margin-bottom: 10px; border-left: 3px solid #ffd700; transition: 0.3s; }
        .trade-card:hover { background: rgba(255,255,255,0.05); }
        .trade-card .head { display: flex; justify-content: space-between; align-items: center; }
        .trade-card .symbol { font-weight: bold; color: #fff; font-size: 15px; }
        .trade-card .status { font-size: 12px; padding: 2px 10px; border-radius: 12px; }
        .status-active { background: rgba(0,255,0,0.15); color: #00ff00; }
        .status-closed { background: rgba(255,255,255,0.05); color: #666; }
        .trade-card .details { font-size: 12px; color: #888; margin-top: 5px; display: grid; grid-template-columns: 1fr 1fr; gap: 2px 10px; }
        .trade-card .details span { display: flex; justify-content: space-between; }
        .trade-card .details .label { color: #666; }
        .trade-card .details .value { color: #eee; }
        .trade-card .pnl { font-weight: bold; font-size: 14px; margin-top: 5px; text-align: center; padding: 4px; border-radius: 6px; }
        .pnl-profit { background: rgba(0,255,0,0.08); color: #00ff00; }
        .pnl-loss { background: rgba(255,0,0,0.08); color: #ff4444; }
        .pnl-waiting { background: rgba(255,165,0,0.08); color: #ffa500; }
        .trade-card .remove-btn { background: rgba(255,0,0,0.15); color: #ff4444; border: none; border-radius: 50%; width: 22px; height: 22px; cursor: pointer; font-size: 12px; transition: 0.3s; }
        .trade-card .remove-btn:hover { background: rgba(255,0,0,0.3); }
        .header { text-align: center; padding: 25px; background: rgba(255,255,255,0.03); border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px; }
        .header h1 { color: #ffd700; font-size: 2.2em; }
        .header p { color: #888; margin-top: 5px; }
        .status { display: flex; justify-content: center; align-items: center; gap: 15px; margin-top: 12px; flex-wrap: wrap; }
        .status span { background: rgba(255,255,255,0.05); padding: 4px 14px; border-radius: 15px; font-size: 12px; }
        .status .live { color: #00ff00; }
        .status .restart-btn { background: #ff6b35; color: #fff; border: none; padding: 6px 15px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 12px; transition: 0.3s; }
        .status .restart-btn:hover { transform: scale(1.05); box-shadow: 0 0 20px rgba(255,107,53,0.3); }
        .status .restart-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .search { background: rgba(255,255,255,0.03); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px; }
        .search-row { display: flex; gap: 10px; flex-wrap: wrap; }
        .search-row input { flex: 1; min-width: 120px; padding: 10px 16px; border-radius: 10px; border: 1px solid #333; background: #1a1a2e; color: #fff; font-size: 15px; }
        .search-row input:focus { outline: none; border-color: #ffd700; }
        .search-row button { padding: 10px 20px; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 14px; transition: 0.3s; }
        .btn-analyze { background: #ffd700; color: #000; }
        .btn-analyze:hover { transform: scale(1.02); box-shadow: 0 5px 20px rgba(255,215,0,0.3); }
        .btn-trade { background: #00ff88; color: #000; }
        .btn-trade:hover { transform: scale(1.02); box-shadow: 0 5px 20px rgba(0,255,136,0.3); }
        .btn-take { background: #ff6b35; color: #fff; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%, 100% { box-shadow: 0 0 10px rgba(255,107,53,0.3); } 50% { box-shadow: 0 0 25px rgba(255,107,53,0.6); } }
        .quick { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px; }
        .quick button { padding: 5px 14px; border: 1px solid #333; border-radius: 20px; background: transparent; color: #aaa; cursor: pointer; transition: 0.3s; font-size: 13px; }
        .quick button:hover { background: #ffd700; color: #000; border-color: #ffd700; }
        .result { background: rgba(255,255,255,0.03); border-radius: 15px; padding: 20px; border: 1px solid rgba(255,255,255,0.05); margin-top: 15px; }
        .result h2 { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; font-size: 20px; }
        .result h2 .symbol { color: #fff; }
        .result h2 .signal { font-size: 16px; padding: 3px 16px; border-radius: 20px; }
        .signal-buy { background: rgba(0,255,0,0.15); color: #00ff00; border: 1px solid rgba(0,255,0,0.2); }
        .signal-wait { background: rgba(255,165,0,0.15); color: #ffa500; border: 1px solid rgba(255,165,0,0.2); }
        .signal-reject { background: rgba(255,0,0,0.15); color: #ff4444; border: 1px solid rgba(255,0,0,0.2); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin: 12px 0; }
        .item { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; text-align: center; }
        .item .label { font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
        .item .value { font-size: 16px; font-weight: bold; margin-top: 3px; }
        .gold { color: #ffd700; }
        .green { color: #00ff00; }
        .red { color: #ff4444; }
        .blue { color: #4fc3f7; }
        .trade-plan { background: rgba(0,255,0,0.05); border-radius: 12px; padding: 15px; border: 1px solid rgba(0,255,0,0.1); margin-top: 12px; }
        .trade-plan h3 { color: #00ff00; margin-bottom: 8px; font-size: 16px; }
        .trade-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 6px; }
        .trade-item { display: flex; justify-content: space-between; padding: 5px 10px; background: rgba(0,0,0,0.2); border-radius: 6px; font-size: 13px; }
        .trade-item .label { color: #888; }
        .trade-item .value { font-weight: bold; }
        .details { margin-top: 12px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px; font-size: 13px; color: #aaa; }
        .details li { list-style: none; padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.02); }
        .loading { text-align: center; padding: 30px; }
        .spinner { width: 35px; height: 35px; border: 4px solid rgba(255,215,0,0.1); border-top-color: #ffd700; border-radius: 50%; margin: 0 auto 12px; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .footer { text-align: center; color: #444; font-size: 11px; margin-top: 20px; padding: 12px; border-top: 1px solid rgba(255,255,255,0.02); }
        .auto-trades-box { background: rgba(255,215,0,0.05); border: 1px solid rgba(255,215,0,0.15); border-radius: 12px; padding: 15px; margin-bottom: 15px; }
        .auto-trades-box h3 { color: #ffd700; font-size: 16px; margin-bottom: 10px; }
        @media (max-width: 900px) { .container { flex-direction: column; } .sidebar { width: 100%; min-width: unset; position: relative; top: 0; max-height: 400px; } .main { width: 100%; } }
        @media (max-width: 600px) { .header h1 { font-size: 1.6em; } .search-row { flex-direction: column; } .search-row input { width: 100%; } .search-row button { width: 100%; } .grid { grid-template-columns: repeat(2, 1fr); } .trade-grid { grid-template-columns: 1fr; } .sidebar { max-height: 300px; } }
    </style>
</head>
<body>
<div class="container">
    <div class="main">
        <div class="header">
            <h1>🎯 SNIPER BOT</h1>
            <p>11 طبقة تحليل | Binance Edition | تحديث كل ساعة</p>
            <div class="status">
                <span class="live">🟢 النظام يعمل</span>
                <span id="time">⏰ --:--:--</span>
                <span>📊 100 عملة</span>
                <span>🎯 حد أدنى 5 نقاط</span>
                <button class="restart-btn" onclick="restartServer()">🔄 تحديث البيانات</button>
            </div>
        </div>
        
        <div id="autoTradesContainer"></div>
        
        <div class="search">
            <div class="search-row">
                <input id="symbolInput" placeholder="أدخل اسم العملة... BTC, ETH, SOL" onkeypress="if(event.key==='Enter')analyze()">
                <button class="btn-analyze" onclick="analyze()">🔍 تحليل</button>
                <button class="btn-trade" onclick="getTrade()">🎯 اعطني صفقة</button>
            </div>
            <div class="quick">
                <button onclick="quick('BTC')">₿ BTC</button>
                <button onclick="quick('ETH')">⟠ ETH</button>
                <button onclick="quick('SOL')">◎ SOL</button>
                <button onclick="quick('BNB')">◆ BNB</button>
                <button onclick="quick('XRP')">✕ XRP</button>
                <button onclick="quick('DOGE')">🐕 DOGE</button>
                <button onclick="quick('ADA')">🟣 ADA</button>
            </div>
        </div>
        
        <div id="loading" class="loading" style="display:none;">
            <div class="spinner"></div>
            <p style="color:#888;">جاري التحليل...</p>
        </div>
        
        <div id="result"></div>
        
        <div class="footer">Sniper Bot v12.0 | تحديث كل ساعة | الحد الأدنى 5 نقاط</div>
    </div>
    
    <div class="sidebar" id="sidebar">
        <h3>📋 صفقاتي <span id="tradeCount">0/10</span></h3>
        <div id="tradeList"><div class="empty">لا توجد صفقات مختارة</div></div>
    </div>
</div>

<script>
let currentTrade = null;

function updateTime() {
    document.getElementById('time').textContent = '⏰ ' + new Date().toLocaleTimeString('ar-EG');
}
setInterval(updateTime, 1000);
updateTime();

function quick(s) {
    document.getElementById('symbolInput').value = s;
    analyze();
}

function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

function showResult(html) {
    document.getElementById('result').innerHTML = html;
}

function analyze() {
    const s = document.getElementById('symbolInput').value.trim().toUpperCase();
    if (!s) return alert('⚠️ ادخل اسم العملة');
    showLoading(true);
    showResult('');
    fetch('/analyze', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({symbol: s})
    })
    .then(r => r.json())
    .then(d => {
        showLoading(false);
        if (d.error) {
            showResult('<div style="color:#ff4444;text-align:center;padding:30px;">❌ ' + d.error + '</div>');
        } else {
            renderResult(d);
        }
    })
    .catch(e => {
        showLoading(false);
        showResult('<div style="color:#ff4444;text-align:center;padding:30px;">❌ خطأ: ' + e.message + '</div>');
    });
}

function getTrade() {
    showLoading(true);
    showResult('');
    fetch('/trade')
    .then(r => r.json())
    .then(d => {
        showLoading(false);
        if (d.status === 'success') {
            let html = '<div class="result"><h2>🎯 أفضل الصفقات</h2>';
            d.signals.forEach((s, i) => {
                const icons = ['🥇', '🥈', '🥉'];
                html += `
                    <div class="trade-card" style="border-left-color: #ffd700; margin-top: 10px;">
                        <div class="head">
                            <span class="symbol">${icons[i] || '⭐'} ${s.symbol}</span>
                            <span class="status status-active">${s.score} نقاط</span>
                        </div>
                        <div class="details">
                            <span><span class="label">الدخول:</span> <span class="value">${s.entry}</span></span>
                            <span><span class="label">SL:</span> <span class="value">${s.sl}</span></span>
                            <span><span class="label">TP:</span> <span class="value">${s.tp1}</span></span>
                            <span><span class="label">RR:</span> <span class="value">1:${s.rr}</span></span>
                        </div>
                        <button onclick="quick('${s.symbol.replace('USDT', '')}')" 
                                style="margin-top:8px; padding:4px 12px; border:1px solid #ffd700; border-radius:6px; background:transparent; color:#ffd700; cursor:pointer; font-size:12px;">
                            🔍 تحليل مفصل
                        </button>
                        <button onclick="quickTakeTrade('${s.symbol}', '${s.entry}', '${s.sl}', '${s.tp1}', '${s.rr}', '${s.score}')" 
                                style="margin-top:8px; padding:4px 12px; border:1px solid #ff6b35; border-radius:6px; background:#ff6b35; color:#fff; cursor:pointer; font-size:12px; margin-left:5px;">
                            📌 خذ الصفقة
                        </button>
                    </div>
                `;
            });
            html += '</div>';
            showResult(html);
        } else {
            showResult('<div style="text-align:center;padding:40px;color:#ffa500;">⏳ ' + d.message + '</div>');
        }
    })
    .catch(e => {
        showLoading(false);
        showResult('<div style="color:#ff4444;text-align:center;padding:30px;">❌ خطأ: ' + e.message + '</div>');
    });
}

function quickTakeTrade(symbol, entry, sl, tp1, rr, score) {
    const trade = {
        symbol: symbol,
        entry: parseFloat(entry),
        sl: parseFloat(sl),
        tp1: parseFloat(tp1),
        rr: parseFloat(rr),
        score: parseInt(score)
    };
    
    fetch('/take_trade', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(trade)
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            alert('✅ تم أخذ الصفقة!');
            loadTrades();
        } else {
            alert('⚠️ ' + data.message);
        }
    })
    .catch(e => alert('❌ خطأ: ' + e.message));
}

function renderResult(d) {
    const signalClass = d.signal === 'شراء' ? 'signal-buy' : d.signal === 'مرفوض' ? 'signal-reject' : 'signal-wait';
    const signalText = d.signal === 'شراء' ? '✅ شراء' : d.signal === 'مرفوض' ? '❌ مرفوض' : '⏳ انتظار';
    let html = `<div class="result"><h2><span class="symbol">${d.symbol || 'N/A'}</span><span class="signal ${signalClass}">${signalText}</span></h2>
        <div class="grid">
            <div class="item"><div class="label">السعر</div><div class="value gold">$${d.price || 0}</div></div>
            <div class="item"><div class="label">النقاط</div><div class="value gold">${d.score || 0}</div></div>
            <div class="item"><div class="label">نقاط الحيتان</div><div class="value blue">${d.whale_score || 0}</div></div>
            <div class="item"><div class="label">النقاط التقنية</div><div class="value blue">${d.tech_score || 0}</div></div>
            <div class="item"><div class="label">RSI</div><div class="value ${d.rsi > 70 ? 'red' : d.rsi < 30 ? 'green' : 'gold'}">${d.rsi || 50}</div></div>
            <div class="item"><div class="label">الاتجاه</div><div class="value ${d.trend === 'صاعد' ? 'green' : 'red'}">${d.trend || 'محايد'}</div></div>
            <div class="item"><div class="label">الدعم</div><div class="value">${d.support || 0}</div></div>
            <div class="item"><div class="label">المقاومة</div><div class="value">${d.resistance || 0}</div></div>
        </div>`;
    if (d.signal === 'شراء') {
        html += `<div class="trade-plan"><h3>📊 خطة الصفقة</h3>
            <div class="trade-grid">
                <div class="trade-item"><span class="label">📍 الدخول</span><span class="value">${d.entry}</span></div>
                <div class="trade-item"><span class="label">🔴 وقف الخسارة</span><span class="value" style="color:#ff4444;">${d.sl}</span></div>
                <div class="trade-item"><span class="label">🟢 TP1</span><span class="value" style="color:#00ff00;">${d.tp1}</span></div>
                <div class="trade-item"><span class="label">⚖️ RR</span><span class="value" style="color:#ffd700;">1:${d.rr}</span></div>
            </div>
            <div style="text-align:center; margin-top:10px;">
                <button onclick="quickTakeTrade('${d.symbol}', '${d.entry}', '${d.sl}', '${d.tp1}', '${d.rr}', '${d.score}')" 
                        style="padding:8px 25px; border:none; border-radius:8px; background:#ff6b35; color:#fff; font-weight:bold; cursor:pointer; animation:pulse 1.5s infinite;">
                    📌 خذ الصفقة
                </button>
            </div>
        </div>`;
    }
    if (d.details && d.details.length > 0) {
        html += `<div class="details"><ul>${d.details.map(x => `<li>${x}</li>`).join('')}</ul></div>`;
    }
    html += `</div>`;
    showResult(html);
}

function loadTrades() {
    fetch('/get_trades')
    .then(r => r.json())
    .then(data => {
        const list = document.getElementById('tradeList');
        const count = document.getElementById('tradeCount');
        count.textContent = data.length + '/10';
        if (data.length === 0) {
            list.innerHTML = '<div class="empty">لا توجد صفقات مختارة</div>';
            return;
        }
        let html = '';
        data.forEach((t, i) => {
            const isActive = t.status === 'active';
            const pnlClass = t.pnl > 0 ? 'pnl-profit' : t.pnl < 0 ? 'pnl-loss' : 'pnl-waiting';
            const statusClass = isActive ? 'status-active' : 'status-closed';
            const pnlText = t.pnl !== null ? (t.pnl > 0 ? '+' : '') + t.pnl + '%' : 'جاري المراقبة...';
            html += `
                <div class="trade-card" style="border-left-color: ${isActive ? '#00ff00' : '#666'};">
                    <div class="head">
                        <span class="symbol">${t.symbol}</span>
                        <span class="status ${statusClass}">${isActive ? '🟢 نشط' : '🔴 مغلق'}</span>
                        <button class="remove-btn" onclick="removeTrade(${i})" title="حذف">✕</button>
                    </div>
                    <div class="details">
                        <span><span class="label">الدخول:</span> <span class="value">${t.entry}</span></span>
                        <span><span class="label">SL:</span> <span class="value">${t.sl}</span></span>
                        <span><span class="label">TP:</span> <span class="value">${t.tp1}</span></span>
                        <span><span class="label">RR:</span> <span class="value">1:${t.rr}</span></span>
                        <span><span class="label">النقاط:</span> <span class="value">${t.score}</span></span>
                        <span><span class="label">التاريخ:</span> <span class="value">${t.date || ''}</span></span>
                    </div>
                    <div class="pnl ${pnlClass}">📊 ${pnlText}</div>
                </div>
            `;
        });
        list.innerHTML = html;
    });
}

function removeTrade(index) {
    if (!confirm('هل أنت متأكد من حذف هذه الصفقة؟')) return;
    fetch('/remove_trade/' + index, { method: 'DELETE' })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') loadTrades();
    });
}

function loadAutoTrades() {
    fetch('/api/auto_trades')
    .then(r => r.json())
    .then(data => {
        const container = document.getElementById('autoTradesContainer');
        if (data.status === 'success' && data.signals && data.signals.length > 0) {
            let html = `<div class="auto-trades-box"><h3>🔄 أفضل ${data.signals.length} صفقات متاحة (تحديث تلقائي)</h3>`;
            data.signals.forEach((s, i) => {
                const icons = ['🥇', '🥈', '🥉'];
                html += `
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.05);">
                        <span>${icons[i] || '⭐'} <strong>${s.symbol}</strong> (<span style="color:#ffd700;">${s.score}</span> نقاط)</span>
                        <span style="color:#888; font-size:12px;">دخول: ${s.entry} | RR: 1:${s.rr}</span>
                        <button onclick="quick('${s.symbol.replace('USDT', '')}')" style="padding:2px 10px; border:1px solid #ffd700; border-radius:4px; background:transparent; color:#ffd700; cursor:pointer; font-size:11px;">🔍</button>
                        <button onclick="quickTakeTrade('${s.symbol}', '${s.entry}', '${s.sl}', '${s.tp1}', '${s.rr}', '${s.score}')" 
                                style="padding:2px 10px; border:1px solid #ff6b35; border-radius:4px; background:#ff6b35; color:#fff; cursor:pointer; font-size:11px; margin-left:3px;">
                            📌
                        </button>
                    </div>
                `;
            });
            html += `
                <div style="text-align:center; margin-top:10px;">
                    <button onclick="getTrade()" style="padding:6px 20px; border:none; border-radius:8px; background:#00ff88; color:#000; font-weight:bold; cursor:pointer;">
                        🎯 خذ أفضل صفقة
                    </button>
                </div>
            `;
            html += `</div>`;
            container.innerHTML = html;
        } else {
            container.innerHTML = `<div class="auto-trades-box"><h3>⏳ جاري البحث عن صفقات...</h3></div>`;
        }
    })
    .catch(e => {
        document.getElementById('autoTradesContainer').innerHTML = `<div class="auto-trades-box"><h3>⚠️ خطأ في تحميل الصفقات</h3></div>`;
    });
}

// ===== زر تحديث البيانات =====
function restartServer() {
    if (!confirm('⚠️ هل تريد تحديث البيانات؟')) return;
    
    const btn = document.querySelector('.restart-btn');
    btn.textContent = '⏳ جاري...';
    btn.disabled = true;
    btn.style.opacity = '0.6';
    
    fetch('/api/restart', {
        method: 'POST'
    })
    .then(r => r.json())
    .then(data => {
        alert('✅ ' + data.message);
        location.reload();
    })
    .catch(e => {
        // إذا فشل الاتصال، نعيد تحميل الصفحة
        alert('⚠️ سيتم إعادة تحميل الصفحة لتحديث البيانات');
        location.reload();
    });
}

setInterval(loadAutoTrades, 60000);
loadAutoTrades();

setInterval(loadTrades, 30000);
loadTrades();
</script>
</body>
</html>
"""

# ========== Routes ==========

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    symbol = data.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': 'ادخل اسم العملة'}), 400
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    result = analyze_single_coin(symbol)
    if result.error:
        return jsonify({'error': result.error})
    return jsonify(result.to_dict())

@app.route('/trade')
def trade():
    signals = db.get_best_signals(3)
    if signals:
        return jsonify({'status': 'success', 'signals': signals})
    return jsonify({'status': 'waiting', 'message': 'لا توجد صفقات حالياً'})

@app.route('/api/auto_trades')
def auto_trades():
    global AUTO_TRADE_RESULTS
    if AUTO_TRADE_RESULTS:
        return jsonify({'status': 'success', 'signals': AUTO_TRADE_RESULTS})
    signals = db.get_best_signals(3)
    if signals:
        AUTO_TRADE_RESULTS = signals
        return jsonify({'status': 'success', 'signals': signals})
    return jsonify({'status': 'waiting', 'message': 'لا توجد صفقات'})

@app.route('/take_trade', methods=['POST'])
def take_trade():
    global SELECTED_TRADES
    data = request.get_json()
    if len(SELECTED_TRADES) >= MAX_SELECTED_TRADES:
        return jsonify({'status': 'error', 'message': f'لا يمكنك اختيار أكثر من {MAX_SELECTED_TRADES} صفقات'})
    trade = {
        'symbol': data.get('symbol'),
        'entry': float(data.get('entry', 0)),
        'sl': float(data.get('sl', 0)),
        'tp1': float(data.get('tp1', 0)),
        'rr': float(data.get('rr', 0)),
        'score': int(data.get('score', 0)),
        'status': 'active',
        'pnl': None,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'entry_price': float(data.get('entry', 0))
    }
    SELECTED_TRADES.append(trade)
    return jsonify({'status': 'success', 'trade': trade})

@app.route('/get_trades')
def get_trades():
    update_trade_prices()
    return jsonify(SELECTED_TRADES)

@app.route('/remove_trade/<int:index>', methods=['DELETE'])
def remove_trade(index):
    global SELECTED_TRADES
    if 0 <= index < len(SELECTED_TRADES):
        SELECTED_TRADES.pop(index)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'الصفقة غير موجودة'})

# ========== تحديث البيانات ==========

@app.route('/api/restart', methods=['POST'])
def restart_server():
    """تحديث البيانات وإعادة التحميل"""
    try:
        # تحديث الصفقات
        update_auto_trades()
        
        # تحديث الأسعار
        update_trade_prices()
        
        return jsonify({
            'status': 'success', 
            'message': 'تم تحديث البيانات بنجاح!',
            'trades_count': len(AUTO_TRADE_RESULTS)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def update_trade_prices():
    global SELECTED_TRADES
    for trade in SELECTED_TRADES:
        if trade.get('status') == 'active':
            try:
                result = analyze_single_coin(trade['symbol'])
                current_price = result.price
                if current_price and trade.get('entry_price'):
                    entry = float(trade['entry_price'])
                    pnl = ((current_price - entry) / entry) * 100
                    trade['pnl'] = round(pnl, 2)
                    trade['current_price'] = current_price
                    if current_price >= float(trade['tp1']):
                        trade['status'] = 'closed'
                        trade['pnl'] = 5.0
                    elif current_price <= float(trade['sl']):
                        trade['status'] = 'closed'
                        trade['pnl'] = round(((float(trade['sl']) - entry) / entry) * 100, 2)
            except:
                pass

def update_auto_trades():
    global AUTO_TRADE_RESULTS
    signals = db.get_best_signals(3)
    if signals:
        AUTO_TRADE_RESULTS = signals
        print(f"🔄 تم تحديث الصفقات: {len(signals)} صفقة")
    else:
        AUTO_TRADE_RESULTS = []
        print("⏳ لا توجد صفقات جديدة")

def scheduled_trade_update():
    while True:
        update_auto_trades()
        time.sleep(3600)

def start_background_scheduler():
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        from scheduler import start_scheduler
        start_scheduler()

# ========== التشغيل ==========

if __name__ == '__main__':
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        scheduler_thread = threading.Thread(target=start_background_scheduler, daemon=True)
        scheduler_thread.start()
        
        auto_trade_thread = threading.Thread(target=scheduled_trade_update, daemon=True)
        auto_trade_thread.start()
    
    update_auto_trades()
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║  🎯 SNIPER BOT v12.0 شغال!                                     ║
║                                                                  ║
║  🌐 افتح: http://localhost:{PORT}                              ║
║  ⏰ جلب كل {FETCH_INTERVAL_HOURS} ساعة                         ║
║  📊 عدد العملات: {TOP_COINS_COUNT}                            ║
║  🎯 الحد الأدنى: {MIN_SCORE} نقاط                            ║
║  🔄 تحديث الصفقات التلقائي: كل ساعة                          ║
║  📋 أقصى صفقات مختارة: {MAX_SELECTED_TRADES}                  ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(debug=DEBUG, host=HOST, port=PORT)