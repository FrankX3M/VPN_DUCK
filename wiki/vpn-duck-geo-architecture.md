# Обработчик возврата в главное меню
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' для возврата в главное меню."""
    await bot.answer_callback_query(callback_query.id)
    
    # Завершаем все состояния
    current_state = await state.get_state()
    if current_state:
        await state.finish()
    
    # Получаем информацию о пользователе
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name
    
    # Получаем конфигурацию пользователя
    config = await get_user_config(user_id)
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if config and config.get("active", False):
        # Если есть активная конфигурация, показываем соответствующие кнопки
        keyboard.add(
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📋 Получить конфиг", callback_data="get_config")
        )
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
            InlineKeyboardButton("🌍 Геолокация", callback_data="choose_geo")
        )
        keyboard.add(
            InlineKeyboardButton("🔄 Пересоздать", callback_data="recreate_config")
        )
    else:
        # Если нет активной конфигурации, показываем кнопку создания
        keyboard.add(
            InlineKeyboardButton("🔑 Создать конфигурацию", callback_data="create_config")
        )
    
    await bot.edit_message_text(
        f"👋 Привет, {user_name}!\n\n"
        f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
        f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN "
        f"с возможностью выбора оптимальной геолокации для ваших задач.\n\n"
        f"Выберите действие из меню ниже:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )

##### 8. Обновление скрипта для сбора и анализа метрик серверов

Добавим скрипт для регулярного сбора и анализа метрик серверов, который будет запускаться автоматически:

```python
# Новый файл: server_metrics_collector.py

import os
import time
import logging
import requests
import subprocess
import re
import json
import threading
import math
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
DATABASE_SERVICE_URL = os.getenv('DATABASE_SERVICE_URL', 'http://database-service:5002')
CHECK_INTERVAL = int(os.getenv('METRICS_CHECK_INTERVAL', '300'))  # Интервал проверки в секундах

def get_all_active_servers():
    """Получает список всех активных серверов."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/servers/active", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("servers", [])
        else:
            logger.error(f"Ошибка при получении списка серверов: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return []

def measure_server_metrics(server_id, endpoint):
    """Измеряет сетевые характеристики сервера."""
    try:
        logger.info(f"Измерение метрик для сервера {server_id} ({endpoint})")
        
        # Измерение задержки и джиттера с помощью ping
        ping_result = subprocess.run(
            ["ping", "-c", "10", endpoint],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )
        
        latency = None
        jitter = None
        packet_loss = None
        
        if ping_result.returncode == 0:
            ping_output = ping_result.stdout
            
            # Извлекаем среднюю задержку
            latency_match = re.search(r'min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/([\d.]+)', ping_output)
            if latency_match:
                latency = float(latency_match.group(1))
                jitter = float(latency_match.group(2))
            
            # Извлекаем процент потери пакетов
            packet_loss_match = re.search(r'(\d+)% packet loss', ping_output)
            if packet_loss_match:
                packet_loss = float(packet_loss_match.group(1))
        else:
            logger.warning(f"Ошибка ping для сервера {server_id} ({endpoint}): {ping_result.stderr}")
        
        # Примерное измерение пропускной способности
        # В реальном проекте здесь будет более точная оценка скорости соединения
        bandwidth = None
        try:
            # Запрос небольшого файла для оценки скорости
            start_time = time.time()
            response = requests.get(f"http://{endpoint}/speedtest", timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                content_length = len(response.content)
                duration = end_time - start_time
                if duration > 0:
                    bandwidth = (content_length * 8 / 1000000) / duration  # Mbps
        except Exception as e:
            logger.warning(f"Ошибка при измерении скорости для сервера {server_id}: {str(e)}")
        
        # Сохраняем метрики в базу данных
        metrics = {
            "server_id": server_id,
            "latency": latency,
            "jitter": jitter,
            "packet_loss": packet_loss,
            "bandwidth": bandwidth
        }
        
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/servers/metrics/add",
            json=metrics,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Метрики для сервера {server_id} успешно сохранены")
        else:
            logger.error(f"Ошибка при сохранении метрик: {response.status_code}, {response.text}")
        
        return metrics
    except Exception as e:
        logger.error(f"Ошибка при измерении метрик сервера {server_id}: {str(e)}")
        return None

def analyze_server_metrics():
    """Анализирует метрики серверов и обновляет их рейтинги."""
    try:
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/servers/metrics/analyze",
            timeout=20
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Анализ метрик завершен. Обновлено серверов: {data.get('updated_servers', 0)}")
        else:
            logger.error(f"Ошибка при анализе метрик: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при запросе анализа метрик: {str(e)}")

def check_servers_availability():
    """Проверяет доступность серверов и обновляет их статус."""
    servers = get_all_active_servers()
    
    for server in servers:
        server_id = server.get('id')
        endpoint = server.get('endpoint')
        
        if not endpoint:
            continue
        
        threading.Thread(
            target=measure_server_metrics,
            args=(server_id, endpoint),
            daemon=True
        ).start()
    
    # Даем время на выполнение измерений
    time.sleep(60)
    
    # Анализируем полученные метрики
    analyze_server_metrics()

def run_metrics_collector():
    """Запускает сборщик метрик серверов."""
    logger.info("Запуск сборщика метрик серверов")
    
    while True:
        try:
            # Проверяем доступность и производительность серверов
            check_servers_availability()
        except Exception as e:
            logger.error(f"Ошибка в цикле сбора метрик: {str(e)}")
        
        # Ждем перед следующей проверкой
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Ждем некоторое время перед запуском сборщика метрик
    # для того, чтобы другие сервисы успели запуститься
    time.sleep(60)
    run_metrics_collector()
```

Добавим соответствующий сервис в docker-compose.yml:

```yaml
  metrics-collector:
    build: ./wireguard-service
    restart: always
    depends_on:
      - database-service
      - wireguard-service
    environment:
      - DATABASE_SERVICE_URL=http://database-service:5002
      - METRICS_CHECK_INTERVAL=300
    command: ["python", "server_metrics_collector.py"]
```

##### 9. Обновление API для работы с метриками серверов

Добавим новые эндпоинты в db_manager.py для работы с метриками:

```python
@app.route('/servers/metrics/add', methods=['POST'])
def add_server_metrics():
    """Добавляет новые метрики сервера."""
    data = request.json
    
    server_id = data.get('server_id')
    latency = data.get('latency')
    jitter = data.get('jitter')
    packet_loss = data.get('packet_loss')
    bandwidth = data.get('bandwidth')
    
    if not server_id:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO server_metrics
            (server_id, latency, jitter, packet_loss, bandwidth, measured_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (server_id, latency, jitter, packet_loss, bandwidth)
        )
        
        metric_id = cursor.fetchone()[0]
        
        # Обновляем время последней проверки сервера
        cursor.execute(
            """
            UPDATE servers
            SET last_check = NOW()
            WHERE id = %s
            """,
            (server_id,)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "metric_id": metric_id}), 200
    except Exception as e:
        logger.error(f"Ошибка при добавлении метрик сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/metrics/analyze', methods=['POST'])
def analyze_servers_metrics():
    """Анализирует метрики серверов и обновляет их рейтинги."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем средние метрики за последние 24 часа
        cursor.execute(
            """
            WITH server_avg_metrics AS (
                SELECT 
                    server_id,
                    AVG(latency) as avg_latency,
                    AVG(jitter) as avg_jitter,
                    AVG(packet_loss) as avg_packet_loss,
                    AVG(bandwidth) as avg_bandwidth,
                    COUNT(*) as measurement_count
                FROM server_metrics
                WHERE measured_at > NOW() - INTERVAL '24 hours'
                GROUP BY server_id
            )
            UPDATE servers s
            SET 
                status = CASE
                    WHEN sam.avg_latency IS NULL THEN 'inactive'
                    WHEN sam.avg_packet_loss > 10 THEN 'degraded'
                    ELSE 'active'
                END,
                metrics_rating = CASE
                    WHEN sam.avg_latency IS NULL THEN 0
                    ELSE (
                        (1 - LEAST(sam.avg_latency / 500, 1)) * 0.4 +
                        (1 - LEAST(COALESCE(sam.avg_jitter, 50) / 100, 1)) * 0.2 +
                        (1 - LEAST(COALESCE(sam.avg_packet_loss, 5) / 20, 1)) * 0.2 +
                        LEAST(COALESCE(sam.avg_bandwidth, 10) / 100, 1) * 0.2
                    ) * 100
                END
            FROM server_avg_metrics sam
            WHERE s.id = sam.server_id
            RETURNING s.id, s.status, s.metrics_rating
            """
        )
        
        updated_servers = cursor.fetchall()
        
        # Обновляем связанные таблицы (геолокации, рейтинги серверов и т.д.)
        cursor.execute(
            """
            WITH geo_servers AS (
                SELECT 
                    g.id,
                    COUNT(s.id) FILTER (WHERE s.status = 'active') AS active_servers_count,
                    AVG(s.metrics_rating) FILTER (WHERE s.status = 'active') AS avg_metrics_rating
                FROM geolocations g
                LEFT JOIN servers s ON g.id = s.geolocation_id
                GROUP BY g.id
            )
            UPDATE geolocations g
            SET 
                available = (gs.active_servers_count > 0),
                avg_rating = COALESCE(gs.avg_metrics_rating, 0)
            FROM geo_servers gs
            WHERE g.id = gs.id
            """
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success", 
            "updated_servers": len(updated_servers)
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при анализе метрик: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/<int:server_id>/metrics', methods=['GET'])
def get_server_metrics(server_id):
    """Получает метрики сервера."""
    hours = request.args.get('hours', default=24, type=int)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем средние метрики
        cursor.execute(
            """
            SELECT 
                AVG(latency) as avg_latency,
                AVG(jitter) as avg_jitter,
                AVG(packet_loss) as avg_packet_loss,
                AVG(bandwidth) as avg_bandwidth,
                COUNT(*) as measurement_count,
                MIN(measured_at) as first_measurement,
                MAX(measured_at) as last_measurement
            FROM server_metrics
            WHERE server_id = %s AND measured_at > NOW() - INTERVAL '%s hours'
            """,
            (server_id, hours)
        )
        
        metrics = cursor.fetchone()
        
        # Получаем историю метрик с разбивкой по часам
        cursor.execute(
            """
            SELECT 
                DATE_TRUNC('hour', measured_at) as hour,
                AVG(latency) as avg_latency,
                AVG(jitter) as avg_jitter,
                AVG(packet_loss) as avg_packet_loss,
                AVG(bandwidth) as avg_bandwidth,
                COUNT(*) as measurement_count
            FROM server_metrics
            WHERE server_id = %s AND measured_at > NOW() - INTERVAL '%s hours'
            GROUP BY DATE_TRUNC('hour', measured_at)
            ORDER BY hour
            """,
            (server_id, hours)
        )
        
        metrics_history = cursor.fetchall()
        
        # Преобразуем временные метки в строки
        for item in metrics_history:
            item['hour'] = item['hour'].isoformat()
        
        if metrics and 'first_measurement' in metrics and metrics['first_measurement']:
            metrics['first_measurement'] = metrics['first_measurement'].isoformat()
        if metrics and 'last_measurement' in metrics and metrics['last_measurement']:
            metrics['last_measurement'] = metrics['last_measurement'].isoformat()
        
        conn.close()
        
        return jsonify({
            "metrics": metrics,
            "history": metrics_history
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при получении метрик сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500
```

##### 10. Обновление схемы базы данных для поддержки метрик и рейтингов

Добавим новые поля в таблицы и индексы для оптимизации запросов:

```sql
-- Добавляем поля для рейтингов
ALTER TABLE servers ADD COLUMN IF NOT EXISTS metrics_rating FLOAT DEFAULT 0;
ALTER TABLE geolocations ADD COLUMN IF NOT EXISTS avg_rating FLOAT DEFAULT 0;

-- Создаем дополнительные индексы
CREATE INDEX IF NOT EXISTS idx_servers_metrics_rating ON servers(metrics_rating);
CREATE INDEX IF NOT EXISTS idx_geolocations_avg_rating ON geolocations(avg_rating);
CREATE INDEX IF NOT EXISTS idx_servers_last_check ON servers(last_check);
CREATE INDEX IF NOT EXISTS idx_server_metrics_server_id_measured_at ON server_metrics(server_id, measured_at);
```

##### 11. Заключение

Внедрение улучшенного алгоритма выбора оптимального сервера в мульти-геолокационную архитектуру VPN Duck значительно повысит качество пользовательского опыта. Основные преимущества:

1. **Интеллектуальный выбор сервера** на основе географической близости, сетевых характеристик, нагрузки и предпочтений пользователя.

2. **Мониторинг производительности серверов** позволяет своевременно выявлять проблемы и перенаправлять пользователей на более стабильные серверы.

3. **Динамическая балансировка нагрузки** предотвращает перегрузку отдельных серверов и обеспечивает равномерное распределение пользователей.

4. **Персонализация подключений** на основе истории использования повышает лояльность пользователей и улучшает их опыт.

5. **Улучшенный интерфейс** с информацией о характеристиках серверов помогает пользователям сделать более осознанный выбор геолокации.

Эти улучшения делают VPN Duck более конкурентоспособным на рынке VPN-сервисов, особенно среди технически подкованных пользователей, которые ценят возможность выбора оптимального сервера и прозрачность метрик производительности.
error": "Отсутствуют обязательные поля"}), 400
    
    try:
        # Запускаем измерение метрик в отдельном потоке
        threading.Thread(
            target=measure_server_metrics,
            args=(server_id, endpoint),
            daemon=True
        ).start()
        
        return jsonify({"status": "success", "message": "Обновление метрик запущено"}), 200
    except Exception as e:
        logger.error(f"Ошибка при запуске обновления метрик сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/rebalance', methods=['POST'])
def rebalance_servers_api():
    """API для перебалансировки нагрузки серверов."""
    data = request.json
    
    geolocation_id = data.get('geolocation_id')
    threshold = data.get('threshold', 80)
    
    if not geolocation_id:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        # Обновляем факторы нагрузки серверов
        updated_count = update_server_load_factors()
        
        # Выполняем перебалансировку
        migrated_count = rebalance_server_load(geolocation_id, threshold)
        
        return jsonify({
            "status": "success", 
            "updated_servers": updated_count,
            "migrated_users": migrated_count
        }), 200
    except Exception as e:
        logger.error(f"Ошибка при перебалансировке серверов: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/users/analyze_preferences', methods=['POST'])
def analyze_user_preferences_api():
    """API для анализа предпочтений пользователя."""
    data = request.json
    
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        # Анализируем историю подключений пользователя
        preferences = analyze_user_connection_history(user_id)
        
        if not preferences:
            return jsonify({"error": "Недостаточно данных для анализа предпочтений"}), 404
        
        return jsonify({"preferences": preferences}), 200
    except Exception as e:
        logger.error(f"Ошибка при анализе предпочтений пользователя: {str(e)}")
        return jsonify({"error": str(e)}), 500
```

##### 7. Интеграция с Telegram-ботом

Обновим обработчики геолокаций для использования улучшенного алгоритма выбора сервера:

```python
# Обновляем обработчик выбора геолокации
async def process_geolocation_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора геолокации с использованием улучшенного алгоритма."""
    await bot.answer_callback_query(callback_query.id)
    
    # Получаем выбранную геолокацию
    geolocation_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    
    # Получаем данные из состояния
    state_data = await state.get_data()
    geolocations = state_data.get('geolocations', [])
    
    # Находим название выбранной геолокации
    geolocation_name = "Неизвестная геолокация"
    for geo in geolocations:
        if geo.get('id') == geolocation_id:
            geolocation_name = geo.get('name')
            break
    
    try:
        # Сообщаем пользователю о начале анализа и выбора оптимального сервера
        await bot.edit_message_text(
            f"🔄 <b>Анализ и выбор оптимального сервера...</b>\n\n"
            f"Геолокация: <b>{geolocation_name}</b>\n\n"
            f"Пожалуйста, подождите. Это может занять несколько секунд.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        # Получаем IP-адрес пользователя (если возможно)
        ip_address = None
        # В производственной версии здесь был бы код для определения IP
        
        # Отправляем запрос на выбор оптимального сервера
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/servers/select_optimal",
            json={
                "user_id": user_id,
                "geolocation_id": geolocation_id,
                "ip_address": ip_address
            },
            timeout=10
        )
        
        if response.status_code != 200:
            await bot.edit_message_text(
                f"❌ <b>Ошибка при выборе сервера</b>\n\n"
                f"Не удалось найти оптимальный сервер в выбранной геолокации.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            await state.finish()
            return
        
        server_data = response.json().get("server")
        
        # Обновляем геолокацию в базе данных
        result = await change_config_geolocation(user_id, geolocation_id, server_data['id'])
        
        if "error" in result:
            await bot.edit_message_text(
                f"❌ <b>Ошибка!</b>\n\n{result['error']}",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            await state.finish()
            return
        
        # Дополнительная информация о выбранном сервере
        server_info = []
        if server_data.get('city'):
            server_info.append(f"📍 Город: <b>{server_data['city']}</b>")
        if server_data.get('avg_latency'):
            server_info.append(f"⏱ Ожидаемая задержка: <b>{int(server_data['avg_latency'])} мс</b>")
        
        server_info_text = "\n".join(server_info) if server_info else ""
        
        # Сообщаем пользователю об успешном обновлении конфигурации
        await bot.edit_message_text(
            f"✅ <b>Геолокация успешно изменена на</b> <b>{geolocation_name}</b>\n\n"
            f"Выбран оптимальный сервер на основе:\n"
            f"• Вашего географического положения\n"
            f"• Текущей загрузки серверов\n"
            f"• Качества сетевого соединения\n"
            f"• Ваших предыдущих подключений\n\n"
            f"{server_info_text}\n\n"
            f"Все ваши устройства будут автоматически переключены на новую геолокацию.\n\n"
            f"Если вы используете стандартный клиент WireGuard, вам понадобится обновить конфигурацию. "
            f"Новая конфигурация будет отправлена вам сейчас.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        # Получаем обновленную конфигурацию
        config = await get_user_config(user_id)
        
        if config and config.get("config"):
            config_text = config.get("config")
            
            # Создаем файл конфигурации
            config_file = BytesIO(config_text.encode('utf-8'))
            config_file.name = f"vpn_duck_{user_id}.conf"
            
            # Генерируем QR-код
            qr_buffer = await generate_config_qr(config_text)
            
            if qr_buffer:
                # Отправляем QR-код
                await bot.send_photo(
                    user_id,
                    qr_buffer,
                    caption=f"🔑 <b>QR-код вашей новой конфигурации WireGuard</b>\n\n"
                            f"Геолокация: <b>{geolocation_name}</b>\n\n"
                            f"Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                    parse_mode=ParseMode.HTML
                )
            
            # Отправляем файл конфигурации
            await bot.send_document(
                user_id,
                config_file,
                caption=f"📋 <b>Файл конфигурации WireGuard</b>\n\n"
                        f"Геолокация: <b>{geolocation_name}</b>\n\n"
                        f"Импортируйте этот файл в приложение WireGuard для настройки соединения.",
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем информацию о мобильном приложении
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("📊 Проверить статус", callback_data="status")
            )
            
            await bot.send_message(
                user_id,
                f"📱 <b>Информация о приложении VPN Duck</b>\n\n"
                f"Для более комфортного использования сервиса вы можете скачать наше приложение, "
                f"которое автоматически переключается между серверами и геолокациями "
                f"без необходимости обновления конфигурации.\n\n"
                f"Приложение использует улучшенный алгоритм выбора оптимального сервера, "
                f"который учитывает:\n"
                f"• Ваше географическое положение\n"
                f"• Сетевые характеристики (задержка, скорость)\n"
                f"• Текущую нагрузку на серверы\n"
                f"• Ваши предпочтения на основе истории использования\n\n"
                f"Название для поиска: <b>VPN Duck</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                user_id,
                "⚠️ <b>Не удалось получить обновленную конфигурацию</b>\n\n"
                "Пожалуйста, используйте команду /create для создания новой конфигурации.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Ошибка при обновлении геолокации: {str(e)}", exc_info=True)
        await bot.send_message(
            user_id,
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )
    
    await state.finish()

# Обновляем обработчик получения всех конфигураций
async def get_all_configs(message: types.Message):
    """Получение всех конфигураций пользователя для разных серверов с информацией о характеристиках."""
    user_id = message.from_user.id
    
    try:
        # Получаем все конфигурации пользователя
        result = await get_all_user_configs(user_id)
        
        if "error" in result:
            await message.reply(
                f"⚠️ <b>Ошибка при получении конфигураций</b>\n\n{result['error']}",
                parse_mode=ParseMode.HTML
            )
            return
        
        active_config = result.get("active_config", {})
        all_configs = result.get("all_configs", [])
        
        if not all_configs:
            await message.reply(
                "⚠️ <b>У вас нет сохраненных конфигураций</b>\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем метрики для всех серверов
        server_metrics = {}
        for config in all_configs:
            server_id = config.get("server_id")
            if server_id and server_id not in server_metrics:
                response = requests.get(
                    f"{DATABASE_SERVICE_URL}/servers/{server_id}/metrics",
                    timeout=5
                )
                if response.status_code == 200:
                    server_metrics[server_id] = response.json().get("metrics", {})
        
        # Группируем конфигурации по геолокациям
        geo_configs = {}
        for config in all_configs:
            geo_code = config.get("geo_code")
            geo_name = config.get("geo_name")
            
            if geo_code not in geo_configs:
                geo_configs[geo_code] = {
                    "name": geo_name,
                    "configs": []
                }
            
            # Добавляем метрики сервера
            server_id = config.get("server_id")
            if server_id in server_metrics:
                config["metrics"] = server_metrics[server_id]
            
            geo_configs[geo_code]["configs"].append(config)
        
        # Отправляем информацию о доступных конфигурациях
        message_text = f"📋 <b>Ваши конфигурации VPN Duck</b>\n\n"
        
        # Информация о текущей конфигурации
        expiry_time = active_config.get("expiry_time")
        if expiry_time:
            try:
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                
                message_text += (
                    f"<b>Текущая конфигурация:</b>\n"
                    f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n\n"
                )
            except Exception:
                pass
        
        message_text += "Ниже будут отправлены конфигурации для всех доступных серверов по регионам.\n"
        message_text += "Каждая конфигурация содержит информацию о характеристиках сервера.\n"
        
        await message.reply(message_text, parse_mode=ParseMode.HTML)
        
        # Отправляем конфигурации для каждой геолокации с информацией о характеристиках
        for geo_code, geo_data in geo_configs.items():
            geo_name = geo_data["name"]
            configs = geo_data["configs"]
            
            # Сортируем конфигурации по ожидаемому качеству
            for config in configs:
                metrics = config.get("metrics", {})
                latency = metrics.get("avg_latency", 100)
                bandwidth = metrics.get("avg_bandwidth", 10)
                jitter = metrics.get("avg_jitter", 50)
                
                # Простая формула для оценки качества
                quality_score = (
                    (1 - min(latency / 500, 1)) * 0.5 +  # Чем меньше задержка, тем лучше
                    min(bandwidth / 1000, 1) * 0.3 +     # Чем больше пропускная способность, тем лучше
                    (1 - min(jitter / 100, 1)) * 0.2     # Чем меньше джиттер, тем лучше
                )
                
                config["quality_score"] = quality_score
            
            configs.sort(key=lambda c: c.get("quality_score", 0), reverse=True)
            
            await message.reply(
                f"🌍 <b>Геолокация: {geo_name}</b>\n\n"
                f"Количество серверов: <b>{len(configs)}</b>\n\n"
                f"Отправляю конфигурации для всех серверов в этой геолокации, "
                f"отсортированные по ожидаемому качеству соединения.",
                parse_mode=ParseMode.HTML
            )
            
            # Создаем архив с конфигурациями для этой геолокации
            zip_buffer = BytesIO()
            
            # Используем модуль zipfile для создания архива
            import zipfile
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, config in enumerate(configs, 1):
                    server_endpoint = config.get("endpoint")
                    config_text = config.get("config_text")
                    metrics = config.get("metrics", {})
                    
                    # Добавляем информацию о характеристиках в начало файла конфигурации
                    info_text = (
                        "# VPN Duck - Конфигурация WireGuard\n"
                        f"# Геолокация: {geo_name}\n"
                        f"# Сервер: {server_endpoint}\n"
                    )
                    
                    if metrics:
                        info_text += (
                            f"# Средняя задержка: {int(metrics.get('avg_latency', 0))} мс\n"
                            f"# Средняя скорость: {int(metrics.get('avg_bandwidth', 0))} Мбит/с\n"
                            f"# Стабильность (джиттер): {int(metrics.get('avg_jitter', 0))} мс\n"
                        )
                    
                    info_text += (
                        f"# Ожидаемое качество: {int(config.get('quality_score', 0) * 100)}%\n"
                        "# Для автоматического выбора оптимального сервера используйте мобильное приложение VPN Duck\n\n"
                    )
                    
                    enhanced_config = info_text + config_text
                    
                    # Создаем имя файла конфигурации с рейтингом качества
                    quality_rating = int(config.get('quality_score', 0) * 100)
                    config_filename = f"vpn_duck_{geo_code}_{i:02d}_{quality_rating}_{server_endpoint}.conf"
                    
                    # Добавляем конфигурацию в архив
                    zip_file.writestr(config_filename, enhanced_config)
                
                # Добавляем README файл с инструкциями
                readme_text = (
                    "# VPN Duck - Инструкция по использованию\n\n"
                    f"## Геолокация: {geo_name}\n\n"
                    "Этот архив содержит конфигурации для всех доступных серверов в выбранной геолокации.\n\n"
                    "### Формат имени файлов\n\n"
                    "vpn_duck_[геокод]_[номер]_[рейтинг]_[сервер].conf\n\n"
                    "- [геокод] - код геолокации\n"
                    "- [номер] - порядковый номер сервера\n"
                    "- [рейтинг] - ожидаемое качество соединения (от 0 до 100)\n"
                    "- [сервер] - адрес сервера\n\n"
                    "### Рекомендации\n\n"
                    "1. Для наилучшего результата используйте конфигурации с наивысшим рейтингом.\n"
                    "2. Если соединение нестабильно, попробуйте другой сервер из списка.\n"
                    "3. Для автоматического выбора оптимального сервера используйте мобильное приложение VPN Duck.\n\n"
                    "### Установка\n\n"
                    "1. Распакуйте архив\n"
                    "2. Импортируйте нужный конфигурационный файл в клиент WireGuard\n"
                    "3. Подключитесь к VPN\n\n"
                    "Для вопросов и поддержки обращайтесь в Telegram бот VPN Duck."
                )
                
                zip_file.writestr("README.md", readme_text)
            
            # Перемещаем указатель в начало буфера
            zip_buffer.seek(0)
            
            # Отправляем архив
            zip_buffer.name = f"vpn_duck_{geo_code}_configs.zip"
            await message.reply_document(
                zip_buffer,
                caption=f"📦 <b>Архив с конфигурациями для {geo_name}</b>\n\n"
                        f"Содержит конфигурации для всех серверов в этой геолокации, "
                        f"отсортированные по ожидаемому качеству соединения.\n\n"
                        f"Для использования в приложении VPN Duck, распакуйте архив и "
                        f"импортируйте все конфигурации.",
                parse_mode=ParseMode.HTML
            )
        
        # Отправляем инструкцию для мобильного приложения с информацией об улучшенном алгоритме
        await message.reply(
            "📱 <b>Инструкция для приложения VPN Duck</b>\n\n"
            "1. Скачайте и установите приложение VPN Duck\n"
            "2. Импортируйте все полученные конфигурации\n"
            "3. Приложение автоматически выберет оптимальный сервер на основе:\n"
            "   - Вашего географического положения\n"
            "   - Сетевых характеристик (задержка, скорость)\n"
            "   - Текущей нагрузки на серверы\n"
            "   - Ваших предпочтений на основе истории использования\n\n"
            "Приложение VPN Duck обеспечивает бесшовное переключение между серверами в случае "
            "недоступности текущего сервера или при смене геолокации, используя интеллектуальный "
            "алгоритм выбора оптимального сервера.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка при получении конфигураций: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

def register_handlers_geolocation(dp: Dispatcher):
    """Регистрирует обработчики для геолокаций."""
    dp.register_message_handler(choose_geolocation, commands=['geolocation'])
    dp.register_message_handler(choose_geolocation, lambda message: message.text == "🌍 Геолокация")
    dp.register_message_handler(get_all_configs, commands=['allconfigs'])
    dp.register_callback_query_handler(process_geolocation_selection, lambda c: c.data.startswith('geo_'), state=GeoLocationStates.selecting_geolocation)
    dp.register_callback_query_handler(cancel_geolocation_selection, lambda c: c.data == 'cancel_geo', state=GeoLocationStates.selecting_geolocation)
    
    # Дополнительные обработчики для UI-кнопок
    dp.register_callback_query_handler(choose_geolocation, lambda c: c.data == 'choose_geo')
    dp.register_callback_query_handler(get_all_configs, lambda c: c.data == 'get_all_configs')
    
    # Обработчик для кнопки "Назад"
    dp.register_callback_query_handler(back_to_main_menu, lambda c: c.data == 'back_to_main', state='*')

# Обработчик возврата в главное меню
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' для возврата в главное меню."""
    await bot.answer_callback_query(callback_query.id)
    
    # Завершаем все состояния
    current_state = await state.get_state()
    if current_state:
        await state.finish()
    
    # Получаем информацию о пользователе
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name
    
    # Получаем конфигурацию пользователя
    config = await get_user_config(user_id)
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if config and config.get("active", False):
        # Если есть активная конфигурация, показываем соответствующие кнопки
        keyboard.add(
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📋 Получить конфиг", callback_data="get_config")
        )
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
            InlineKeyboardButton("🌍 Геолокация", callback_data="choose_geo")
        )
        keyboard.add(
            InlineKeyboardButton("🔄 Пересоздать", callback_data="recreate_config")
        )
    else:
        # Если нет активной конфигурации, показываем кнопку создания
        keyboard.add(
            InlineKeyboardButton("🔑 Создать конфигурацию", callback_data="create_config")
        )
    
    await bot.edit_message_text(
        f"👋 Привет, {user_name}!\n\n"
        f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
        f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN "
        f"с возможностью выбора оптимальной геолокации для ваших задач.\n\n"
        f"Выберите действие из меню ниже:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
```

#### Улучшенный интерфейс для управления геолокациями

Обновим клавиатуру для управления геолокациями, добавив информацию о рейтинге серверов:

```python
def get_geolocation_keyboard(geolocations):
    """Возвращает клавиатуру с доступными геолокациями и информацией о серверах."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    # Получаем статистику по серверам в каждой геолокации
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    for geo in geolocations:
        geo_id = geo.get('id')
        
        # Получаем количество активных серверов и среднюю задержку
        cursor.execute(
            """
            SELECT 
                COUNT(*) as server_count,
                AVG(sm.latency) as avg_latency
            FROM servers s
            LEFT JOIN (
                SELECT 
                    server_id,
                    AVG(latency) as latency
                FROM server_metrics
                WHERE measured_at > NOW() - INTERVAL '1 hour'
                GROUP BY server_id
            ) sm ON s.id = sm.server_id
            WHERE s.geolocation_id = %s AND s.status = 'active'
            """,
            (geo_id,)
        )
        
        stats = cursor.fetchone()
        server_count = stats['server_count'] if stats else 0
        avg_latency = int(stats['avg_latency']) if stats and stats['avg_latency'] else "N/A"
        
        # Формируем текст кнопки с информацией
        button_text = f"{geo.get('name', 'Неизвестно')} ({server_count} серв."
        if avg_latency != "N/A":
            button_text += f", ~{avg_latency} мс"
        button_text += ")"
        
        keyboard.add(
            InlineKeyboardButton(
                button_text,
                callback_data=f"geo_{geo.get('id')}"
            )
        )
    
    conn.close()
    
    # Доб### 17. Улучшение алгоритма выбора оптимального сервера

Текущий алгоритм выбора сервера имеет ряд ограничений, которые снижают качество пользовательского опыта. Рассмотрим детально эти ограничения и предложим конкретные улучшения в рамках архитектуры мульти-геолокаций.

#### Текущие ограничения

1. **Отсутствие учета географической близости**: Текущий алгоритм не учитывает фактическое расстояние между пользователем и сервером в рамках одной геолокации, что может приводить к неоптимальным подключениям.

2. **Отсутствие учета сетевых характеристик**: Не учитываются такие важные параметры как задержка (latency), пропускная способность (bandwidth) и джиттер (jitter), что напрямую влияет на качество VPN-соединения.

3. **Статическое распределение**: Нет динамического перераспределения пользователей для балансировки нагрузки, что может приводить к перегрузке отдельных серверов.

4. **Отсутствие персонализации**: Не учитываются предпочтения пользователя и история его подключений, что ухудшает пользовательский опыт.

#### Предлагаемые улучшения

##### 1. Учет географической близости

Добавим функциональность для определения примерного географического местоположения пользователя и выбора ближайшего сервера в рамках выбранной геолокации:

```python
# Добавим новые таблицы в базу данных

"""
CREATE TABLE IF NOT EXISTS server_locations (
    server_id INTEGER PRIMARY KEY REFERENCES servers(id),
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    city TEXT,
    country TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_locations (
    user_id INTEGER PRIMARY KEY,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    city TEXT,
    country TEXT,
    accuracy FLOAT,  -- Точность определения в километрах
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

def determine_user_location(user_id, ip_address=None):
    """Определяет географическое положение пользователя по IP-адресу или истории."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже свежие данные о местоположении пользователя
    cursor.execute(
        """
        SELECT latitude, longitude, city, country, updated_at
        FROM user_locations
        WHERE user_id = %s AND updated_at > NOW() - INTERVAL '1 day'
        """,
        (user_id,)
    )
    
    user_location = cursor.fetchone()
    
    if user_location:
        # Используем существующие данные, если они свежие
        conn.close()
        return {
            'latitude': user_location[0],
            'longitude': user_location[1],
            'city': user_location[2],
            'country': user_location[3]
        }
    
    # Если IP-адрес не передан, пытаемся получить последний известный
    if not ip_address:
        cursor.execute(
            """
            SELECT ip_address 
            FROM user_connections 
            WHERE user_id = %s 
            ORDER BY connected_at DESC 
            LIMIT 1
            """,
            (user_id,)
        )
        result = cursor.fetchone()
        if result:
            ip_address = result[0]
    
    if ip_address:
        try:
            # Используем внешний сервис геолокации по IP
            geo_service_url = os.getenv('GEO_SERVICE_URL', 'https://ipapi.co')
            response = requests.get(f"{geo_service_url}/{ip_address}/json/")
            
            if response.status_code == 200:
                location_data = response.json()
                
                # Сохраняем полученные данные
                latitude = location_data.get('latitude')
                longitude = location_data.get('longitude')
                city = location_data.get('city')
                country = location_data.get('country_name')
                
                if latitude and longitude:
                    cursor.execute(
                        """
                        INSERT INTO user_locations (user_id, latitude, longitude, city, country, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (user_id) DO UPDATE 
                        SET latitude = EXCLUDED.latitude, 
                            longitude = EXCLUDED.longitude,
                            city = EXCLUDED.city,
                            country = EXCLUDED.country,
                            updated_at = NOW()
                        """,
                        (user_id, latitude, longitude, city, country)
                    )
                    conn.commit()
                    
                    conn.close()
                    return {
                        'latitude': latitude,
                        'longitude': longitude,
                        'city': city,
                        'country': country
                    }
        except Exception as e:
            logger.error(f"Ошибка при определении геолокации по IP: {str(e)}")
    
    # Если не удалось определить местоположение, возвращаем None
    conn.close()
    return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Рассчитывает расстояние между двумя точками на земной поверхности в километрах."""
    R = 6371  # Радиус Земли в километрах
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def find_nearest_servers(user_location, geolocation_id, limit=3):
    """Находит ближайшие серверы к пользователю в указанной геолокации."""
    if not user_location or 'latitude' not in user_location or 'longitude' not in user_location:
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Получаем все активные серверы в указанной геолокации
    cursor.execute(
        """
        SELECT s.id, s.endpoint, s.port, s.status, s.load_factor, sl.latitude, sl.longitude, sl.city
        FROM servers s
        JOIN server_locations sl ON s.id = sl.server_id
        WHERE s.geolocation_id = %s AND s.status = 'active'
        """,
        (geolocation_id,)
    )
    
    servers = cursor.fetchall()
    conn.close()
    
    # Рассчитываем расстояние для каждого сервера
    for server in servers:
        if 'latitude' in server and 'longitude' in server:
            server['distance'] = calculate_distance(
                user_location['latitude'], user_location['longitude'],
                server['latitude'], server['longitude']
            )
        else:
            server['distance'] = float('inf')
    
    # Сортируем серверы по расстоянию
    sorted_servers = sorted(servers, key=lambda s: s.get('distance', float('inf')))
    
    return sorted_servers[:limit]
```

##### 2. Учет сетевых характеристик

Внедрим систему мониторинга сетевых характеристик и учет их при выборе сервера:

```python
# Добавим новую таблицу для хранения метрик серверов

"""
CREATE TABLE IF NOT EXISTS server_metrics (
    id SERIAL PRIMARY KEY,
    server_id INTEGER REFERENCES servers(id),
    latency FLOAT,  -- Задержка в миллисекундах
    bandwidth FLOAT,  -- Пропускная способность в Mbps
    jitter FLOAT,  -- Джиттер в миллисекундах
    packet_loss FLOAT,  -- Потеря пакетов в процентах
    measured_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_server_metrics_server_id ON server_metrics(server_id);
CREATE INDEX IF NOT EXISTS idx_server_metrics_measured_at ON server_metrics(measured_at);
"""

def measure_server_metrics(server_id, endpoint):
    """Измеряет сетевые характеристики сервера."""
    try:
        # Измерение задержки и джиттера с помощью ping
        ping_result = subprocess.run(
            ["ping", "-c", "10", endpoint],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )
        
        if ping_result.returncode == 0:
            ping_output = ping_result.stdout
            
            # Извлекаем среднюю задержку
            latency_match = re.search(r'min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/([\d.]+)', ping_output)
            if latency_match:
                avg_latency = float(latency_match.group(1))
                jitter = float(latency_match.group(2))
            else:
                avg_latency = None
                jitter = None
            
            # Извлекаем процент потери пакетов
            packet_loss_match = re.search(r'(\d+)% packet loss', ping_output)
            packet_loss = float(packet_loss_match.group(1)) if packet_loss_match else None
            
            # Измерение пропускной способности (в реальном сценарии здесь будет более сложный код)
            # Для примера используем фиктивное значение
            bandwidth = 100.0  # Mbps
            
            # Сохраняем метрики в базу данных
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO server_metrics (server_id, latency, bandwidth, jitter, packet_loss, measured_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                (server_id, avg_latency, bandwidth, jitter, packet_loss)
            )
            
            conn.commit()
            conn.close()
            
            return {
                'latency': avg_latency,
                'bandwidth': bandwidth,
                'jitter': jitter,
                'packet_loss': packet_loss
            }
    except Exception as e:
        logger.error(f"Ошибка при измерении метрик сервера {server_id}: {str(e)}")
    
    return None

def get_server_average_metrics(server_id, hours=1):
    """Получает средние метрики сервера за указанный период."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        """
        SELECT 
            AVG(latency) as avg_latency,
            AVG(bandwidth) as avg_bandwidth,
            AVG(jitter) as avg_jitter,
            AVG(packet_loss) as avg_packet_loss
        FROM server_metrics
        WHERE server_id = %s AND measured_at > NOW() - INTERVAL '%s hours'
        """,
        (server_id, hours)
    )
    
    metrics = cursor.fetchone()
    conn.close()
    
    return metrics
```

##### 3. Динамическое распределение нагрузки

Реализуем механизм динамического перераспределения пользователей для оптимизации нагрузки:

```python
# Добавим новую таблицу для хранения активных соединений

"""
CREATE TABLE IF NOT EXISTS active_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    server_id INTEGER REFERENCES servers(id),
    connected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address TEXT,
    bytes_sent BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_active_connections_user_id ON active_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_active_connections_server_id ON active_connections(server_id);
"""

def update_server_load_factors():
    """Обновляет факторы нагрузки серверов на основе активных соединений."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Рассчитываем нагрузку на основе количества активных соединений и трафика
    cursor.execute(
        """
        WITH server_loads AS (
            SELECT 
                server_id,
                COUNT(*) as connection_count,
                SUM(bytes_sent + bytes_received) as total_traffic
            FROM active_connections
            WHERE last_activity > NOW() - INTERVAL '10 minutes'
            GROUP BY server_id
        )
        UPDATE servers s
        SET load_factor = COALESCE(
            -- Нормализуем значение к диапазону [0, 100]
            LEAST(
                (sl.connection_count * 5) + (sl.total_traffic / 1000000000), 
                100
            ),
            0
        )
        FROM server_loads sl
        WHERE s.id = sl.server_id
        RETURNING s.id, s.load_factor
        """
    )
    
    updated_servers = cursor.fetchall()
    conn.commit()
    
    # Логируем обновленные значения
    for server in updated_servers:
        logger.info(f"Обновлен фактор нагрузки сервера {server[0]}: {server[1]}")
    
    conn.close()
    
    return len(updated_servers)

def rebalance_server_load(geolocation_id, threshold=80):
    """Перераспределяет пользователей с перегруженных серверов."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Находим перегруженные серверы
    cursor.execute(
        """
        SELECT id, endpoint, load_factor
        FROM servers
        WHERE geolocation_id = %s AND status = 'active' AND load_factor > %s
        ORDER BY load_factor DESC
        """,
        (geolocation_id, threshold)
    )
    
    overloaded_servers = cursor.fetchall()
    
    if not overloaded_servers:
        conn.close()
        return 0
    
    # Находим недогруженные серверы
    cursor.execute(
        """
        SELECT id, endpoint, load_factor
        FROM servers
        WHERE geolocation_id = %s AND status = 'active' AND load_factor < %s
        ORDER BY load_factor ASC
        """,
        (geolocation_id, threshold / 2)
    )
    
    underloaded_servers = cursor.fetchall()
    
    if not underloaded_servers:
        conn.close()
        return 0
    
    migrated_count = 0
    
    # Для каждого перегруженного сервера находим пользователей для миграции
    for overloaded_server in overloaded_servers:
        # Определяем сколько пользователей нужно мигрировать
        target_reduction = (overloaded_server['load_factor'] - threshold) / 5  # Примерно 5% нагрузки на пользователя
        users_to_migrate = max(1, int(target_reduction))
        
        # Находим пользователей для миграции
        cursor.execute(
            """
            SELECT ac.id, ac.user_id
            FROM active_connections ac
            WHERE ac.server_id = %s AND ac.last_activity > NOW() - INTERVAL '30 minutes'
            ORDER BY ac.last_activity ASC
            LIMIT %s
            """,
            (overloaded_server['id'], users_to_migrate)
        )
        
        users = cursor.fetchall()
        
        for user in users:
            # Выбираем недогруженный сервер с наименьшей нагрузкой
            target_server = underloaded_servers[0]
            
            # Создаем новую запись в таблице миграций
            cursor.execute(
                """
                INSERT INTO server_migrations (user_id, from_server_id, to_server_id, migration_reason)
                VALUES (%s, %s, %s, 'load_balancing')
                """,
                (user['user_id'], overloaded_server['id'], target_server['id'])
            )
            
            # Обновляем нагрузку серверов
            target_server['load_factor'] += 5  # Примерное увеличение
            overloaded_server['load_factor'] -= 5  # Примерное уменьшение
            
            # Переупорядочиваем недогруженные серверы
            underloaded_servers.sort(key=lambda s: s['load_factor'])
            
            migrated_count += 1
    
    conn.commit()
    conn.close()
    
    return migrated_count
```

##### 4. Персонализация выбора сервера

Учет предпочтений пользователя и истории его подключений:

```python
# Добавим новые таблицы для хранения истории подключений и предпочтений

"""
CREATE TABLE IF NOT EXISTS user_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    server_id INTEGER REFERENCES servers(id),
    geolocation_id INTEGER REFERENCES geolocations(id),
    connected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    disconnected_at TIMESTAMP,
    duration INTEGER,  -- Длительность соединения в секундах
    bytes_sent BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0,
    connection_quality INTEGER,  -- Оценка качества от 1 до 10
    ip_address TEXT
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY,
    preferred_server_id INTEGER REFERENCES servers(id),
    preferred_geolocation_id INTEGER REFERENCES geolocations(id),
    preferred_time_start TIME,
    preferred_time_end TIME,
    preferred_connection_type TEXT,  -- streaming, browsing, gaming, etc.
    auto_connect BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_connections_user_id ON user_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_user_connections_server_id ON user_connections(server_id);
CREATE INDEX IF NOT EXISTS idx_user_connections_connected_at ON user_connections(connected_at);
"""

def analyze_user_connection_history(user_id):
    """Анализирует историю подключений пользователя для выявления предпочтений."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Получаем историю подключений пользователя за последние 30 дней
    cursor.execute(
        """
        SELECT 
            server_id,
            geolocation_id,
            COUNT(*) as connection_count,
            AVG(duration) as avg_duration,
            AVG(connection_quality) as avg_quality,
            EXTRACT(HOUR FROM connected_at) as hour_of_day
        FROM user_connections
        WHERE user_id = %s AND connected_at > NOW() - INTERVAL '30 days'
        GROUP BY server_id, geolocation_id, EXTRACT(HOUR FROM connected_at)
        ORDER BY connection_count DESC, avg_quality DESC
        """,
        (user_id,)
    )
    
    connections = cursor.fetchall()
    
    if not connections:
        conn.close()
        return None
    
    # Определяем предпочитаемый сервер и геолокацию
    preferred_server_id = connections[0]['server_id']
    preferred_geolocation_id = connections[0]['geolocation_id']
    
    # Определяем предпочитаемое время суток
    hour_counts = {}
    for conn in connections:
        hour = int(conn['hour_of_day'])
        hour_counts[hour] = hour_counts.get(hour, 0) + conn['connection_count']
    
    peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
    preferred_time_start = peak_hours[0][0] if peak_hours else None
    preferred_time_end = (preferred_time_start + 3) % 24 if preferred_time_start is not None else None
    
    # Сохраняем предпочтения пользователя
    cursor.execute(
        """
        INSERT INTO user_preferences 
        (user_id, preferred_server_id, preferred_geolocation_id, preferred_time_start, preferred_time_end, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE
        SET preferred_server_id = EXCLUDED.preferred_server_id,
            preferred_geolocation_id = EXCLUDED.preferred_geolocation_id,
            preferred_time_start = EXCLUDED.preferred_time_start,
            preferred_time_end = EXCLUDED.preferred_time_end,
            updated_at = NOW()
        """,
        (
            user_id, 
            preferred_server_id, 
            preferred_geolocation_id, 
            f"{preferred_time_start}:00" if preferred_time_start is not None else None,
            f"{preferred_time_end}:00" if preferred_time_end is not None else None
        )
    )
    
    conn.commit()
    conn.close()
    
    return {
        'preferred_server_id': preferred_server_id,
        'preferred_geolocation_id': preferred_geolocation_id,
        'preferred_time_start': preferred_time_start,
        'preferred_time_end': preferred_time_end
    }

def get_user_preferences(user_id):
    """Получает сохраненные предпочтения пользователя."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        """
        SELECT * FROM user_preferences WHERE user_id = %s
        """,
        (user_id,)
    )
    
    preferences = cursor.fetchone()
    conn.close()
    
    return preferences
```

##### 5. Комплексный алгоритм выбора сервера

Объединим все факторы в комплексный алгоритм выбора оптимального сервера:

```python
def select_optimal_server(user_id, geolocation_id):
    """Выбирает оптимальный сервер с учетом всех факторов."""
    try:
        # 1. Получаем локацию пользователя
        user_location = determine_user_location(user_id)
        
        # 2. Получаем предпочтения пользователя
        user_preferences = get_user_preferences(user_id)
        
        # 3. Получаем все активные серверы в выбранной геолокации
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT s.*, sl.latitude, sl.longitude, sl.city
            FROM servers s
            LEFT JOIN server_locations sl ON s.id = sl.server_id
            WHERE s.geolocation_id = %s AND s.status = 'active'
            """,
            (geolocation_id,)
        )
        
        servers = cursor.fetchall()
        
        if not servers:
            conn.close()
            return None
        
        # 4. Для каждого сервера получаем сетевые метрики
        for server in servers:
            metrics = get_server_average_metrics(server['id'])
            if metrics:
                server.update(metrics)
        
        # 5. Рассчитываем рейтинг для каждого сервера
        for server in servers:
            # Базовый рейтинг - инвертированная нагрузка (чем меньше нагрузка, тем выше рейтинг)
            load_score = 1 - min(server.get('load_factor', 0) / 100, 1)
            
            # Рейтинг по задержке (чем меньше задержка, тем выше рейтинг)
            latency_score = 0.5
            if server.get('avg_latency'):
                latency_score = 1 - min(server.get('avg_latency', 0) / 500, 1)
            
            # Рейтинг по пропускной способности (чем выше пропускная способность, тем выше рейтинг)
            bandwidth_score = 0.5
            if server.get('avg_bandwidth'):
                bandwidth_score = min(server.get('avg_bandwidth', 0) / 1000, 1)
            
            # Рейтинг по джиттеру (чем меньше джиттер, тем выше рейтинг)
            jitter_score = 0.5
            if server.get('avg_jitter'):
                jitter_score = 1 - min(server.get('avg_jitter', 0) / 100, 1)
            
            # Рейтинг по географической близости
            distance_score = 0.5
            if user_location and 'latitude' in user_location and 'longitude' in user_location and 'latitude' in server and 'longitude' in server:
                distance = calculate_distance(
                    user_location['latitude'], user_location['longitude'],
                    server['latitude'], server['longitude']
                )
                distance_score = 1 - min(distance / 5000, 1)  # Максимальное расстояние 5000 км
            
            # Рейтинг по предпочтениям пользователя
            preference_score = 0
            if user_preferences and user_preferences.get('preferred_server_id') == server['id']:
                preference_score = 1
            
            # Рассчитываем общий рейтинг с весами
            server['score'] = (
                0.3 * load_score +  # Нагрузка
                0.2 * latency_score +  # Задержка
                0.1 * bandwidth_score +  # Пропускная способность
                0.1 * jitter_score +  # Джиттер
                0.2 * distance_score +  # Географическая близость
                0.1 * preference_score  # Предпочтения пользователя
            )
        
        # 6. Сортируем серверы по рейтингу и выбираем лучший
        servers.sort(key=lambda s: s.get('score', 0), reverse=True)
        
        # 7. Логируем результаты для отладки
        logger.info(f"Выбран сервер {servers[0]['id']} с рейтингом {servers[0].get('score', 0)}")
        
        conn.close()
        return servers[0]
    
    except Exception as e:
        logger.error(f"Ошибка при выборе оптимального сервера: {str(e)}")
        
        # В случае ошибки возвращаемся к простому выбору по нагрузке
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(
                """
                SELECT * FROM servers
                WHERE geolocation_id = %s AND status = 'active'
                ORDER BY load_factor ASC
                LIMIT 1
                """,
                (geolocation_id,)
            )
            
            server = cursor.fetchone()
            conn.close()
            
            return server
        except Exception as e2:
            logger.error(f"Ошибка при запасном выборе сервера: {str(e2)}")
            return None
```

##### 6. Обновление API endpoint для интеграции с улучшенным алгоритмом

```python
@app.route('/servers/select_optimal', methods=['POST'])
def select_optimal_server_api():
    """API для выбора оптимального сервера для пользователя."""
    data = request.json
    
    user_id = data.get('user_id')
    geolocation_id = data.get('geolocation_id')
    ip_address = data.get('ip_address')
    
    if not user_id or not geolocation_id:
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    try:
        # Если передан IP-адрес, обновляем информацию о местоположении пользователя
        if ip_address:
            determine_user_location(user_id, ip_address)
        
        # Выбираем оптимальный сервер
        server = select_optimal_server(user_id, geolocation_id)
        
        if not server:
            return jsonify({"error": "Не удалось найти подходящий сервер"}), 404
        
        return jsonify({"server": server}), 200
    except Exception as e:
        logger.error(f"Ошибка при выборе оптимального сервера: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/servers/update_metrics', methods=['POST'])
def update_server_metrics_api():
    """API для обновления метрик сервера."""
    data = request.json
    
    server_id = data.get('server_id')
    endpoint = data.get('endpoint')
    
    if not server_id or not endpoint:
        return jsonify({"# VPN Duck - Расширение для поддержки нескольких геолокаций

## Описание проекта

Проект "VPN Duck" - это Telegram-бот для создания и управления личными VPN-конфигурациями на базе WireGuard. В рамках модернизации проекта добавляется поддержка нескольких геолокаций, автоматического переключения серверов и интеграции с будущим приложением на WireGuard SDK.

## Основные требования

### Telegram-бот:
- Выбор геолокации перед созданием конфигурации
- Возможность смены геолокации без изменения данных об оплате и сроке действия
- Обновление UI и команд для работы с геолокациями

### WireGuard-сервис:
- Поддержка нескольких серверов в разных странах/регионах
- Возможность размещения нескольких серверов в одном регионе для балансировки нагрузки
- Автоматическое переключение между серверами (Failover)
- Мониторинг состояния серверов (Health Checks)

### Будущая интеграция:
- Создание и хранение конфигураций для всех доступных серверов
- Подготовка к взаимодействию с кастомным приложением на WireGuard SDK
- Бесшовное переключение между серверами разных геолокаций

## Архитектура решения

### 1. Обновление структуры базы данных

```sql
-- Новая таблица для геолокаций
CREATE TABLE IF NOT EXISTS geolocations (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,  -- Уникальный код страны/региона (например, "us", "eu", "asia")
    name TEXT NOT NULL,                -- Название страны/региона
    description TEXT,                  -- Описание региона
    available BOOLEAN NOT NULL DEFAULT TRUE,  -- Доступность региона
    created_at TIMESTAMP NOT NULL
);

-- Новая таблица для серверов
CREATE TABLE IF NOT EXISTS servers (
    id SERIAL PRIMARY KEY,
    geolocation_id INTEGER REFERENCES geolocations(id),
    endpoint TEXT NOT NULL,           -- Endpoint сервера
    port INTEGER NOT NULL,            -- Порт сервера
    public_key TEXT NOT NULL,         -- Публичный ключ сервера
    private_key TEXT NOT NULL,        -- Приватный ключ сервера
    address TEXT NOT NULL,            -- Адрес сервера в сети WireGuard
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- Статус сервера (active, inactive, maintenance)
    last_check TIMESTAMP,             -- Время последней проверки
    load_factor FLOAT DEFAULT 0,      -- Фактор загрузки (для балансировки)
    created_at TIMESTAMP NOT NULL
);

-- Добавление колонки geolocation_id в существующую таблицу configurations
ALTER TABLE configurations ADD COLUMN geolocation_id INTEGER REFERENCES geolocations(id);
ALTER TABLE configurations ADD COLUMN server_id INTEGER REFERENCES servers(id);

-- Новая таблица для хранения всех конфигураций пользователя
CREATE TABLE IF NOT EXISTS user_configurations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    config_id INTEGER REFERENCES configurations(id),
    server_id INTEGER REFERENCES servers(id),
    config_text TEXT NOT NULL,         -- Текст конфигурации для конкретного сервера
    created_at TIMESTAMP NOT NULL
);
```

### 2. Обновление WireGuard-сервиса

Обновленный API для работы с WireGuard:

```python
# wireguard_manager.py - новый функционал

def get_servers_by_geolocation(geolocation_id):
    """Получает список доступных серверов для заданной геолокации."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/servers/geolocation/{geolocation_id}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("servers", [])
        else:
            logger.error(f"Ошибка при получении списка серверов: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return []

def select_optimal_server(servers):
    """Выбирает оптимальный сервер из списка доступных."""
    if not servers:
        return None
    
    # Сортировка серверов по нагрузке (load_factor)
    sorted_servers = sorted(servers, key=lambda s: float(s.get('load_factor', 0)))
    return sorted_servers[0]

def generate_all_configs_for_user(user_id, primary_geolocation_id=None):
    """Генерирует конфигурации для всех доступных серверов для пользователя."""
    try:
        # Получаем список всех геолокаций
        response = requests.get(f"{DATABASE_SERVICE_URL}/geolocations", timeout=5)
        
        if response.status_code != 200:
            logger.error(f"Ошибка при получении списка геолокаций: {response.status_code}, {response.text}")
            return {"error": "Не удалось получить список геолокаций"}
        
        geolocations = response.json().get("geolocations", [])
        
        # Генерируем ключи клиента (одна пара для всех конфигураций)
        client_private_key, client_public_key = generate_client_keys()
        
        configs = []
        primary_config = None
        primary_server_id = None
        
        # Для каждой геолокации генерируем конфигурации для всех серверов
        for geolocation in geolocations:
            geo_id = geolocation.get("id")
            servers = get_servers_by_geolocation(geo_id)
            
            for server in servers:
                server_id = server.get("id")
                server_endpoint = server.get("endpoint")
                server_port = server.get("port")
                server_public_key = server.get("public_key")
                
                # Генерируем уникальный IP-адрес для клиента на этом сервере
                client_ip = f"10.{geo_id}.{server_id % 250}.{(user_id % 250) + 2}/24"
                
                # Создаем конфигурацию клиента для этого сервера
                config_text = (
                    f"[Interface]\n"
                    f"PrivateKey = {client_private_key}\n"
                    f"Address = {client_ip}\n"
                    f"DNS = 1.1.1.1, 8.8.8.8\n\n"
                    f"[Peer]\n"
                    f"PublicKey = {server_public_key}\n"
                    f"Endpoint = {server_endpoint}:{server_port}\n"
                    f"AllowedIPs = 0.0.0.0/0\n"
                    f"PersistentKeepalive = 25\n"
                )
                
                # Добавляем клиента в конфигурацию сервера
                add_peer_command = [
                    "wg", "set", "wg0", 
                    "peer", client_public_key,
                    "allowed-ips", client_ip.split('/')[0] + "/32"
                ]
                
                try:
                    subprocess.run(add_peer_command, check=True)
                    
                    # Сохраняем конфигурацию сервера
                    subprocess.run(["wg-quick", "save", "wg0"], check=True)
                    
                    configs.append({
                        "server_id": server_id,
                        "geolocation_id": geo_id,
                        "config_text": config_text
                    })
                    
                    # Если это выбранная пользователем геолокация, сохраняем как основную
                    if geo_id == primary_geolocation_id:
                        if primary_config is None or float(server.get('load_factor', 0)) < float(get_server_by_id(primary_server_id).get('load_factor', 0) if primary_server_id else float('inf')):
                            primary_config = config_text
                            primary_server_id = server_id
                except Exception as e:
                    logger.error(f"Ошибка при добавлении пира для сервера {server_id}: {str(e)}")
        
        # Если основная геолокация не была указана или не найдена, берем первую конфигурацию
        if not primary_config and configs:
            primary_config = configs[0]["config_text"]
            primary_server_id = configs[0]["server_id"]
            primary_geolocation_id = configs[0]["geolocation_id"]
        
        # Сохраняем все конфигурации в базу данных
        save_response = requests.post(
            f"{DATABASE_SERVICE_URL}/configs/save_all",
            json={
                "user_id": user_id,
                "configs": configs,
                "primary_geolocation_id": primary_geolocation_id,
                "primary_server_id": primary_server_id,
                "client_public_key": client_public_key
            },
            timeout=30
        )
        
        if save_response.status_code != 200:
            logger.error(f"Ошибка при сохранении конфигураций: {save_response.status_code}, {save_response.text}")
            return {"error": "Не удалось сохранить конфигурации"}
        
        return {
            "config_text": primary_config,
            "public_key": client_public_key,
            "server_id": primary_server_id,
            "geolocation_id": primary_geolocation_id,
            "total_configs": len(configs)
        }
    except Exception as e:
        logger.error(f"Ошибка при генерации конфигураций: {str(e)}")
        return {"error": f"Ошибка при генерации конфигураций: {str(e)}"}

@app.route('/create', methods=['POST'])
def create_config():
    """Создает новые конфигурации WireGuard для пользователя для всех серверов."""
    data = request.json
    user_id = data.get('user_id')
    geolocation_id = data.get('geolocation_id', None)
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    try:
        # Генерируем конфигурации для всех серверов
        result = generate_all_configs_for_user(user_id, geolocation_id)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 500
        
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Error creating configurations: {str(e)}")
        return jsonify({"error": str(e)}), 500
```

### 3. Мониторинг и автоматическое переключение серверов

```python
# server_monitor.py

import os
import time
import logging
import requests
import subprocess
import json
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
DATABASE_SERVICE_URL = os.getenv('DATABASE_SERVICE_URL', 'http://database-service:5002')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # Интервал проверки в секундах

def check_server(server):
    """Проверяет доступность сервера."""
    try:
        # Выполняем ping до сервера
        endpoint = server.get('endpoint').split(':')[0]  # Получаем только хост без порта
        ping_result = subprocess.run(
            ["ping", "-c", "3", "-W", "5", endpoint],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Проверяем результат ping
        if ping_result.returncode == 0:
            logger.info(f"Сервер {endpoint} доступен")
            return True
        else:
            logger.warning(f"Сервер {endpoint} недоступен: {ping_result.stdout}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при проверке сервера {server.get('endpoint')}: {str(e)}")
        return False

def update_server_status(server_id, status, load_factor=None):
    """Обновляет статус сервера в базе данных."""
    try:
        data = {
            "status": status,
            "last_check": datetime.now().isoformat()
        }
        
        if load_factor is not None:
            data["load_factor"] = load_factor
        
        response = requests.post(
            f"{DATABASE_SERVICE_URL}/servers/{server_id}/update",
            json=data,
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info(f"Статус сервера {server_id} обновлен на {status}")
            return True
        else:
            logger.error(f"Ошибка при обновлении статуса сервера: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return False

def get_active_servers():
    """Получает список активных серверов из базы данных."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/servers/active", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("servers", [])
        else:
            logger.error(f"Ошибка при получении списка серверов: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return []

def run_monitor():
    """Запускает мониторинг серверов."""
    logger.info("Запуск системы мониторинга серверов")
    
    while True:
        try:
            # Получаем список всех активных серверов
            servers = get_active_servers()
            
            # Проверяем каждый сервер
            for server in servers:
                server_id = server.get('id')
                is_available = check_server(server)
                
                # Обновляем статус сервера
                if is_available:
                    # Если сервер доступен, устанавливаем статус active
                    update_server_status(server_id, 'active')
                else:
                    # Если сервер недоступен, устанавливаем статус inactive
                    update_server_status(server_id, 'inactive')
            
            # Для каждой геолокации проверяем, есть ли доступные серверы
            check_geolocation_availability()
            
            # Проверяем необходимость миграции пользователей
            check_users_migration()
            
        except Exception as e:
            logger.error(f"Ошибка в цикле мониторинга: {str(e)}")
        
        # Ждем перед следующей проверкой
        time.sleep(CHECK_INTERVAL)

def check_geolocation_availability():
    """Проверяет доступность геолокаций и обновляет их статус."""
    try:
        response = requests.get(f"{DATABASE_SERVICE_URL}/geolocations/check", timeout=5)
        
        if response.status_code != 200:
            logger.error(f"Ошибка при проверке доступности геолокаций: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при запросе проверки геолокаций: {str(e)}")

def check_users_migration():
    """Проверяет и мигрирует пользователей с недоступных серверов."""
    try:
        response = requests.post(f"{DATABASE_SERVICE_URL}/configs/migrate_users", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            migrated_count = result.get("migrated", 0)
            if migrated_count > 0:
                logger.info(f"Мигрировано {migrated_count} пользователей на новые серверы")
        else:
            logger.error(f"Ошибка при миграции пользователей: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при запросе миграции пользователей: {str(e)}")

if __name__ == "__main__":
    # Ждем некоторое время перед запуском мониторинга
    # для того, чтобы другие сервисы успели запуститься
    time.sleep(30)
    run_monitor()
```

### 4. Обновление Database-сервиса

Добавим новые API endpoints в `db_manager.py`:

```python
@app.route('/configs/save_all', methods=['POST'])
def save_all_configs():
    """Сохранение всех конфигураций для пользователя."""
    data = request.json
    
    required_fields = ['user_id', 'configs', 'primary_geolocation_id', 'primary_server_id', 'client_public_key']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    user_id = data.get('user_id')
    configs = data.get('configs')
    primary_geolocation_id = data.get('primary_geolocation_id')
    primary_server_id = data.get('primary_server_id')
    client_public_key = data.get('client_public_key')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Деактивируем существующие конфигурации для этого пользователя
        cursor.execute(
            "UPDATE configurations SET active = FALSE WHERE user_id = %s",
            (user_id,)
        )
        
        # Вставляем новую основную конфигурацию
        # Находим конфиг для основного сервера
        primary_config_text = None
        for config in configs:
            if config.get('server_id') == primary_server_id:
                primary_config_text = config.get('config_text')
                break
        
        if not primary_config_text:
            return jsonify({"error": "Не найдена конфигурация для основного сервера"}), 400
        
        # Рассчитываем дату истечения (7 дней от текущей даты или берем из предыдущей конфигурации)
        expiry_time = data.get('expiry_time')
        if not expiry_time:
            # Ищем предыдущую активную конфигурацию
            cursor.execute(
                "SELECT expiry_time FROM configurations WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            )
            prev_config = cursor.fetchone()
            if prev_config and prev_config[0]:
                expiry_time = prev_config[0]
            else:
                # Если предыдущей конфигурации нет, то 7 дней от текущей даты
                expiry_time = (datetime.now() + timedelta(days=7)).isoformat()
        
        # Вставляем основную конфигурацию
        cursor.execute(
            """
            INSERT INTO configurations 
            (user_id, config, public_key, expiry_time, active, created_at, geolocation_id, server_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, primary_config_text, client_public_key, expiry_time, True, datetime.now(), 
             primary_geolocation_id, primary_server_id)
        )
        
        config_id = cursor.fetchone()[0]
        
        # Сохраняем все конфигурации в таблицу user_configurations
        for config in configs:
            server_id = config.get('server_id')
            config_text = config.get('config_text')
            
            cursor.execute(
                """
                INSERT INTO user_configurations 
                (user_id, config_id, server_id, config_text, created_at) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, config_id, server_id, config_text, datetime.now())
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "config_id": config_id}), 200
    except Exception as e:
        logger.error(f"Ошибка при сохранении конфигураций: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/configs/get_all/<int:user_id>', methods=['GET'])
def get_all_user_configs(user_id):
    """Получение всех конфигураций для пользователя."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем активную конфигурацию
        cursor.execute(
            "SELECT * FROM configurations WHERE user_id = %s AND active = TRUE",
            (user_id,)
        )
        
        active_config = cursor.fetchone()
        if not active_config:
            conn.close()
            return jsonify({"error": "Активная конфигурация не найдена"}), 404
        
        # Получаем все конфигурации для всех серверов
        cursor.execute(
            """
            SELECT uc.*, s.endpoint, s.port, g.code as geo_code, g.name as geo_name 
            FROM user_configurations uc
            JOIN servers s ON uc.server_id = s.id
            JOIN geolocations g ON s.geolocation_id = g.id
            WHERE uc.user_id = %s AND uc.config_id = %s
            """,
            (user_id, active_config['id'])
        )
        
        all_configs = cursor.fetchall()
        
        # Преобразуем timestamp в строку для JSON-сериализации
        active_config['expiry_time'] = active_config['expiry_time'].isoformat()
        active_config['created_at'] = active_config['created_at'].isoformat()
        
        for config in all_configs:
            config['created_at'] = config['created_at'].isoformat()
        
        conn.close()
        
        result = {
            "active_config": active_config,
            "all_configs": all_configs,
            "count": len(all_configs)
        }
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Ошибка при получении конфигураций: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/configs/change_geolocation', methods=['POST'])
def change_config_geolocation():
    """Изменение геолокации для активной конфигурации."""
    data = request.json
    
    required_fields = ['user_id', 'geolocation_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Отсутствуют обязательные поля"}), 400
    
    user_id = data.get('user_id')
    geolocation_id = data.get('geolocation_id')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Получаем активную конфигурацию
        cursor.execute(
            "SELECT * FROM configurations WHERE user_id = %s AND active = TRUE",
            (user_id,)
        )
        
        active_config = cursor.fetchone()
        if not active_config:
            conn.close()
            return jsonify({"error": "Активная конфигурация не найдена"}), 404
        
        # Получаем все конфигурации для этой геолокации
        cursor.execute(
            """
            SELECT uc.*, s.endpoint, s.port 
            FROM user_configurations uc
            JOIN servers s ON uc.server_id = s.id
            WHERE uc.user_id = %s AND uc.config_id = %s AND s.geolocation_id = %s
            """,
            (user_id, active_config['id'], geolocation_id)
        )
        
        geo_configs = cursor.fetchall()
        
        if not geo_configs:
            conn.close()
            return jsonify({"error": "Конфигурации для выбранной геолокации не найдены"}), 404
        
        # Выбираем сервер с наименьшей нагрузкой
        cursor.execute(
            """
            SELECT s.* FROM servers s
            WHERE s.geolocation_id = %s AND s.status = 'active'
            ORDER BY s.load_factor ASC
            LIMIT 1
            """,
            (geolocation_id,)
        )
        
        optimal_server = cursor.fetchone()
        
        if not optimal_server:
            conn.close()
            return jsonify({"error": "Нет доступных серверов в выбранной геолокации"}), 404
        
        # Находим конфигурацию для этого сервера
        new_config = None
        for config in geo_configs:
            if config['server_id'] == optimal_server['id']:
                new_config = config
                break
        
        if not new_config:
            conn.close()
            return jsonify({"error": "Конфигурация для выбранного сервера не найдена"}), 404
        
        # Обновляем активную конфигурацию
        cursor.execute(
            """
            UPDATE configurations 
            SET config = %s, geolocation_id = %s, server_id = %s
            WHERE id = %s
            """,
            (new_config['config_text'], geolocation_id, optimal_server['id'], active_config['id'])
        )
        
        conn.commit()
        
        # Получаем обновленную конфигурацию
        cursor.execute(
            "SELECT * FROM configurations WHERE id = %s",
            (active_config['id'],)
        )
        
        updated_config = cursor.fetchone()
        
        # Преобразуем timestamp в строку для JSON-сериализации
        updated_config['expiry_time'] = updated_config['expiry_time'].isoformat()
        updated_config['created_at'] = updated_config['created_at'].isoformat()
        
        conn.close()
        
        return jsonify({"status": "success", "config": updated_config}), 200
    except Exception as e:
        logger.error(f"Ошибка при изменении геолокации: {str(e)}")
        return jsonify({"error": str(e)}), 500
```

### 5. Обновление Telegram-бота

Добавим обработчики для работы с геолокациями:

```python
# handlers/geolocation.py

from aiogram import types, Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from datetime import datetime
from io import BytesIO

from core.settings import bot, logger
from states.states import GeoLocationStates
from keyboards.keyboards import get_geolocation_keyboard
from utils.bd import get_available_geolocations, change_config_geolocation, get_user_config, get_all_user_configs
from utils.qr import generate_config_qr

# Обработчик для выбора геолокации
async def choose_geolocation(message: types.Message, state: FSMContext):
    """Выбор геолокации для конфигурации."""
    try:
        # Проверяем, есть ли у пользователя активная конфигурация
        user_id = message.from_user.id
        config = await get_user_config(user_id)
        
        if not config or not config.get("active", False):
            await message.reply(
                "⚠️ <b>У вас нет активной конфигурации</b>\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получаем список доступных геолокаций
        geolocations = await get_available_geolocations()
        
        if not geolocations:
            await message.reply(
                "⚠️ <b>Нет доступных геолокаций</b>\n\n"
                "Попробуйте позже.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Сохраняем список геолокаций в состоянии
        await state.update_data(geolocations=geolocations)
        
        # Формируем клавиатуру с геолокациями
        keyboard = get_geolocation_keyboard(geolocations)
        
        # Определяем текущую геолокацию
        current_geo_id = config.get("geolocation_id")
        current_geo_name = "Неизвестно"
        
        for geo in geolocations:
            if geo.get('id') == current_geo_id:
                current_geo_name = geo.get('name')
                break
        
        await message.reply(
            f"🌍 <b>Выберите геолокацию для вашего VPN</b>\n\n"
            f"От выбранной геолокации зависит скорость соединения и доступность некоторых сервисов.\n\n"
            f"Текущая геолокация: <b>{current_geo_name}</b>\n\n"
            f"При смене геолокации ваша текущая конфигурация будет обновлена, "
            f"срок действия останется прежним.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        # Переходим в состояние выбора геолокации
        await GeoLocationStates.selecting_geolocation.set()
    except Exception as e:
        logger.error(f"Ошибка при получении геолокаций: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

# Обработчик выбора геолокации из списка
async def process_geolocation_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора геолокации."""
    await bot.answer_callback_query(callback_query.id)
    
    # Получаем выбранную геолокацию
    geolocation_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    
    # Получаем данные из состояния
    state_data = await state.get_data()
    geolocations = state_data.get('geolocations', [])
    
    # Находим название выбранной геолокации
    geolocation_name = "Неизвестная геолокация"
    for geo in geolocations:
        if geo.get('id') == geolocation_id:
            geolocation_name = geo.get('name')
            break
    
    try:
        # Обновляем геолокацию в базе данных
        result = await change_config_geolocation(user_id, geolocation_id)
        
        if "error" in result:
            await bot.edit_message_text(
                f"❌ <b>Ошибка!</b>\n\n{result['error']}",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                parse_mode=ParseMode.HTML
            )
            await state.finish()
            return
        
        # Сообщаем пользователю об успешном обновлении конфигурации
        await bot.edit_message_text(
            f"✅ <b>Геолокация успешно изменена на</b> <b>{geolocation_name}</b>\n\n"
            f"Все ваши устройства будут автоматически переключены на новую геолокацию.\n\n"
            f"Если вы используете стандартный клиент WireGuard, вам понадобится обновить конфигурацию. "
            f"Новая конфигурация будет отправлена вам сейчас.",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        
        # Получаем обновленную конфигурацию
        config = await get_user_config(user_id)
        
        if config and config.get("config"):
            config_text = config.get("config")
            
            # Создаем файл конфигурации
            config_file = BytesIO(config_text.encode('utf-8'))
            config_file.name = f"vpn_duck_{user_id}.conf"
            
            # Генерируем QR-код
            qr_buffer = await generate_config_qr(config_text)
            
            if qr_buffer:
                # Отправляем QR-код
                await bot.send_photo(
                    user_id,
                    qr_buffer,
                    caption=f"🔑 <b>QR-код вашей новой конфигурации WireGuard</b>\n\n"
                            f"Геолокация: <b>{geolocation_name}</b>\n\n"
                            f"Отсканируйте этот код в приложении WireGuard для быстрой настройки.",
                    parse_mode=ParseMode.HTML
                )
            
            # Отправляем файл конфигурации
            await bot.send_document(
                user_id,
                config_file,
                caption=f"📋 <b>Файл конфигурации WireGuard</b>\n\n"
                        f"Геолокация: <b>{geolocation_name}</b>\n\n"
                        f"Импортируйте этот файл в приложение WireGuard для настройки соединения.",
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем информацию о мобильном приложении
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("📊 Проверить статус", callback_data="status")
            )
            
            await bot.send_message(
                user_id,
                f"📱 <b>Информация о приложении VPN Duck</b>\n\n"
                f"Для более комфортного использования сервиса вы можете скачать наше приложение, "
                f"которое автоматически переключается между серверами и геолокациями "
                f"без необходимости обновления конфигурации.\n\n"
                f"Приложение доступно для скачивания на нашем сайте или через сторонние магазины приложений.\n\n"
                f"Название для поиска: <b>VPN Duck</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                user_id,
                "⚠️ <b>Не удалось получить обновленную конфигурацию</b>\n\n"
                "Пожалуйста, используйте команду /create для создания новой конфигурации.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Ошибка при обновлении геолокации: {str(e)}", exc_info=True)
        await bot.send_message(
            user_id,
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )
    
    await state.finish()

# Обработчик для отмены выбора геолокации
async def cancel_geolocation_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена выбора геолокации."""
    await bot.answer_callback_query(callback_query.id)
    
    await bot.edit_message_text(
        "❌ Выбор геолокации отменен.",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id
    )
    
    await state.finish()

# Обработчик для получения всех конфигураций для разных серверов
async def get_all_configs(message: types.Message):
    """Получение всех конфигураций пользователя для разных серверов."""
    user_id = message.from_user.id
    
    try:
        # Получаем все конфигурации пользователя
        result = await get_all_user_configs(user_id)
        
        if "error" in result:
            await message.reply(
                f"⚠️ <b>Ошибка при получении конфигураций</b>\n\n{result['error']}",
                parse_mode=ParseMode.HTML
            )
            return
        
        active_config = result.get("active_config", {})
        all_configs = result.get("all_configs", [])
        
        if not all_configs:
            await message.reply(
                "⚠️ <b>У вас нет сохраненных конфигураций</b>\n\n"
                "Сначала создайте конфигурацию с помощью команды /create.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Группируем конфигурации по геолокациям
        geo_configs = {}
        for config in all_configs:
            geo_code = config.get("geo_code")
            geo_name = config.get("geo_name")
            
            if geo_code not in geo_configs:
                geo_configs[geo_code] = {
                    "name": geo_name,
                    "configs": []
                }
            
            geo_configs[geo_code]["configs"].append(config)
        
        # Отправляем информацию о доступных конфигурациях
        message_text = f"📋 <b>Ваши конфигурации VPN Duck</b>\n\n"
        
        # Информация о текущей конфигурации
        expiry_time = active_config.get("expiry_time")
        if expiry_time:
            try:
                expiry_dt = datetime.fromisoformat(expiry_time)
                expiry_formatted = expiry_dt.strftime("%d.%m.%Y %H:%M:%S")
                
                message_text += (
                    f"<b>Текущая конфигурация:</b>\n"
                    f"▫️ Срок действия: до <b>{expiry_formatted}</b>\n\n"
                )
            except Exception:
                pass
        
        message_text += "Ниже будут отправлены конфигурации для всех доступных серверов по регионам.\n"
        
        await message.reply(message_text, parse_mode=ParseMode.HTML)
        
        # Отправляем конфигурации для каждой геолокации
        for geo_code, geo_data in geo_configs.items():
            geo_name = geo_data["name"]
            configs = geo_data["configs"]
            
            await message.reply(
                f"🌍 <b>Геолокация: {geo_name}</b>\n\n"
                f"Количество серверов: <b>{len(configs)}</b>\n\n"
                f"Отправляю конфигурации для всех серверов в этой геолокации...",
                parse_mode=ParseMode.HTML
            )
            
            # Создаем архив с конфигурациями для этой геолокации
            zip_buffer = BytesIO()
            
            # Используем модуль zipfile для создания архива
            import zipfile
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, config in enumerate(configs, 1):
                    server_endpoint = config.get("endpoint")
                    config_text = config.get("config_text")
                    
                    # Создаем имя файла конфигурации
                    config_filename = f"vpn_duck_{geo_code}_{i}_{server_endpoint}.conf"
                    
                    # Добавляем конфигурацию в архив
                    zip_file.writestr(config_filename, config_text)
            
            # Перемещаем указатель в начало буфера
            zip_buffer.seek(0)
            
            # Отправляем архив
            zip_buffer.name = f"vpn_duck_{geo_code}_configs.zip"
            await message.reply_document(
                zip_buffer,
                caption=f"📦 <b>Архив с конфигурациями для {geo_name}</b>\n\n"
                        f"Содержит конфигурации для всех серверов в этой геолокации.\n\n"
                        f"Для использования в приложении VPN Duck, распакуйте архив и "
                        f"импортируйте все конфигурации.",
                parse_mode=ParseMode.HTML
            )
        
        # Отправляем инструкцию для мобильного приложения
        await message.reply(
            "📱 <b>Инструкция для приложения VPN Duck</b>\n\n"
            "1. Скачайте и установите приложение VPN Duck\n"
            "2. Импортируйте все полученные конфигурации\n"
            "3. Приложение автоматически выберет оптимальный сервер\n"
            "4. При изменении геолокации приложение переключится на соответствующий сервер\n\n"
            "Приложение VPN Duck обеспечивает бесшовное переключение между серверами в случае "
            "недоступности текущего сервера или при смене геолокации.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка при получении конфигураций: {str(e)}", exc_info=True)
        await message.reply(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

def register_handlers_geolocation(dp: Dispatcher):
    """Регистрирует обработчики для геолокаций."""
    dp.register_message_handler(choose_geolocation, commands=['geolocation'])
    dp.register_message_handler(choose_geolocation, lambda message: message.text == "🌍 Геолокация")
    dp.register_message_handler(get_all_configs, commands=['allconfigs'])
    dp.register_callback_query_handler(process_geolocation_selection, lambda c: c.data.startswith('geo_'), state=GeoLocationStates.selecting_geolocation)
    dp.register_callback_query_handler(cancel_geolocation_selection, lambda c: c.data == 'cancel_geo', state=GeoLocationStates.selecting_geolocation)
    
    # Дополнительные обработчики для UI-кнопок
    dp.register_callback_query_handler(choose_geolocation, lambda c: c.data == 'choose_geo')
    dp.register_callback_query_handler(get_all_configs, lambda c: c.data == 'get_all_configs')
    
    # Обработчик для кнопки "Назад"
    dp.register_callback_query_handler(back_to_main_menu, lambda c: c.data == 'back_to_main', state='*')

# Обработчик возврата в главное меню
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' для возврата в главное меню."""
    await bot.answer_callback_query(callback_query.id)
    
    # Завершаем все состояния
    current_state = await state.get_state()
    if current_state:
        await state.finish()
    
    # Получаем информацию о пользователе
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name
    
    # Получаем конфигурацию пользователя
    config = await get_user_config(user_id)
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if config and config.get("active", False):
        # Если есть активная конфигурация, показываем соответствующие кнопки
        keyboard.add(
            InlineKeyboardButton("📊 Статус", callback_data="status"),
            InlineKeyboardButton("📋 Получить конфиг", callback_data="get_config")
        )
        keyboard.add(
            InlineKeyboardButton("⏰ Продлить", callback_data="start_extend"),
            InlineKeyboardButton("🌍 Геолокация", callback_data="choose_geo")
        )
        keyboard.add(
            InlineKeyboardButton("🔄 Пересоздать", callback_data="recreate_config")
        )
    else:
        # Если нет активной конфигурации, показываем кнопку создания
        keyboard.add(
            InlineKeyboardButton("🔑 Создать конфигурацию", callback_data="create_config")
        )
    
    await bot.edit_message_text(
        f"👋 Привет, {user_name}!\n\n"
        f"Добро пожаловать в бот VPN Duck! 🦆\n\n"
        f"Этот бот поможет вам создать и управлять вашей личной конфигурацией WireGuard VPN "
        f"с возможностью выбора оптимальной геолокации для ваших задач.\n\n"
        f"Выберите действие из меню ниже:",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )
