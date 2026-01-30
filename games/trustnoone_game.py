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
TASK_TIME = 15
VOTE_TIME = 20
WIN_PROGRESS = 100
SABOTAGE_PENALTY = -5
TASK_REWARD = 8
MIN_PLAYERS = 3

TASK_CARDS = [
    "Router Reset",
    "Firewall Check",
    "Database Backup",
    "CCTV Feed Verify",
    "Patch Update",
    "Log Scan",
    "Power Cycle",
    "Security Audit",
    "Network Ping",
    "System Diagnostics"
]

# --- Oyun Durumu ---
game_state = {
    "started": False,
    "phase": "lobby",
    "roles": {},
    "alive": set(),
    "progress": 0,
    "round": 0,
    "current_task": None,
    "choices": {},
    "votes": {},
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
    typ = data.get("type")
    
    if typ == "join":
        pid = player_by_ws.get(ws)
        if not pid:
            return
        name = data.get("name", "Guest")
        players[pid]["name"] = name
        await ws.send_str(build_payload("joined", pid=pid))
        await send_state()
        return
    
    pid = player_by_ws.get(ws)
    if not pid:
        return
    
    if typ == "start_game":
        if not game_state["started"] and len(players) >= MIN_PLAYERS:
            await start_game()
    
    elif typ == "submit_action":
        if game_state["phase"] == "task" and pid in game_state["alive"]:
            action = data.get("action")
            if action in ["DO", "SKIP", "SABOTAGE"]:
                if action == "SABOTAGE" and game_state["roles"].get(pid) != "saboteur":
                    return
                game_state["choices"][pid] = action
                await send_state()
    
    elif typ == "vote":
        if game_state["phase"] == "meeting" and pid in game_state["alive"]:
            target = data.get("target")
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
    
    player_ids = list(players.keys())
    saboteur_id = random.choice(player_ids)
    game_state["saboteur"] = saboteur_id
    
    for pid in player_ids:
        role = "saboteur" if pid == saboteur_id else "crew"
        game_state["roles"][pid] = role
        
        ws = [w for w, p in player_by_ws.items() if p == pid][0] if pid in player_by_ws.values() else None
        if ws:
            try:
                await ws.send_str(build_payload("your_role", role=role, is_saboteur=(role == "saboteur")))
            except:
                pass
    
    await send_state()
    await broadcast(build_payload("game_started"))
    await asyncio.sleep(2)
    await start_task_round()

async def start_task_round():
    """Yeni görev turu başlat"""
    if game_state["progress"] >= WIN_PROGRESS:
        await end_game("crew")
        return
    
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
    
    for i in range(TASK_TIME, 0, -1):
        game_state["timer"] = i
        await send_state()
        await asyncio.sleep(1)
    
    await end_task_round()

async def end_task_round():
    """Görev turunu bitir"""
    sabotaged = False
    task_done_count = 0
    
    for pid in game_state["alive"]:
        choice = game_state["choices"].get(pid, "SKIP")
        if choice == "SABOTAGE":
            sabotaged = True
        elif choice == "DO":
            task_done_count += 1
    
    if sabotaged:
        game_state["progress"] += SABOTAGE_PENALTY
        result = "sabotaged"
    else:
        game_state["progress"] += TASK_REWARD
        result = "success"
    
    game_state["progress"] = max(0, min(WIN_PROGRESS, game_state["progress"]))
    
    await send_state()
    await broadcast(build_payload("task_result", result=result, progress=game_state["progress"], sabotaged=sabotaged))
    
    if game_state["progress"] >= WIN_PROGRESS:
        await end_game("crew")
        return
    
    await asyncio.sleep(3)
    await start_meeting()

async def start_meeting():
    """Oylama toplantısı başlat"""
    game_state["phase"] = "meeting"
    game_state["votes"] = {}
    game_state["timer"] = VOTE_TIME
    
    await send_state()
    await broadcast(build_payload("meeting_started", time=VOTE_TIME))
    
    for i in range(VOTE_TIME, 0, -1):
        game_state["timer"] = i
        await send_state()
        await asyncio.sleep(1)
    
    await end_meeting()

async def end_meeting():
    """Oylamayı bitir ve sonucu değerlendir"""
    vote_counts = {}
    for pid in game_state["alive"]:
        target = game_state["votes"].get(pid, "skip")
        if target != "skip":
            vote_counts[target] = vote_counts.get(target, 0) + 1
    
    if vote_counts:
        max_votes = max(vote_counts.values())
        top_voted = [pid for pid, count in vote_counts.items() if count == max_votes]
        
        if len(top_voted) == 1:
            eliminated_pid = top_voted[0]
            game_state["alive"].discard(eliminated_pid)
            game_state["eliminated"].append(eliminated_pid)
            
            eliminated_name = players[eliminated_pid]["name"]
            was_saboteur = game_state["roles"][eliminated_pid] == "saboteur"
            
            await broadcast(build_payload("player_eliminated", pid=eliminated_pid, name=eliminated_name, was_saboteur=was_saboteur))
            
            if was_saboteur:
                await asyncio.sleep(3)
                await end_game("crew")
                return
        else:
            await broadcast(build_payload("vote_tie"))
    else:
        await broadcast(build_payload("no_elimination"))
    
    await send_state()
    
    crew_count = sum(1 for pid in game_state["alive"] if game_state["roles"].get(pid) == "crew")
    if crew_count <= 1:
        await asyncio.sleep(3)
        await end_game("saboteur")
        return
    
    await asyncio.sleep(3)
    await start_task_round()

async def end_game(winner):
    """Oyunu bitir"""
    game_state["phase"] = "ended"
    
    if winner == "crew":
        for pid in players:
            if game_state["roles"].get(pid) == "crew" and pid in game_state["alive"]:
                players[pid]["score"] += 100
    else:
        saboteur_pid = game_state["saboteur"]
        if saboteur_pid:
            players[saboteur_pid]["score"] += 200
    
    await send_state()
    await broadcast(build_payload("game_ended", winner=winner, saboteur_pid=game_state["saboteur"], 
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
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trust No One</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0B0F19 0%, #1F2937 100%); color: #fff; min-height: 100vh; padding: 20px; }
body::before { content: ""; position: fixed; inset: 0; background: radial-gradient(900px 450px at 50% 0%, rgba(59,130,246,.20), transparent 60%), radial-gradient(900px 450px at 50% 100%, rgba(16,185,129,.14), transparent 65%), radial-gradient(1200px 700px at 50% 50%, rgba(0,0,0,.35), rgba(0,0,0,.75)); pointer-events: none; z-index: 0; }
.container { max-width: 920px; margin: 0 auto; position: relative; z-index: 1; }
h1 { text-align: center; font-size: 2.5em; margin-bottom: 20px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); letter-spacing: 2px; font-weight: 800; }
.glass-card { background: rgba(255, 255, 255, 0.08); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 18px; padding: 24px; margin-bottom: 18px; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37); }
.glass-card h3 { font-size: 1.1rem; opacity: 0.95; margin-bottom: 12px; }
.glass-card h3::after { content: ""; display: block; height: 2px; width: 72px; margin-top: 10px; background: rgba(255,255,255,.18); border-radius: 99px; }
#join-screen { text-align: center; max-width: 400px; margin: 100px auto; }
#join-screen input { width: 100%; padding: 15px; font-size: 1.2em; border: 2px solid rgba(255, 255, 255, 0.2); border-radius: 12px; margin: 10px 0; background: rgba(255, 255, 255, 0.9); color: #333; }
#join-screen button { width: 100%; padding: 15px; font-size: 1.2em; background: linear-gradient(135deg, #10B981, #059669); color: white; border: none; border-radius: 12px; cursor: pointer; margin-top: 10px; font-weight: bold; transition: all 0.3s ease; }
#join-screen button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4); }
#game-screen { display: none; }
.role-badge { display: inline-block; padding: 10px 20px; border-radius: 8px; font-weight: bold; margin: 10px 0; }
.role-crew { background: #10B981; }
.role-saboteur { background: #EF4444; }
.progress-container { width: 100%; height: 34px; background: rgba(255,255,255,.07); border-radius: 999px; border: 1px solid rgba(255,255,255,.10); overflow: hidden; margin: 20px 0; }
.progress-bar { height: 100%; background: linear-gradient(90deg, #10B981, #34D399); border-radius: 999px; transition: width 0.5s ease; display: flex; align-items: center; justify-content: center; font-weight: bold; box-shadow: 0 0 0 1px rgba(16,185,129,.20) inset, 0 10px 30px rgba(16,185,129,.18); }
.task-card { background: linear-gradient(135deg, #374151, #1F2937); padding: 40px; border-radius: 20px; text-align: center; font-size: 2em; margin: 20px 0; border: 2px solid rgba(255, 255, 255, 0.2); }
.action-buttons { display: flex; gap: 15px; justify-content: center; margin: 20px 0; flex-wrap: wrap; }
button { padding: 15px 30px; font-size: 1.1em; border: none; border-radius: 12px; cursor: pointer; font-weight: bold; transition: all 0.3s ease; }
button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); }
button:active { transform: translateY(0); }
.btn-do { background: linear-gradient(135deg, #10B981, #059669); color: white; }
.btn-skip { background: linear-gradient(135deg, #6B7280, #4B5563); color: white; }
.btn-sabotage { background: linear-gradient(135deg, #EF4444, #DC2626); color: white; }
.btn-vote { background: linear-gradient(135deg, #3B82F6, #2563EB); color: white; }
.btn-start { background: linear-gradient(135deg, #10B981, #059669); color: white; padding: 20px 40px; font-size: 1.3em; border: 1px solid rgba(255,255,255,.12); }
.btn-start:disabled { opacity: 0.45; filter: grayscale(30%); transform: none !important; box-shadow: none !important; cursor: not-allowed; }
.players-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }
.player-card { position: relative; background: rgba(255,255,255,.07); padding: 16px; border-radius: 16px; text-align: center; border: 1px solid rgba(255,255,255,.10); transition: all 0.3s ease; }
.player-card.dead { opacity: 0.6; background: rgba(239, 68, 68, 0.1); }
.player-card:hover { transform: translateY(-3px); }
.player-card.alive::before, .player-card.dead::before { content: ""; position: absolute; top: 12px; right: 12px; width: 10px; height: 10px; border-radius: 99px; }
.player-card.alive::before { background: rgba(16,185,129,.9); box-shadow: 0 0 12px rgba(16,185,129,.6); }
.player-card.dead::before { background: rgba(239,68,68,.9); box-shadow: 0 0 12px rgba(239,68,68,.6); }
.timer { text-align: center; font-size: 3em; font-weight: bold; color: #F59E0B; margin: 20px 0; animation: pulse 1s infinite; }
@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
.announcement { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0, 0, 0, 0.95); padding: 50px 80px; border-radius: 25px; font-size: 2em; text-align: center; z-index: 1000; display: none; border: 3px solid #FFD700; animation: bounce-in 0.5s ease; }
@keyframes bounce-in { 0% { transform: translate(-50%, -50%) scale(0.5); opacity: 0; } 50% { transform: translate(-50%, -50%) scale(1.05); } 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; } }
.hidden { display: none !important; }
</style>
</head>
<body>
<div class="container">
<h1>TRUST NO ONE</h1>
<div id="join-screen" class="glass-card"><h2>Oyuna Katıl</h2><input type="text" id="playerName" placeholder="Adınızı girin" maxlength="24"><button id="joinBtn">Katıl</button></div>
<div id="game-screen">
<div id="roleCard" class="glass-card hidden"><h3>Rolün</h3><div id="roleBadge" class="role-badge"></div><p id="roleDesc"></p></div>
<div class="glass-card"><h3>Görev İlerlemesi</h3><div class="progress-container"><div class="progress-bar" id="progressBar" style="width: 0%"><span id="progressText">0%</span></div></div><div style="text-align: center; margin-top: 10px;"><strong>Tur:</strong> <span id="roundNumber">0</span></div></div>
<div id="timerDisplay" class="timer hidden"></div>
<div id="taskPhase" class="hidden"><div class="task-card" id="taskCard">Gorev bekleniyor...</div><div class="action-buttons"><button class="btn-do" id="doBtn">DO TASK</button><button class="btn-skip" id="skipBtn">SKIP</button><button class="btn-sabotage" id="sabotageBtn" style="display:none;">SABOTAGE</button></div><p id="yourChoice" style="text-align: center; font-size: 1.2em; margin-top: 10px;"></p></div>
<div id="meetingPhase" class="hidden"><div class="glass-card"><h2 style="text-align: center;">Oylama Zamanı</h2><p style="text-align: center; margin: 10px 0;">Kimi elemek istersiniz?</p><div id="voteButtons" class="action-buttons"></div><p id="yourVote" style="text-align: center; font-size: 1.2em; margin-top: 10px;"></p></div></div>
<div id="lobbyPhase" class="hidden"><div class="glass-card" style="text-align: center;"><h2 style="margin-bottom: 20px;">Lobi</h2><p id="lobbyMessage" style="font-size: 1.2em; margin-bottom: 20px; color: #F59E0B;">Diger oyuncular bekleniyor...</p><button class="btn-start" id="startGameBtn" disabled>OYUNU BASLAT</button><p style="margin-top: 20px; opacity: 0.7;">Minimum 3 oyuncu gerekli</p></div></div>
<div class="glass-card"><h3>Oyuncular (<span id="aliveCount">0</span> hayatta)</h3><div class="players-grid" id="playersList"></div></div>
<div class="glass-card" style="text-align: center;"><button class="btn-skip" id="resetBtn">YENI OYUN</button></div>
</div>
</div>
<div class="announcement" id="announcement"></div>
<script>
var ws=null;var myPid=null;var myRole=null;var gameState={};
function joinGame(){var name=document.getElementById('playerName').value.trim()||'Guest';var protocol=window.location.protocol==='https:'?'wss:':'ws:';ws=new WebSocket(protocol+'//'+window.location.host+'/ws');ws.onopen=function(){ws.send(JSON.stringify({type:'join',name:name}));};ws.onmessage=function(event){var data=JSON.parse(event.data);handleMessage(data);};}
function handleMessage(data){if(data.type==='joined'){myPid=data.pid;document.getElementById('join-screen').style.display='none';document.getElementById('game-screen').style.display='block';document.getElementById('lobbyPhase').classList.remove('hidden');}else if(data.type==='state'){gameState=data;updateUI();updateLobbyButton();}else if(data.type==='your_role'){myRole=data.role;showRole(data.role,data.is_saboteur);}else if(data.type==='game_started'){document.getElementById('lobbyPhase').classList.add('hidden');}else if(data.type==='task_started'){document.getElementById('taskCard').textContent=data.task;document.getElementById('yourChoice').textContent='';}else if(data.type==='task_result'){var msg=data.sabotaged?'SABOTAJ! Gorev basarisiz!':'Gorev tamamlandi!';showAnnouncement(msg,2000);}else if(data.type==='meeting_started'){updateVoteButtons();document.getElementById('yourVote').textContent='';}else if(data.type==='player_eliminated'){var msg=data.name+' elendi!\n'+(data.was_saboteur?'SABOTEUR BULUNDU!':'Masum birini attiniz...');showAnnouncement(msg,3000);}else if(data.type==='vote_tie'){showAnnouncement('Esitlik! Kimse elenmedi.',2000);}else if(data.type==='no_elimination'){showAnnouncement('Skip kazandi, kimse elenmedi.',2000);}else if(data.type==='game_ended'){var winnerText=data.winner==='crew'?'CREW KAZANDI!':'SABOTEUR KAZANDI!';showAnnouncement(winnerText+'\n\nSaboteur: '+data.saboteur_name,5000);}else if(data.type==='game_reset'){location.reload();}}
function updateUI(){var progress=Math.max(0,Math.min(100,gameState.progress));document.getElementById('progressBar').style.width=progress+'%';document.getElementById('progressText').textContent=progress+'%';document.getElementById('roundNumber').textContent=gameState.round;if(gameState.timer>0){document.getElementById('timerDisplay').textContent=gameState.timer;document.getElementById('timerDisplay').classList.remove('hidden');}else{document.getElementById('timerDisplay').classList.add('hidden');}if(gameState.phase==='task'){document.getElementById('taskPhase').classList.remove('hidden');}else{document.getElementById('taskPhase').classList.add('hidden');}if(gameState.phase==='meeting'){document.getElementById('meetingPhase').classList.remove('hidden');}else{document.getElementById('meetingPhase').classList.add('hidden');}updatePlayersList();document.getElementById('aliveCount').textContent=gameState.alive_count||0;}
function showRole(role,isSaboteur){var roleCard=document.getElementById('roleCard');var roleBadge=document.getElementById('roleBadge');var roleDesc=document.getElementById('roleDesc');roleCard.classList.remove('hidden');if(isSaboteur){roleBadge.className='role-badge role-saboteur';roleBadge.textContent='SABOTEUR';roleDesc.textContent='Gorevleri sabote et ve yakalanma!';document.getElementById('sabotageBtn').style.display='inline-block';}else{roleBadge.className='role-badge role-crew';roleBadge.textContent='CREW';roleDesc.textContent='Gorevleri tamamla ve saboteur bul!';}}
function updatePlayersList(){var list=document.getElementById('playersList');if(!gameState.players)return;var html='';for(var i=0;i<gameState.players.length;i++){var p=gameState.players[i];var statusClass=p.alive?'alive':'dead';var eliminatedBadge=!p.alive?'<div style="position:absolute;top:8px;left:8px;background:rgba(239,68,68,.9);color:#fff;font-size:0.65rem;padding:3px 8px;border-radius:6px;font-weight:700;">ELENDİ</div>':'';html+='<div class="player-card '+statusClass+'">';html+=eliminatedBadge;html+='<div style="font-weight: bold; font-size: 1.1em; margin-bottom: 6px;">'+p.name+'</div>';html+='<div style="opacity: 0.6; font-size: 0.9em;">Skor: '+p.score+'</div>';html+='</div>';}list.innerHTML=html;}
function updateVoteButtons(){var container=document.getElementById('voteButtons');if(!gameState.players)return;var html='';for(var i=0;i<gameState.players.length;i++){var p=gameState.players[i];if(p.alive&&p.id!==myPid){html+='<button class="btn-vote" data-id="'+p.id+'">'+p.name+'</button>';}}html+='<button class="btn-skip" data-id="skip">SKIP</button>';container.innerHTML=html;var btns=container.getElementsByTagName('button');for(var j=0;j<btns.length;j++){btns[j].onclick=function(){vote(this.getAttribute('data-id'));}}}
function startGame(){ws.send(JSON.stringify({type:'start_game'}));}
function submitAction(action){ws.send(JSON.stringify({type:'submit_action',action:action}));document.getElementById('yourChoice').textContent='Seciminiz: '+action;}
function vote(target){ws.send(JSON.stringify({type:'vote',target:target}));var targetName='SKIP';if(target!=='skip'&&gameState.players){for(var i=0;i<gameState.players.length;i++){if(gameState.players[i].id==target){targetName=gameState.players[i].name;break;}}}document.getElementById('yourVote').textContent='Oyunuz: '+targetName;}
function resetGame(){ws.send(JSON.stringify({type:'reset_game'}));}
function showAnnouncement(msg,duration){var ann=document.getElementById('announcement');ann.textContent=msg;ann.style.display='block';setTimeout(function(){ann.style.display='none';},duration);}
function updateLobbyButton(){if(!gameState.started&&gameState.players){var playerCount=gameState.players.length;var lobbyMsg=document.getElementById('lobbyMessage');var startBtn=document.getElementById('startGameBtn');if(playerCount<3){lobbyMsg.textContent='Diğer oyuncular bekleniyor... ('+playerCount+'/3)';lobbyMsg.style.color='#F59E0B';startBtn.disabled=true;}else{lobbyMsg.textContent='Hazır! '+playerCount+' oyuncu bağlandı';lobbyMsg.style.color='#10B981';startBtn.disabled=false;}}}
document.getElementById('joinBtn').onclick=joinGame;
document.getElementById('startGameBtn').onclick=startGame;
document.getElementById('doBtn').onclick=function(){submitAction('DO');};
document.getElementById('skipBtn').onclick=function(){submitAction('SKIP');};
document.getElementById('sabotageBtn').onclick=function(){submitAction('SABOTAGE');};
document.getElementById('resetBtn').onclick=resetGame;
</script>
</body>
</html>
"""

# Sunucu mesaj yöneticisini override et
import lan.lan_server as server
server.handle_game_message = handle_game_message
server.send_state = send_state

def main():
    print("Trust No One - LAN Edition")
    print("=" * 50)
    app = create_app(INDEX_HTML)
    run_server(app, port=8080)

if __name__ == "__main__":
    main()
