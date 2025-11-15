#!/usr/bin/env python3
"""
Генератор дефолтного аватара для админ панели
"""

from PIL import Image, ImageDraw
import os

def create_default_avatar():
    """Создает красивый дефолтный аватар"""
    
    # Размер аватара
    size = 120
    
    # Создаем изображение с прозрачным фоном
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Рисуем круглый фон
    bg_color = (229, 231, 235, 255)  # Серый цвет
    draw.ellipse([0, 0, size-1, size-1], fill=bg_color)
    
    # Рисуем иконку пользователя
    # Голова (круг)
    head_radius = size // 8
    head_center = (size // 2, size // 2 - size // 6)
    head_bbox = [
        head_center[0] - head_radius,
        head_center[1] - head_radius,
        head_center[0] + head_radius,
        head_center[1] + head_radius
    ]
    icon_color = (156, 163, 175, 255)  # Более темный серый
    draw.ellipse(head_bbox, fill=icon_color)
    
    # Тело (полукруг внизу)
    body_radius = size // 3
    body_center = (size // 2, size - size // 6)
    body_bbox = [
        body_center[0] - body_radius,
        body_center[1] - body_radius,
        body_center[0] + body_radius,
        body_center[1] + body_radius
    ]
    draw.ellipse(body_bbox, fill=icon_color)
    
    return img

def main():
    """Создает PNG файл с дефолтным аватаром"""
    
    # Создаем директорию если не существует
    static_dir = "static"
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Генерируем и сохраняем аватар
    avatar = create_default_avatar()
    avatar_path = os.path.join(static_dir, "default-avatar.png")
    avatar.save(avatar_path, "PNG")
    
    print(f"✅ Дефолтный аватар создан: {avatar_path}")
    
    # Создаем также маленькую версию
    small_avatar = avatar.resize((40, 40), Image.LANCZOS)
    small_path = os.path.join(static_dir, "default-avatar-small.png")
    small_avatar.save(small_path, "PNG")
    
    print(f"✅ Маленький аватар создан: {small_path}")

if __name__ == "__main__":
    try:
        main()
    except ImportError:
        print("⚠️ Для создания PNG аватара установите Pillow: pip install Pillow")
        print("📝 Используется SVG версия")
    except Exception as e:
        print(f"❌ Ошибка: {e}")



