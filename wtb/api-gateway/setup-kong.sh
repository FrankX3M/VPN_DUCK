#!/bin/bash
# Setup Kong API Gateway

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Настройка Kong API Gateway ===${NC}"

# Параметры подключения к Kong
KONG_ADMIN_URL="http://localhost:8001"
CONFIG_FILE="kong.yml"

# Функция для проверки доступности Kong
check_kong_availability() {
  echo -e "${YELLOW}Проверка доступности Kong Admin API...${NC}"
  
  for i in {1..30}; do
    if curl -s -o /dev/null -w "%{http_code}" "${KONG_ADMIN_URL}" | grep -q "200"; then
      echo -e "${GREEN}Kong Admin API доступен!${NC}"
      return 0
    fi
    
    echo -e "${YELLOW}Попытка $i: Kong Admin API недоступен, ожидание 5 секунд...${NC}"
    sleep 5
  done
  
  echo -e "${RED}Kong Admin API недоступен после 30 попыток. Выход.${NC}"
  return 1
}

# Функция для применения декларативной конфигурации Kong
apply_kong_config() {
  echo -e "${YELLOW}Применение конфигурации Kong из файла ${CONFIG_FILE}...${NC}"
  
  # Проверка наличия файла конфигурации
  if [ ! -f "${CONFIG_FILE}" ]; then
    echo -e "${RED}Файл конфигурации ${CONFIG_FILE} не найден!${NC}"
    return 1
  fi
  
  # Применение конфигурации
  RESPONSE=$(curl -s -X POST "${KONG_ADMIN_URL}/config" \
    -H "Content-Type: application/json" \
    -d '{"config": "'"$(cat ${CONFIG_FILE} | sed 's/"/\\"/g')"'"}')
  
  if echo "${RESPONSE}" | grep -q "error"; then
    echo -e "${RED}Ошибка применения конфигурации: ${RESPONSE}${NC}"
    return 1
  else
    echo -e "${GREEN}Конфигурация успешно применена!${NC}"
    return 0
  fi
}

# Функция для проверки настроенных сервисов
check_kong_services() {
  echo -e "${YELLOW}Проверка настроенных сервисов Kong...${NC}"
  
  SERVICES=$(curl -s "${KONG_ADMIN_URL}/services" | jq -r '.data[].name')
  
  if [ -z "${SERVICES}" ]; then
    echo -e "${RED}Сервисы не настроены!${NC}"
    return 1
  else
    echo -e "${GREEN}Настроенные сервисы:${NC}"
    echo "${SERVICES}" | while read -r SERVICE; do
      echo -e "  - ${SERVICE}"
    done
    return 0
  fi
}

# Основная логика
echo -e "${YELLOW}Начало настройки Kong API Gateway...${NC}"

# Шаг 1: Проверка доступности Kong
check_kong_availability
if [ $? -ne 0 ]; then
  echo -e "${RED}Не удалось подключиться к Kong Admin API. Убедитесь, что Kong запущен и доступен.${NC}"
  exit 1
fi

# Шаг 2: Применение конфигурации
apply_kong_config
if [ $? -ne 0 ]; then
  echo -e "${RED}Не удалось применить конфигурацию Kong.${NC}"
  exit 1
fi

# Шаг 3: Проверка настроенных сервисов
check_kong_services
if [ $? -ne 0 ]; then
  echo -e "${RED}Проверка настроенных сервисов не удалась.${NC}"
  exit 1
fi

echo -e "${GREEN}Настройка Kong API Gateway успешно завершена!${NC}"
exit 0