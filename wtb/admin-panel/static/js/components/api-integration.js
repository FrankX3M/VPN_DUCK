/**
 * Модуль для взаимодействия с WireGuard Proxy API
 */
(function() {
    // Базовый URL API
    const API_BASE_URL = '/api';
    
    /**
     * Получить список всех серверов
     * @returns {Promise<Object>} Результат запроса
     */
    async function fetchServers() {
        try {
            const response = await fetch(`${API_BASE_URL}/servers`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка при получении списка серверов:', error);
            throw error;
        }
    }
    
    /**
     * Получить детальную информацию о сервере
     * @param {number} serverId - ID сервера
     * @returns {Promise<Object>} Информация о сервере
     */
    async function fetchServerDetails(serverId) {
        try {
            const response = await fetch(`${API_BASE_URL}/servers/${serverId}`);
            return await response.json();
        } catch (error) {
            console.error(`Ошибка при получении информации о сервере ${serverId}:`, error);
            throw error;
        }
    }
    
    /**
     * Добавить новый сервер
     * @param {Object} serverData - Данные нового сервера
     * @returns {Promise<Object>} Результат операции
     */
    async function addServer(serverData) {
        // Проверяем обязательные поля
        const requiredFields = [
            'endpoint', 'port', 'address', 'public_key', 'geolocation_id'
        ];
        
        for (const field of requiredFields) {
            if (!serverData[field]) {
                throw new Error(`Отсутствует обязательное поле: ${field}`);
            }
        }
        
        // Преобразуем числовые значения
        if (serverData.port) serverData.port = parseInt(serverData.port);
        if (serverData.geolocation_id) serverData.geolocation_id = parseInt(serverData.geolocation_id);
        if (serverData.max_peers) serverData.max_peers = parseInt(serverData.max_peers);
        
        // Устанавливаем API URL, если не указан
        if (!serverData.api_url && serverData.endpoint) {
            serverData.api_url = `http://${serverData.endpoint}/`;
        }
        
        // Генерируем API ключ, если не указан
        if (!serverData.api_key) {
            serverData.api_key = generateApiKey();
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/servers`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(serverData)
            });
            
            return await response.json();
        } catch (error) {
            console.error('Ошибка при добавлении сервера:', error);
            throw error;
        }
    }
    
    /**
     * Обновить информацию о сервере
     * @param {number} serverId - ID сервера
     * @param {Object} updateData - Данные для обновления
     * @returns {Promise<Object>} Результат операции
     */
    async function updateServer(serverId, updateData) {
        try {
            const response = await fetch(`${API_BASE_URL}/servers/${serverId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });
            
            return await response.json();
        } catch (error) {
            console.error(`Ошибка при обновлении сервера ${serverId}:`, error);
            throw error;
        }
    }
    
    /**
     * Удалить сервер
     * @param {number} serverId - ID сервера
     * @returns {Promise<Object>} Результат операции
     */
    async function deleteServer(serverId) {
        try {
            const response = await fetch(`${API_BASE_URL}/servers/${serverId}/delete`, {
                method: 'POST'
            });
            
            return await response.json();
        } catch (error) {
            console.error(`Ошибка при удалении сервера ${serverId}:`, error);
            throw error;
        }
    }
    
    /**
     * Получить метрики сервера
     * @param {number} serverId - ID сервера
     * @param {number} hours - Временной диапазон в часах
     * @returns {Promise<Object>} Метрики сервера
     */
    async function fetchServerMetrics(serverId, hours = 24) {
        try {
            const response = await fetch(`${API_BASE_URL}/server_metrics/${serverId}?hours=${hours}`);
            return await response.json();
        } catch (error) {
            console.error(`Ошибка при получении метрик сервера ${serverId}:`, error);
            throw error;
        }
    }
    
    /**
     * Получить список геолокаций
     * @returns {Promise<Object>} Список геолокаций
     */
    async function fetchGeolocations() {
        try {
            const response = await fetch(`${API_BASE_URL}/geolocations`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка при получении списка геолокаций:', error);
            throw error;
        }
    }
    
    /**
     * Проверить соединение с сервером
     * @param {number} serverId - ID сервера
     * @returns {Promise<Object>} Результат проверки
     */
    async function testServerConnection(serverId) {
        try {
            // В API документации не указан точный эндпоинт для тестирования соединения
            // Поэтому используем запрос статуса сервера
            const response = await fetch(`${API_BASE_URL}/status?server_id=${serverId}`);
            return await response.json();
        } catch (error) {
            console.error(`Ошибка при проверке соединения с сервером ${serverId}:`, error);
            throw error;
        }
    }
    
    /**
     * Генерировать случайный API ключ
     * @param {number} length - Длина ключа
     * @returns {string} Сгенерированный ключ
     */
    function generateApiKey(length = 32) {
        const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        const charactersLength = characters.length;
        
        for (let i = 0; i < length; i++) {
            result += characters.charAt(Math.floor(Math.random() * charactersLength));
        }
        
        return result;
    }
    
    /**
     * Функция для анализа и обработки ошибок API
     * @param {Object} response - Ответ API
     * @returns {Object} Обработанная ошибка
     */
    function handleApiError(response) {
        if (response.status === 'error') {
            return {
                status: 'error',
                message: response.message || 'Неизвестная ошибка',
                details: response.details || null
            };
        }
        
        return response;
    }
    
    // Экспортируем API функции в глобальное пространство имен
    window.Api = {
        fetchServers,
        fetchServerDetails,
        addServer,
        updateServer,
        deleteServer,
        fetchServerMetrics,
        fetchGeolocations,
        testServerConnection,
        generateApiKey,
        handleApiError
    };
})();