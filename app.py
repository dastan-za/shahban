import os
from flask import Flask, request, redirect, session, url_for, render_template_string
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "shahban_super_secret_key"

# بەستنەوە بە داتابەیسی ڕێندەر
MYSQL_URL = "mysql+pymysql://root:HITVDFaMFehpQFmWrZlnaTKtavNtBZyw@sakura.proxy.rlwy.net:31707/shahban"
engine = create_engine(MYSQL_URL, pool_recycle=3600, pool_pre_ping=True)

# ئامادەکردنی داتابەیس
with engine.begin() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) UNIQUE, password VARCHAR(50), role VARCHAR(50))"))
    if conn.execute(text("SELECT COUNT(*) FROM users WHERE username='admin'")).scalar() == 0:
        conn.execute(text("INSERT INTO users (username, password, role) VALUES ('admin', '12345', 'admin')"))
    if conn.execute(text("SELECT COUNT(*) FROM users WHERE username='dastan'")).scalar() == 0:
        conn.execute(text("INSERT INTO users (username, password, role) VALUES ('dastan', '1111', 'user')"))
        
    conn.execute(text("CREATE TABLE IF NOT EXISTS clients (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), phone VARCHAR(50))"))
    
    # خشتەی موڵکەکان
    conn.execute(text("""CREATE TABLE IF NOT EXISTS properties (
        id INT AUTO_INCREMENT PRIMARY KEY, 
        property_type VARCHAR(50), 
        property_number VARCHAR(100), 
        area VARCHAR(100), 
        address VARCHAR(255), 
        location VARCHAR(100), 
        neighborhood VARCHAR(100), 
        orientation VARCHAR(100), 
        price DECIMAL(15,2), 
        currency VARCHAR(20) DEFAULT 'دۆلار', 
        eviction_period VARCHAR(100), 
        eviction_date VARCHAR(50), 
        monthly_rent VARCHAR(100), 
        specs TEXT, 
        block_number VARCHAR(100), 
        eviction_penalty VARCHAR(255), 
        status VARCHAR(50) DEFAULT 'بەردەستە'
    )"""))
    
    conn.execute(text("CREATE TABLE IF NOT EXISTS transactions (id INT AUTO_INCREMENT PRIMARY KEY, transaction_type VARCHAR(50), amount DECIMAL(15,2), description TEXT, transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS contracts (id INT PRIMARY KEY, property_id INT, seller_id INT, buyer_id INT, contract_date DATE, total_price DECIMAL(15,2), advance_payment DECIMAL(15,2) DEFAULT 0, currency VARCHAR(20) DEFAULT 'دۆلار', office_commission DECIMAL(15,2), witness1 VARCHAR(100), witness2 VARCHAR(100), contract_details TEXT)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS safe_box (id INT AUTO_INCREMENT PRIMARY KEY, trans_date DATE, person_name VARCHAR(255), amount DECIMAL(15,2), currency VARCHAR(50), trans_type VARCHAR(50), note TEXT)"))

# چارەسەری ئیرۆرەکەی کاتی کردنەوەی موڵکی بەردەست بە شێوەیەکی پارێزراو
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE properties ADD COLUMN owner_name VARCHAR(100)"))
        conn.commit()
except Exception:
    pass

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE properties ADD COLUMN owner_phone VARCHAR(50)"))
        conn.commit()
except Exception:
    pass

# قاڵبی بنەڕەتی HTML
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ku" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>نوسینگەی شەعبان</title>
    <script>
        const themes = {
            'crimson': { primary: '#e11d48', bg: '#1c050a', card: '#2e0a13', border: '#4c1020' }, 
            'emerald': { primary: '#10b981', bg: '#022c22', card: '#064e3b', border: '#065f46' }, 
            'gold': { primary: '#f59e0b', bg: '#0f172a', card: '#1e293b', border: '#334155' },    
            'diamond': { primary: '#cbd5e1', bg: '#050505', card: '#121212', border: '#262626' }  
        };
        function applyTheme(name) {
            const t = themes[name] || themes['gold'];
            document.documentElement.style.setProperty('--main-color', t.primary);
            document.documentElement.style.setProperty('--bg-dark', t.bg);
            document.documentElement.style.setProperty('--bg-card', t.card);
            document.documentElement.style.setProperty('--border-color', t.border);
            localStorage.setItem('shahban_theme_name', name);
        }
        const savedTheme = localStorage.getItem('shahban_theme_name') || 'gold';
        applyTheme(savedTheme);
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;900&display=swap');
        :root { --main-color: #f59e0b; --bg-dark: #0f172a; --bg-card: #1e293b; --border-color: #334155; }
        body { background-color: var(--bg-dark); color: #cbd5e1; font-family: 'Noto Kufi Arabic', sans-serif; margin: 0; padding: 0; transition: background-color 0.3s; overflow-x: hidden; }
        
        .container { padding: 20px; max-width: 1400px; margin: auto; }
        
        .main-menu { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 30px; background: var(--bg-card); padding: 15px; border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 10px 25px rgba(0,0,0,0.3); position: relative; overflow: hidden; }
        .main-menu::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 60%); pointer-events: none; }
        .main-menu a { flex: 1; min-width: 120px; text-align: center; color: #f8fafc; text-decoration: none; font-weight: bold; font-size: 14px; padding: 12px 10px; border-radius: 10px; transition: 0.3s; background-color: var(--bg-dark); border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: center; gap: 6px; z-index: 1; }
        .main-menu a:hover { background-color: var(--main-color); color: var(--bg-dark); transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.4); border-color: var(--main-color); }
        .main-menu a.danger-menu { background-color: #450a0a; color: #fca5a5; border-color: #7f1d1d; }
        .main-menu a.danger-menu:hover { background-color: #dc2626; color: white; border-color: #ef4444; }
        .menu-title { width: 100%; text-align: center; color: var(--main-color); font-size: 24px; font-weight: 900; margin-bottom: 15px; text-shadow: 0 2px 4px rgba(0,0,0,0.3); z-index: 1; display: flex; align-items: center; justify-content: center; gap: 15px; }
        .menu-logo { height: 45px; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); }

        .card { background-color: var(--bg-card); padding: 25px; border-radius: 12px; border: 1px solid var(--border-color); box-shadow: 0 10px 15px rgba(0,0,0,0.3); margin-bottom: 20px; border-top: 4px solid var(--main-color); transition: 0.3s; width: 100%; box-sizing: border-box; }
        
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
        .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }
        .grid-30-70 { display: grid; grid-template-columns: 30fr 70fr; gap: 20px; }
        .grid-35-65 { display: grid; grid-template-columns: 35fr 65fr; gap: 20px; }
        
        label { font-weight: bold; color: var(--main-color); display: block; margin-top: 15px; margin-bottom: 5px; font-size: 14px; }
        input, select { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); background-color: var(--bg-dark); color: #f8fafc; font-family: 'Noto Kufi Arabic'; font-weight: bold; box-sizing: border-box; transition: 0.3s; font-size: 14px; }
        input:focus, select:focus { outline: none; border-color: var(--main-color); box-shadow: 0 0 8px rgba(0,0,0,0.4); }
        .btn-primary { background-color: var(--main-color); color: var(--bg-dark); width: 100%; padding: 14px; border: none; border-radius: 8px; font-weight: 900; font-size: 16px; font-family: 'Noto Kufi Arabic'; cursor: pointer; margin-top: 25px; transition: 0.3s; display: block; text-align: center; text-decoration: none; box-sizing: border-box; }
        .btn-primary:hover { opacity: 0.8; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        
        .action-flex { display: flex; gap: 8px; align-items: center; justify-content: center; }
        .action-btn { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 6px; cursor: pointer; border: none; font-size: 16px; text-decoration: none; transition: 0.2s; }
        .action-btn:hover { transform: scale(1.1); }
        .btn-warning { background-color: #f59e0b; color: white; }
        .btn-danger { background-color: #ef4444; color: white; }
        .btn-print { background-color: #3b82f6; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-weight:bold; font-family: 'Noto Kufi Arabic'; text-decoration: none; display:inline-block; }
        
        .table-responsive { overflow-x: auto; width: 100%; border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; text-align: right; min-width: 650px; }
        th, td { padding: 12px 10px; border-bottom: 1px solid var(--border-color); font-size: 14px; }
        th { background-color: var(--bg-dark); color: var(--main-color); font-weight: 900; white-space: nowrap; }
        tr:hover { background-color: var(--border-color); }
        .section-title { color: var(--main-color); font-size: 18px; font-weight: 900; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid var(--border-color); padding-bottom: 5px; }

        @media (max-width: 768px) {
            .grid-2, .grid-3, .grid-4, .grid-30-70, .grid-35-65 { grid-template-columns: 1fr; gap: 10px; }
            .container { padding: 10px; }
            .card { padding: 15px; }
            .main-menu a { min-width: 45%; font-size: 13px; padding: 10px; }
            .menu-title { font-size: 20px; }
            .menu-logo { height: 35px; }
            input, select { padding: 10px; font-size: 13px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="main-menu">
            <div class="menu-title">
                <img src="/static/logo.png" onerror="this.style.display='none'" class="menu-logo" alt="لۆگۆ">
                نوسینگەی شەعبان
            </div>
            <a href="/dashboard"><span>🏠</span> داشبۆرد</a>
            <a href="/properties_available"><span>🏢</span> موڵکی بەردەست</a>
            <a href="/contract"><span>📝</span> گرێبەست</a>
            <a href="/archive"><span>🗂️</span> ئەرشیف</a>
            <a href="/expenses"><span>💸</span> مەسروفات</a>
            <a href="/safe"><span>💰</span> قاسە</a>
            <a href="/users" style="border-color: #3b82f6; color: #3b82f6;"><span>👥</span> بەکارهێنەران</a>
            <a href="/logout" class="danger-menu"><span>🚪</span> دەرچوون</a>
        </div>
        <!--CONTENT_PLACEHOLDER-->
    </div>
    
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const pType = document.querySelector('select[name="p_type"]');
            const evRow = document.getElementById('eviction_row');
            if (pType && evRow) {
                function toggleEv() {
                    if (pType.value === 'زەوی') {
                        evRow.style.display = 'none';
                    } else {
                        evRow.style.display = 'grid'; 
                        if(window.innerWidth > 768) { evRow.style.gridTemplateColumns = 'repeat(4, 1fr)'; }
                        else { evRow.style.gridTemplateColumns = '1fr'; }
                    }
                }
                pType.addEventListener('change', toggleEv);
                window.addEventListener('resize', toggleEv);
                toggleEv();
            }
        });
    </script>
</body>
</html>
"""

# ==========================================
# ڕاوتەکان
# ==========================================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        with engine.connect() as conn:
            res = conn.execute(text("SELECT * FROM users WHERE username=:u AND password=:p"), {"u": user, "p": pwd}).fetchone()
            if res:
                session['logged_in'] = True
                return redirect(url_for('dashboard'))
            else:
                return "<h3 style='text-align:center; color:red; margin-top:50px; font-family: Tahoma;'>ناو یان وشەی نهێنی هەڵەیە! <a href='/'>گەڕانەوە</a></h3>"
    
    login_html = """
    <!DOCTYPE html>
    <html lang="ku" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>چوونەژوورەوە</title>
        <script>
            const themes = {
                'crimson': { primary: '#e11d48', bg: '#1c050a', card: '#2e0a13', border: '#4c1020' }, 
                'emerald': { primary: '#10b981', bg: '#022c22', card: '#064e3b', border: '#065f46' }, 
                'gold': { primary: '#f59e0b', bg: '#0f172a', card: '#1e293b', border: '#334155' },    
                'diamond': { primary: '#cbd5e1', bg: '#050505', card: '#121212', border: '#262626' }  
            };
            function applyTheme(name) {
                const t = themes[name] || themes['gold'];
                document.documentElement.style.setProperty('--main-color', t.primary);
                document.documentElement.style.setProperty('--bg-dark', t.bg);
                document.documentElement.style.setProperty('--bg-card', t.card);
                document.documentElement.style.setProperty('--border-color', t.border);
                localStorage.setItem('shahban_theme_name', name);
            }
            window.onload = function() {
                const savedTheme = localStorage.getItem('shahban_theme_name') || 'gold';
                applyTheme(savedTheme);
            }
        </script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700;900&display=swap');
            :root { --main-color: #f59e0b; --bg-dark: #0f172a; --bg-card: #1e293b; --border-color: #334155; }
            body { background: radial-gradient(circle at center, var(--bg-card) 0%, var(--bg-dark) 100%); font-family: 'Noto Kufi Arabic', sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; color: white; transition: background 0.3s; }
            .login-box { background: var(--bg-card); border: 1px solid var(--border-color); padding: 30px; border-radius: 16px; box-shadow: 0 15px 35px rgba(0,0,0,0.5); width: 90%; max-width: 350px; text-align: center; border-top: 5px solid var(--main-color); transition: 0.3s; box-sizing: border-box; }
            input { width: 100%; padding: 15px; margin: 15px 0; border-radius: 8px; border: 1px solid var(--border-color); background: var(--bg-dark); color: white; font-family: 'Noto Kufi Arabic'; font-weight:bold; box-sizing: border-box; transition: 0.3s; font-size: 15px; }
            input:focus { outline: none; border-color: var(--main-color); box-shadow: 0 0 10px rgba(0,0,0,0.5); }
            button { width: 100%; padding: 15px; border: none; background: var(--main-color); color: var(--bg-dark); font-weight: 900; font-size:18px; font-family: 'Noto Kufi Arabic'; border-radius: 8px; cursor: pointer; transition: 0.3s; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
            button:hover { transform: scale(1.03); }
            .color-picker { margin-bottom: 25px; display: flex; justify-content: center; gap: 15px; background: rgba(255,255,255,0.05); padding: 10px 20px; border-radius: 30px; border: 1px solid var(--border-color); flex-wrap: wrap; }
            .color-circle { width: 25px; height: 25px; border-radius: 50%; cursor: pointer; border: 2px solid white; transition: 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.5); }
            .color-circle:hover { transform: scale(1.2); }
        </style>
    </head>
    <body>
        <div class="color-picker">
            <div class="color-circle" style="background:#e11d48;" onclick="applyTheme('crimson')" title="جەرگی"></div>
            <div class="color-circle" style="background:#10b981;" onclick="applyTheme('emerald')" title="سەوز"></div>
            <div class="color-circle" style="background:#f59e0b;" onclick="applyTheme('gold')" title="گۆڵد"></div>
            <div class="color-circle" style="background:#cbd5e1;" onclick="applyTheme('diamond')" title="ڕەشی ئەڵماسی"></div>
        </div>
        <div class="login-box">
            <h2 style="color:var(--main-color); font-weight:900; text-shadow: 0 0 10px rgba(0,0,0,0.5); font-size:24px;">🏢 نوسینگەی شەعبان</h2>
            <form method="POST">
                <input type="text" name="username" placeholder="ناوی بەکارهێنەر" required autocomplete="off">
                <input type="password" name="password" placeholder="وشەی نهێنی" required>
                <button type="submit">چوونەژوورەوە</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(login_html)

@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.connect() as conn:
        clients_count = conn.execute(text("SELECT COUNT(*) FROM clients")).scalar() or 0
        avail_props = conn.execute(text("SELECT COUNT(*) FROM properties WHERE status='بەردەستە'")).scalar() or 0
        contracts_count = conn.execute(text("SELECT COUNT(*) FROM contracts")).scalar() or 0
        total_income = conn.execute(text("SELECT SUM(amount) FROM transactions WHERE transaction_type='داهات'")).scalar() or 0

    content = """
    <style>
        /* دیزاینی نوێ و مۆدێرنی داشبۆرد */
        .welcome-banner { background: linear-gradient(135deg, rgba(245,158,11,0.1) 0%, rgba(245,158,11,0.02) 100%); border-right: 4px solid var(--main-color); padding: 40px 30px; border-radius: 16px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); position: relative; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); }
        .welcome-banner::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.03) 0%, transparent 60%); pointer-events: none; }
        .welcome-text h1 { color: var(--main-color); margin: 0 0 10px 0; font-size: 32px; font-weight: 900; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
        .welcome-text p { color: #cbd5e1; margin: 0; font-size: 16px; line-height: 1.6; max-width: 600px; }
        .welcome-logo { max-width: 150px; opacity: 0.9; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.4)); z-index: 1; transition: 0.3s; }
        .welcome-logo:hover { transform: scale(1.05); }
        
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card-new { background: var(--bg-card); padding: 25px; border-radius: 16px; display: flex; align-items: center; justify-content: space-between; border: 1px solid var(--border-color); box-shadow: 0 8px 15px rgba(0,0,0,0.2); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; cursor: default; }
        .stat-card-new:hover { transform: translateY(-5px); box-shadow: 0 15px 30px rgba(0,0,0,0.4); border-color: var(--main-color); }
        .stat-card-new::after { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; }
        .stat-card-new.c1::after { background: #f59e0b; }
        .stat-card-new.c2::after { background: #3b82f6; }
        .stat-card-new.c3::after { background: #a855f7; }
        .stat-card-new.c4::after { background: #10b981; }
        
        .stat-info { z-index: 1; }
        .stat-title { color: #94a3b8; font-size: 14px; font-weight: bold; margin-bottom: 8px; }
        .stat-value { color: var(--main-color); font-size: 34px; font-weight: 900; margin: 0; line-height: 1; }
        .stat-icon { font-size: 50px; opacity: 0.15; position: absolute; left: -5px; bottom: -10px; transform: rotate(-15deg); transition: 0.4s; }
        .stat-card-new:hover .stat-icon { transform: rotate(0deg) scale(1.1); opacity: 0.3; }

        .dashboard-sections { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
        .action-panel { background: var(--bg-card); border-radius: 16px; padding: 30px; border: 1px solid var(--border-color); box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
        .action-header { display: flex; align-items: center; gap: 15px; border-bottom: 2px solid rgba(255,255,255,0.05); padding-bottom: 15px; margin-bottom: 25px; }
        .action-header h3 { margin: 0; color: #fff; font-size: 20px; font-weight: 900; }
        .action-icon { background: rgba(245,158,11,0.1); color: var(--main-color); width: 45px; height: 45px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
        
        .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .btn-dash { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; color: #e2e8f0; text-decoration: none; font-weight: bold; transition: 0.3s; text-align: center; }
        .btn-dash i { font-size: 32px; margin-bottom: 5px; transition: 0.3s; }
        .btn-dash:hover { background: var(--main-color); color: var(--bg-dark); transform: translateY(-4px); box-shadow: 0 10px 20px rgba(245,158,11,0.3); }
        .btn-dash:hover i { transform: scale(1.2); }
        
        .btn-dash-row { display: flex; flex-direction: row; align-items: center; justify-content: flex-start; gap: 20px; padding: 20px 25px; font-size: 16px; }
        .btn-dash-row i { margin-bottom: 0; font-size: 28px; }

        @media (max-width: 768px) {
            .dashboard-sections { grid-template-columns: 1fr; }
            .welcome-banner { flex-direction: column; text-align: center; border-right: none; border-top: 4px solid var(--main-color); gap: 20px; }
            .welcome-logo { max-width: 120px; }
            .stat-grid { grid-template-columns: 1fr 1fr; }
            .stat-value { font-size: 26px; }
        }
    </style>

    <!-- بانەری سەرەکی -->
    <div class="welcome-banner">
        <div class="welcome-text">
            <h1>داشبۆردی بەڕێوەبردن</h1>
            <p>بەخێربێیت بۆ نوسینگەی شەعبان، لێرەوە دەتوانیت بە خێرایی و ئاسانی کۆنترۆڵی سەرجەم گرێبەست، حیسابات و موڵکەکان بکەیت.</p>
        </div>
        <img src="/static/logo.png" onerror="this.style.display='none'" alt="لۆگۆ" class="welcome-logo">
    </div>
    
    <!-- کارتەکانی ئامار -->
    <div class="stat-grid">
        <div class="stat-card-new c1">
            <div class="stat-info">
                <div class="stat-title">کۆی کڕیارەکان</div>
                <div class="stat-value">{{ clients_count }}</div>
            </div>
            <div class="stat-icon">👥</div>
        </div>
        <div class="stat-card-new c2">
            <div class="stat-info">
                <div class="stat-title">موڵکی بەردەست</div>
                <div class="stat-value">{{ avail_props }}</div>
            </div>
            <div class="stat-icon">🏢</div>
        </div>
        <div class="stat-card-new c3">
            <div class="stat-info">
                <div class="stat-title">گرێبەستەکان</div>
                <div class="stat-value">{{ contracts_count }}</div>
            </div>
            <div class="stat-icon">📝</div>
        </div>
        <div class="stat-card-new c4">
            <div class="stat-info">
                <div class="stat-title">داهاتی قاسە</div>
                <div class="stat-value" dir="ltr">{{ "{:,.0f}".format(total_income) }} $</div>
            </div>
            <div class="stat-icon">💰</div>
        </div>
    </div>
    
    <!-- بەشەکانی گەیشتنی خێرا -->
    <div class="dashboard-sections">
        <div class="action-panel">
            <div class="action-header">
                <div class="action-icon">⚡</div>
                <h3>گەیشتنی خێرا</h3>
            </div>
            <div class="btn-grid">
                <a href="/contract" class="btn-dash"><i>📝</i> <span>گرێبەستی نوێ</span></a>
                <a href="/properties_available" class="btn-dash"><i>🏢</i> <span>تۆماری موڵک</span></a>
                <a href="/safe" class="btn-dash"><i>📥</i> <span>پارە وەرگرتن</span></a>
                <a href="/expenses" class="btn-dash"><i>💸</i> <span>تۆماری خەرجی</span></a>
            </div>
        </div>
        
        <div class="action-panel">
            <div class="action-header">
                <div class="action-icon" style="color: #ef4444; background: rgba(239,68,68,0.1);">📊</div>
                <h3 style="color: #fca5a5;">ڕاپۆرت و داتا</h3>
            </div>
            <div class="btn-grid" style="grid-template-columns: 1fr;">
                <a href="/archive" class="btn-dash btn-dash-row" style="border-left: 3px solid #3b82f6;">
                    <i>🗂️</i> <span>بینینی ئەرشیفی گرێبەستەکان</span>
                </a>
                <a href="/users" class="btn-dash btn-dash-row" style="border-left: 3px solid #10b981;">
                    <i>👥</i> <span>بەڕێوەبردنی بەکارهێنەران</span>
                </a>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content), clients_count=clients_count, avail_props=avail_props, contracts_count=contracts_count, total_income=total_income)

@app.route("/properties_available", methods=["GET", "POST"])
def properties_available():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    # فلتەرەکان
    f_type = request.args.get('f_type', '')
    f_loc = request.args.get('f_loc', '')
    f_neigh = request.args.get('f_neigh', '')
    
    query = "SELECT * FROM properties WHERE status='بەردەستە'"
    params = {}
    if f_type:
        query += " AND property_type = :t"
        params['t'] = f_type
    if f_loc:
        query += " AND location = :l"
        params['l'] = f_loc
    if f_neigh:
        query += " AND neighborhood = :n"
        params['n'] = f_neigh
        
    query += " ORDER BY id DESC"
    
    with engine.connect() as conn:
        props = conn.execute(text(query), params).mappings().fetchall()
        types_res = conn.execute(text("SELECT DISTINCT property_type FROM properties")).fetchall()
        locs_res = conn.execute(text("SELECT DISTINCT location FROM properties WHERE location != ''")).fetchall()
        neighs_res = conn.execute(text("SELECT DISTINCT neighborhood FROM properties WHERE neighborhood != ''")).fetchall()
        
    p_types = [r[0] for r in types_res if r[0]]
    p_locs = list(set([r[0] for r in locs_res if r[0]] + ['ڕانیە', 'چوارقوڕنە', 'حاجیاوا', 'سەرکەپکان', 'بۆسکێن']))
    p_neighs = list(set([r[0] for r in neighs_res if r[0]] + ['ئازادی١', 'سەرا', 'نەورۆز', 'شارەوانی', 'داستان']))

    content = """
    <style>
        /* دیزاینی تایبەتی ئەم پەڕەیە */
        .modern-layout { display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; }
        .form-section { flex: 1; min-width: 320px; background: linear-gradient(145deg, var(--bg-card), var(--bg-dark)); padding: 25px; border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .list-section { flex: 2.5; min-width: 300px; }
        
        .form-section input, .form-section select { background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: #fff; padding: 14px 15px; font-weight: normal; font-size: 14px; transition: all 0.3s; margin-bottom: 18px; width: 100%; box-sizing: border-box; }
        .form-section input::placeholder { color: #94a3b8; }
        .form-section input:focus, .form-section select:focus { border-color: var(--main-color); background: rgba(0,0,0,0.4); box-shadow: 0 0 12px rgba(245, 158, 11, 0.2); }
        .btn-modern { background: linear-gradient(45deg, var(--main-color), #d97706); border: none; color: #fff; font-weight: bold; font-family: 'Noto Kufi Arabic'; padding: 14px; border-radius: 10px; width: 100%; margin-top: 10px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .btn-modern:hover { transform: translateY(-3px); box-shadow: 0 8px 15px rgba(245, 158, 11, 0.4); }

        .filter-card { background: var(--bg-card); padding: 15px 20px; border-radius: 16px; margin-bottom: 20px; border: 1px solid var(--border-color); box-shadow: 0 5px 15px rgba(0,0,0,0.2); display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-end; }
        .filter-card select, .filter-card input { background: var(--bg-dark); border-radius: 8px; border: 1px solid var(--border-color); padding: 10px; color: white; min-width: 150px; }
        
        /* Grid-ی کارتەکانی موڵک */
        .properties-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
        .prop-card { background: var(--bg-card); border-radius: 16px; overflow: hidden; border: 1px solid var(--border-color); box-shadow: 0 8px 20px rgba(0,0,0,0.2); transition: all 0.3s; display: flex; flex-direction: column; position: relative; }
        .prop-card:hover { transform: translateY(-5px); border-color: var(--main-color); box-shadow: 0 15px 30px rgba(0,0,0,0.4); }
        
        .prop-header { padding: 20px; text-align: left; background: rgba(0,0,0,0.1); border-bottom: 1px solid rgba(255,255,255,0.05); }
        .badge-type { position: absolute; top: 15px; right: 15px; background: rgba(245, 158, 11, 0.15); color: var(--main-color); padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid rgba(245, 158, 11, 0.3); }
        .price-text { font-size: 24px; font-weight: 900; color: #10b981; text-align: left; direction: ltr; }
        .currency-span { font-size: 14px; color: #94a3b8; font-weight: normal; }
        
        .prop-body { padding: 20px; flex-grow: 1; }
        .info-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; font-size: 13.5px; color: #cbd5e1; }
        .info-icon { font-size: 16px; width: 25px; text-align: center; }
        .owner-name { color: #f8fafc; font-weight: bold; }
        
        .prop-footer { padding: 15px 20px; background: rgba(0,0,0,0.2); border-top: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
        .action-circle { width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; text-decoration: none; font-size: 14px; transition: 0.2s; border: none; cursor: pointer; }
        .action-circle:hover { transform: scale(1.15); }
        .edit-btn { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .del-btn { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
    </style>

    <div class="modern-layout">
        <!-- بەشی تۆمارکردن بەبێ تایتڵ (تەنها پڵەیسهۆڵدەر) -->
        <div class="form-section">
            <h3 style="color:var(--main-color); text-align:center; margin-top:0; margin-bottom: 25px; font-size:20px;">➕ تۆمارکردنی موڵکی نوێ</h3>
            <form method="POST" action="/add_property_available">
                
                <input type="text" name="owner_name" required autocomplete="off" placeholder="ناوی خاوەن موڵک بنوسە">
                
                <input type="text" name="owner_phone" placeholder="مۆبایلی خاوەن موڵک بنوسە">
                
                <select name="property_type" required>
                    <option value="" disabled selected>جۆری موڵک دیاری بکە</option>
                    <option value="خانوو">خانوو</option>
                    <option value="زەوی">زەوی</option>
                    <option value="شوقە">شوقە</option>
                    <option value="دوکان">دوکان</option>
                    <option value="باغ">باغ</option>
                    <option value="دەواجین">دەواجین</option>
                    <option value="بەنزینخانە">بەنزینخانە</option>
                    <option value="کارگە">کارگە</option>
                </select>
                
                <!-- تەنها نرخ و دراو تایتڵیان هەیە -->
                <div class="grid-2" style="margin-bottom: 18px;">
                    <div style="margin-bottom: 0;">
                        <label style="margin-top:0; font-size:12px; margin-bottom:5px;">💰 نرخی موڵک</label>
                        <input type="number" step="0.01" name="price" required placeholder="0.00" style="margin-bottom:0;">
                    </div>
                    <div style="margin-bottom: 0;">
                        <label style="margin-top:0; font-size:12px; margin-bottom:5px;">💵 دراو</label>
                        <select name="currency" style="margin-bottom:0;"><option>دۆلار</option><option>دینار</option></select>
                    </div>
                </div>
                
                <input list="loc_list" name="location" required autocomplete="off" placeholder="شوێنی مووڵک هەڵبژێرە یان بنوسە">
                <datalist id="loc_list">{% for l in locs %}<option value="{{ l }}">{% endfor %}</datalist>
                
                <input list="neigh_list" name="neighborhood" required autocomplete="off" placeholder="گەڕەک هەڵبژێرە یان بنوسە">
                <datalist id="neigh_list">{% for n in neighs %}<option value="{{ n }}">{% endfor %}</datalist>
                
                <input type="text" name="specs" placeholder="تێبینی موسەفات یان هەرزانیاریەک بنوسە">
                
                <button type="submit" class="btn-modern">💾 پاشەکەوتکردنی موڵک</button>
            </form>
        </div>
        
        <!-- بەشی پیشاندان و فلتەر -->
        <div class="list-section">
            <!-- فلتەر -->
            <form class="filter-card" method="GET" action="/properties_available">
                <div style="flex:1;">
                    <label style="font-size:12px; color:#94a3b8; margin:0 0 5px 0;">جۆری موڵک</label>
                    <select name="f_type">
                        <option value="">هەموو جۆرەکان</option>
                        <option value="خانوو" {% if f_type=='خانوو' %}selected{% endif %}>خانوو</option>
                        <option value="زەوی" {% if f_type=='زەوی' %}selected{% endif %}>زەوی</option>
                        <option value="شوقە" {% if f_type=='شوقە' %}selected{% endif %}>شوقە</option>
                        <option value="دوکان" {% if f_type=='دوکان' %}selected{% endif %}>دوکان</option>
                        <option value="باغ" {% if f_type=='باغ' %}selected{% endif %}>باغ</option>
                    </select>
                </div>
                <div style="flex:1;">
                    <label style="font-size:12px; color:#94a3b8; margin:0 0 5px 0;">شوێن</label>
                    <input list="loc_list" name="f_loc" value="{{ f_loc }}" placeholder="بۆ نموونە: ڕانیە">
                </div>
                <div style="flex:1;">
                    <label style="font-size:12px; color:#94a3b8; margin:0 0 5px 0;">گەڕەک</label>
                    <input list="neigh_list" name="f_neigh" value="{{ f_neigh }}" placeholder="ناوی گەڕەک...">
                </div>
                <div style="display:flex; gap:10px;">
                    <button type="submit" style="background:#3b82f6; color:white; border:none; padding:10px 20px; border-radius:8px; font-family:'Noto Kufi Arabic'; font-weight:bold; cursor:pointer;">🔍 فلتەر</button>
                    <a href="/properties_available" style="background:#ef4444; color:white; text-decoration:none; padding:10px 20px; border-radius:8px; font-weight:bold; display:flex; align-items:center;">لادان</a>
                </div>
            </form>
            
            <!-- کارتەکانی موڵک -->
            <div class="properties-grid">
                {% for p in props %}
                <div class="prop-card">
                    <span class="badge-type">{{ p.get('property_type', '') }}</span>
                    <div class="prop-header">
                        <div class="price-text">{{ "{:,.0f}".format(p.get('price') or 0) }} <span class="currency-span">{{ p.get('currency', '') }}</span></div>
                    </div>
                    <div class="prop-body">
                        <div class="info-row">
                            <span class="info-icon">📍</span>
                            <span>{{ p.get('location', '') }} - {{ p.get('neighborhood', '') }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-icon">👤</span>
                            <span class="owner-name">{{ p.get('owner_name') or 'نەزانراو' }}</span>
                        </div>
                        <div class="info-row" style="direction:ltr; justify-content:flex-end;">
                            <span style="color:#94a3b8; font-size:12px;">{{ p.get('owner_phone') or '-' }}</span>
                            <span class="info-icon">📱</span>
                        </div>
                        {% if p.get('specs') %}
                        <div class="info-row" style="align-items:flex-start; margin-top:15px; padding-top:15px; border-top:1px dashed rgba(255,255,255,0.1);">
                            <span class="info-icon">📝</span>
                            <span style="font-size:12px; line-height:1.6; color:#94a3b8;">{{ p.get('specs', '') }}</span>
                        </div>
                        {% endif %}
                    </div>
                    <div class="prop-footer">
                        <span style="font-size:11px; color:#10b981; font-weight:bold;">🟢 {{ p.get('status', '') }}</span>
                        <div style="display:flex; gap:10px;">
                            <a href="/edit_property/{{ p.get('id') }}" class="action-circle edit-btn" title="دەستکاری">✏️</a>
                            <form method="POST" action="/delete_property/{{ p.get('id') }}" style="margin:0;">
                                <button type="submit" class="action-circle del-btn" onclick="return confirm('ئەم موڵکە بسڕێتەوە؟');" title="سڕینەوە">🗑️</button>
                            </form>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            {% if not props %}
            <div style="text-align:center; padding:50px; background:var(--bg-card); border-radius:16px; border:1px dashed var(--border-color); color:#94a3b8;">
                <h3 style="margin-bottom:10px;">هیچ موڵکێک نەدۆزرایەوە 🔍</h3>
                <p>بەپێی ئەو فلتەرانەی دیاریت کردوون هیچ ئەنجامێک نییە، یان هێشتا موڵک تۆمار نەکراوە.</p>
            </div>
            {% endif %}
            
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content), props=props, locs=p_locs, neighs=p_neighs, f_type=f_type, f_loc=f_loc, f_neigh=f_neigh)

@app.route("/add_property_available", methods=["POST"])
def add_property_available():
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.begin() as conn:
        conn.execute(text("""INSERT INTO properties 
            (owner_name, owner_phone, property_type, price, currency, location, neighborhood, address, specs, status) 
            VALUES (:on, :op, :pt, :pr, :cur, :loc, :neigh, :ad, :sp, 'بەردەستە')"""),
            {
                "on": request.form.get("owner_name"),
                "op": request.form.get("owner_phone"),
                "pt": request.form.get("property_type"),
                "pr": float(request.form.get("price") or 0),
                "cur": request.form.get("currency"),
                "loc": request.form.get("location"),
                "neigh": request.form.get("neighborhood"),
                "ad": f"{request.form.get('location')} - {request.form.get('neighborhood')}",
                "sp": request.form.get("specs")
            })
    return redirect(url_for('properties_available'))

@app.route("/edit_property/<int:id>", methods=["GET", "POST"])
def edit_property(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == "POST":
        with engine.begin() as conn:
            conn.execute(text("""UPDATE properties SET 
                owner_name=:on, owner_phone=:op, property_type=:pt, price=:pr, currency=:cur, location=:loc, neighborhood=:neigh, specs=:sp 
                WHERE id=:id"""),
                {
                    "on": request.form.get("owner_name"),
                    "op": request.form.get("owner_phone"),
                    "pt": request.form.get("property_type"),
                    "pr": float(request.form.get("price") or 0),
                    "cur": request.form.get("currency"),
                    "loc": request.form.get("location"),
                    "neigh": request.form.get("neighborhood"),
                    "sp": request.form.get("specs"),
                    "id": id
                })
        return redirect(url_for('properties_available'))
        
    with engine.connect() as conn:
        p = conn.execute(text("SELECT * FROM properties WHERE id=:id"), {"id": id}).mappings().fetchone()
        
    content = f"""
    <div class="card" style="max-width:600px; margin:auto;">
        <h3 style="color:var(--main-color); text-align:center;">✏️ دەستکاریکردنی موڵکی بەردەست</h3>
        <form method="POST">
            <label>ناوی خاوەن موڵک:</label><input type="text" name="owner_name" value="{p.get('owner_name', '')}" required>
            <label>مۆبایلی خاوەن موڵک:</label><input type="text" name="owner_phone" value="{p.get('owner_phone', '')}">
            <label>جۆری موڵک:</label>
            <select name="property_type">
                <option value="{p.get('property_type', '')}">{p.get('property_type', '')}</option>
                <option>خانوو</option><option>زەوی</option><option>شوقە</option><option>دوکان</option><option>باغ</option><option>دەواجین</option><option>بەنزینخانە</option><option>کارگە</option>
            </select>
            <div class="grid-2">
                <div><label>نرخی موڵک:</label><input type="number" step="0.01" name="price" value="{p.get('price', 0)}" required></div>
                <div><label>دراو:</label><select name="currency"><option>{p.get('currency', 'دۆلار')}</option><option>دۆلار</option><option>دینار</option></select></div>
            </div>
            <label>شوێن:</label><input type="text" name="location" value="{p.get('location', '')}" required>
            <label>گەڕەک:</label><input type="text" name="neighborhood" value="{p.get('neighborhood', '')}" required>
            <label>تێبینی:</label><input type="text" name="specs" value="{p.get('specs', '')}">
            
            <button type="submit" class="btn-warning" style="width:100%; padding:15px; margin-top:20px; border-radius:8px; font-weight:bold; cursor:pointer; font-family:'Noto Kufi Arabic';">💾 پاشەکەوتکردن</button>
            <a href="/properties_available" class="btn-danger" style="display:block; text-align:center; margin-top:10px; padding: 12px; border-radius: 8px; text-decoration:none;">گەڕانەوە</a>
        </form>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content))

@app.route("/delete_property/<int:id>", methods=["POST"])
def delete_property(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM properties WHERE id=:id"), {"id": id})
    return redirect(url_for('properties_available'))

# ==========================================
# گرێبەست، ئەرشیف، مەسروف، قاسە، یوزەرەکان
# ==========================================
@app.route("/contract", methods=["GET", "POST"])
def contract():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    if request.method == "POST":
        c_num = request.form.get("c_number")
        with engine.begin() as conn:
            res_s = conn.execute(text("INSERT INTO clients (name, phone) VALUES (:n, :p)"), {"n": request.form.get("seller_name"), "p": request.form.get("seller_phone")})
            res_b = conn.execute(text("INSERT INTO clients (name, phone) VALUES (:n, :p)"), {"n": request.form.get("buyer_name"), "p": request.form.get("buyer_phone")})
            
            res_p = conn.execute(text("""INSERT INTO properties 
                (property_type, property_number, area, address, location, neighborhood, orientation, price, currency, eviction_period, eviction_date, monthly_rent, specs, block_number, eviction_penalty, status) 
                VALUES (:pt, :pnum, :pa, :pad, :loc, :neigh, :ori, :pr, :cur, :ev, :evd, :rent, :sp, :bn, :pen, 'فرۆشراوە')"""),
                {"pt": request.form.get("p_type"), "pnum": request.form.get("p_number"), "pa": request.form.get("p_area"), "pad": f"{request.form.get('location')} - {request.form.get('neighborhood')}", "loc": request.form.get("location"), "neigh": request.form.get("neighborhood"), "ori": request.form.get("p_orientation"), "pr": float(request.form.get("price") or 0), "cur": request.form.get("currency"), "ev": request.form.get("evict_period"), "evd": request.form.get("evict_date"), "rent": request.form.get("rent"), "sp": request.form.get("specs"), "bn": request.form.get("p_block"), "pen": request.form.get("penalty")})
            
            comm = float(request.form.get("commission") or 0)
            conn.execute(text("""INSERT INTO contracts 
                (id, property_id, seller_id, buyer_id, contract_date, total_price, advance_payment, currency, office_commission, witness1, witness2, contract_details) 
                VALUES (:cid, :pid, :sid, :bid, :dt, :tp, :ap, :cur, :oc, :w1, :w2, :nt)"""),
                {"cid": int(c_num), "pid": res_p.lastrowid, "sid": res_s.lastrowid, "bid": res_b.lastrowid, "dt": request.form.get("c_date"), "tp": float(request.form.get("price") or 0), "ap": float(request.form.get("advance") or 0), "cur": request.form.get("currency"), "oc": comm, "w1": request.form.get("wit1"), "w2": request.form.get("wit2"), "nt": request.form.get("note")})
            
            if comm > 0:
                conn.execute(text("INSERT INTO transactions (transaction_type, amount, description) VALUES ('داهات', :amt, :desc)"), {"amt": comm, "desc": f"کۆمسیۆنی گرێبەستی {c_num}"})
                
        return redirect(url_for('print_a4', id=c_num))

    with engine.connect() as conn:
        last_cnum = conn.execute(text("SELECT MAX(id) FROM contracts")).scalar()
        suggested_cnum = (last_cnum or 0) + 1
        
        clients = conn.execute(text("SELECT DISTINCT name FROM clients")).fetchall()
        locs_res = conn.execute(text("SELECT DISTINCT location FROM properties WHERE location != ''")).fetchall()
        neighs_res = conn.execute(text("SELECT DISTINCT neighborhood FROM properties WHERE neighborhood != ''")).fetchall()
        wits_res = conn.execute(text("SELECT witness1 FROM contracts UNION SELECT witness2 FROM contracts")).fetchall()
        
    c_names = [r[0] for r in clients if r[0]]
    c_locs = list(set([r[0] for r in locs_res if r[0]] + ['ڕانیە', 'چوارقوڕنە', 'حاجیاوا', 'سەرکەپکان', 'بۆسکێن']))
    c_neighs = list(set([r[0] for r in neighs_res if r[0]] + ['ئازادی١', 'سەرا', 'نەورۆز', 'شارەوانی', 'داستان']))
    c_wits = list(set([r[0] for r in wits_res if r[0]]))
    today = datetime.now().strftime("%Y-%m-%d")

    content = """
    <form method="POST">
        <div class="card">
            <h3 style="color:var(--main-color); text-align:center; margin-top:0;">📝 فۆڕمی یەکگرتووی گرێبەستی کڕین و فرۆشتن</h3>
            
            <div class="section-title">🏠 زانیاری بنەڕەتی گرێبەست</div>
            <div class="grid-4">
                <div><label>ژمارەی گرێبەست:</label><input type="number" name="c_number" value="{{ suggested_cnum }}" required></div>
                <div><label>جۆری موڵک:</label><select name="p_type"><option>زەوی</option><option>خانوو</option><option>شوقە</option><option>دوکان</option><option>باغ</option></select></div>
                <div>
                    <label>شوێنی موڵک (شار/قەزا):</label>
                    <input list="loc_list" name="location" required autocomplete="off">
                    <datalist id="loc_list">{% for l in locs %}<option value="{{ l }}">{% endfor %}</datalist>
                </div>
                <div>
                    <label>گەڕەک:</label>
                    <input list="neigh_list" name="neighborhood" required autocomplete="off">
                    <datalist id="neigh_list">{% for n in neighs %}<option value="{{ n }}">{% endfor %}</datalist>
                </div>
            </div>
            
            <div class="section-title">👤 زانیاری لایەنەکان</div>
            <div class="grid-4" style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid var(--border-color);">
                <div><label style="color:#ef4444;">ناوی فرۆشیار:</label><input list="c_list" name="seller_name" required autocomplete="off"></div>
                <div><label style="color:#ef4444;">مۆبایلی فرۆشیار:</label><input type="text" name="seller_phone"></div>
                <div><label style="color:#10b981;">ناوی کڕیار:</label><input list="c_list" name="buyer_name" required autocomplete="off"></div>
                <div><label style="color:#10b981;">مۆبایلی کڕیار:</label><input type="text" name="buyer_phone"></div>
            </div>
            <datalist id="c_list">{% for c in clients %}<option value="{{ c }}">{% endfor %}</datalist>

            <div class="section-title">📍 زانیاری وردی موڵک</div>
            <div class="grid-4">
                <div><label>ژمارەی موڵک (زەوی):</label><input type="text" name="p_number" required></div>
                <div><label>ژمارەی تاپۆ (پارچە):</label><input type="text" name="p_block"></div>
                <div><label>ڕووبەر (م٢):</label><input type="text" name="p_area" required></div>
                <div><label>ڕووی موڵک:</label><select name="p_orientation"><option>ڕۆژهەڵات</option><option>ڕۆژئاوا</option><option>ڕوو لە شاخ</option><option>قیبلە</option><option>باکوور</option><option>باشوور</option></select></div>
            </div>
            
            <div id="eviction_row" class="grid-4" style="margin-top:15px;">
                <div><label>ماوەی چۆڵکردن:</label><input type="text" name="evict_period"></div>
                <div><label>بەرواری چۆڵکردن:</label><input type="date" name="evict_date" value="{{ today }}"></div>
                <div><label>کرێی مانگانە:</label><input type="text" name="rent"></div>
                <div><label>سزای چۆڵنەکردن:</label><input type="text" name="penalty"></div>
            </div>
            
            <label>مواسەفاتی موڵک:</label><input type="text" name="specs">

            <div class="section-title">💰 زانیاری دارایی و شاهێدەکان</div>
            <div class="grid-4">
                <div><label>نرخی کۆتایی:</label><input type="number" step="0.01" name="price" required></div>
                <div><label>بڕی پێشەکی:</label><input type="number" step="0.01" name="advance" value="0"></div>
                <div><label>جۆری دراو:</label><select name="currency"><option>دۆلار</option><option>دینار</option></select></div>
                <div><label>کۆمسیۆنی نوسینگە:</label><input type="number" step="0.01" name="commission" value="0"></div>
            </div>
            <div class="grid-2" style="margin-top:15px;">
                <div>
                    <label>👁️ شاهێدی یەکەم:</label>
                    <input list="wit_list" name="wit1" required autocomplete="off">
                </div>
                <div>
                    <label>👁️ شاهێدی دووەم:</label>
                    <input list="wit_list" name="wit2" required autocomplete="off">
                </div>
            </div>
            <datalist id="wit_list">{% for w in wits %}<option value="{{ w }}">{% endfor %}</datalist>
            
            <div class="grid-2" style="margin-top:15px;">
                <div><label>📅 بەرواری گرێبەست:</label><input type="date" name="c_date" value="{{ today }}" required></div>
                <div><label>📝 تێبینی زیادە:</label><input type="text" name="note"></div>
            </div>
            
            <button type="submit" class="btn-primary">💾 تۆمارکردن و چاپکردنی گرێبەست</button>
        </div>
    </form>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content), clients=c_names, locs=c_locs, neighs=c_neighs, wits=c_wits, suggested_cnum=suggested_cnum, today=today)

@app.route("/archive")
def archive():
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.connect() as conn:
        q = text("""SELECT c.id, c.contract_date, p.property_type, p.property_number, c.total_price, c.currency, s.name, b.name 
                    FROM contracts c JOIN properties p ON c.property_id = p.id JOIN clients s ON c.seller_id = s.id JOIN clients b ON c.buyer_id = b.id ORDER BY c.id DESC""")
        data = conn.execute(q).fetchall()
        
    content = """
    <div class="card">
        <h3 style="color:var(--main-color); text-align:center; margin-top:0;">🗂 ئەرشیفی گرێبەستەکان</h3>
        <div class="table-responsive">
            <table>
                <tr><th>ژ.گرێبەست</th><th>بەروار</th><th>جۆری موڵک</th><th>فرۆشیار</th><th>کڕیار</th><th>نرخ</th><th>کردارەکان</th></tr>
                {% for r in data %}
                <tr>
                    <td style="font-weight:bold; color:var(--main-color);">{{ r[0] }}</td>
                    <td dir="ltr" style="font-size:12px;">{{ r[1] }}</td>
                    <td>{{ r[2] }} ({{ r[3] }})</td>
                    <td style="color:#ef4444;">{{ r[6] }}</td>
                    <td style="color:#10b981;">{{ r[7] }}</td>
                    <td dir="ltr" style="font-weight:900; color:var(--main-color);">{{ "{:,.0f}".format(r[4]) }} <span>{{ r[5] }}</span></td>
                    <td class="action-flex">
                        <a href="/print/{{ r[0] }}" class="btn-print" style="padding: 6px 12px; font-size:14px;" target="_blank">🖨️ چاپ</a>
                        <a href="/edit_contract/{{ r[0] }}" class="action-btn btn-warning" title="دەستکاری تەواوەتی">✏️</a>
                        <form method="POST" action="/delete_contract/{{ r[0] }}" style="margin:0;">
                            <button type="submit" class="action-btn btn-danger" onclick="return confirm('دڵنیایت لە سڕینەوەی بە یەکجاری؟');" title="سڕینەوە">🗑️</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content), data=data)

@app.route("/edit_contract/<int:id>", methods=["GET", "POST"])
def edit_contract(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    if request.method == "POST":
        with engine.begin() as conn:
            ids = conn.execute(text("SELECT property_id, seller_id, buyer_id FROM contracts WHERE id=:id"), {"id": id}).mappings().fetchone()
            
            # دەستکاری کڕیار و فرۆشیار
            conn.execute(text("UPDATE clients SET name=:n, phone=:p WHERE id=:cid"), {"n": request.form.get("seller_name"), "p": request.form.get("seller_phone"), "cid": ids['seller_id']})
            conn.execute(text("UPDATE clients SET name=:n, phone=:p WHERE id=:cid"), {"n": request.form.get("buyer_name"), "p": request.form.get("buyer_phone"), "cid": ids['buyer_id']})
            
            # دەستکاری موڵک
            conn.execute(text("""UPDATE properties SET 
                property_type=:pt, property_number=:pnum, area=:pa, address=:pad, location=:loc, neighborhood=:neigh, 
                orientation=:ori, price=:pr, currency=:cur, eviction_period=:ev, eviction_date=:evd, 
                monthly_rent=:rent, specs=:sp, block_number=:bn, eviction_penalty=:pen 
                WHERE id=:pid"""),
                {"pt": request.form.get("p_type"), "pnum": request.form.get("p_number"), "pa": request.form.get("p_area"), "pad": f"{request.form.get('location')} - {request.form.get('neighborhood')}", "loc": request.form.get("location"), "neigh": request.form.get("neighborhood"), "ori": request.form.get("p_orientation"), "pr": float(request.form.get("price") or 0), "cur": request.form.get("currency"), "ev": request.form.get("evict_period"), "evd": request.form.get("evict_date"), "rent": request.form.get("rent"), "sp": request.form.get("specs"), "bn": request.form.get("p_block"), "pen": request.form.get("penalty"), "pid": ids['property_id']})
            
            # دەستکاری گرێبەست
            conn.execute(text("""UPDATE contracts SET 
                contract_date=:dt, total_price=:tp, advance_payment=:ap, currency=:cur, 
                office_commission=:oc, witness1=:w1, witness2=:w2, contract_details=:nt 
                WHERE id=:id"""),
                {"dt": request.form.get("c_date"), "tp": float(request.form.get("price") or 0), "ap": float(request.form.get("advance") or 0), "cur": request.form.get("currency"), "oc": float(request.form.get("commission") or 0), "w1": request.form.get("wit1"), "w2": request.form.get("wit2"), "nt": request.form.get("note"), "id": id})
            
            # دەستکاری کۆمسیۆن لە خشتەی داهات
            conn.execute(text("UPDATE transactions SET amount=:amt WHERE description LIKE :desc AND transaction_type='داهات'"), {"amt": float(request.form.get("commission") or 0), "desc": f"کۆمسیۆنی گرێبەستی {id}"})
            
        return redirect(url_for('archive'))
    
    with engine.connect() as conn:
        q = text("""
            SELECT c.*,
                   p.property_type, p.property_number, p.area, p.neighborhood, p.orientation, p.block_number, p.location, p.eviction_period, p.eviction_date, p.monthly_rent, p.eviction_penalty, p.specs as p_specs,
                   s.name as seller_name, s.phone as seller_phone,
                   b.name as buyer_name, b.phone as buyer_phone
            FROM contracts c
            JOIN properties p ON c.property_id = p.id
            JOIN clients s ON c.seller_id = s.id
            JOIN clients b ON c.buyer_id = b.id
            WHERE c.id=:id
        """)
        c = conn.execute(q, {"id": id}).mappings().fetchone()
        
        clients = conn.execute(text("SELECT DISTINCT name FROM clients")).fetchall()
        locs_res = conn.execute(text("SELECT DISTINCT location FROM properties WHERE location != ''")).fetchall()
        neighs_res = conn.execute(text("SELECT DISTINCT neighborhood FROM properties WHERE neighborhood != ''")).fetchall()
        wits_res = conn.execute(text("SELECT witness1 FROM contracts UNION SELECT witness2 FROM contracts")).fetchall()
        
    if not c: return "نەدۆزرایەوە"
    
    c_names = [r[0] for r in clients if r[0]]
    c_locs = list(set([r[0] for r in locs_res if r[0]] + ['ڕانیە', 'چوارقوڕنە', 'حاجیاوا', 'سەرکەپکان', 'بۆسکێن']))
    c_neighs = list(set([r[0] for r in neighs_res if r[0]] + ['ئازادی١', 'سەرا', 'نەورۆز', 'شارەوانی', 'داستان']))
    c_wits = list(set([r[0] for r in wits_res if r[0]]))
    
    content = f"""
    <form method="POST">
        <div class="card">
            <h3 style="color:var(--main-color); text-align:center; margin-top:0;">✏️ دەستکاریکردنی گرێبەستی ژمارە {id}</h3>
            
            <div class="section-title">🏠 زانیاری بنەڕەتی گرێبەست</div>
            <div class="grid-4">
                <div><label>ژمارەی گرێبەست:</label><input type="text" value="{id}" disabled style="opacity: 0.7;"></div>
                <div><label>جۆری موڵک:</label><select name="p_type"><option value="{c['property_type']}">{c['property_type']}</option><option>زەوی</option><option>خانوو</option><option>شوقە</option><option>دوکان</option><option>باغ</option></select></div>
                <div>
                    <label>شوێنی موڵک (شار/قەزا):</label>
                    <input list="loc_list" name="location" value="{c['location']}" required autocomplete="off">
                    <datalist id="loc_list">{"".join(['<option value="'+l+'">' for l in c_locs])}</datalist>
                </div>
                <div>
                    <label>گەڕەک:</label>
                    <input list="neigh_list" name="neighborhood" value="{c['neighborhood']}" required autocomplete="off">
                    <datalist id="neigh_list">{"".join(['<option value="'+n+'">' for n in c_neighs])}</datalist>
                </div>
            </div>
            
            <div class="section-title">👤 زانیاری لایەنەکان</div>
            <div class="grid-4" style="background: var(--bg-dark); padding: 15px; border-radius: 8px; border: 1px solid var(--border-color);">
                <div><label style="color:#ef4444;">ناوی فرۆشیار:</label><input list="c_list" name="seller_name" value="{c['seller_name']}" required autocomplete="off"></div>
                <div><label style="color:#ef4444;">مۆبایلی فرۆشیار:</label><input type="text" name="seller_phone" value="{c['seller_phone'] or ''}"></div>
                <div><label style="color:#10b981;">ناوی کڕیار:</label><input list="c_list" name="buyer_name" value="{c['buyer_name']}" required autocomplete="off"></div>
                <div><label style="color:#10b981;">مۆبایلی کڕیار:</label><input type="text" name="buyer_phone" value="{c['buyer_phone'] or ''}"></div>
            </div>
            <datalist id="c_list">{"".join(['<option value="'+cl+'">' for cl in c_names])}</datalist>

            <div class="section-title">📍 زانیاری وردی موڵک</div>
            <div class="grid-4">
                <div><label>ژمارەی موڵک (زەوی):</label><input type="text" name="p_number" value="{c['property_number']}" required></div>
                <div><label>ژمارەی تاپۆ (پارچە):</label><input type="text" name="p_block" value="{c['block_number'] or ''}"></div>
                <div><label>ڕووبەر (م٢):</label><input type="text" name="p_area" value="{c['area']}" required></div>
                <div><label>ڕووی موڵک:</label><select name="p_orientation"><option value="{c['orientation']}">{c['orientation']}</option><option>ڕۆژهەڵات</option><option>ڕۆژئاوا</option><option>ڕوو لە شاخ</option><option>قیبلە</option><option>باکوور</option><option>باشوور</option></select></div>
            </div>
            
            <div id="eviction_row" class="grid-4" style="margin-top:15px;">
                <div><label>ماوەی چۆڵکردن:</label><input type="text" name="evict_period" value="{c['eviction_period'] or ''}"></div>
                <div><label>بەرواری چۆڵکردن:</label><input type="date" name="evict_date" value="{c['eviction_date']}"></div>
                <div><label>کرێی مانگانە:</label><input type="text" name="rent" value="{c['monthly_rent'] or ''}"></div>
                <div><label>سزای چۆڵنەکردن:</label><input type="text" name="penalty" value="{c['eviction_penalty'] or ''}"></div>
            </div>
            
            <label>مواسەفاتی موڵک:</label><input type="text" name="specs" value="{c['p_specs'] or ''}">

            <div class="section-title">💰 زانیاری دارایی و شاهێدەکان</div>
            <div class="grid-4">
                <div><label>نرخی کۆتایی:</label><input type="number" step="0.01" name="price" value="{c['total_price']}" required></div>
                <div><label>بڕی پێشەکی:</label><input type="number" step="0.01" name="advance" value="{c['advance_payment']}"></div>
                <div><label>جۆری دراو:</label><select name="currency"><option value="{c['currency']}">{c['currency']}</option><option>دۆلار</option><option>دینار</option></select></div>
                <div><label>کۆمسیۆنی نوسینگە:</label><input type="number" step="0.01" name="commission" value="{c['office_commission'] or 0}"></div>
            </div>
            <div class="grid-2" style="margin-top:15px;">
                <div>
                    <label>👁️ شاهێدی یەکەم:</label>
                    <input list="wit_list" name="wit1" value="{c['witness1'] or ''}" required autocomplete="off">
                </div>
                <div>
                    <label>👁️ شاهێدی دووەم:</label>
                    <input list="wit_list" name="wit2" value="{c['witness2'] or ''}" required autocomplete="off">
                </div>
            </div>
            <datalist id="wit_list">{"".join(['<option value="'+w+'">' for w in c_wits])}</datalist>
            
            <div class="grid-2" style="margin-top:15px;">
                <div><label>📅 بەرواری گرێبەست:</label><input type="date" name="c_date" value="{c['contract_date']}" required></div>
                <div><label>📝 تێبینی زیادە:</label><input type="text" name="note" value="{c['contract_details'] or ''}"></div>
            </div>
            
            <button type="submit" class="btn-warning" style="width:100%; padding:15px; margin-top:25px; border:none; border-radius:8px; font-weight:900; font-size:16px; font-family:'Noto Kufi Arabic'; cursor:pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">💾 پاشەکەوتکردنی هەموو گۆڕانکارییەکان</button>
            <a href="/archive" class="btn-danger" style="display:block; text-align:center; margin-top:10px; padding: 14px; border-radius: 8px; text-decoration:none; font-weight:bold;">پاشگەزبوونەوە</a>
        </div>
    </form>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content))

@app.route("/delete_contract/<int:id>", methods=["POST"])
def delete_contract(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.begin() as conn:
        cid = conn.execute(text("SELECT property_id FROM contracts WHERE id=:id"), {"id":id}).scalar()
        if cid: conn.execute(text("UPDATE properties SET status='بەردەستە' WHERE id=:pid"), {"pid": cid})
        conn.execute(text("DELETE FROM transactions WHERE description LIKE :d"), {"d": f"%{id}%"})
        conn.execute(text("DELETE FROM contracts WHERE id=:id"), {"id": id})
    return redirect(url_for('archive'))

@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.connect() as conn:
        data = conn.execute(text("SELECT id, transaction_date, amount, description FROM transactions WHERE transaction_type='خەرجی' ORDER BY id DESC")).fetchall()
        
        t_types, t_persons = set(), set()
        for r in data:
            parts = str(r[3]).split('|')
            if len(parts) > 0 and parts[0]: t_types.add(parts[0].replace('جۆر:', '').strip())
            if len(parts) > 1 and parts[1]: t_persons.add(parts[1].replace('کەس:', '').strip())
            
        total = sum([r[2] for r in data])
        
    content = """
    <div class="grid-35-65">
        <div class="card">
            <h3 style="color:var(--main-color); text-align:center; margin-top:0;">➕ تۆمارکردنی خەرجی</h3>
            <form method="POST" action="/add_expense">
                <label>جۆری مەسروف:</label>
                <input list="e_types" name="type" autocomplete="off" required>
                <datalist id="e_types">{% for t in types %}<option value="{{ t }}">{% endfor %}</datalist>
                
                <label>کێ مەسروفی کردووە:</label>
                <input list="e_persons" name="person" autocomplete="off" required>
                <datalist id="e_persons">{% for p in persons %}<option value="{{ p }}">{% endfor %}</datalist>
                
                <label>بڕی پارە:</label>
                <input type="number" step="0.01" name="amount" required>
                
                <label>تێبینی:</label>
                <input type="text" name="note">
                <button type="submit" class="btn-primary">💾 تۆمارکردن</button>
            </form>
        </div>
        <div class="card">
            <div style="background:var(--bg-dark); padding:15px; border-radius:10px; text-align:center; border:1px solid var(--border-color); margin-bottom:15px;">
                <h4 style="color:#94a3b8; margin:0;">کۆی خەرجییەکان</h4>
                <h2 style="color:#ef4444; margin:5px 0 0 0;" dir="ltr">{{ "{:,.0f}".format(total) }}</h2>
            </div>
            <div class="table-responsive">
                <table>
                    <tr><th>بەروار</th><th>جۆری مەسروف</th><th>کەس</th><th>تێبینی</th><th>بڕی پارە</th><th>کردارەکان</th></tr>
                    {% for r in data %}
                    {% set parts = r[3].split('|') %}
                    {% set t = parts[0].replace('جۆر:', '').strip() if parts|length > 0 else r[3] %}
                    {% set p = parts[1].replace('کەس:', '').strip() if parts|length > 1 else '-' %}
                    {% set n = parts[2].replace('تێبینی:', '').strip() if parts|length > 2 else '-' %}
                    <tr>
                        <td dir="ltr" style="font-size:12px; color:var(--main-color);">{{ r[1].strftime('%Y-%m-%d') }}</td>
                        <td style="font-weight:bold;">{{ t }}</td>
                        <td>{{ p }}</td>
                        <td style="font-size:12px; color:#94a3b8;">{{ n }}</td>
                        <td style="font-weight:900; color:#ef4444;" dir="ltr">{{ "{:,.0f}".format(r[2]) }}</td>
                        <td class="action-flex">
                            <a href="/edit_expense/{{ r[0] }}" class="action-btn btn-warning" title="دەستکاری">✏️</a>
                            <form method="POST" action="/delete_expense/{{ r[0] }}" style="margin:0;">
                                <button type="submit" class="action-btn btn-danger" onclick="return confirm('بسڕێتەوە؟');" title="سڕینەوە">🗑</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content), data=data, total=total, types=t_types, persons=t_persons)

@app.route("/add_expense", methods=["POST"])
def add_expense():
    if not session.get('logged_in'): return redirect(url_for('login'))
    desc = f"{request.form.get('type')}|{request.form.get('person')}|{request.form.get('note', '')}"
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO transactions (transaction_type, amount, description) VALUES ('خەرجی', :amt, :desc)"), {"amt": request.form.get('amount'), "desc": desc})
    return redirect(url_for('expenses'))

@app.route("/edit_expense/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == "POST":
        desc = f"{request.form.get('type')}|{request.form.get('person')}|{request.form.get('note', '')}"
        with engine.begin() as conn:
            conn.execute(text("UPDATE transactions SET transaction_date=:dt, amount=:amt, description=:desc WHERE id=:id"), {"dt": request.form.get("trans_date"), "amt": request.form.get("amount"), "desc": desc, "id": id})
        return redirect(url_for('expenses'))
    
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM transactions WHERE id=:id"), {"id": id}).mappings().fetchone()
    
    parts = str(row['description']).split('|')
    t = parts[0].replace('جۆر:', '').strip() if len(parts) > 0 else ''
    p = parts[1].replace('کەس:', '').strip() if len(parts) > 1 else ''
    n = parts[2].replace('تێبینی:', '').strip() if len(parts) > 2 else ''
    dt_str = row['transaction_date'].strftime('%Y-%m-%d') if row['transaction_date'] else ''
    
    content = f"""
    <div class="card" style="max-width:500px; margin:auto;">
        <h3 style="color:var(--main-color); text-align:center;">✏ دەستکاریکردنی مەسروفات</h3>
        <form method="POST">
            <label>بەروار:</label><input type="date" name="trans_date" value="{dt_str}" required>
            <label>جۆری مەسروف:</label><input type="text" name="type" value="{t}" required>
            <label>کێ مەسروفی کردووە:</label><input type="text" name="person" value="{p}" required>
            <label>بڕی پارە:</label><input type="number" step="0.01" name="amount" value="{row['amount']}" required>
            <label>تێبینی:</label><input type="text" name="note" value="{n}">
            
            <button type="submit" class="btn-warning" style="width:100%; padding:15px; margin-top:20px; border-radius:8px; font-weight:bold; cursor:pointer; font-family:'Noto Kufi Arabic';">💾 پاشەکەوتکردن</button>
            <a href="/expenses" class="btn-danger" style="display:block; text-align:center; margin-top:10px; padding: 12px; border-radius: 8px; text-decoration:none;">گەڕانەوە</a>
        </form>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content))

@app.route("/delete_expense/<int:id>", methods=["POST"])
def delete_expense(id):
    with engine.begin() as conn: conn.execute(text("DELETE FROM transactions WHERE id=:id"), {"id": id})
    return redirect(url_for('expenses'))

@app.route("/safe")
def safe():
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.connect() as conn:
        transactions = conn.execute(text("SELECT * FROM safe_box ORDER BY id DESC")).fetchall()
    
    t_in, t_out = sum([r[3] for r in transactions if r[5]=='هاتوو' and r[4]=='دۆلار']), sum([r[3] for r in transactions if r[5]=='ڕۆیشتوو' and r[4]=='دۆلار'])
    t_in_d, t_out_d = sum([r[3] for r in transactions if r[5]=='هاتوو' and r[4]=='دینار']), sum([r[3] for r in transactions if r[5]=='ڕۆیشتوو' and r[4]=='دینار'])

    content = """
    <div class="grid-35-65">
        <div class="card">
            <h3 style="color:var(--main-color); text-align:center; margin-top:0;">➕ تۆمارکردن لە قاسە</h3>
            <form method="POST" action="/add_safe">
                <label>جۆری مامەڵە:</label>
                <select name="trans_type">
                    <option value="هاتوو">هاتنی دراو 📥</option>
                    <option value="ڕۆیشتوو">ڕۆیشتنی دراو 📤</option>
                </select>
                <div class="grid-2">
                    <div><label>جۆری دراو:</label><select name="currency"><option>دۆلار</option><option>دینار</option></select></div>
                    <div><label>بڕی پارە:</label><input type="number" step="0.01" name="amount" required></div>
                </div>
                <label>ناو / لایەن:</label><input type="text" name="person_name" required>
                <label>تێبینی:</label><input type="text" name="note">
                <label>بەروار:</label><input type="date" name="trans_date" value="{{ today }}" required>
                <button type="submit" class="btn-primary">💾 تۆمارکردن</button>
            </form>
        </div>
        <div class="card">
            <div class="grid-2" style="margin-bottom:15px;">
                <div style="background:var(--bg-dark); padding:15px; border-radius:10px; text-align:center; border:1px solid var(--border-color);">
                    <div style="color:#10b981; font-weight:bold;">سەرجەم مەوجودی دۆلار ($)</div>
                    <div style="font-size:24px; font-weight:900; color:#10b981;" dir="ltr">{{ "{:,.0f}".format(bal_usd) }}</div>
                </div>
                <div style="background:var(--bg-dark); padding:15px; border-radius:10px; text-align:center; border:1px solid var(--border-color);">
                    <div style="color:var(--main-color); font-weight:bold;">سەرجەم مەوجودی دینار</div>
                    <div style="font-size:24px; font-weight:900; color:var(--main-color);" dir="ltr">{{ "{:,.0f}".format(bal_iqd) }}</div>
                </div>
            </div>
            <div class="table-responsive">
                <table>
                    <tr><th>بەروار</th><th>جۆر</th><th>بڕی پارە</th><th>ناو / لایەن</th><th>تێبینی</th><th>کردارەکان</th></tr>
                    {% for r in transactions %}
                    <tr>
                        <td dir="ltr" style="font-size:12px; color:var(--main-color);">{{ r[1] }}</td>
                        <td style="color: {% if r[5] == 'هاتوو' %}#10b981{% else %}#ef4444{% endif %}; font-weight:bold;">{{ r[5] }}</td>
                        <td style="font-weight:900; color:var(--main-color);" dir="ltr">{{ "{:,.0f}".format(r[3]) }} <span style="font-size:11px;">{{ '$' if r[4] == 'دۆلار' else 'د.ع' }}</span></td>
                        <td style="font-weight:bold;">{{ r[2] }}</td>
                        <td style="font-size:12px;">{{ r[6] }}</td>
                        <td class="action-flex">
                            <a href="/edit_safe/{{ r[0] }}" class="action-btn btn-warning" title="دەستکاری">✏️</a>
                            <form method="POST" action="/delete_safe/{{ r[0] }}" style="margin:0;">
                                <button type="submit" class="action-btn btn-danger" onclick="return confirm('بسڕێتەوە؟');" title="سڕینەوە">🗑️</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content), transactions=transactions, bal_usd=t_in-t_out, bal_iqd=t_in_d-t_out_d, today=datetime.now().strftime("%Y-%m-%d"))

@app.route("/add_safe", methods=["POST"])
def add_safe():
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO safe_box (trans_date, person_name, amount, currency, trans_type, note) VALUES (:dt, :nm, :amt, :curr, :typ, :nt)"), {"dt": request.form.get("trans_date"), "nm": request.form.get("person_name"), "amt": request.form.get("amount"), "curr": request.form.get("currency"), "typ": request.form.get("trans_type"), "nt": request.form.get("note")})
    return redirect(url_for('safe'))

@app.route("/edit_safe/<int:id>", methods=["GET", "POST"])
def edit_safe(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == "POST":
        with engine.begin() as conn:
            conn.execute(text("""UPDATE safe_box SET 
                trans_date=:dt, trans_type=:typ, currency=:curr, person_name=:nm, amount=:amt, note=:nt 
                WHERE id=:id"""), 
                {"dt": request.form.get("trans_date"), "typ": request.form.get("trans_type"), "curr": request.form.get("currency"), "nm": request.form.get("person_name"), "amt": request.form.get("amount"), "nt": request.form.get("note"), "id": id})
        return redirect(url_for('safe'))
    
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM safe_box WHERE id=:id"), {"id": id}).mappings().fetchone()
    
    content = f"""
    <div class="card" style="max-width:500px; margin:auto;">
        <h3 style="color:var(--main-color); text-align:center;">✏️ دەستکاریکردنی تۆماری قاسە</h3>
        <form method="POST">
            <label>بەروار:</label><input type="date" name="trans_date" value="{row['trans_date']}" required>
            
            <div class="grid-2">
                <div>
                    <label>جۆری مامەڵە:</label>
                    <select name="trans_type">
                        <option value="{row['trans_type']}">{row['trans_type']}</option>
                        <option value="هاتوو">هاتنی دراو 📥</option>
                        <option value="ڕۆیشتوو">ڕۆیشتنی دراو 📤</option>
                    </select>
                </div>
                <div>
                    <label>جۆری دراو:</label>
                    <select name="currency">
                        <option value="{row['currency']}">{row['currency']}</option>
                        <option>دۆلار</option>
                        <option>دینار</option>
                    </select>
                </div>
            </div>
            
            <label>بڕی پارە:</label><input type="number" step="0.01" name="amount" value="{row['amount']}">
            <label>ناو / لایەن:</label><input type="text" name="person_name" value="{row['person_name']}">
            <label>تێبینی:</label><input type="text" name="note" value="{row['note'] or ''}">
            
            <button type="submit" class="btn-warning" style="width:100%; padding:15px; margin-top:20px; border-radius:8px; font-weight:bold; cursor:pointer; font-family:'Noto Kufi Arabic';">💾 پاشەکەوتکردن</button>
            <a href="/safe" class="btn-danger" style="display:block; text-align:center; margin-top:10px; padding: 12px; border-radius: 8px; text-decoration:none;">گەڕانەوە</a>
        </form>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content))

@app.route("/delete_safe/<int:id>", methods=["POST"])
def delete_safe(id):
    with engine.begin() as conn: conn.execute(text("DELETE FROM safe_box WHERE id=:id"), {"id": id})
    return redirect(url_for('safe'))

@app.route("/users", methods=["GET"])
def users():
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.connect() as conn:
        data = conn.execute(text("SELECT * FROM users ORDER BY id")).fetchall()
        
    content = """
    <div class="grid-35-65">
        <div class="card">
            <h3 style="color:var(--main-color); text-align:center; margin-top:0;">➕ بەکارهێنەری نوێ</h3>
            <form method="POST" action="/add_user">
                <label>ناوی بەکارهێنەر:</label><input type="text" name="username" required>
                <label>وشەی نهێنی:</label><input type="text" name="password" required>
                <label>ڕۆڵ:</label>
                <select name="role">
                    <option value="admin">بەڕێوەبەر (Admin)</option>
                    <option value="user">کارمەند (User)</option>
                </select>
                <button type="submit" class="btn-primary">💾 دروستکردن</button>
            </form>
        </div>
        <div class="card">
            <h3 style="color:var(--main-color); text-align:center; margin-top:0;">👥 لیستی بەکارهێنەران</h3>
            <div class="table-responsive">
                <table>
                    <tr><th>ناو</th><th>وشەی نهێنی</th><th>ڕۆڵ</th><th>کردارەکان</th></tr>
                    {% for r in data %}
                    <tr>
                        <td style="font-weight:bold;">{{ r[1] }}</td>
                        <td style="color:#ef4444;" dir="ltr">{{ r[2] }}</td>
                        <td>{{ r[3] }}</td>
                        <td class="action-flex">
                            <a href="/edit_user/{{ r[0] }}" class="action-btn btn-warning" title="دەستکاری">✏️️</a>
                            {% if r[1] != 'admin' %}
                            <form method="POST" action="/delete_user/{{ r[0] }}" style="margin:0;">
                                <button type="submit" class="action-btn btn-danger" onclick="return confirm('بە یەکجاری بسڕێتەوە؟');" title="سڕینەوە">🗑️</button>
                            </form>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content), data=data)

@app.route("/add_user", methods=["POST"])
def add_user():
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.begin() as conn:
        try:
            conn.execute(text("INSERT INTO users (username, password, role) VALUES (:u, :p, :r)"), {"u": request.form.get("username"), "p": request.form.get("password"), "r": request.form.get("role")})
        except:
            pass
    return redirect(url_for('users'))

@app.route("/edit_user/<int:id>", methods=["GET", "POST"])
def edit_user(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == "POST":
        with engine.begin() as conn:
            conn.execute(text("UPDATE users SET username=:u, password=:p, role=:r WHERE id=:id"), {"u": request.form.get("username"), "p": request.form.get("password"), "r": request.form.get("role"), "id": id})
        return redirect(url_for('users'))
    
    with engine.connect() as conn:
        u = conn.execute(text("SELECT * FROM users WHERE id=:id"), {"id": id}).mappings().fetchone()
    
    content = f"""
    <div class="card" style="max-width:400px; margin:auto;">
        <h3 style="color:var(--main-color); text-align:center;">✏ دەستکاری بەکارهێنەر</h3>
        <form method="POST">
            <label>ناوی بەکارهێنەر:</label><input type="text" name="username" value="{u['username']}" required>
            <label>وشەی نهێنی:</label><input type="text" name="password" value="{u['password']}" required>
            <label>ڕۆڵ:</label>
            <select name="role">
                <option value="{u['role']}">{u['role']}</option>
                <option value="admin">admin</option>
                <option value="user">user</option>
            </select>
            <button type="submit" class="btn-warning" style="width:100%; padding:15px; margin-top:20px; border-radius:8px; font-weight:bold; cursor:pointer; font-family:'Noto Kufi Arabic';">💾 پاشەکەوتکردن</button>
            <a href="/users" class="btn-danger" style="display:block; text-align:center; margin-top:10px; padding: 12px; border-radius: 8px; text-decoration:none;">گەڕانەوە</a>
        </form>
    </div>
    """
    return render_template_string(BASE_TEMPLATE.replace('<!--CONTENT_PLACEHOLDER-->', content))

@app.route("/delete_user/<int:id>", methods=["POST"])
def delete_user(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.begin() as conn: 
        conn.execute(text("DELETE FROM users WHERE id=:id AND username != 'admin'"), {"id": id})
    return redirect(url_for('users'))

# ==========================================
# فۆڕمی ئەیفۆڕ (A4) لەگەڵ دیزاینی تایبەت بۆ واتەرمارک و لۆگۆی سەرەوە
# ==========================================
@app.route("/print/<int:id>")
def print_a4(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    with engine.connect() as conn:
        q = text("""
            SELECT 
                c.id as cid, c.contract_date, c.total_price, c.advance_payment, c.currency, c.witness1, c.witness2, c.contract_details,
                p.property_type, p.property_number, p.area, p.neighborhood, p.orientation, p.block_number, p.location, p.eviction_period, p.eviction_date, p.monthly_rent, p.eviction_penalty,
                s.name as seller_name, s.phone as seller_phone,
                b.name as buyer_name, b.phone as buyer_phone
            FROM contracts c 
            JOIN properties p ON c.property_id = p.id 
            JOIN clients s ON c.seller_id = s.id 
            JOIN clients b ON c.buyer_id = b.id 
            WHERE c.id=:id
        """)
        c_data = conn.execute(q, {"id": id}).mappings().fetchone()
    
    if not c_data: return "هەڵە: گرێبەست نەدۆزرایەوە."
    
    tp = float(c_data['total_price'] or 0)
    ap = float(c_data['advance_payment'] or 0)
    remain_pay = tp - ap
    currency = c_data['currency']
    
    eviction_html = ""
    if c_data['property_type'] != 'زەوی' and (c_data['eviction_period'] or c_data['monthly_rent'] or c_data['eviction_penalty']):
        eviction_html = f"<li><span class='highlight'>مەرجەکانی چۆڵکردن:</span> لایەنی یەکەم دەبێت ئەم موڵکە چۆڵبکات لەماوەی (<span class='highlight'>{c_data['eviction_period'] or 'دیارینەکراو'}</span>) وە بەرواری چۆڵکردن (<span class='highlight' dir='ltr'>{c_data['eviction_date'] or '-'}</span>) دەبێت. کرێی مانگانە (<span class='highlight'>{c_data['monthly_rent'] or '0'}</span>) وە سزای چۆڵنەکردن (<span class='highlight'>{c_data['eviction_penalty'] or 'نییە'}</span>) دەبێت.</li>"
    else:
        eviction_html = "<li>لایەنی یەکەم دەبێت ئەم موڵکە چۆڵبکات لەماوەی کە بڕیارە لە گرێبەستەکەدا، بەپێچەوانەوە دەبێت قەرەبووی لایەنی دووەم بکاتەوە.</li>"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ku" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>گرێبەستی چاپکراو</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;700&display=swap');
            body {{ font-family: 'Noto Kufi Arabic', sans-serif; background: #e2e8f0; margin: 0; padding: 20px; color: #000; font-size: 13px; line-height: 2.1; }}
            .a4-page {{ width: 21cm; min-height: 29.7cm; padding: 0.5cm 1cm; margin: 0 auto; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); box-sizing: border-box; position: relative; z-index: 1; }}
            
            /* ڕێکخستنی واتەرمارک بۆ کاتی پرێنتکردن */
            .watermark-container {{
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: -1;
                opacity: 0.15; 
            }}
            .watermark-container img {{
                width: 70%;
                max-width: 600px;
            }}
            
            .header-flex {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #721c24; padding-bottom: 12px; margin-bottom: 20px; }}
            
            /* دیزاینی نوێی بەشی تەلەفۆنەکان کە ئایکۆنی تەلەفۆنی تیایە */
            .phones-wrapper {{ width: 33%; display: flex; justify-content: flex-start; align-items: center; }}
            .phones-box {{
                color: #1e3a8a;
                font-weight: bold;
                font-size: 13px;
                line-height: 1.8;
                border: 2px solid #3b82f6;
                background-color: #eff6ff;
                border-radius: 12px;
                padding: 10px 15px;
                text-align: left;
                display: inline-block;
            }}
            
            .title-center {{ text-align: center; color: #721c24; width: 34%; }}
            .title-center h1 {{ margin: 0; font-size: 26px; font-weight: 900; }}
            .title-center h3 {{ margin: 5px 0 0 0; font-size: 15px; color: #ef4444; }}
            .title-center span {{ font-size: 11px; color: #666; }}
            
            .logo-wrap {{ width: 33%; display: flex; justify-content: flex-end; align-items: center; }}
            .logo-img {{ max-width: 160px; height: auto; object-fit: contain; }}
            
            .meta-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
            .meta-box {{ border: 1px solid #ccc; padding: 5px 15px; border-radius: 8px; font-weight: bold; }}
            .meta-center {{ border: 1px solid #ccc; padding: 5px 30px; border-radius: 8px; font-weight: bold; color: #721c24; background: #fdfdfd; }}
            
            .parties-row {{ display: flex; justify-content: space-between; margin-bottom: 25px; border: 1px solid #eee; padding: 12px; border-radius: 8px; }}
            .party {{ text-align: center; width: 45%; }}
            .party-title {{ color: #ef4444; font-weight: bold; margin-bottom: 10px; font-size: 11px; }}
            .party-phone {{ font-size: 11px; color: #555; }}
            
            ol {{ padding-right: 20px; text-align: justify; margin-bottom: 25px; }}
            li {{ margin-bottom: 8px; }}
            
            .highlight {{ font-weight: bold; text-decoration: underline; color: #ef4444; }}
            
            .note-red {{ color: #ef4444; text-align: center; font-weight: bold; margin: 25px 0; font-size: 12px; }}
            
            .signatures-row {{ display: flex; justify-content: space-between; text-align: center; font-weight: bold; font-size: 11px; margin-top: 40px; border-top: 2px dotted #ccc; padding-top: 15px; }}
            .sig-col {{ display: flex; flex-direction: column; gap: 15px; width: 18%; }}
            .sig-name {{ color: #555; }}
            
            .footer-text {{ text-align: center; font-size: 10px; color: #999; margin-top: 30px; }}
            
            @media print {{
                @page {{ margin: 0.5cm; }} /* ڕێگری دەکات لە دروستبوونی پەڕەی بەتاڵ */
                body {{ background: white; padding: 0; margin: 0; }}
                .a4-page {{ box-shadow: none; border: none; margin: 0; padding: 0.5cm 1cm; width: 100%; height: auto; page-break-after: avoid; page-break-inside: avoid; }}
                #print-btn {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="a4-page">
            
            <!-- واتەرمارکی سەد لە سەد جێگیر (لۆگۆی پشتەوە) -->
            <div class="watermark-container">
                <img src="/static/logo.png" onerror="this.style.display='none'" alt="واتەرمارک">
            </div>
            
            <div class="header-flex">
                <!-- دیزاینی نوێی ژمارەی تەلەفۆن بەبێ تایتڵ و لەگەڵ ئایکۆن -->
                <div class="phones-wrapper">
                    <div class="phones-box" dir="ltr">
                        📞 0770 073 7171<br>
                        📞 0750 073 7171<br>
                        📞 0750 184 4609<br>
                        📞 0770 102 8801
                    </div>
                </div>

                <div class="title-center">
                    <h1>نوسینگەی شەعبان</h1>
                    <h3>بۆ کڕین و فرۆشتنی موڵک</h3>
                    <span>(ڕانیە گەڕەکی شارەوانی)</span>
                </div>
                <div class="logo-wrap">
                    <img src="/static/logo.png" onerror="this.style.display='none'" class="logo-img" alt="لۆگۆی نوسینگە">
                </div>
            </div>
            
            <div class="meta-row">
                <div class="meta-box">بەروار: <span dir="ltr">{c_data['contract_date']}</span></div>
                <div class="meta-center">گرێبەستی کڕین و فرۆشتن</div>
                <div class="meta-box">ژمارەی گرێبەست: {c_data['cid']}</div>
            </div>
            
            <div class="parties-row">
                <div class="party">
                    <div class="party-title">٢. لایەنی دووەم (کڕیار): {c_data['buyer_name']}</div>
                    <div class="party-phone">مۆبایل: <span dir="ltr">{c_data['buyer_phone'] or '-'}</span></div>
                </div>
                <div class="party" style="border-right: 1px solid #ddd;">
                    <div class="party-title">١. لایەنی یەکەم (فرۆشیار): {c_data['seller_name']}</div>
                    <div class="party-phone">مۆبایل: <span dir="ltr">{c_data['seller_phone'] or '-'}</span></div>
                </div>
            </div>
            
            <ol>
                <li>لایەنی یەکەم دان بەوە دادەنێت کە ئەو <span class="highlight">{c_data['property_type']}</span> هەیە بە مەبەستی فرۆشتنی بە لایەنی دووەم کە ژمارەکەی <span class="highlight">{c_data['property_number']}</span> و ڕووبەرەکەی بریتییە لە <span class="highlight">{c_data['area']}</span> ڕووەو <span class="highlight">{c_data['orientation']}</span> جۆری موڵک <span class="highlight">{c_data['property_type']}</span> تاپۆ ژمارە <span class="highlight">{c_data['block_number'] or '-'}</span> لە گەڕەکی <span class="highlight">{c_data['neighborhood']}</span>.</li>
                <li>نرخی فرۆشتن <span class="highlight" dir="ltr">{tp:,.0f} {currency}</span> دان بەوە دادەنێت کە بڕی <span class="highlight" dir="ltr">{ap:,.0f} {currency}</span> وەرگرتووە وە بڕی <span class="highlight" dir="ltr">{remain_pay:,.0f} {currency}</span> ماوە لای کڕیار تا دوای تۆمارکردنی موڵک.</li>
                <li>هەر لایەنێک پەشیمان بێتەوە لە مامەڵەکە دەبێتە بەزەرەر بچێتە دەر بە ڕەزامەندی لایەنی بەرامبەر و نوسینگە.</li>
                <li>لایەنی دووەم بەرپرسیارە لەو پارەیەی کە دەچێتە نێو کاروباری فرۆشتن لە بەڕێوەبەرایەتی تۆمارکردنی موڵک.</li>
                <li>لایەنی یەکەم بەرپرسیارە لە پارەی پاککردنەوە و جیابوونەوە و باجی خانووبەرە (الدخل) و شارەوانی ئەگەر هەبوو.</li>
                <li>هەردوو لایەن کرێی نێوەند (نوسینگە) دەدەن مەگەر لەسەر شتێک ڕێکەوتبن.</li>
                {eviction_html}
                <li>دەبێت لایەنی دووەم کاروباری تەواوکردنی موڵک تەواوبکات لەماوەی دیاریکراودا.</li>
                <li>هەر کێشەیەکی حکومی و مەدەنی هەبێت بە نرخی ڕۆژ دەگەڕێندرێتەوە بۆ فرۆشیار.</li>
                <li>بە ڕەزامەندی هەردوو لایەن ئەم بڕگانەی لە بەڵگەنامەکەدا هاتووە ئیمزا کرا.</li>
            </ol>
            
            <div class="note-red">تێبینی: {c_data['contract_details'] or 'هیچ تێبینییەکی زیاده بوونی نییه.'}</div>
            
            <div class="signatures-row">
                <div class="sig-col">
                    <div>مۆر و واژۆی نوسینگە</div>
                    <div class="sig-name" style="color:#721c24;">نوسینگەی شەعبان</div>
                </div>
                <div class="sig-col">
                    <div>لایەنی دووەم (کڕیار)</div>
                    <div class="sig-name">{c_data['buyer_name']}</div>
                </div>
                <div class="sig-col">
                    <div>شاهێدی دووەم</div>
                    <div class="sig-name">{c_data['witness2'] or '.............'}</div>
                </div>
                <div class="sig-col">
                    <div>شاهێدی یەکەم</div>
                    <div class="sig-name">{c_data['witness1'] or '.............'}</div>
                </div>
                <div class="sig-col">
                    <div>لایەنی یەکەم (فرۆشیار)</div>
                    <div class="sig-name">{c_data['seller_name']}</div>
                </div>
            </div>
            
            <div class="footer-text">ئەم گرێبەستە لە ڕێگەی سیستەمی ئەلیکترۆنی نوسینگەی شەعبانەوە دروست کراوە.</div>
        </div>
        
        <div style="text-align:center; margin-top: 20px;" id="print-btn">
            <button onclick="window.print();" style="padding: 15px 30px; font-size: 18px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-family: 'Noto Kufi Arabic'; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">🖨 چاپکردنی فەرمی</button>
            <a href="/archive" style="display: block; margin-top: 15px; color: #ef4444; text-decoration: none; font-weight: bold;">گەڕانەوە بۆ ئەرشیف</a>
        </div>
    </body>
    </html>
    """
    return html

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
