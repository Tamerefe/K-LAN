#!/usr/bin/env python3
# build_exe.py
# Windows .exe dosyası oluşturmak için PyInstaller scripti

import os
import sys
import subprocess

def check_dependencies():
    """Gerekli bağımlılıkları kontrol et"""
    missing = []
    
    try:
        import PyInstaller
        print("✅ PyInstaller yüklü")
    except ImportError:
        print("❌ PyInstaller yüklü değil")
        missing.append("pyinstaller")
    
    try:
        from PIL import Image
        print("✅ Pillow yüklü")
    except ImportError:
        print("❌ Pillow yüklü değil (logo için gerekli)")
        missing.append("Pillow")
    
    return missing

def install_dependencies(packages):
    """Eksik bağımlılıkları yükle"""
    print(f"\n📦 Bağımlılıklar kuruluyor: {', '.join(packages)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
        print("✅ Bağımlılıklar başarıyla yüklendi")
        return True
    except subprocess.CalledProcessError:
        print("❌ Bağımlılıklar yüklenemedi")
        return False

def convert_logo_to_icon():
    """logo.jpg'yi logo.ico'ya çevir"""
    logo_path = "logo.jpg"
    icon_path = "logo.ico"
    
    # .ico zaten varsa tekrar çevirme
    if os.path.exists(icon_path):
        print(f"✅ {icon_path} mevcut")
        return True
    
    if not os.path.exists(logo_path):
        print(f"⚠️ {logo_path} bulunamadı, ikon olmadan devam ediliyor")
        return False
    
    try:
        from PIL import Image
        print(f"🎨 {logo_path} -> {icon_path} dönüştürülüyor...")
        
        img = Image.open(logo_path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        img.save(icon_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print(f"✅ İkon oluşturuldu: {icon_path}")
        return True
        
    except Exception as e:
        print(f"⚠️ İkon oluşturulamadı: {e}")
        return False

def build_exe():
    """main.py'den .exe oluştur"""
    print("\n🔨 K-LAN.exe oluşturuluyor...")
    
    # Ana dizine geçiş yap (main.py'nin olduğu yer)
    original_dir = os.getcwd()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    print(f"📂 Çalışma dizini: {project_root}")
    
    # Logo'yu ikona çevir
    icon_available = convert_logo_to_icon()
    
    # PyInstaller komutunu hazırla
    cmd = [
        "pyinstaller",
        "--onefile",                    # Tek dosya halinde
        "--windowed",                   # Konsol penceresi açma (GUI için)
        "--name=K-LAN",                 # Çıktı dosya adı
        "--add-data=games;games",       # games klasörünü dahil et
        "--add-data=lan;lan",           # lan klasörünü dahil et
        "--add-data=README.md;.",       # README'yi dahil et
        "--clean",                      # Önceki build'leri temizle
        "main.py"
    ]
    
    # İkon varsa ekle
    if icon_available and os.path.exists("logo.ico"):
        cmd.insert(4, "--icon=logo.ico")
        print("🎨 Logo ikonu ekleniyor...")
    else:
        print("⚠️ İkon bulunamadı, ikon olmadan devam ediliyor...")
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ BUILD BAŞARILI!")
        print(f"\n📁 K-LAN.exe dosyası şurada: {os.path.join(project_root, 'dist', 'K-LAN.exe')}")
        print("\n🚀 Kullanım:")
        print("   1. dist\\K-LAN.exe dosyasını çift tıklayın")
        print("   2. İstediğiniz yere kopyalayıp kullanabilirsiniz")
        print("   3. Python yüklemeye gerek yok!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build başarısız: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ PyInstaller bulunamadı")
        return False
    finally:
        # Orijinal dizine geri dön
        os.chdir(original_dir)

def clean_build_files():
    """Build dosyalarını temizle"""
    import shutil
    
    # Ana dizinde temizlik yap
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_dir = os.getcwd()
    os.chdir(project_root)
    
    print("\n🧹 Build dosyaları temizleniyor...")
    dirs_to_remove = ["build", "__pycache__"]
    files_to_remove = ["K-LAN.spec", "logo.ico"]
    
    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"   Silindi: {d}")
    
    for f in files_to_remove:
        if os.path.exists(f):
            os.remove(f)
            print(f"   Silindi: {f}")
    
    os.chdir(original_dir)

def main():
    print("=" * 60)
    print("🎮 K-LAN Windows .EXE Builder")
    print("=" * 60)
    
    # Bağımlılıkları kontrol et
    missing = check_dependencies()
    
    if missing:
        print(f"\n⚠️ Eksik bağımlılıklar: {', '.join(missing)}")
        choice = input("\nEksik paketleri yüklemek ister misiniz? (E/H): ")
        if choice.lower() in ['e', 'evet', 'y', 'yes']:
            if not install_dependencies(missing):
                print("\n❌ Kurulum başarısız. Manuel olarak yükleyin:")
                print(f"   pip install {' '.join(missing)}")
                sys.exit(1)
        else:
            print("\n❌ Gerekli paketler eksik. Çıkılıyor...")
            sys.exit(1)
    
    # .exe oluştur
    if build_exe():
        # Temizlik
        clean_choice = input("\nBuild dosyalarını temizlemek ister misiniz? (E/H): ")
        if clean_choice.lower() in ['e', 'evet', 'y', 'yes']:
            clean_build_files()
        
        print("\n" + "=" * 60)
        print("✅ İŞLEM TAMAMLANDI!")
        print("=" * 60)
    else:
        print("\n❌ Build başarısız oldu")
        sys.exit(1)

if __name__ == "__main__":
    main()
