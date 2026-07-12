"""
=============================================================================
  SNIPER BOT - قاعدة البيانات SQLite
=============================================================================
"""

import sqlite3
import json
import os
import threading
from datetime import datetime, timedelta
from config import DATABASE_PATH, DATA_RETENTION_DAYS, FETCH_INTERVAL_HOURS

class Database:
    def __init__(self):
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price REAL,
                score INTEGER,
                signal TEXT,
                rsi REAL,
                trend TEXT,
                support REAL,
                resistance REAL,
                entry REAL,
                sl REAL,
                tp1 REAL,
                rr REAL,
                whale_score INTEGER,
                tech_score INTEGER,
                details TEXT,
                FOREIGN KEY (symbol_id) REFERENCES symbols(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                score INTEGER,
                entry REAL,
                sl REAL,
                tp1 REAL,
                rr REAL,
                sent INTEGER DEFAULT 0,
                FOREIGN KEY (symbol_id) REFERENCES symbols(id)
            )
        ''')
        
        self.conn.commit()
        self._clean_old_data()

    def _clean_old_data(self):
        cutoff = datetime.now() - timedelta(days=DATA_RETENTION_DAYS)
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM market_data WHERE timestamp < ?', (cutoff,))
            cursor.execute('DELETE FROM signals WHERE timestamp < ?', (cutoff,))
            self.conn.commit()

    def get_symbol_id(self, symbol: str) -> int:
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('SELECT id FROM symbols WHERE symbol = ?', (symbol,))
            result = cursor.fetchone()
            if result:
                return result['id']
            try:
                cursor.execute('INSERT INTO symbols (symbol) VALUES (?)', (symbol,))
                self.conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                cursor.execute('SELECT id FROM symbols WHERE symbol = ?', (symbol,))
                return cursor.fetchone()['id']

    def save_market_data(self, symbol: str, data: dict):
        symbol_id = self.get_symbol_id(symbol)
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO market_data (
                    symbol_id, price, score, signal, rsi, trend,
                    support, resistance, entry, sl, tp1, rr,
                    whale_score, tech_score, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol_id,
                data.get('price', 0),
                data.get('score', 0),
                data.get('signal', 'انتظار'),
                data.get('rsi', 50),
                data.get('trend', 'محايد'),
                data.get('support', 0),
                data.get('resistance', 0),
                data.get('entry', 0),
                data.get('sl', 0),
                data.get('tp1', 0),
                data.get('rr', 0),
                data.get('whale_score', 0),
                data.get('tech_score', 0),
                json.dumps(data.get('details', []), ensure_ascii=False)
            ))
            self.conn.commit()

        if data.get('signal') == 'شراء' and data.get('score', 0) >= 5:
            self.save_signal(symbol, data)

    def save_signal(self, symbol: str, data: dict):
        symbol_id = self.get_symbol_id(symbol)
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO signals (symbol_id, score, entry, sl, tp1, rr)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                symbol_id,
                data.get('score', 0),
                data.get('entry', 0),
                data.get('sl', 0),
                data.get('tp1', 0),
                data.get('rr', 0)
            ))
            self.conn.commit()

    def get_best_signals(self, limit: int = 3, hours: float = None):
        """
        أفضل الإشارات *الحديثة* فقط (وليس أفضل إشارة في تاريخ قاعدة البيانات كاملاً)،
        مع أخذ آخر إشارة لكل عملة فقط لتفادي تكرار نفس العملة عدة مرات.
        """
        if hours is None:
            hours = FETCH_INTERVAL_HOURS * 2  # نافذة أمان: ضعف فترة الجلب
        cutoff = datetime.now() - timedelta(hours=hours)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT s.symbol, sig.score, sig.entry, sig.sl, sig.tp1, sig.rr, sig.timestamp
            FROM signals sig
            JOIN symbols s ON s.id = sig.symbol_id
            WHERE sig.timestamp >= ?
              AND sig.id = (
                  SELECT MAX(id) FROM signals WHERE symbol_id = sig.symbol_id
              )
            ORDER BY sig.score DESC, sig.timestamp DESC
            LIMIT ?
        ''', (cutoff, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_latest_data(self, limit: int = 50):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT s.symbol, md.*
            FROM market_data md
            JOIN symbols s ON s.id = md.symbol_id
            ORDER BY md.timestamp DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_symbol_history(self, symbol: str, limit: int = 50):
        symbol_id = self.get_symbol_id(symbol)
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM market_data
            WHERE symbol_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (symbol_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def search_symbols(self, query: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT symbol FROM symbols
            WHERE symbol LIKE ?
            LIMIT 20
        ''', (f'%{query.upper()}%',))
        return [row['symbol'] for row in cursor.fetchall()]

    def close(self):
        self.conn.close()

db = Database()