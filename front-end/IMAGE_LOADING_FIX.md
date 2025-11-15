# 🖼️ Исправление загрузки изображений

## 🔴 Проблема

Изображения сохраняются на бэкенде, но фронтенд получает 404 ошибки:
```
GET https://instabot-ten.vercel.app/storage/images/posts/... 404
```

Фронтенд пытается загрузить изображения **со своего домена Vercel**, вместо бэкенда.

## ✅ Что исправлено

Добавлен отладочный лог в функцию `getProxyImageUrl` в `front-end/src/utils/api.ts`:

```typescript
if (url.startsWith('/storage/')) {
  const fullUrl = `${API_BASE_URL}${url}`;
  console.log(`🖼️ Local image: ${url} → ${fullUrl}`);
  return fullUrl;
}
```

## 🚀 Как задеплоить

### 1. Пересоберите фронтенд
```bash
cd front-end
npm run build
```

### 2. Задеплойте на Vercel
```bash
# Если у вас установлен Vercel CLI
vercel --prod

# Или через Git (если настроен auto-deploy)
git add .
git commit -m "fix: add debug logging for image URLs"
git push
```

### 3. Проверьте в консоли браузера

После деплоя откройте приложение и проверьте консоль. Вы должны увидеть логи:
```
🖼️ Local image: /storage/images/profiles/username_hash.jpg → https://insta.truck-tma.ru/storage/images/profiles/username_hash.jpg
🖼️ Local image: /storage/images/posts/post_xxx_hash.jpg → https://insta.truck-tma.ru/storage/images/posts/post_xxx_hash.jpg
```

### 4. Если изображения всё ещё не загружаются

Проверьте:

#### A. Бэкенд раздаёт файлы
```bash
# На сервере
curl -I https://insta.truck-tma.ru/storage/images/profiles/yuroksex_95e0b6ef950192f84aadc8d7c1c1dbac.jpg
```

Должен вернуть `200 OK` и `Content-Type: image/jpeg`

#### B. CORS настроен правильно
В `back-end/main.py` должно быть:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← Разрешить все домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### C. Файлы действительно существуют
```bash
# На сервере
ls -lah storage/images/profiles/
ls -lah storage/images/posts/
ls -lah storage/images/followers/
```

## 🐛 Возможные проблемы

### Проблема 1: Изображения не вызывают `getProxyImageUrl`

**Симптом:** В консоли нет логов `🖼️ Local image:`

**Решение:** Проверьте, что все `<img src={...}>` используют `getProxyImageUrl()`:

```tsx
// ❌ НЕПРАВИЛЬНО
<img src={post.thumbnail_url} />

// ✅ ПРАВИЛЬНО
<img src={getProxyImageUrl(post.thumbnail_url)} />
```

### Проблема 2: URL не начинается с `/storage/`

**Симптом:** В консоли логи показывают другой URL

**Решение:** Проверьте, что бэкенд возвращает правильные пути:
- `save_profile_avatar()` должна возвращать `/storage/images/profiles/{filename}`
- `save_post_image()` должна возвращать `/storage/images/posts/{filename}`
- `save_follower_avatar()` должна возвращать `/storage/images/followers/{filename}`

### Проблема 3: Бэкенд не раздаёт статические файлы

**Симптом:** `curl` возвращает 404

**Решение:** Проверьте в `back-end/main.py`:
```python
from fastapi.staticfiles import StaticFiles

# Должно быть ДО всех роутов
app.mount("/storage", StaticFiles(directory="storage"), name="storage")
```

## 📊 Проверка работы

1. Откройте приложение
2. Спарсите профиль
3. Откройте DevTools → Console
4. Должны увидеть логи `🖼️ Local image:`
5. Откройте DevTools → Network → Img
6. Все запросы к изображениям должны идти на `https://insta.truck-tma.ru/storage/...`
7. Статус должен быть `200 OK`

## 🎯 После исправления

Когда всё заработает, **удалите** отладочные логи из `getProxyImageUrl`:

```typescript
if (url.startsWith('/storage/')) {
  return `${API_BASE_URL}${url}`;  // Без console.log
}
```

И задеплойте финальную версию.




