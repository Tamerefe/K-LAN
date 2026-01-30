# 🏗️ K-LAN Windows .EXE Oluşturma Kılavuzu

## 🎯 Hızlı Başlangıç

### Yöntem 1: Otomatik Build (ÖNERİLEN)

1. **`build.bat`** dosyasına çift tıklayın
2. PyInstaller yoksa kurulumu onaylayın (E)
3. Build tamamlanana kadar bekleyin
4. **`dist\K-LAN.exe`** dosyası oluşacak

### Yöntem 2: Python ile Manuel

```powershell
# PyInstaller kur (ilk seferinde)
pip install pyinstaller

# Build scripti çalıştır
python build_exe.py
```

### Yöntem 3: Doğrudan PyInstaller

```powershell
pyinstaller --onefile --windowed --name=K-LAN --add-data="games;games" --add-data="lan;lan" main.py
```

---

## 📦 Oluşan Dosyalar

### Build Sonrası Klasör Yapısı

```
K-LAN/
├── dist/
│   └── K-LAN.exe          ⬅️ BU DOSYA DAĞITILACAK!
├── build/                 (silinebilir)
├── K-LAN.spec            (silinebilir)
└── ... (diğer dosyalar)
```

---

## 🚀 .EXE Dosyasını Kullanma

1. **`dist\K-LAN.exe`** dosyasını istediğiniz yere kopyalayın
2. Çift tıklayın - Python yüklemeye gerek yok!
3. Oyun menüsü açılacak

### ⚠️ Önemli Notlar

- ✅ Python yüklü olmasına gerek yok
- ✅ Tüm bağımlılıklar dahil
- ✅ Tek dosya - kolay paylaşım
- ⚠️ İlk çalıştırma biraz yavaş olabilir
- ⚠️ Antivirüs programı uyarı verebilir (false positive)

---

## 🔧 Gelişmiş Seçenekler

### İkon Eklemek

**Otomatik (Önerilen):**
- `logo.jpg` dosyası varsa otomatik olarak `.ico` formatına çevrilir ve kullanılır

**Manuel:**
1. `.ico` dosyası oluşturun (32x32, 64x64, 256x256 boyutlarında)
2. `logo.ico` olarak kaydedin
3. `build.bat` veya `build_exe.py` çalıştırın

**JPG/PNG'den ICO'ya Çevirme:**
```powershell
python convert_logo_to_icon.py
```

### Konsol Penceresini Göstermek

`build_exe.py` içinde `--windowed` satırını kaldırın veya `--console` yapın

### Daha Küçük Dosya Boyutu

```powershell
pyinstaller --onefile --name=K-LAN --exclude-module=tkinter.test main.py
```

---

## 🧹 Temizlik

Build dosyalarını temizlemek için:

```powershell
# Windows
rmdir /s /q build dist
del K-LAN.spec

# PowerShell
Remove-Item -Recurse -Force build, dist, K-LAN.spec
```

---

## 🐛 Sorun Giderme

### "PyInstaller bulunamadı"
```powershell
pip install pyinstaller
```

### "ModuleNotFoundError"
```powershell
pip install -r requirements.txt
```

### Antivirüs Uyarısı
- Windows Defender'da istisna ekleyin
- Veya `.exe` dosyasını VirusTotal.com'da taratın

### .exe Çalışmıyor
- `--console` modu ile yeniden build edin (hata mesajlarını görmek için)
- `dist` klasöründeki dosyayı doğrudan çalıştırın

---

## 📤 Dağıtım

### Seçenek 1: Sadece .EXE
- `dist\K-LAN.exe` dosyasını paylaşın
- En basit yöntem

### Seçenek 2: ZIP Paketi
```powershell
# dist klasörünü zipleyip paylaşın
Compress-Archive -Path dist\K-LAN.exe -DestinationPath K-LAN-v1.0.zip
```

### Seçenek 3: Installer (İleri Seviye)
- Inno Setup kullanarak Windows installer oluşturun
- Başlat menüsüne kısayol ekleyin

---

## 📊 Dosya Boyutu

- **Beklenen Boyut:** ~15-25 MB
- Python runtime + tüm kütüphaneler dahil
- İnternet bağlantısı gerekmez

---

## ✅ Build Checklist

- [ ] PyInstaller kurulu
- [ ] `requirements.txt` bağımlılıkları yüklü
- [ ] `build.bat` veya `build_exe.py` çalıştırıldı
- [ ] `dist\K-LAN.exe` oluştu
- [ ] .exe test edildi
- [ ] Antivirüs istisnaları eklendi (gerekirse)
- [ ] Paylaşıma hazır!

---

## 🎮 Kullanıcılar İçin Talimatlar

Projeyi paylaştığınızda kullanıcılara:

1. **K-LAN.exe** dosyasını indirin
2. Çift tıklayın
3. Oyun menüsünden bir oyun seçin
4. Keyfini çıkarın!

*Not: Python yüklemenize gerek yok!*
