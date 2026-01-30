# tombala_game.py
# Tombala (Bingo) Oyunu - LAN Edition

import asyncio
import os
import random
import sys

# LAN server modülünü ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lan.lan_server import (
    create_app, run_server, broadcast, build_payload, 
    players, player_by_ws, clients
)

# --- Oyun Ayarları ---
NUMBERS_RANGE = (1, 90)  # Tombala 1-90 arası sayılar
AUTO_DRAW_INTERVAL = 3   # Otomatik çekim (saniye, None ise manuel)

# --- Oyun Durumu ---
game_state = {
    "started": False,
    "drawn_numbers": [],      # Çekilen sayılar
    "player_cards": {},       # pid -> kartlar
    "cinko1_winner": None,    # İlk çinko kazananı
    "cinko2_winner": None,    # İkinci çinko kazananı
    "tombala_winner": None,   # Tombala kazananı
}

def generate_tombala_card():
    """Klasik Türk tombala kartı oluştur (3 satır, 9 sütun, satır başına 5 sayı)"""
    card = [[None for _ in range(9)] for _ in range(3)]
    
    # Her sütun için sayı aralıkları
    # Sütun 0: 1-9, Sütun 1: 10-19, ..., Sütun 8: 80-90
    for col in range(9):
        if col == 0:
            pool = list(range(1, 10))
        elif col == 8:
            pool = list(range(80, 91))
        else:
            pool = list(range(col * 10, (col + 1) * 10))
        
        random.shuffle(pool)
        nums = pool[:3]  # Her sütundan 3 sayı seç
        
        # 3 satıra yerleştir
        for row in range(3):
            card[row][col] = nums[row]
    
    # Her satırda sadece 5 sayı olmalı, 4 boş olmalı
    for row in range(3):
        # 9 sütundan 4 tanesini boşalt
        cols_to_clear = random.sample(range(9), 4)
        for col in cols_to_clear:
            card[row][col] = None
    
    # Satırlardaki sayıları sırala (None'lar aynı yerde kalır)
    for row in range(3):
        row_nums = [(card[row][col], col) for col in range(9) if card[row][col] is not None]
        row_nums.sort(key=lambda x: x[0])
        
        # Temizle ve sıralı yerleştir
        non_none_cols = [col for col in range(9) if card[row][col] is not None]
        for i, col in enumerate(non_none_cols):
            card[row][col] = row_nums[i][0]
    
    return card

def check_line(card, drawn_numbers, line_idx):
    """Bir satırın tamamlanıp tamamlanmadığını kontrol et"""
    line = card[line_idx]
    for num in line:
        if num is not None and num not in drawn_numbers:
            return False
    return True

def check_card_lines(card, drawn_numbers):
    """Kaçtane satır tamamlandı?"""
    completed = 0
    for i in range(3):
        if check_line(card, drawn_numbers, i):
            completed += 1
    return completed

def check_tombala(card, drawn_numbers):
    """Tüm kart tamamlandı mı?"""
    for row in card:
        for num in row:
            if num is not None and num not in drawn_numbers:
                return False
    return True

async def send_state():
    """Oyun durumunu tüm oyunculara gönder"""
    state = {
        "players": [{"id": pid, "name": p["name"], "score": p["score"]} for pid, p in players.items()],
        "started": game_state["started"],
        "drawn_numbers": game_state["drawn_numbers"],
        "last_number": game_state["drawn_numbers"][-1] if game_state["drawn_numbers"] else None,
        "total_drawn": len(game_state["drawn_numbers"]),
        "cinko1_winner": game_state["cinko1_winner"],
        "cinko2_winner": game_state["cinko2_winner"],
        "tombala_winner": game_state["tombala_winner"],
    }
    await broadcast(build_payload("state", **state))

async def handle_game_message(ws, data):
    """Oyundan gelen mesajları işle"""
    pid = player_by_ws.get(ws)
    if not pid:
        return
    
    typ = data.get("type")
    
    if typ == "start_game":
        if not game_state["started"]:
            await start_game()
    
    elif typ == "draw_number":
        if game_state["started"] and not game_state["tombala_winner"]:
            await draw_number()
    
    elif typ == "claim_cinko1":
        if game_state["started"] and not game_state["cinko1_winner"]:
            await check_cinko_claim(pid, 1)
    
    elif typ == "claim_cinko2":
        if game_state["started"] and not game_state["cinko2_winner"]:
            await check_cinko_claim(pid, 2)
    
    elif typ == "claim_tombala":
        if game_state["started"] and not game_state["tombala_winner"]:
            await check_tombala_claim(pid)
    
    elif typ == "reset_game":
        await reset_game()

async def start_game():
    """Oyunu başlat ve her oyuncuya kart ver"""
    game_state["started"] = True
    game_state["drawn_numbers"] = []
    game_state["player_cards"] = {}
    game_state["cinko1_winner"] = None
    game_state["cinko2_winner"] = None
    game_state["tombala_winner"] = None
    
    # Her oyuncuya kart oluştur
    for pid in players:
        card = generate_tombala_card()
        game_state["player_cards"][pid] = card
        
        # Oyuncuya kartını gönder
        ws = [w for w, p in player_by_ws.items() if p == pid][0] if pid in player_by_ws.values() else None
        if ws:
            try:
                await ws.send_str(build_payload("your_card", card=card))
            except:
                pass
    
    await send_state()
    await broadcast(build_payload("game_started"))
    
    # Otomatik çekim başlat
    if AUTO_DRAW_INTERVAL:
        asyncio.create_task(auto_draw_loop())

async def auto_draw_loop():
    """Otomatik sayı çekme döngüsü"""
    while game_state["started"] and not game_state["tombala_winner"]:
        await asyncio.sleep(AUTO_DRAW_INTERVAL)
        if len(game_state["drawn_numbers"]) < 90:
            await draw_number()
        else:
            break

async def draw_number():
    """Yeni bir sayı çek"""
    available = [n for n in range(NUMBERS_RANGE[0], NUMBERS_RANGE[1] + 1) 
                 if n not in game_state["drawn_numbers"]]
    
    if not available:
        await broadcast(build_payload("no_more_numbers"))
        return
    
    number = random.choice(available)
    game_state["drawn_numbers"].append(number)
    
    await broadcast(build_payload("number_drawn", number=number, total=len(game_state["drawn_numbers"])))
    await send_state()

async def check_cinko_claim(pid, cinko_level):
    """Çinko iddiasını kontrol et"""
    card = game_state["player_cards"].get(pid)
    if not card:
        return
    
    completed_lines = check_card_lines(card, game_state["drawn_numbers"])
    
    if cinko_level == 1 and completed_lines >= 1:
        game_state["cinko1_winner"] = pid
        players[pid]["score"] += 10
        winner_name = players[pid]["name"]
        await broadcast(build_payload("cinko1_won", winner=winner_name, pid=pid))
        await send_state()
    
    elif cinko_level == 2 and completed_lines >= 2:
        game_state["cinko2_winner"] = pid
        players[pid]["score"] += 20
        winner_name = players[pid]["name"]
        await broadcast(build_payload("cinko2_won", winner=winner_name, pid=pid))
        await send_state()
    
    else:
        # Yanlış iddia
        await broadcast(build_payload("wrong_claim", pid=pid, claim_type=f"cinko{cinko_level}"))

async def check_tombala_claim(pid):
    """Tombala iddiasını kontrol et"""
    card = game_state["player_cards"].get(pid)
    if not card:
        return
    
    if check_tombala(card, game_state["drawn_numbers"]):
        game_state["tombala_winner"] = pid
        players[pid]["score"] += 50
        winner_name = players[pid]["name"]
        await broadcast(build_payload("tombala_won", winner=winner_name, pid=pid))
        await send_state()
    else:
        # Yanlış iddia
        await broadcast(build_payload("wrong_claim", pid=pid, claim_type="tombala"))

async def reset_game():
    """Oyunu sıfırla"""
    game_state["started"] = False
    game_state["drawn_numbers"] = []
    game_state["player_cards"] = {}
    game_state["cinko1_winner"] = None
    game_state["cinko2_winner"] = None
    game_state["tombala_winner"] = None
    await send_state()
    await broadcast(build_payload("game_reset"))

# --- HTML Arayüzü ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎲 Tombala - LAN Edition</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0B0F19 0%, #1F2937 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
            overflow-x: hidden;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
        }
        h1 {
            text-align: center;
            font-size: 3em;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 2px 2px 4px rgba(0,0,0,0.3), 0 0 10px rgba(255,255,255,0.2); }
            to { text-shadow: 2px 2px 4px rgba(0,0,0,0.3), 0 0 20px rgba(255,255,255,0.4); }
        }
        
        /* Glassmorphism Cards */
        .glass-card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 16px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        
        /* Stats Bar with different sizes */
        .info-bar {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        .info-card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s ease;
        }
        .info-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
        }
        .info-card strong { 
            display: block; 
            font-size: 0.85em; 
            opacity: 0.7; 
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .info-card span { 
            font-size: 1.8em; 
            font-weight: bold;
            display: block;
        }
        .info-card.main-stat {
            position: relative;
            overflow: hidden;
        }
        .info-card.main-stat span {
            font-size: 2.2em;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            margin-top: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            border-radius: 3px;
            transition: width 0.5s ease;
            box-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
        }
        .winner-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        .trophy-icon {
            display: inline-block;
            font-size: 0.8em;
        }
        
        /* Join Screen */
        #join-screen {
            text-align: center;
            background: rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            padding: 50px;
            border-radius: 20px;
            max-width: 450px;
            margin: 100px auto;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        #join-screen h2 {
            margin-bottom: 30px;
            font-size: 2em;
        }
        #join-screen input {
            width: 100%;
            padding: 15px;
            font-size: 1.2em;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            margin: 10px 0;
            background: rgba(255, 255, 255, 0.9);
            transition: all 0.3s ease;
        }
        #join-screen input:focus {
            outline: none;
            border-color: #4CAF50;
            box-shadow: 0 0 20px rgba(76, 175, 80, 0.3);
        }
        #join-screen button {
            width: 100%;
            padding: 18px;
            font-size: 1.3em;
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            margin-top: 15px;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
        }
        #join-screen button:hover { 
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(76, 175, 80, 0.6);
        }
        #join-screen button:active {
            transform: translateY(0);
        }
        
        #game-screen { display: none; }
        
        /* Main Layout Grid */
        .game-layout {
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            grid-template-rows: auto 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .layout-left { grid-column: 1; grid-row: 1 / 3; }
        .layout-right-top { grid-column: 2; grid-row: 1; }
        .layout-right-bottom { grid-column: 2; grid-row: 2; }
        .layout-bottom { grid-column: 1 / 3; }
        
        /* Card Container - Premium look */
        .card-container {
            background: rgba(255, 255, 255, 0.95);
            color: #333;
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }
        .card-title {
            text-align: center;
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #667eea;
            font-weight: bold;
        }
        .tombala-card {
            display: grid;
            grid-template-columns: repeat(9, 1fr);
            gap: 8px;
            max-width: 600px;
            margin: 0 auto;
        }
        .card-cell {
            aspect-ratio: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3em;
            font-weight: bold;
            border-radius: 12px;
            background: linear-gradient(145deg, #ffffff, #f0f0f0);
            border: 2px solid #e0e0e0;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05),
                        0 2px 6px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            position: relative;
        }
        .card-cell:not(.empty):hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        .card-cell.empty { 
            background: transparent;
            border: 2px dashed rgba(0, 0, 0, 0.1);
            box-shadow: none;
        }
        .card-cell.drawn {
            background: linear-gradient(145deg, #4CAF50, #45a049);
            color: white;
            border-color: #388E3C;
            animation: stamp 0.4s ease;
            box-shadow: 0 4px 15px rgba(76, 175, 80, 0.5),
                        inset 0 1px 3px rgba(255, 255, 255, 0.3);
        }
        .card-cell.drawn::after {
            content: '✓';
            position: absolute;
            font-size: 0.7em;
            top: 2px;
            right: 4px;
            opacity: 0.7;
        }
        @keyframes stamp {
            0% { transform: scale(1.3) rotate(5deg); }
            50% { transform: scale(0.9) rotate(-3deg); }
            100% { transform: scale(1) rotate(0deg); }
        }
        
        /* Last Number Display - Big Focus */
        .last-number-container {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            text-align: center;
        }
        .drawn-title {
            font-size: 1.2em;
            margin-bottom: 15px;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        .last-number {
            font-size: 5em;
            font-weight: bold;
            margin: 20px 0;
            padding: 30px;
            background: linear-gradient(135deg, #FF6B35, #F7931E);
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(255, 107, 53, 0.4),
                        inset 0 0 30px rgba(255, 255, 255, 0.2);
            animation: pulse 1s ease-in-out;
            position: relative;
        }
        .last-number::before {
            content: '';
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            width: 60%;
            height: 20px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            filter: blur(10px);
        }
        @keyframes pulse {
            0% { transform: scale(0.8); opacity: 0; }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); opacity: 1; }
        }
        
        /* Number Grid - Ball Effect */
        .drawn-numbers {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 20px;
            padding: 25px;
        }
        .numbers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(45px, 1fr));
            gap: 8px;
            max-width: 100%;
        }
        .number-ball {
            aspect-ratio: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            font-weight: bold;
            font-size: 0.95em;
            background: linear-gradient(145deg, rgba(255,255,255,0.15), rgba(255,255,255,0.05));
            border: 2px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
            cursor: default;
            position: relative;
        }
        .number-ball::before {
            content: '';
            position: absolute;
            top: 15%;
            left: 25%;
            width: 30%;
            height: 25%;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 50%;
            filter: blur(3px);
        }
        .number-ball.drawn {
            background: linear-gradient(145deg, #FF5722, #E64A19);
            border-color: #D84315;
            transform: scale(1.15);
            box-shadow: 0 4px 15px rgba(255, 87, 34, 0.6),
                        inset 0 1px 5px rgba(255, 255, 255, 0.3);
            animation: bounce 0.5s ease;
        }
        @keyframes bounce {
            0%, 100% { transform: scale(1.15) translateY(0); }
            50% { transform: scale(1.2) translateY(-8px); }
        }
        
        /* Modern Buttons */
        .controls {
            text-align: center;
            margin: 25px 0;
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            justify-content: center;
        }
        button {
            padding: 14px 32px;
            font-size: 1.1em;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        button:hover { 
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
            filter: brightness(1.1);
        }
        button:active { 
            transform: translateY(-1px);
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
        }
        button::before {
            font-size: 1.2em;
        }
        
        .btn-start { 
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
        }
        .btn-start::before { content: '▶'; }
        
        .btn-draw { 
            background: linear-gradient(135deg, #2196F3, #1976D2);
            color: white;
            font-size: 1.3em;
            padding: 16px 40px;
        }
        .btn-draw::before { content: '🎲'; }
        
        .btn-claim { 
            background: linear-gradient(135deg, #FF9800, #F57C00);
            color: white;
        }
        .btn-claim::before { content: '🏆'; }
        
        .btn-reset { 
            background: linear-gradient(135deg, #f44336, #d32f2f);
            color: white;
        }
        .btn-reset::before { content: '↻'; }
        
        /* Lobby & Players */
        .lobby-container {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .lobby-title {
            font-size: 1.4em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .players-list {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 16px;
            padding: 20px;
        }
        .players-list h3 {
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .player-item {
            padding: 12px 15px;
            margin: 8px 0;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .player-item:hover {
            background: rgba(255, 255, 255, 0.15);
            transform: translateX(5px);
        }
        .player-name {
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .host-badge {
            background: #FFD700;
            color: #333;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.75em;
            font-weight: bold;
        }
        
        /* Countdown Timer */
        .countdown-timer {
            text-align: center;
            font-size: 2.5em;
            font-weight: bold;
            color: #FFD700;
            margin: 15px 0;
            animation: countdown-pulse 1s infinite;
        }
        @keyframes countdown-pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        /* Winner Announcement with Confetti */
        .winner-announcement {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.95);
            padding: 50px 80px;
            border-radius: 25px;
            font-size: 2.5em;
            text-align: center;
            z-index: 1000;
            display: none;
            animation: winner-bounce 0.6s ease;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
            border: 3px solid #FFD700;
        }
        @keyframes winner-bounce {
            0%, 100% { transform: translate(-50%, -50%) scale(1); }
            25% { transform: translate(-50%, -50%) scale(1.1) rotate(-2deg); }
            50% { transform: translate(-50%, -50%) scale(1.05) rotate(2deg); }
            75% { transform: translate(-50%, -50%) scale(1.08) rotate(-1deg); }
        }
        
        /* Confetti */
        .confetti {
            position: fixed;
            width: 10px;
            height: 10px;
            background: #f0f;
            position: absolute;
            animation: confetti-fall 3s linear forwards;
        }
        @keyframes confetti-fall {
            to {
                transform: translateY(100vh) rotate(360deg);
                opacity: 0;
            }
        }
        
        /* Responsive */
        @media (max-width: 1024px) {
            .game-layout {
                grid-template-columns: 1fr;
                grid-template-rows: auto;
            }
            .layout-left, .layout-right-top, .layout-right-bottom {
                grid-column: 1;
                grid-row: auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎲 TOMBALA LAN PARTY</h1>
        
        <div id="join-screen">
            <h2>🎮 Oyuna Katıl</h2>
            <input type="text" id="playerName" placeholder="Adınızı girin" maxlength="24">
            <button onclick="joinGame()">Katıl</button>
        </div>
        
        <div id="game-screen">
            <!-- Stats Bar -->
            <div class="info-bar">
                <div class="info-card main-stat">
                    <strong>📊 Çekilen Sayı</strong>
                    <span><span id="totalDrawn">0</span>/90</span>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressBar" style="width: 0%"></div>
                    </div>
                </div>
                <div class="info-card">
                    <strong>🏅 1. Çinko</strong>
                    <span id="cinko1" class="winner-badge">
                        <span class="trophy-icon">🏆</span> <span>-</span>
                    </span>
                </div>
                <div class="info-card">
                    <strong>🏅 2. Çinko</strong>
                    <span id="cinko2" class="winner-badge">
                        <span class="trophy-icon">🏆</span> <span>-</span>
                    </span>
                </div>
                <div class="info-card">
                    <strong>👑 Tombala</strong>
                    <span id="tombala" class="winner-badge">
                        <span class="trophy-icon">🎊</span> <span>-</span>
                    </span>
                </div>
            </div>
            
            <!-- Lobby Info -->
            <div class="lobby-container" id="lobbyInfo" style="display:none;">
                <div class="lobby-title">
                    <span>🌐</span>
                    <span>LAN Lobi - Oyuncular Bağlanıyor...</span>
                </div>
                <div id="lobbyPlayers"></div>
            </div>
            
            <!-- Countdown -->
            <div class="countdown-timer" id="countdown" style="display:none;"></div>
            
            <!-- Controls -->
            <div class="controls">
                <button class="btn-start" onclick="startGame()" id="btnStart">Oyunu Başlat</button>
                <button class="btn-draw" onclick="drawNumber()" id="btnDraw" style="display:none;">Sayı Çek</button>
                <button class="btn-claim" onclick="claimCinko1()" id="btnCinko1" style="display:none;">1. Çinko!</button>
                <button class="btn-claim" onclick="claimCinko2()" id="btnCinko2" style="display:none;">2. Çinko!</button>
                <button class="btn-claim" onclick="claimTombala()" id="btnTombala" style="display:none;">TOMBALA!</button>
                <button class="btn-reset" onclick="resetGame()" id="btnReset" style="display:none;">Yeni Oyun</button>
            </div>
            
            <!-- Game Layout -->
            <div class="game-layout">
                <!-- Left: My Card -->
                <div class="layout-left">
                    <div class="card-container" id="cardContainer" style="display:none;">
                        <div class="card-title">🎴 Kartınız</div>
                        <div class="tombala-card" id="myCard"></div>
                    </div>
                </div>
                
                <!-- Right Top: Last Number -->
                <div class="layout-right-top">
                    <div class="last-number-container">
                        <div class="drawn-title">Son Çekilen Numara</div>
                        <div class="last-number" id="lastNumber">-</div>
                    </div>
                </div>
                
                <!-- Right Bottom: Number Grid -->
                <div class="layout-right-bottom">
                    <div class="drawn-numbers">
                        <div class="numbers-grid" id="numbersGrid"></div>
                    </div>
                </div>
                
                <!-- Bottom: Players List -->
                <div class="layout-bottom">
                    <div class="players-list">
                        <h3>👥 Oyuncular ve Skorlar</h3>
                        <div id="playersList"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="winner-announcement" id="winnerMsg"></div>
    <div id="confettiContainer"></div>
    
    <script>
        let ws = null;
        let myPid = null;
        let myCard = null;
        let drawnNumbers = [];
        let autoDrawTimer = null;
        let countdownInterval = null;
        let isHost = false;
        
        function joinGame() {
            const name = document.getElementById('playerName').value.trim() || 'Guest';
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                ws.send(JSON.stringify({type: 'join', name: name}));
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onclose = () => {
                console.log('Bağlantı kesildi');
            };
        }
        
        function handleMessage(data) {
            if (data.type === 'joined') {
                myPid = data.pid;
                document.getElementById('join-screen').style.display = 'none';
                document.getElementById('game-screen').style.display = 'block';
                initNumbersGrid();
                
                // İlk oyuncu host olur
                if (data.pid === 1) {
                    isHost = true;
                }
            }
            else if (data.type === 'state') {
                updateState(data);
                updateLobby(data);
            }
            else if (data.type === 'your_card') {
                myCard = data.card;
                displayCard();
                document.getElementById('cardContainer').style.display = 'block';
                document.getElementById('lobbyInfo').style.display = 'none';
            }
            else if (data.type === 'game_started') {
                document.getElementById('btnStart').style.display = 'none';
                document.getElementById('btnDraw').style.display = 'inline-flex';
                document.getElementById('btnCinko1').style.display = 'inline-flex';
                document.getElementById('btnCinko2').style.display = 'inline-flex';
                document.getElementById('btnTombala').style.display = 'inline-flex';
                document.getElementById('btnReset').style.display = 'inline-flex';
                
                // Auto-draw countdown başlat
                startAutoDrawCountdown();
            }
            else if (data.type === 'number_drawn') {
                drawnNumbers.push(data.number);
                updateNumbersGrid();
                displayCard();
                document.getElementById('lastNumber').textContent = data.number;
                
                // Progress bar güncelle
                const progress = (data.total / 90) * 100;
                document.getElementById('progressBar').style.width = progress + '%';
                
                // Countdown'u resetle
                if (autoDrawTimer) {
                    startAutoDrawCountdown();
                }
            }
            else if (data.type === 'cinko1_won') {
                showWinner(`🎉 ${data.winner} birinci çinkoyu yaptı!`);
                document.getElementById('btnCinko1').style.display = 'none';
                playSound('win');
            }
            else if (data.type === 'cinko2_won') {
                showWinner(`🎉 ${data.winner} ikinci çinkoyu yaptı!`);
                document.getElementById('btnCinko2').style.display = 'none';
                playSound('win');
            }
            else if (data.type === 'tombala_won') {
                showWinner(`🎊 ${data.winner} TOMBALA YAPTI! 🎊`);
                document.getElementById('btnCinko1').style.display = 'none';
                document.getElementById('btnCinko2').style.display = 'none';
                document.getElementById('btnTombala').style.display = 'none';
                document.getElementById('btnDraw').style.display = 'none';
                createConfetti();
                playSound('tombala');
                
                // Countdown'u durdur
                if (countdownInterval) {
                    clearInterval(countdownInterval);
                    document.getElementById('countdown').style.display = 'none';
                }
            }
            else if (data.type === 'game_reset') {
                location.reload();
            }
        }
        
        function startAutoDrawCountdown() {
            if (countdownInterval) {
                clearInterval(countdownInterval);
            }
            
            let timeLeft = 3; // AUTO_DRAW_INTERVAL
            const countdownEl = document.getElementById('countdown');
            countdownEl.style.display = 'block';
            countdownEl.textContent = `Sıradaki çekiliş: ${timeLeft}...`;
            
            countdownInterval = setInterval(() => {
                timeLeft--;
                if (timeLeft > 0) {
                    countdownEl.textContent = `Sıradaki çekiliş: ${timeLeft}...`;
                } else {
                    countdownEl.textContent = 'ÇEKİLİYOR...';
                }
            }, 1000);
        }
        
        function updateState(data) {
            document.getElementById('totalDrawn').textContent = data.total_drawn;
            
            // Winner badges with trophies
            const cinko1El = document.getElementById('cinko1');
            if (data.cinko1_winner) {
                const winner = data.players.find(p => p.id === data.cinko1_winner);
                cinko1El.innerHTML = `<span class="trophy-icon">🏆</span> <span>${winner?.name || '-'}</span>`;
            } else {
                cinko1El.innerHTML = `<span class="trophy-icon">🏆</span> <span>-</span>`;
            }
            
            const cinko2El = document.getElementById('cinko2');
            if (data.cinko2_winner) {
                const winner = data.players.find(p => p.id === data.cinko2_winner);
                cinko2El.innerHTML = `<span class="trophy-icon">🏆</span> <span>${winner?.name || '-'}</span>`;
            } else {
                cinko2El.innerHTML = `<span class="trophy-icon">🏆</span> <span>-</span>`;
            }
            
            const tombalaEl = document.getElementById('tombala');
            if (data.tombala_winner) {
                const winner = data.players.find(p => p.id === data.tombala_winner);
                tombalaEl.innerHTML = `<span class="trophy-icon">🎊</span> <span>${winner?.name || '-'}</span>`;
            } else {
                tombalaEl.innerHTML = `<span class="trophy-icon">🎊</span> <span>-</span>`;
            }
            
            drawnNumbers = data.drawn_numbers;
            updateNumbersGrid();
            
            const playersList = document.getElementById('playersList');
            playersList.innerHTML = data.players
                .sort((a, b) => b.score - a.score)
                .map((p, idx) => `
                    <div class="player-item">
                        <span class="player-name">
                            ${idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : '👤'}
                            <strong>${p.name}</strong>
                            ${p.id === myPid ? '(Sen)' : ''}
                        </span>
                        <span><strong>${p.score}</strong> puan</span>
                    </div>
                `).join('');
            
            // Progress bar
            const progress = (data.total_drawn / 90) * 100;
            document.getElementById('progressBar').style.width = progress + '%';
        }
        
        function updateLobby(data) {
            if (!data.started && data.players && data.players.length > 0) {
                const lobbyInfo = document.getElementById('lobbyInfo');
                const lobbyPlayers = document.getElementById('lobbyPlayers');
                
                lobbyInfo.style.display = 'block';
                lobbyPlayers.innerHTML = data.players.map((p, idx) => `
                    <div class="player-item">
                        <span class="player-name">
                            ${idx === 0 ? '<span class="host-badge">HOST</span>' : ''}
                            <strong>${p.name}</strong>
                            ${p.id === myPid ? '(Sen)' : ''}
                        </span>
                        <span>Hazır ✓</span>
                    </div>
                `).join('');
            }
        }
        
        function initNumbersGrid() {
            const grid = document.getElementById('numbersGrid');
            for (let i = 1; i <= 90; i++) {
                const ball = document.createElement('div');
                ball.className = 'number-ball';
                ball.id = `ball-${i}`;
                ball.textContent = i;
                grid.appendChild(ball);
            }
        }
        
        function updateNumbersGrid() {
            // Önce tüm topları temizle
            for (let i = 1; i <= 90; i++) {
                const ball = document.getElementById(`ball-${i}`);
                if (ball) ball.classList.remove('drawn');
            }
            
            // Çekilen numaraları işaretle
            drawnNumbers.forEach(num => {
                const ball = document.getElementById(`ball-${num}`);
                if (ball) ball.classList.add('drawn');
            });
        }
        
        function displayCard() {
            if (!myCard) return;
            const cardDiv = document.getElementById('myCard');
            cardDiv.innerHTML = '';
            
            for (let row = 0; row < 3; row++) {
                for (let col = 0; col < 9; col++) {
                    const cell = document.createElement('div');
                    const num = myCard[row][col];
                    
                    if (num === null) {
                        cell.className = 'card-cell empty';
                    } else {
                        cell.className = 'card-cell';
                        cell.textContent = num;
                        if (drawnNumbers.includes(num)) {
                            cell.classList.add('drawn');
                        }
                    }
                    cardDiv.appendChild(cell);
                }
            }
        }
        
        function showWinner(msg) {
            const winnerDiv = document.getElementById('winnerMsg');
            winnerDiv.textContent = msg;
            winnerDiv.style.display = 'block';
            setTimeout(() => {
                winnerDiv.style.display = 'none';
            }, 4000);
        }
        
        function createConfetti() {
            const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff', '#ffa500'];
            const container = document.getElementById('confettiContainer');
            
            for (let i = 0; i < 100; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.className = 'confetti';
                    confetti.style.left = Math.random() * 100 + '%';
                    confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
                    confetti.style.animationDelay = Math.random() * 0.5 + 's';
                    confetti.style.animationDuration = (Math.random() * 2 + 2) + 's';
                    container.appendChild(confetti);
                    
                    setTimeout(() => confetti.remove(), 3000);
                }, i * 30);
            }
        }
        
        function playSound(type) {
            // Basit ses efekti (tarayıcı destekliyorsa)
            const context = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = context.createOscillator();
            const gainNode = context.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(context.destination);
            
            if (type === 'win') {
                oscillator.frequency.value = 800;
                gainNode.gain.setValueAtTime(0.3, context.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.5);
                oscillator.start(context.currentTime);
                oscillator.stop(context.currentTime + 0.5);
            } else if (type === 'tombala') {
                // Tombala için daha uzun ses
                oscillator.frequency.value = 1000;
                gainNode.gain.setValueAtTime(0.3, context.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 1);
                oscillator.start(context.currentTime);
                oscillator.stop(context.currentTime + 1);
            }
        }
        
        function startGame() {
            ws.send(JSON.stringify({type: 'start_game'}));
        }
        
        function drawNumber() {
            ws.send(JSON.stringify({type: 'draw_number'}));
        }
        
        function claimCinko1() {
            ws.send(JSON.stringify({type: 'claim_cinko1'}));
        }
        
        function claimCinko2() {
            ws.send(JSON.stringify({type: 'claim_cinko2'}));
        }
        
        function claimTombala() {
            ws.send(JSON.stringify({type: 'claim_tombala'}));
        }
        
        function resetGame() {
            ws.send(JSON.stringify({type: 'reset_game'}));
        }
    </script>
</body>
</html>
"""

# Sunucu mesaj yöneticisini override et
import lan.lan_server as server
server.handle_game_message = handle_game_message
server.send_state = send_state

def main():
    print("🎲 Tombala (Bingo) - LAN Edition")
    print("=" * 50)
    app = create_app(INDEX_HTML)
    run_server(app, port=8080)

if __name__ == "__main__":
    main()
