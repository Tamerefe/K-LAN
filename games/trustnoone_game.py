# trustnoone_game.py
# Trust No One - Social Deduction Game

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
TASK_TIME = 15  # Görev seçim süresi (saniye)
VOTE_TIME = 20  # Oylama süresi (saniye)
WIN_PROGRESS = 100  # Kazanmak için gerekli ilerleme
SABOTAGE_PENALTY = -5  # Sabotaj cezası
TASK_REWARD = 8  # Normal görev ödülü
MIN_PLAYERS = 3  # Minimum oyuncu sayısı

# Task kartları
TASK_CARDS = [
    "🔌 Router Reset",
    "🛡️ Firewall Check",
    "💾 Database Backup",
    "📹 CCTV Feed Verify",
    "🔄 Patch Update",
    "📋 Log Scan",
    "⚡ Power Cycle",
    "🔐 Security Audit",
    "🌐 Network Ping",
    "💻 System Diagnostics"
]

# --- Oyun Durumu ---
game_state = {
    "started": False,
    "phase": "lobby",  # lobby, task, meeting, ended
    "roles": {},  # pid -> role (crew/saboteur)
    "alive": set(),  # Hayatta olan oyuncular
    "progress": 0,  # Görev ilerlemesi
    "round": 0,
    "current_task": None,
    "choices": {},  # pid -> action (DO/SKIP/SABOTAGE)
    "votes": {},  # pid -> target_pid
    "saboteur": None,
    "timer": 0,
    "eliminated": []
}

async def send_state():
    """Oyun durumunu tüm oyunculara gönder"""
    state = {
        "players": [{"id": pid, "name": p["name"], "score": p["score"], "alive": pid in game_state["alive"]} 
                    for pid, p in players.items()],
        "started": game_state["started"],
        "phase": game_state["phase"],
        "progress": game_state["progress"],
        "round": game_state["round"],
        "current_task": game_state["current_task"],
        "timer": game_state["timer"],
        "alive_count": len(game_state["alive"]),
        "eliminated": game_state["eliminated"]
    }
    await broadcast(build_payload("state", **state))

async def handle_game_message(ws, data):
    """Oyundan gelen mesajları işle"""
    pid = player_by_ws.get(ws)
    if not pid:
        return
    
    typ = data.get("type")
    
    if typ == "start_game":
        if not game_state["started"] and len(players) >= MIN_PLAYERS:
            await start_game()
    
    elif typ == "submit_action":
        if game_state["phase"] == "task" and pid in game_state["alive"]:
            action = data.get("action")
            if action in ["DO", "SKIP", "SABOTAGE"]:
                # Sabotage sadece saboteur yapabilir
                if action == "SABOTAGE" and game_state["roles"].get(pid) != "saboteur":
                    return
                game_state["choices"][pid] = action
                await send_state()
    
    elif typ == "vote":
        if game_state["phase"] == "meeting" and pid in game_state["alive"]:
            target = data.get("target")  # "skip" veya pid
            game_state["votes"][pid] = target
            await send_state()
    
    elif typ == "reset_game":
        await reset_game()

async def start_game():
    """Oyunu başlat"""
    if len(players) < MIN_PLAYERS:
        await broadcast(build_payload("error", message=f"En az {MIN_PLAYERS} oyuncu gerekli!"))
        return
    
    game_state["started"] = True
    game_state["phase"] = "lobby"
    game_state["alive"] = set(players.keys())
    game_state["progress"] = 0
    game_state["round"] = 0
    game_state["eliminated"] = []
    
    # Rolleri dağıt
    player_ids = list(players.keys())
    saboteur_id = random.choice(player_ids)
    game_state["saboteur"] = saboteur_id
    
    for pid in player_ids:
        role = "saboteur" if pid == saboteur_id else "crew"
        game_state["roles"][pid] = role
        
        # Her oyuncuya rolünü gönder (private)
        ws = [w for w, p in player_by_ws.items() if p == pid][0] if pid in player_by_ws.values() else None
        if ws:
            try:
                await ws.send_str(build_payload("your_role", role=role, is_saboteur=(role == "saboteur")))
            except:
                pass
    
    await send_state()
    await broadcast(build_payload("game_started"))
    
    # İlk turu başlat
    await asyncio.sleep(2)
    await start_task_round()

async def start_task_round():
    """Yeni görev turu başlat"""
    if game_state["progress"] >= WIN_PROGRESS:
        await end_game("crew")
        return
    
    # Saboteur kazanma kontrolü (crew sayısı <= saboteur sayısı)
    crew_count = sum(1 for pid in game_state["alive"] if game_state["roles"].get(pid) == "crew")
    if crew_count <= 1:
        await end_game("saboteur")
        return
    
    game_state["round"] += 1
    game_state["phase"] = "task"
    game_state["current_task"] = random.choice(TASK_CARDS)
    game_state["choices"] = {}
    game_state["timer"] = TASK_TIME
    
    await send_state()
    await broadcast(build_payload("task_started", task=game_state["current_task"], time=TASK_TIME))
    
    # Timer countdown
    for i in range(TASK_TIME, 0, -1):
        game_state["timer"] = i
        await send_state()
        await asyncio.sleep(1)
    
    await end_task_round()

async def end_task_round():
    """Görev turunu bitir"""
    # Seçimleri değerlendir
    sabotaged = False
    task_done_count = 0
    
    for pid in game_state["alive"]:
        choice = game_state["choices"].get(pid, "SKIP")
        if choice == "SABOTAGE":
            sabotaged = True
        elif choice == "DO":
            task_done_count += 1
    
    # İlerleme güncelle
    if sabotaged:
        game_state["progress"] += SABOTAGE_PENALTY
        result = "sabotaged"
    else:
        game_state["progress"] += TASK_REWARD
        result = "success"
    
    game_state["progress"] = max(0, min(WIN_PROGRESS, game_state["progress"]))
    
    await send_state()
    await broadcast(build_payload("task_result", 
                                  result=result, 
                                  progress=game_state["progress"],
                                  sabotaged=sabotaged))
    
    # Win kontrolü
    if game_state["progress"] >= WIN_PROGRESS:
        await end_game("crew")
        return
    
    # Meeting başlat
    await asyncio.sleep(3)
    await start_meeting()

async def start_meeting():
    """Oylama toplantısı başlat"""
    game_state["phase"] = "meeting"
    game_state["votes"] = {}
    game_state["timer"] = VOTE_TIME
    
    await send_state()
    await broadcast(build_payload("meeting_started", time=VOTE_TIME))
    
    # Timer countdown
    for i in range(VOTE_TIME, 0, -1):
        game_state["timer"] = i
        await send_state()
        await asyncio.sleep(1)
    
    await end_meeting()

async def end_meeting():
    """Oylamayı bitir ve sonucu değerlendir"""
    # Oyları say
    vote_counts = {}
    for pid in game_state["alive"]:
        target = game_state["votes"].get(pid, "skip")
        if target != "skip":
            vote_counts[target] = vote_counts.get(target, 0) + 1
    
    # En çok oy alan
    if vote_counts:
        max_votes = max(vote_counts.values())
        top_voted = [pid for pid, count in vote_counts.items() if count == max_votes]
        
        # Eşitlik yoksa elen
        if len(top_voted) == 1:
            eliminated_pid = top_voted[0]
            game_state["alive"].discard(eliminated_pid)
            game_state["eliminated"].append(eliminated_pid)
            
            eliminated_name = players[eliminated_pid]["name"]
            was_saboteur = game_state["roles"][eliminated_pid] == "saboteur"
            
            await broadcast(build_payload("player_eliminated", 
                                         pid=eliminated_pid,
                                         name=eliminated_name,
                                         was_saboteur=was_saboteur))
            
            # Saboteur elendiyse crew kazanır
            if was_saboteur:
                await asyncio.sleep(3)
                await end_game("crew")
                return
        else:
            await broadcast(build_payload("vote_tie"))
    else:
        await broadcast(build_payload("no_elimination"))
    
    await send_state()
    
    # Win kontrolü
    crew_count = sum(1 for pid in game_state["alive"] if game_state["roles"].get(pid) == "crew")
    if crew_count <= 1:
        await asyncio.sleep(3)
        await end_game("saboteur")
        return
    
    # Yeni tur başlat
    await asyncio.sleep(3)
    await start_task_round()

async def end_game(winner):
    """Oyunu bitir"""
    game_state["phase"] = "ended"
    
    # Skor dağıt
    if winner == "crew":
        for pid in players:
            if game_state["roles"].get(pid) == "crew" and pid in game_state["alive"]:
                players[pid]["score"] += 100
    else:
        saboteur_pid = game_state["saboteur"]
        if saboteur_pid:
            players[saboteur_pid]["score"] += 200
    
    await send_state()
    await broadcast(build_payload("game_ended", 
                                  winner=winner,
                                  saboteur_pid=game_state["saboteur"],
                                  saboteur_name=players.get(game_state["saboteur"], {}).get("name", "Unknown")))

async def reset_game():
    """Oyunu sıfırla"""
    game_state["started"] = False
    game_state["phase"] = "lobby"
    game_state["roles"] = {}
    game_state["alive"] = set()
    game_state["progress"] = 0
    game_state["round"] = 0
    game_state["current_task"] = None
    game_state["choices"] = {}
    game_state["votes"] = {}
    game_state["saboteur"] = None
    game_state["eliminated"] = []
    await send_state()
    await broadcast(build_payload("game_reset"))

# --- HTML Arayüzü ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🕵️ Trust No One</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0B0F19 0%, #1F2937 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        
        /* Glass Cards */
        .glass-card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        
        /* Join Screen */
        #join-screen {
            text-align: center;
            max-width: 400px;
            margin: 100px auto;
        }
        #join-screen input {
            width: 100%;
            padding: 15px;
            font-size: 1.2em;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            margin: 10px 0;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
        }
        #join-screen button {
            width: 100%;
            padding: 15px;
            font-size: 1.2em;
            background: linear-gradient(135deg, #10B981, #059669);
            color: white;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            margin-top: 10px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        #join-screen button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        }
        
        #game-screen { display: none; }
        
        /* Role Badge */
        .role-badge {
            display: inline-block;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: bold;
            margin: 10px 0;
        }
        .role-crew { background: #10B981; }
        .role-saboteur { background: #EF4444; }
        
        /* Progress Bar */
        .progress-container {
            width: 100%;
            height: 40px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #10B981, #34D399);
            border-radius: 20px;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.5);
        }
        
        /* Task Card */
        .task-card {
            background: linear-gradient(135deg, #374151, #1F2937);
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            font-size: 2em;
            margin: 20px 0;
            border: 2px solid rgba(255, 255, 255, 0.2);
        }
        
        /* Buttons */
        .action-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        button {
            padding: 15px 30px;
            font-size: 1.1em;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); }
        button:active { transform: translateY(0); }
        
        .btn-do { background: linear-gradient(135deg, #10B981, #059669); color: white; }
        .btn-skip { background: linear-gradient(135deg, #6B7280, #4B5563); color: white; }
        .btn-sabotage { background: linear-gradient(135deg, #EF4444, #DC2626); color: white; }
        .btn-vote { background: linear-gradient(135deg, #3B82F6, #2563EB); color: white; }
        .btn-start { background: linear-gradient(135deg, #10B981, #059669); color: white; padding: 20px 40px; font-size: 1.3em; }
        
        /* Players List */
        .players-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .player-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            border: 2px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }
        .player-card.dead {
            opacity: 0.5;
            background: rgba(239, 68, 68, 0.2);
            border-color: #EF4444;
        }
        .player-card.alive {
            border-color: #10B981;
        }
        .player-card:hover {
            transform: translateY(-3px);
        }
        
        /* Timer */
        .timer {
            text-align: center;
            font-size: 3em;
            font-weight: bold;
            color: #F59E0B;
            margin: 20px 0;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        /* Announcement */
        .announcement {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.95);
            padding: 50px 80px;
            border-radius: 25px;
            font-size: 2em;
            text-align: center;
            z-index: 1000;
            display: none;
            border: 3px solid #FFD700;
            animation: bounce-in 0.5s ease;
        }
        @keyframes bounce-in {
            0% { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
            50% { transform: translate(-50%, -50%) scale(1.05); }
            100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
        
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🕵️ TRUST NO ONE</h1>
        
        <div id="join-screen" class="glass-card">
            <h2>Oyuna Katıl</h2>
            <input type="text" id="playerName" placeholder="Adınızı girin" maxlength="24">
            <button onclick="joinGame()">Katıl</button>
        </div>
        
        <div id="game-screen">
            <!-- Role Display -->
            <div id="roleCard" class="glass-card hidden">
                <h3>Rolünüz:</h3>
                <div id="roleBadge" class="role-badge"></div>
                <p id="roleDesc"></p>
            </div>
            
            <!-- Progress Bar -->
            <div class="glass-card">
                <h3>Görev İlerlemesi</h3>
                <div class="progress-container">
                    <div class="progress-bar" id="progressBar" style="width: 0%">
                        <span id="progressText">0%</span>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <strong>Tur:</strong> <span id="roundNumber">0</span>
                </div>
            </div>
            
            <!-- Timer -->
            <div id="timerDisplay" class="timer hidden"></div>
            
            <!-- Task Phase -->
            <div id="taskPhase" class="hidden">
                <div class="task-card" id="taskCard">
                    Görev bekleniyor...
                </div>
                <div class="action-buttons">
                    <button class="btn-do" onclick="submitAction('DO')">✅ DO TASK</button>
                    <button class="btn-skip" onclick="submitAction('SKIP')">⏭️ SKIP</button>
                    <button class="btn-sabotage" id="sabotageBtn" onclick="submitAction('SABOTAGE')" style="display:none;">💣 SABOTAGE</button>
                </div>
                <p id="yourChoice" style="text-align: center; font-size: 1.2em; margin-top: 10px;"></p>
            </div>
            
            <!-- Meeting Phase -->
            <div id="meetingPhase" class="hidden">
                <div class="glass-card">
                    <h2 style="text-align: center;">🗳️ VOTING TIME</h2>
                    <p style="text-align: center; margin: 10px 0;">Kimi elemek istersiniz?</p>
                    <div id="voteButtons" class="action-buttons"></div>
                    <p id="yourVote" style="text-align: center; font-size: 1.2em; margin-top: 10px;"></p>
                </div>
            </div>
            
            <!-- Lobby -->
            <div id="lobbyPhase" class="hidden">
                <div class="glass-card" style="text-align: center;">
                    <h2 style="margin-bottom: 20px;">🎮 Lobi</h2>
                    <p id="lobbyMessage" style="font-size: 1.2em; margin-bottom: 20px; color: #F59E0B;">Diğer oyuncular bekleniyor...</p>
                    <button class="btn-start" id="startGameBtn" onclick="startGame()" disabled>▶ OYUNU BAŞLAT</button>
                    <p style="margin-top: 20px; opacity: 0.7;">Minimum 3 oyuncu gerekli</p>
                </div>
            </div>
            
            <!-- Players List -->
            <div class="glass-card">
                <h3>👥 Oyuncular (<span id="aliveCount">0</span> hayatta)</h3>
                <div class="players-grid" id="playersList"></div>
            </div>
            
            <!-- Controls -->
            <div class="glass-card" style="text-align: center;">
                <button class="btn-skip" onclick="resetGame()">🔄 YENİ OYUN</button>
            </div>
        </div>
    </div>
    
    <div class="announcement" id="announcement"></div>
    
    <script>
        let ws = null;
        let myPid = null;
        let myRole = null;
        let gameState = {};
        
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
        }
        
        function handleMessage(data) {
            if (data.type === 'joined') {
                myPid = data.pid;
                document.getElementById('join-screen').style.display = 'none';
                document.getElementById('game-screen').style.display = 'block';
                document.getElementById('lobbyPhase').classList.remove('hidden');
            }
            else if (data.type === 'state') {
                gameState = data;
                updateUI();
                updateLobbyButton();
            }
            else if (data.type === 'your_role') {
                myRole = data.role;
                showRole(data.role, data.is_saboteur);
            }
            else if (data.type === 'game_started') {
                document.getElementById('lobbyPhase').classList.add('hidden');
            }
            else if (data.type === 'task_started') {
                document.getElementById('taskCard').textContent = data.task;
                document.getElementById('yourChoice').textContent = '';
            }
            else if (data.type === 'task_result') {
                const msg = data.sabotaged ? '💥 SABOTAJ! Görev başarısız!' : '✅ Görev tamamlandı!';
                showAnnouncement(msg, 2000);
            }
            else if (data.type === 'meeting_started') {
                updateVoteButtons();
                document.getElementById('yourVote').textContent = '';
            }
            else if (data.type === 'player_eliminated') {
                const msg = `${data.name} elendi!\n${data.was_saboteur ? '🎉 SABOTEUR BULUNDU!' : '😔 Masum birini attınız...'}`;
                showAnnouncement(msg, 3000);
            }
            else if (data.type === 'vote_tie') {
                showAnnouncement('⚖️ Eşitlik! Kimse elenmedi.', 2000);
            }
            else if (data.type === 'no_elimination') {
                showAnnouncement('⏭️ Skip kazandı, kimse elenmedi.', 2000);
            }
            else if (data.type === 'game_ended') {
                const winnerText = data.winner === 'crew' ? '🎉 CREW KAZANDI!' : '💀 SABOTEUR KAZANDI!';
                showAnnouncement(`${winnerText}\n\nSaboteur: ${data.saboteur_name}`, 5000);
            }
            else if (data.type === 'game_reset') {
                location.reload();
            }
        }
        
        function updateUI() {
            // Progress bar
            const progress = Math.max(0, Math.min(100, gameState.progress));
            document.getElementById('progressBar').style.width = progress + '%';
            document.getElementById('progressText').textContent = progress + '%';
            
            // Round
            document.getElementById('roundNumber').textContent = gameState.round;
            
            // Timer
            if (gameState.timer > 0) {
                document.getElementById('timerDisplay').textContent = '⏱️ ' + gameState.timer;
                document.getElementById('timerDisplay').classList.remove('hidden');
            } else {
                document.getElementById('timerDisplay').classList.add('hidden');
            }
            
            // Phase
            document.getElementById('taskPhase').classList.toggle('hidden', gameState.phase !== 'task');
            document.getElementById('meetingPhase').classList.toggle('hidden', gameState.phase !== 'meeting');
            
            // Players
            updatePlayersList();
            
            // Alive count
            document.getElementById('aliveCount').textContent = gameState.alive_count || 0;
        }
        
        function showRole(role, isSaboteur) {
            const roleCard = document.getElementById('roleCard');
            const roleBadge = document.getElementById('roleBadge');
            const roleDesc = document.getElementById('roleDesc');
            
            roleCard.classList.remove('hidden');
            
            if (isSaboteur) {
                roleBadge.className = 'role-badge role-saboteur';
                roleBadge.textContent = '💀 SABOTEUR';
                roleDesc.textContent = 'Görevleri sabote et ve yakalanma!';
                document.getElementById('sabotageBtn').style.display = 'inline-block';
            } else {
                roleBadge.className = 'role-badge role-crew';
                roleBadge.textContent = '👷 CREW';
                roleDesc.textContent = 'Görevleri tamamla ve saboteur\'ü bul!';
            }
        }
        
        function updatePlayersList() {
            const list = document.getElementById('playersList');
            if (!gameState.players) return;
            
            list.innerHTML = gameState.players.map(p => `
                <div class="player-card ${p.alive ? 'alive' : 'dead'}">
                    <div style="font-size: 1.5em;">${p.alive ? '✅' : '💀'}</div>
                    <div style="font-weight: bold; margin: 5px 0;">${p.name}</div>
                    <div style="opacity: 0.7;">Skor: ${p.score}</div>
                    ${!p.alive ? '<div style="color: #EF4444; margin-top: 5px;">ELENDİ</div>' : ''}
                </div>
            `).join('');
        }
        
        function updateVoteButtons() {
            const container = document.getElementById('voteButtons');
            if (!gameState.players) return;
            
            const alivePlayers = gameState.players.filter(p => p.alive && p.id !== myPid);
            
            container.innerHTML = alivePlayers.map(p => `
                <button class="btn-vote" onclick="vote(${p.id})">${p.name}</button>
            `).join('') + '<button class="btn-skip" onclick="vote(\'skip\')">⏭️ SKIP</button>';
        }
        
        function startGame() {
            ws.send(JSON.stringify({type: 'start_game'}));
        }
        
        function submitAction(action) {
            ws.send(JSON.stringify({type: 'submit_action', action: action}));
            document.getElementById('yourChoice').textContent = `Seçiminiz: ${action}`;
        }
        
        function vote(target) {
            ws.send(JSON.stringify({type: 'vote', target: target}));
            const targetName = target === 'skip' ? 'SKIP' : gameState.players.find(p => p.id === target)?.name;
            document.getElementById('yourVote').textContent = `Oyunuz: ${targetName}`;
        }
        
        function resetGame() {
            ws.send(JSON.stringify({type: 'reset_game'}));
        }
        
        function showAnnouncement(msg, duration) {
            const ann = document.getElementById('announcement');
            ann.textContent = msg;
            ann.style.display = 'block';
            setTimeout(() => {
                ann.style.display = 'none';
            }, duration);
        }
        
        function updateLobbyButton() {
            if (!gameState.started && gameState.players) {
                const playerCount = gameState.players.length;
                const lobbyMsg = document.getElementById('lobbyMessage');
                const startBtn = document.getElementById('startGameBtn');
                
                if (playerCount < 3) {
                    lobbyMsg.textContent = `Diğer oyuncular bekleniyor... (${playerCount}/3)`;
                    lobbyMsg.style.color = '#F59E0B';
                    startBtn.disabled = true;
                    startBtn.style.opacity = '0.5';
                    startBtn.style.cursor = 'not-allowed';
                } else {
                    lobbyMsg.textContent = `Hazır! ${playerCount} oyuncu bağlandı`;
                    lobbyMsg.style.color = '#10B981';
                    startBtn.disabled = false;
                    startBtn.style.opacity = '1';
                    startBtn.style.cursor = 'pointer';
                }
            }
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
    print("🕵️ Trust No One - LAN Edition")
    print("=" * 50)
    app = create_app(INDEX_HTML)
    run_server(app, port=8080)

if __name__ == "__main__":
    main()
