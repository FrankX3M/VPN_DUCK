import pytest
import requests
import json
import time
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('wireguard-proxy-test')

# Конфигурация для тестов
BASE_URL = "http://localhost:5001"  # Замените на адрес вашего прокси-сервера
ADMIN_KEY = "admin-api-key"  # Замените на ваш административный ключ, если требуется

# Тестовые данные
TEST_SERVER = {
    "api_url": "https://test-wg-server.example.com/api",
    "location": "Test/Location",
    "geolocation_id": 1,
    "name": "Test Server",
    "auth_type": "api_key",
    "api_key": "test-api-key-for-server"
}

TEST_USER = {
    "user_id": "test-user-123",
    "geolocation_id": 1
}

# Служебные функции
def log_response(response):
    """Логирование ответа для отладки"""
    logger.info(f"Status Code: {response.status_code}")
    try:
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        logger.info(f"Response Text: {response.text}")

class TestWireguardProxyAPI:
    """Тесты для API WireGuard Proxy"""
    
    # Сохранение данных между тестами
    public_key = None
    server_id = None
    
    def test_health_check(self):
        """Тест эндпоинта проверки работоспособности"""
        logger.info("Testing health check endpoint...")
        
        response = requests.get(f"{BASE_URL}/health")
        log_response(response)
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "wireguard-proxy"
        
        logger.info("Health check test passed!")
    
    def test_get_servers(self):
        """Тест получения списка серверов"""
        logger.info("Testing get servers endpoint...")
        
        response = requests.get(f"{BASE_URL}/servers")
        log_response(response)
        
        assert response.status_code == 200
        assert "servers" in response.json()
        
        logger.info("Get servers test passed!")
    
    def test_get_status(self):
        """Тест получения статуса серверов"""
        logger.info("Testing status endpoint...")
        
        response = requests.get(f"{BASE_URL}/status")
        log_response(response)
        
        assert response.status_code == 200
        assert "proxy_status" in response.json()
        assert "servers_status" in response.json()
        
        logger.info("Status test passed!")
    
    def test_get_metrics(self):
        """Тест получения метрик"""
        logger.info("Testing metrics endpoint...")
        
        response = requests.get(f"{BASE_URL}/metrics")
        log_response(response)
        
        assert response.status_code == 200
        # Проверка наличия ключевых метрик
        metrics = response.json()
        assert "cache_hits" in metrics
        assert "cache_misses" in metrics
        assert "request_count" in metrics
        
        logger.info("Metrics test passed!")
    
    def test_add_server(self):
        """Тест добавления нового сервера (административный эндпоинт)"""
        logger.info("Testing add server endpoint...")
        
        headers = {}
        if ADMIN_KEY:
            # Если требуется аутентификация для административных эндпоинтов
            headers["Authorization"] = f"Bearer {ADMIN_KEY}"
        
        response = requests.post(
            f"{BASE_URL}/admin/servers",
            headers=headers,
            json=TEST_SERVER
        )
        log_response(response)
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Сохраняем ID сервера для дальнейших тестов
        TestWireguardProxyAPI.server_id = response.json().get("server_id")
        
        logger.info(f"Add server test passed! Server ID: {TestWireguardProxyAPI.server_id}")
    
    def test_create_configuration(self):
        """Тест создания новой конфигурации WireGuard"""
        logger.info("Testing create configuration endpoint...")
        # Проверить наличие серверов
        server_response=$(curl -s "${PROXY_URL}/servers")
        if [[ $(echo "$server_response" | grep -o '"id"' | wc -l) -eq 0 ]]; then
            warning "Нет доступных серверов. Тест создания конфигурации будет пропущен."
            skip_create_test=true
        # Если предыдущий тест прошел успешно, используем созданный сервер
        if TestWireguardProxyAPI.server_id:
            TEST_USER["preferred_server_id"] = TestWireguardProxyAPI.server_id
        
        response = requests.post(
            f"{BASE_URL}/create",
            json=TEST_USER
        )
        log_response(response)
        
        assert response.status_code == 200
        # Сохраняем public_key для теста удаления
        TestWireguardProxyAPI.public_key = response.json().get("public_key")
        
        assert TestWireguardProxyAPI.public_key is not None
        
        logger.info(f"Create configuration test passed! Public key: {TestWireguardProxyAPI.public_key}")
    
    def test_remove_peer(self):
        """Тест удаления пира"""
        logger.info("Testing remove peer endpoint...")
        
        # Проверяем, что предыдущий тест прошел успешно
        if not TestWireguardProxyAPI.public_key:
            pytest.skip("No public key available from previous test")
        
        response = requests.delete(
            f"{BASE_URL}/remove/{TestWireguardProxyAPI.public_key}"
        )
        log_response(response)
        
        assert response.status_code == 200
        assert response.json().get("success") is True
        
        logger.info("Remove peer test passed!")

class TestErrorHandling:
    """Тесты для проверки обработки ошибок API"""
    
    def test_create_with_missing_params(self):
        """Тест создания конфигурации с отсутствующими параметрами"""
        logger.info("Testing error handling for missing parameters...")
        
        response = requests.post(
            f"{BASE_URL}/create",
            json={}  # Отсутствует обязательный параметр user_id
        )
        log_response(response)
        
        assert response.status_code == 400
        assert "error" in response.json()
        
        logger.info("Error handling test for missing parameters passed!")
    
    def test_remove_nonexistent_peer(self):
        """Тест удаления несуществующего пира"""
        logger.info("Testing error handling for nonexistent peer...")
        
        response = requests.delete(
            f"{BASE_URL}/remove/nonexistent-public-key-that-does-not-exist"
        )
        log_response(response)
        
        # В зависимости от реализации может вернуть либо 404, либо 200 с деталями ошибки
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            # Проверяем, что в ответе есть информация об ошибках на серверах
            assert "details" in response.json()
        
        logger.info("Error handling test for nonexistent peer passed!")

class TestIntegration:
    """Интеграционные тесты для WireGuard Proxy"""
    
    def test_full_lifecycle(self):
        """Полный жизненный цикл: создание конфигурации и удаление пира"""
        logger.info("Testing full lifecycle: create and remove...")
        
        # 1. Создание конфигурации
        create_response = requests.post(
            f"{BASE_URL}/create",
            json={"user_id": "lifecycle-test-user", "geolocation_id": 1}
        )
        log_response(create_response)
        
        assert create_response.status_code == 200
        public_key = create_response.json().get("public_key")
        assert public_key is not None
        
        # Добавляем небольшую задержку, чтобы изменения точно применились
        time.sleep(1)
        
        # 2. Удаление пира
        remove_response = requests.delete(
            f"{BASE_URL}/remove/{public_key}"
        )
        log_response(remove_response)
        
        assert remove_response.status_code == 200
        
        logger.info("Full lifecycle test passed!")
    
    def test_load_balancing(self):
        """Тест балансировки нагрузки между серверами"""
        logger.info("Testing load balancing...")
        
        # Выполняем несколько запросов на создание конфигурации без указания server_id
        # Это должно распределить запросы между доступными серверами
        public_keys = []
        
        for i in range(3):  # Создаем 3 конфигурации
            create_response = requests.post(
                f"{BASE_URL}/create",
                json={"user_id": f"load-balance-test-user-{i}"}
            )
            
            assert create_response.status_code == 200
            public_key = create_response.json().get("public_key")
            server_id = create_response.json().get("server_id")
            
            public_keys.append(public_key)
            logger.info(f"Created configuration on server {server_id}")
        
        # Получаем статус, чтобы проверить распределение
        status_response = requests.get(f"{BASE_URL}/status")
        log_response(status_response)
        
        # Очистка: удаляем созданные конфигурации
        for public_key in public_keys:
            requests.delete(f"{BASE_URL}/remove/{public_key}")
        
        logger.info("Load balancing test completed!")

# Функция для ручного запуска тестов
def run_tests():
    """Ручной запуск всех тестов"""
    # Базовые тесты эндпоинтов
    test = TestWireguardProxyAPI()
    test.test_health_check()
    test.test_get_servers()
    test.test_get_status()
    test.test_get_metrics()
    
    # Тесты с изменением данных
    test.test_add_server()
    test.test_create_configuration()
    test.test_remove_peer()
    
    # Тесты обработки ошибок
    error_test = TestErrorHandling()
    error_test.test_create_with_missing_params()
    error_test.test_remove_nonexistent_peer()
    
    # Интеграционные тесты
    integration_test = TestIntegration()
    integration_test.test_full_lifecycle()
    integration_test.test_load_balancing()

if __name__ == "__main__":
    run_tests()
