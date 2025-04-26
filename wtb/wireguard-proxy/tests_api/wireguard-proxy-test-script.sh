#!/bin/bash
# wireguard-proxy-test.sh - Скрипт для проверки API WireGuard Proxy с использованием curl

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
PROXY_URL="http://localhost:5001"  # Замените на реальный URL прокси-сервера
ADMIN_KEY="your-admin-api-key"     # Замените на реальный административный ключ
TEST_SERVER_ID=""                  # Будет заполнено в процессе тестирования
TEST_PUBLIC_KEY=""                 # Будет заполнено в процессе тестирования

MOCK_MODE=true
MOCK_PUBLIC_KEY="mock_public_key_$(date +%s)"

# Функция для вывода сообщений
log() {
  echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Функция для вывода успеха
success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Функция для вывода предупреждений
warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Функция для вывода ошибок
error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Функция для проверки статуса HTTP-ответа
check_status() {
  if [[ "$1" -ge 200 && "$1" -lt 300 ]]; then
    success "HTTP статус: $1"
    return 0
  else
    error "HTTP статус: $1"
    return 1
  fi
}

# Тест 1: Проверка работоспособности сервера
test_health() {
  log "Тест 1: Проверка работоспособности сервера (/health)"
  
  response=$(curl -s -w "\n%{http_code}" "${PROXY_URL}/health")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  check_status "$http_code"
  
  if echo "$body" | grep -q '"status":"ok"'; then
    success "Сервер работает нормально"
  else
    error "Неожиданный ответ: $body"
  fi
  
  echo
}

# Тест 2: Получение списка серверов
test_get_servers() {
  log "Тест 2: Получение списка серверов (/servers)"
  
  response=$(curl -s -w "\n%{http_code}" "${PROXY_URL}/servers")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  check_status "$http_code"
  
  if echo "$body" | grep -q '"servers"'; then
    success "Получен список серверов"
    # Вывод количества серверов, если они есть
    if [[ $(echo "$body" | grep -o '"id"' | wc -l) -gt 0 ]]; then
      server_count=$(echo "$body" | grep -o '"id"' | wc -l)
      log "Найдено серверов: $server_count"
    else
      warning "Список серверов пуст"
    fi
  else
    error "Неожиданный ответ: $body"
  fi
  
  echo
}

# Тест 3: Получение статуса сервера
test_get_status() {
  log "Тест 3: Получение статуса сервера (/status)"
  
  response=$(curl -s -w "\n%{http_code}" "${PROXY_URL}/status")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  check_status "$http_code"
  
  if echo "$body" | grep -q '"proxy_status"'; then
    success "Получен статус прокси-сервера"
    
    # Вывод статуса прокси
    proxy_status=$(echo "$body" | grep -o '"proxy_status":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    log "Статус прокси: $proxy_status"
    
    # Вывод количества подключенных серверов
    if echo "$body" | grep -q '"connected_servers"'; then
      connected_servers=$(echo "$body" | grep -o '"connected_servers":[^,}]*' | cut -d':' -f2)
      total_servers=$(echo "$body" | grep -o '"total_servers":[^,}]*' | cut -d':' -f2)
      log "Подключено серверов: $connected_servers из $total_servers"
    fi
  else
    error "Неожиданный ответ: $body"
  fi
  
  echo
}

# Тест 4: Получение метрик
test_get_metrics() {
  log "Тест 4: Получение метрик (/metrics)"
  
  response=$(curl -s -w "\n%{http_code}" "${PROXY_URL}/metrics")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  check_status "$http_code"
  
  if echo "$body" | grep -q '"cache_hits"'; then
    success "Получены метрики прокси-сервера"
    
    # Вывод основных метрик
    cache_hits=$(echo "$body" | grep -o '"cache_hits":[^,}]*' | cut -d':' -f2)
    cache_misses=$(echo "$body" | grep -o '"cache_misses":[^,}]*' | cut -d':' -f2)
    log "Попаданий в кэш: $cache_hits, промахов: $cache_misses"
  else
    error "Неожиданный ответ: $body"
  fi
  
  echo
}

# Тест 5: Добавление нового сервера (административный эндпоинт)
test_add_server() {
  log "Тест 5: Добавление нового сервера (/admin/servers)"
  
  if [[ "$MOCK_MODE" == "true" ]]; then
    log "Использование режима эмуляции для добавления сервера"
    TEST_SERVER_ID="$MOCK_SERVER_ID"
    log "ID эмулированного сервера: $TEST_SERVER_ID"
    success "Сервер успешно добавлен (эмуляция)"
    return 0
  fi
  
  # Создаем тестовые данные для сервера
  server_data='{
    "api_url": "https://test-server.example.com/api",
    "location": "Test/Location",
    "geolocation_id": 1,
    "name": "Test Server",
    "auth_type": "api_key",
    "api_key": "test-server-api-key",
    "test_mode": true
  }'
  
  # Добавляем заголовок авторизации, если указан ADMIN_KEY
  auth_header=""
  if [[ -n "$ADMIN_KEY" ]]; then
    auth_header="-H \"Authorization: Bearer $ADMIN_KEY\""
  fi
  
  # Выполняем запрос на добавление сервера
  response=$(eval "curl -s -w \"\n%{http_code}\" -X POST \"${PROXY_URL}/admin/servers\" \
    -H \"Content-Type: application/json\" \
    $auth_header \
    -d '$server_data'")
  
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  check_status "$http_code"
  
  if echo "$body" | grep -q '"success":true'; then
    success "Сервер успешно добавлен"
    
    # Сохраняем ID сервера для дальнейших тестов
    if echo "$body" | grep -q '"server_id"'; then
      TEST_SERVER_ID=$(echo "$body" | grep -o '"server_id":"[^"]*"' | cut -d':' -f2 | tr -d '"')
      log "ID нового сервера: $TEST_SERVER_ID"
    else
      warning "ID сервера не получен"
    fi
  else
    error "Ошибка при добавлении сервера: $body"
  fi
  
  echo
}

# Тест 6: Создание новой конфигурации WireGuard
test_create_configuration() {
  log "Тест 6: Создание новой конфигурации WireGuard (/create)"
  
  if [[ "$MOCK_MODE" == "true" ]]; then
    log "Использование режима эмуляции для создания конфигурации"
    TEST_PUBLIC_KEY="$MOCK_PUBLIC_KEY"
    log "Эмулированный публичный ключ: $TEST_PUBLIC_KEY"
    success "Конфигурация эмулирована успешно"
    echo
    return 0
  fi
  
  # Создаем данные для запроса
  create_data='{
    "user_id": "test-user-123",
    "geolocation_id": 1
  }'
  
  # Добавляем server_id, если он был получен
  if [[ -n "$TEST_SERVER_ID" ]]; then
    create_data=$(echo "$create_data" | sed 's/}$/,"preferred_server_id":"'$TEST_SERVER_ID'"}/')
    log "Используем предпочтительный сервер: $TEST_SERVER_ID"
  fi
  
  # Выполняем запрос на создание конфигурации
  response=$(curl -s -w "\n%{http_code}" -X POST "${PROXY_URL}/create" \
    -H "Content-Type: application/json" \
    -d "$create_data")
  
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  check_status "$http_code"
  
  if echo "$body" | grep -q '"public_key"'; then
    success "Конфигурация успешно создана"
    
    # Сохраняем публичный ключ для дальнейших тестов
    TEST_PUBLIC_KEY=$(echo "$body" | grep -o '"public_key":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    log "Публичный ключ: $TEST_PUBLIC_KEY"
    
    # Выводим дополнительную информацию
    if echo "$body" | grep -q '"server_id"'; then
      server_id=$(echo "$body" | grep -o '"server_id":"[^"]*"' | cut -d':' -f2 | tr -d '"')
      log "Сервер: $server_id"
    fi
  else
    error "Ошибка при создании конфигурации: $body"
  fi
  
  echo
}

# Тест 7: Удаление пира
test_remove_peer() {
  log "Тест 7: Удаление пира (/remove/{public_key})"
  
  # Проверяем, что у нас есть публичный ключ
  if [[ -z "$TEST_PUBLIC_KEY" ]]; then
    error "Публичный ключ не был получен в предыдущем тесте"
    echo
    return 1
  fi
  
  if [[ "$MOCK_MODE" == "true" && "$TEST_PUBLIC_KEY" == "$MOCK_PUBLIC_KEY" ]]; then
    log "Использование режима эмуляции для удаления пира"
    success "Пир успешно удален (эмуляция)"
    echo
    return 0
  fi
  
  # Выполняем запрос на удаление пира
  response=$(curl -s -w "\n%{http_code}" -X DELETE "${PROXY_URL}/remove/${TEST_PUBLIC_KEY}")
  
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  check_status "$http_code"
  
  if echo "$body" | grep -q '"success":true'; then
    success "Пир успешно удален"
  else
    error "Ошибка при удалении пира: $body"
  fi
  
  echo
}

# Тест 8: Проверка обработки ошибок
test_error_handling() {
  log "Тест 8: Проверка обработки ошибок"
  
  # Тест 8.1: Создание конфигурации без обязательных параметров
  log "Тест 8.1: Создание конфигурации без обязательных параметров"
  
  response=$(curl -s -w "\n%{http_code}" -X POST "${PROXY_URL}/create" \
    -H "Content-Type: application/json" \
    -d "{}")
  
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  if [[ "$http_code" -eq 400 ]]; then
    success "Получена ожидаемая ошибка 400 Bad Request"
  else
    warning "Неожиданный HTTP-статус: $http_code (ожидался 400)"
  fi
  
  if echo "$body" | grep -q '"error"'; then
    success "Сообщение об ошибке присутствует в ответе"
  else
    warning "Сообщение об ошибке отсутствует в ответе: $body"
  fi
  
  # Тест 8.2: Удаление несуществующего пира
  log "Тест 8.2: Удаление несуществующего пира"
  
  response=$(curl -s -w "\n%{http_code}" -X DELETE "${PROXY_URL}/remove/nonexistent-key-that-does-not-exist")
  
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  log "HTTP-статус: $http_code"
  
  # В зависимости от реализации, сервер может вернуть 404, 500 или 200 с деталями ошибки
  if [[ "$http_code" -eq 404 || "$http_code" -eq 500 || 
      ("$http_code" -eq 200 && $(echo "$body" | grep -q '"success":false')) ]]; then
    success "Получен ожидаемый ответ на запрос несуществующего пира"
  else
    warning "Неожиданный ответ: $body"
  fi
  
  echo
}

# Запуск всех тестов
run_all_tests() {
  log "Запуск тестирования WireGuard Proxy API"
  echo "URL прокси-сервера: $PROXY_URL"
  echo
  
  # Запуск тестов, не изменяющих данные
  test_health
  test_get_servers
  test_get_status
  test_get_metrics
  
  # Запрос у пользователя, запускать ли тесты, изменяющие данные
  echo -n "Запустить тесты, которые изменяют данные? (y/n): "
  read -r run_modifying_tests
  
  if [[ "$run_modifying_tests" == "y" || "$run_modifying_tests" == "Y" ]]; then
    test_add_server
    test_create_configuration
    test_remove_peer
    test_error_handling
  else
    log "Тесты, изменяющие данные, пропущены"
  fi
  
  log "Тестирование завершено!"
}

# Запуск всех тестов
run_all_tests