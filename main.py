#!/usr/bin/env python3
# main.py
# LAN Oyun Kumanda Paneli

import os
import sys
import tkinter as tk
from tkinter import messagebox
import subprocess
import socket
import webbrowser

class LANGameController:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Kumandası")
        self.root.geometry("400x700")
        self.root.configure(bg="#0B0F19")
        self.root.resizable(False, False)
        
        self.game_process = None
        self.server_running = False
        self.selected_game = None
        
        self.setup_ui()
        self.load_games()
        
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#1F2937", height=80)
        header.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        title = tk.Label(
            header,
            text="LAN KUMANDASI",
            font=("Segoe UI", 24, "bold"),
            bg="#1F2937",
            fg="#FFFFFF"
        )
        title.pack(pady=20)
        
        # Status Card
        status_frame = tk.Frame(self.root, bg="#1F2937", relief=tk.FLAT)
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(
            status_frame,
            text="🌐 Sunucu Durumu",
            font=("Segoe UI", 12, "bold"),
            bg="#1F2937",
            fg="#9CA3AF"
        ).pack(pady=(15, 5))
        
        self.status_label = tk.Label(
            status_frame,
            text="⚪ KAPALI",
            font=("Segoe UI", 16, "bold"),
            bg="#1F2937",
            fg="#EF4444"
        )
        self.status_label.pack(pady=(0, 15))
        
        # IP Address
        ip_frame = tk.Frame(status_frame, bg="#1F2937")
        ip_frame.pack(pady=(0, 15))
        
        tk.Label(
            ip_frame,
            text="📡 IP Adresiniz:",
            font=("Segoe UI", 10),
            bg="#1F2937",
            fg="#9CA3AF"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ip = self.get_local_ip()
        self.ip_label = tk.Label(
            ip_frame,
            text=ip,
            font=("Segoe UI", 11, "bold"),
            bg="#1F2937",
            fg="#10B981"
        )
        self.ip_label.pack(side=tk.LEFT)
        
        # Port Setting
        port_frame = tk.Frame(self.root, bg="#1F2937")
        port_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(
            port_frame,
            text="🔌 Port:",
            font=("Segoe UI", 11, "bold"),
            bg="#1F2937",
            fg="#FFFFFF"
        ).pack(side=tk.LEFT, padx=(15, 10))
        
        self.port_var = tk.StringVar(value="8080")
        port_entry = tk.Entry(
            port_frame,
            textvariable=self.port_var,
            font=("Segoe UI", 11),
            bg="#374151",
            fg="#FFFFFF",
            relief=tk.FLAT,
            insertbackground="#FFFFFF",
            width=8
        )
        port_entry.pack(side=tk.LEFT, padx=(0, 15), ipady=5)
        
        # Game Selection
        game_frame = tk.Frame(self.root, bg="#1F2937")
        game_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(
            game_frame,
            text="🎯 Oyun Seçimi",
            font=("Segoe UI", 12, "bold"),
            bg="#1F2937",
            fg="#FFFFFF"
        ).pack(pady=(15, 10))
        
        # Listbox with scrollbar
        list_frame = tk.Frame(game_frame, bg="#1F2937")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.games_listbox = tk.Listbox(
            list_frame,
            font=("Segoe UI", 12),
            bg="#374151",
            fg="#FFFFFF",
            selectbackground="#10B981",
            selectforeground="#FFFFFF",
            relief=tk.FLAT,
            height=8,
            yscrollcommand=scrollbar.set
        )
        self.games_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.games_listbox.yview)
        
        self.games_listbox.bind('<<ListboxSelect>>', self.on_game_select)
        
        # Control Buttons
        control_frame = tk.Frame(self.root, bg="#0B0F19")
        control_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Start Button
        self.start_btn = tk.Button(
            control_frame,
            text="▶ SUNUCUYU BAŞLAT",
            font=("Segoe UI", 13, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            activebackground="#059669",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.toggle_server,
            height=2
        )
        self.start_btn.pack(fill=tk.X, pady=5)
        
        # Open Browser Button
        self.browser_btn = tk.Button(
            control_frame,
            text="🌐 TARAYICIYI AÇ",
            font=("Segoe UI", 11, "bold"),
            bg="#3B82F6",
            fg="#FFFFFF",
            activebackground="#2563EB",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.open_browser,
            state=tk.DISABLED
        )
        self.browser_btn.pack(fill=tk.X, pady=5)
        
        # Refresh Button
        refresh_btn = tk.Button(
            control_frame,
            text="↻ YENİLE",
            font=("Segoe UI", 10),
            bg="#374151",
            fg="#FFFFFF",
            activebackground="#4B5563",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.load_games
        )
        refresh_btn.pack(fill=tk.X, pady=5)
        
        # Exit Button
        exit_btn = tk.Button(
            control_frame,
            text="✕ ÇIKIŞ",
            font=("Segoe UI", 10),
            bg="#EF4444",
            fg="#FFFFFF",
            activebackground="#DC2626",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.quit_app
        )
        exit_btn.pack(fill=tk.X, pady=5)
        
    def get_local_ip(self):
        """Yerel IP adresini al"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
    
    def load_games(self):
        """Oyunları yükle"""
        self.games_listbox.delete(0, tk.END)
        self.games = []
        
        games_dir = os.path.join(os.path.dirname(__file__), "games")
        
        if not os.path.exists(games_dir):
            self.games_listbox.insert(tk.END, "❌ Oyun bulunamadı!")
            return
        
        for file in os.listdir(games_dir):
            if file.endswith("_game.py"):
                game_name = file.replace("_game.py", "").upper()
                game_path = os.path.join(games_dir, file)
                
                self.games.append({
                    "name": game_name,
                    "file": file,
                    "path": game_path
                })
                
                self.games_listbox.insert(tk.END, f"🎲 {game_name}")
        
        if not self.games:
            self.games_listbox.insert(tk.END, "❌ Oyun bulunamadı!")
    
    def on_game_select(self, event):
        """Oyun seçildiğinde"""
        selection = self.games_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.games):
                self.selected_game = self.games[idx]
    
    def toggle_server(self):
        """Sunucuyu başlat/durdur"""
        if not self.server_running:
            self.start_server()
        else:
            self.stop_server()
    
    def start_server(self):
        """Sunucuyu başlat"""
        if not self.selected_game:
            messagebox.showwarning("Uyarı", "Lütfen önce bir oyun seçin!")
            return
        
        try:
            # Python çalıştırıcısını bul
            python_cmd = sys.executable
            
            # Oyunu arka planda başlat
            self.game_process = subprocess.Popen(
                [python_cmd, self.selected_game['path']],
                cwd=os.path.dirname(__file__),
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            self.server_running = True
            self.status_label.config(text="🟢 ÇALIŞIYOR", fg="#10B981")
            self.start_btn.config(
                text="⏹ SUNUCUYU DURDUR",
                bg="#EF4444",
                activebackground="#DC2626"
            )
            self.browser_btn.config(state=tk.NORMAL)
            
            messagebox.showinfo(
                "Başarılı",
                f"🎮 {self.selected_game['name']} sunucusu başlatıldı!\n\n"
                f"📡 Adres: http://{self.get_local_ip()}:{self.port_var.get()}\n\n"
                f"💡 LAN'daki diğer oyuncular bu adrese bağlanabilir!"
            )
            
        except Exception as e:
            messagebox.showerror("Hata", f"Sunucu başlatılamadı:\n{e}")
    
    def stop_server(self):
        """Sunucuyu durdur"""
        if self.game_process:
            self.game_process.terminate()
            self.game_process = None
        
        self.server_running = False
        self.status_label.config(text="⚪ KAPALI", fg="#EF4444")
        self.start_btn.config(
            text="▶ SUNUCUYU BAŞLAT",
            bg="#10B981",
            activebackground="#059669"
        )
        self.browser_btn.config(state=tk.DISABLED)
        
        messagebox.showinfo("Durduruldu", "Sunucu kapatıldı.")
        
    def open_browser(self):
        """Tarayıcıyı aç"""
        url = f"http://localhost:{self.port_var.get()}"
        webbrowser.open(url)
    
    def quit_app(self):
        """Uygulamadan çık"""
        if self.server_running:
            if messagebox.askyesno("Çıkış", "Sunucu çalışıyor. Yine de çıkmak istiyor musunuz?"):
                self.stop_server()
                self.root.quit()
        else:
            self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = LANGameController(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()
