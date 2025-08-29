# lan_kkm.py
# Kiss-Kill-Marry (LAN, çok oyunculu) - tek dosya, offline, tarayıcıdan oynanır.
# Python 3.9+ gerekli. Kurulum: pip install aiohttp

import asyncio
import json
import os
import random
from aiohttp import web, WSMsgType

HOST = "0.0.0.0"
PORT = 8080
ROUND_TIME_LIMIT = 180  # saniye; istersen kapat (None)

# --- Karakterleri yükle ---
DEFAULT_CHARACTERS = [
    "Jett","Phoenix","Sage","Omen","Raze","Sova","Killjoy","Cypher","Brimstone",
    "Viper","Reyna","Skye","Yoru","Astra","Kay/O","Chamber","Neon","Fade","Harbor",
    "Gekko","Deadlock","Iso","Clove"
]

def load_characters():
    path = "character.txt"
    chars = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name:
                    chars.append(name)
    if len(chars) < 3:
        chars = DEFAULT_CHARACTERS[:]  # yedek liste
    return chars

CHARACTERS = load_characters()

# --- Hafıza durumu ---
clients = set()                # WebSocket bağlantıları
players = {}                   # player_id -> {"name": str, "score": int}
player_by_ws = {}              # ws -> player_id
current_round = None           # {"triplet": [a,b,c], "choices": {pid: {"kiss":i,"kill":i,"marry":i}}, "open": bool}
round_index = 0

def pick_unique_three():
    triplet = random.sample(CHARACTERS, 3)
    return triplet

def build_payload(type_, **data):
    out = {"type": type_}
    out.update(data)
    return json.dumps(out, ensure_ascii=False)

async def broadcast(msg: str):
    dead = []
    for ws in clients:
        try:
            await ws.send_str(msg)
        except:
            dead.append(ws)
    for ws in dead:
        await unregister(ws)

async def register(ws, player_name):
    pid = f"p{random.randint(100000, 999999)}"
    players[pid] = {"name": player_name[:24] or "Guest", "score": 0}
    player_by_ws[ws] = pid
    await send_state()
    return pid

async def unregister(ws):
    pid = player_by_ws.get(ws)
    if pid:
        players.pop(pid, None)
    player_by_ws.pop(ws, None)
    if ws in clients:
        clients.remove(ws)
    await send_state()

async def send_state():
    # oyuncu listesi + skorlar
    state = {
        "players": [{"id": pid, "name": p["name"], "score": p["score"]} for pid, p in players.items()],
        "round_index": round_index,
        "round_open": bool(current_round and current_round.get("open")),
        "triplet": current_round["triplet"] if current_round else None,
    }
    await broadcast(build_payload("state", **state))

async def start_round():
    global current_round, round_index
    round_index += 1
    triplet = pick_unique_three()
    current_round = {"triplet": triplet, "choices": {}, "open": True}
    await broadcast(build_payload("round_start", round_index=round_index, triplet=triplet))
    await send_state()
    if ROUND_TIME_LIMIT:
        asyncio.create_task(round_timeout(round_index))

async def round_timeout(idx):
    await asyncio.sleep(ROUND_TIME_LIMIT)
    # süre dolduysa ve hâlâ aynı round açıksa kapat
    if current_round and current_round.get("open") and round_index == idx:
        await end_round()

def all_submitted():
    if not current_round: return False
    return len(current_round["choices"]) >= len(players) and len(players) > 0

async def end_round():
    global current_round
    if not current_round: 
        return
    current_round["open"] = False
    # eksik verenler için boş bırak (puan yok)
    # Skor kuralı: Aynı eşleşmeleri paylaşan herkes + Kiss=1, Kill=1, Marry=2
    # Eşleşmelerin kaç kişi tarafından seçildiğine bakıp ortaklık puanı dağıtacağız.
    choices = current_round["choices"]  # pid -> {"kiss":i,"kill":i,"marry":i}
    if choices:
        # Sıklık tabloları
        from collections import defaultdict
        freq = {"kiss":[0,0,0],"kill":[0,0,0],"marry":[0,0,0]}
        for pid, ch in choices.items():
            for key in ("kiss","kill","marry"):
                idx = ch.get(key)
                if idx in (0,1,2):
                    freq[key][idx] += 1

        # Her oyuncuya ortaklık puanı
        for pid, ch in choices.items():
            sc = 0
            if "kiss" in ch:   sc += 1 if freq["kiss"][ch["kiss"]]   > 1 else 0
            if "kill" in ch:   sc += 1 if freq["kill"][ch["kill"]]   > 1 else 0
            if "marry" in ch:  sc += 2 if freq["marry"][ch["marry"]] > 1 else 0
            players[pid]["score"] += sc

    # Tur sonucu yayınla
    await broadcast(build_payload("round_end", triplet=current_round["triplet"], choices=choices, players=players))
    await send_state()

async def handle_submit(pid, data):
    # data: {"kiss":0..2, "kill":0..2, "marry":0..2}
    if not current_round or not current_round.get("open"):
        return
    k = data.get("kiss"); l = data.get("kill"); m = data.get("marry")
    valid = {0,1,2}
    if k in valid and l in valid and m in valid and len({k,l,m}) == 3:
        current_round["choices"][pid] = {"kiss":k, "kill":l, "marry":m}
        await broadcast(build_payload("partial", who=pid, submitted=len(current_round["choices"]), total=len(players)))
        if all_submitted():
            await end_round()

# --- HTTP ve WebSocket ---

INDEX_HTML = r"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <title>Kiss · Kill · Marry (LAN)</title>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;background:#0f1222;color:#f2f4ff}
    .wrap{max-width:900px;margin:0 auto;padding:20px}
    h1{font-size:20px;margin:0 0 12px}
    .card{background:#171a33;border:1px solid #2a2d4f;border-radius:14px;padding:16px;margin:10px 0;box-shadow:0 6px 14px rgba(0,0,0,.2)}
    input,button{padding:10px 12px;border-radius:10px;border:1px solid #2a2d4f;background:#0e1124;color:#e9ecff}
    button{cursor:pointer}
    .row{display:flex;gap:8px;flex-wrap:wrap}
    .pill{background:#0e1124;border:1px dashed #333759;padding:6px 10px;border-radius:999px;font-size:12px}
    .name{font-weight:700}
    .grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
    .opt{background:#0b0f22;border:1px solid #30345a;border-radius:12px;padding:12px}
    .opt h3{margin:6px 0 12px;font-size:16px}
    .opt .choices{display:flex;gap:8px}
    .opt .cbtn{flex:1}
    .muted{opacity:.8}
    .success{color:#80ffbc}
    .warn{color:#ffdf80}
    .danger{color:#ffa1a1}
    .footer{opacity:.7;font-size:12px;margin-top:10px}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Kiss · Kill · Marry <span class="muted">(LAN)</span></h1>

    <div id="join" class="card">
      <div class="row">
        <input id="name" placeholder="İsmin (örn. Tamer)" />
        <button id="joinBtn">Odaya Katıl</button>
        <button id="hostStartBtn" title="Yeni tur başlat (sadece bir kişi sunsun)">Yeni Tur Başlat</button>
      </div>
      <div class="footer">Bu sayfayı aynı ağdaki herkes açabilir: <span id="hostUrl" class="pill"></span></div>
    </div>

    <div id="state" class="card">
      <div class="row" id="players"></div>
      <div class="muted">Tur: <span id="roundIdx">0</span> · Durum: <span id="roundOpen">kapalı</span></div>
    </div>

    <div id="round" class="card" style="display:none">
      <div class="grid" id="triplet"></div>
      <div class="footer">Her bir isim için birini <b>Kiss</b>, birini <b>Kill</b>, kalanını <b>Marry</b> seç.</div>
    </div>

    <div id="log" class="card" style="display:none"></div>
  </div>

<script>
let ws, pid=null, currentTriplet = null, myPick = {kiss:null, kill:null, marry:null};

function $(id){return document.getElementById(id)}
function log(msg){
  const el=$("log"); el.style.display="block";
  const p=document.createElement("div"); p.innerHTML = msg; el.prepend(p);
}
function renderPlayers(list){
  const el=$("players"); el.innerHTML="";
  list.forEach(p=>{
    const pill=document.createElement("div");
    pill.className="pill";
    pill.innerHTML=`<span class="name">${p.name}</span> · ${p.score} puan`;
    el.appendChild(pill);
  });
}
function renderTriplet(names){
  currentTriplet = names;
  myPick = {kiss:null, kill:null, marry:null};
  const el = $("triplet"); el.innerHTML="";
  const roles = ["kiss","kill","marry"];
  const labels = {kiss:"Kiss",kill:"Kill",marry:"Marry"};
  names.forEach((n,idx)=>{
    const box=document.createElement("div");
    box.className="opt";
    box.innerHTML=`<h3>${idx+1}) ${n}</h3>
      <div class="choices">
        <button class="cbtn" data-role="kiss" data-idx="${idx}">Kiss</button>
        <button class="cbtn" data-role="kill" data-idx="${idx}">Kill</button>
        <button class="cbtn" data-role="marry" data-idx="${idx}">Marry</button>
      </div>
      <div class="muted" id="sel-${idx}">Seçilmedi</div>`;
    el.appendChild(box);
  });
  el.querySelectorAll(".cbtn").forEach(btn=>{
    btn.onclick = ()=>{
      const role = btn.dataset.role, idx = parseInt(btn.dataset.idx);
      // aynı role başka ismi seçerse eskiyi sıfırla
      const prevIndex = Object.keys(myPick).find(k=>myPick[k]===idx);
      // rol değişince eski rolün hedefini sıfırla
      for(const r of Object.keys(myPick)){ if(r!==role && myPick[r]===idx){ myPick[r]=null; $("sel-"+idx).textContent="Seçilmedi"; } }
      // aynı rol daha önce başka indekste ise etiketi temizle
      for(let i=0;i<3;i++){
        if(myPick[role]===i){ $("sel-"+i).textContent="Seçilmedi"; }
      }
      myPick[role] = idx;
      $("sel-"+idx).textContent = "Seçim: " + role.toUpperCase();
      // tüm roller dolunca gönder
      if(myPick.kiss!==null && myPick.kill!==null && myPick.marry!==null && new Set([myPick.kiss,myPick.kill,myPick.marry]).size===3){
        ws.send(JSON.stringify({type:"submit", data: myPick}));
        log("<span class='success'>Seçimlerin gönderildi.</span>");
      }
    };
  });
}

function connect(){
  const proto = location.protocol==="https:" ? "wss" : "ws";
  ws = new WebSocket(proto + "://" + location.host + "/ws");
  ws.onopen = ()=>{ if(pid){ ws.send(JSON.stringify({type:"resume", pid:pid})); } };
  ws.onmessage = (ev)=>{
    try{
      const msg = JSON.parse(ev.data);
      if(msg.type==="hello"){ /* ignore */ }
      if(msg.type==="joined"){ pid = msg.pid; log("Katıldın: "+msg.name); }
      if(msg.type==="state"){
        renderPlayers(msg.players||[]);
        $("roundIdx").textContent = msg.round_index||0;
        $("roundOpen").textContent = msg.round_open ? "açık" : "kapalı";
        if(msg.triplet && msg.round_open){ $("round").style.display="block"; renderTriplet(msg.triplet); }
      }
      if(msg.type==="round_start"){
        $("round").style.display="block";
        renderTriplet(msg.triplet);
        log("<b>Yeni Tur #" + msg.round_index + "</b>");
      }
      if(msg.type==="partial"){
        log("Gönderen sayısı: " + msg.submitted + "/" + msg.total);
      }
      if(msg.type==="round_end"){
        const t = msg.triplet;
        const lines = [];
        lines.push("<div><b>Tur bitti.</b></div>");
        for(const pid in msg.choices){
          const ch = msg.choices[pid];
          const pinfo = (msg.players && msg.players[pid]) ? msg.players[pid] : null;
          const name = pinfo ? pinfo.name : pid;
          lines.push(`<div>• <b>${name}</b> → Kiss: ${t[ch.kiss]}, Kill: ${t[ch.kill]}, Marry: ${t[ch.marry]}</div>`);
        }
        log(lines.join(""));
        $("round").style.display="none";
      }
    }catch(e){console.error(e);}
  };
  ws.onclose = ()=>{ setTimeout(connect, 800); };
}

window.addEventListener("load", ()=>{
  // kendi URL'ini göster
  $("hostUrl").textContent = location.protocol + "//" + location.host;

  $("joinBtn").onclick = ()=>{
    const name = $("name").value.trim() || "Guest";
    ws.send(JSON.stringify({type:"join", name}));
  };
  $("hostStartBtn").onclick = ()=>{ ws.send(JSON.stringify({type:"start_round"})); };
  connect();
});
</script>
</body>
</html>
"""

async def index(request):
    return web.Response(text=INDEX_HTML, content_type="text/html")

async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    clients.add(ws)
    await ws.send_str(build_payload("hello"))

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except:
                    continue
                typ = data.get("type")

                if typ == "join":
                    name = (data.get("name") or "Guest").strip()
                    pid = await register(ws, name)
                    await ws.send_str(build_payload("joined", pid=pid, name=players[pid]["name"]))

                elif typ == "resume":
                    # tekrar bağlanma senaryosu için basit davran: yeni kayıt
                    name = players.get(data.get("pid"), {"name":"Guest"})["name"]
                    pid = await register(ws, name)
                    await ws.send_str(build_payload("joined", pid=pid, name=name))

                elif typ == "start_round":
                    # herhangi biri başlatabilir; gerçek hayatta host kontrolü eklenebilir
                    await start_round()

                elif typ == "submit":
                    pid = player_by_ws.get(ws)
                    if not pid:
                        continue
                    await handle_submit(pid, data.get("data") or {})

            elif msg.type == WSMsgType.ERROR:
                pass
    finally:
        await unregister(ws)
    return ws

def main():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)
    
    # LAN bağlantısı için IP adreslerini göster
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"🌐 Sunucu başlatıldı!")
    print(f"📍 Yerel erişim: http://localhost:{PORT}")
    print(f"🌍 LAN erişimi: http://{local_ip}:{PORT}")
    print(f"🔗 Diğer cihazlar bu adresi kullanabilir: http://{local_ip}:{PORT}")
    print(f"⚠️  Eğer bağlanamıyorsa Windows Güvenlik Duvarı'nı kontrol edin")
    print("-" * 50)
    
    web.run_app(app, host=HOST, port=PORT)

if __name__ == "__main__":
    print(f"Sunucu başlıyor: http://0.0.0.0:{PORT}")
    main()
