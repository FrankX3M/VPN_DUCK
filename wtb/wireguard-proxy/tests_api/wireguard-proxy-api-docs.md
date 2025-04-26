# WireGuard Proxy API Documentation

## Общая информация

WireGuard Proxy - это сервис, обеспечивающий централизованное управление несколькими WireGuard серверами. Он работает как промежуточный слой между клиентами и удаленными серверами WireGuard, обеспечивая:

- Маршрутизацию запросов к подходящим серверам
- Балансировку нагрузки
- Географическую маршрутизацию
- Кэширование данных
- Аутентификацию
- Сбор метрик и мониторинг

## Базовая информация

- **Базовый URL**: `http://hostname:5001`
- **Формат данных**: JSON
- **Аутентификация**: Различные методы в зависимости от настройки сервера (API Key, OAuth, HMAC)

---

## Аутентификация 

Прокси-сервер поддерживает различные методы аутентификации для взаимодействия с удаленными серверами:

### API Key

#### Процесс получения и использования API-ключа

1. **Получение API-ключа:**
   - При добавлении сервера в систему через административный эндпоинт `/admin/servers`
   - Из базы данных через database-service
   - При первоначальной настройке сервера WireGuard

2. **Необходимые переменные:**
   - `api_key` - секретный ключ доступа
   - `server_id` - идентификатор сервера, для которого используется ключ

3. **Установка API-ключа для сервера:**
   ```bash
   curl -X POST \
     http://your-proxy-server:5001/admin/servers \
     -H "Content-Type: application/json" \
     -d '{
       "api_url": "https://wg-server.example.com/api",
       "location": "Europe/Amsterdam",
       "geolocation_id": "eu-west",
       "name": "Amsterdam Server",
       "auth_type": "api_key",
       "api_key": "your-secret-api-key-here"
     }'
   ```

4. **Использование API-ключа:**
   
   API-ключ передается в заголовке `Authorization`:
   ```
   Authorization: Bearer YOUR_API_KEY
   ```

   Прокси-сервер автоматически добавляет этот заголовок при отправке запросов к удаленным серверам.

5. **Особенности реализации:**
   - API-ключи кэшируются для повторного использования (TTL: 1 час)
   - Если ключ отсутствует или устарел, прокси-сервер автоматически запросит новый
   - При создании конфигурации прокси-сервер сам определяет подходящий сервер и использует соответствующий API-ключ

### OAuth 2.0

Для получения OAuth-токена необходимо выполнить запрос к соответствующему эндпоинту:

```bash
curl -X POST \
  https://oauth-server-url/token \
  -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

Полученный токен используется в заголовке:

```
Authorization: Bearer YOUR_OAUTH_TOKEN
```

### HMAC

HMAC-аутентификация требует создания подписанного сообщения с использованием секретного ключа.

---

## Эндпоинты API

### Проверка работоспособности 

```
GET /health
```

Проверяет работоспособность прокси-сервера.

**Ответ:**

```json
{
  "status": "ok",
  "service": "wireguard-proxy"
}
```

### Создание новой конфигурации WireGuard

```
POST /create
```

Создает новую конфигурацию WireGuard на подходящем удаленном сервере.

**Параметры запроса:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| user_id | string | Да | ID пользователя |
| geolocation_id | string | Нет | ID предпочтительной геолокации сервера |
| [дополнительные параметры] | - | Нет | Дополнительные параметры для настройки пира |

**Пример запроса:**

```bash
curl -X POST \
  http://hostname:5001/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "geolocation_id": "eu-west"
  }'
```

**Пример успешного ответа:**

```json
{
  "public_key": "abcdefg123456=",
  "private_key": "xyz789=",
  "server_endpoint": "1.2.3.4:51820",
  "allowed_ips": "0.0.0.0/0",
  "dns": "1.1.1.1",
  "config": "# WireGuard configuration...",
  "server_id": "server-123"
}
```

### Удаление пира

```
DELETE /remove/{public_key}
```

Удаляет пир с удаленного сервера по публичному ключу.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| public_key | string | Публичный ключ пира |

**Пример запроса:**

```bash
curl -X DELETE \
  http://hostname:5001/remove/abcdefg123456=
```

**Пример успешного ответа:**

```json
{
  "success": true,
  "message": "Peer removed successfully"
}
```

### Получение списка серверов

```
GET /servers
```

Возвращает список доступных серверов.

**Пример запроса:**

```bash
curl -X GET \
  http://hostname:5001/servers
```

**Пример ответа:**

```json
{
  "servers": [
    {
      "id": "server-123",
      "name": "Server 1",
      "location": "Europe/Amsterdam",
      "geolocation_id": "eu-west",
      "api_url": "https://wg-1.example.com/api",
      "load": 0.35,
      "peers_count": 42
    },
    {
      "id": "server-456",
      "name": "Server 2",
      "location": "US/New York",
      "geolocation_id": "us-east",
      "api_url": "https://wg-2.example.com/api",
      "load": 0.28,
      "peers_count": 37
    }
  ]
}
```

### Статус прокси-сервера и удаленных серверов

```
GET /status
```

Возвращает статус работы прокси-сервера и подключенных удаленных серверов.

**Пример запроса:**

```bash
curl -X GET \
  http://hostname:5001/status
```

**Пример ответа:**

```json
{
  "proxy_status": "active",
  "servers_status": [
    {
      "id": "server-123",
      "name": "Server 1",
      "location": "Europe/Amsterdam",
      "status": "online",
      "peers_count": 42,
      "load": 0.35,
      "response_time": 0.178
    },
    {
      "id": "server-456",
      "name": "Server 2",
      "location": "US/New York",
      "status": "offline"
    }
  ],
  "connected_servers": 1,
  "total_servers": 2
}
```

### Метрики работы прокси-сервера

```
GET /metrics
```

Возвращает метрики работы прокси-сервера и удаленных серверов.

**Пример запроса:**

```bash
curl -X GET \
  http://hostname:5001/metrics
```

**Пример ответа:**

```json
{
  "cache_hits": 156,
  "cache_misses": 42,
  "request_count": {
    "create": 35,
    "remove": 12,
    "status": 87,
    "other": 5
  },
  "error_count": {
    "create": 2,
    "remove": 1,
    "status": 0,
    "other": 0
  },
  "server_stats": {
    "server-123": {
      "total_requests": 42,
      "failures": 2,
      "success_rate": 95.24,
      "avg_response_time": 0.187
    }
  }
}
```

## Административные эндпоинты

### Добавление нового сервера

```
POST /admin/servers
```

Добавляет новый удаленный сервер WireGuard (требуются права администратора).

**Параметры запроса:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| api_url | string | Да | URL API удаленного сервера |
| location | string | Да | Физическое местоположение сервера |
| geolocation_id | string | Да | ID геолокации для маршрутизации |
| name | string | Нет | Название сервера |
| api_key | string | Нет | API-ключ для аутентификации на сервере |
| auth_type | string | Нет | Тип аутентификации (api_key, oauth, hmac) |

**Пример запроса:**

```bash
curl -X POST \
  http://hostname:5001/admin/servers \
  -H "Content-Type: application/json" \
  -d '{
    "api_url": "https://wg-3.example.com/api",
    "location": "Asia/Tokyo",
    "geolocation_id": "asia-east",
    "name": "Tokyo Server",
    "auth_type": "api_key",
    "api_key": "your-secret-api-key"
  }'
```

**Пример успешного ответа:**

```json
{
  "success": true,
  "message": "Server added successfully",
  "server_id": "server-789"
}
```

---

## Коды ошибок и их описание

| Код | Описание |
|-----|----------|
| 400 | Неверный запрос - отсутствуют обязательные параметры или неверный формат |
| 401 | Ошибка аутентификации - неверные учетные данные |
| 403 | Доступ запрещен - недостаточно прав для выполнения операции |
| 500 | Внутренняя ошибка сервера - неожиданная ошибка при обработке запроса |
| 502 | Ошибка связи с удаленным сервером - ошибка при обращении к удаленному серверу WireGuard |
| 503 | Сервис недоступен - нет доступных серверов для обработки запроса |

---

## Примеры использования

### Полный жизненный цикл подключения WireGuard

1. Создание нового пира:

```bash
# Создаем новую конфигурацию WireGuard для пользователя
curl -X POST \
  http://hostname:5001/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "geolocation_id": "eu-west"
  }'
```

2. Использование полученной конфигурации в клиенте WireGuard.

3. Удаление пира при завершении использования:

```bash
# Удаляем пир по его публичному ключу
curl -X DELETE \
  http://hostname:5001/remove/abcdefg123456=
```

---

## Особенности и ограничения

1. Прокси-сервер выбирает сервер на основе следующих критериев:
   - Указанная геолокация (при наличии)
   - Текущая нагрузка на сервере
   - Доступность сервера

2. При удалении пира с неизвестным сервером, прокси-сервер попытается удалить пир на всех доступных серверах.

3. Метрики кэша обновляются в режиме реального времени и доступны через эндпоинт `/metrics`.

---

## Работа с ошибками

Прокси-сервер возвращает стандартизированные сообщения об ошибках в следующем формате:

```json
{
  "error": "Краткое описание ошибки",
  "details": "Подробное описание проблемы"
}
```
