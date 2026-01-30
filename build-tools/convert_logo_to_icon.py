#!/usr/bin/env python3
# convert_logo_to_icon.py
# logo.jpg dosyasını Windows .ico formatına çevirir

import os
from PIL import Image

def convert_jpg_to_ico():
    """logo.jpg'yi logo.ico'ya çevir"""
    logo_path = "logo.jpg"
    icon_path = "logo.ico"
    
    if not os.path.exists(logo_path):
        print(f"❌ {logo_path} bulunamadı!")
        return False
    
    try:
        print(f"📸 {logo_path} yükleniyor...")
        img = Image.open(logo_path)
        
        # RGBA'ya çevir (şeffaflık için)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Çoklu boyutlarda kaydet (Windows için optimal)
        # .ico dosyası birden fazla boyut içerebilir
        print("🔄 .ico formatına dönüştürülüyor...")
        img.save(icon_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        
        print(f"✅ {icon_path} başarıyla oluşturuldu!")
        print(f"📦 Boyutlar: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256")
        return True
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        print("\n💡 İpucu: PIL/Pillow kurulu olmalı:")
        print("   pip install Pillow")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🎨 K-LAN Logo -> Icon Converter")
    print("=" * 50)
    print()
    
    if convert_jpg_to_ico():
        print("\n✅ İkon hazır! build_exe.py çalıştırılabilir.")
    else:
        print("\n❌ İkon oluşturulamadı.")
