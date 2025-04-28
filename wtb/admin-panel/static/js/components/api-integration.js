/**
 * Модуль для взаимодействия с WireGuard Proxy API
 */
(function() {
    // Базовый URL API
    const API_BASE_URL = '/api';
    
    // Флаг для отслеживания ошибок соединения
    let connectionErrorShown = false;
    
    /**
     * Универсальная функция для выполнения API запросов
     * @param {string} endpoint - Конечная точка API
     * @param {Object} options - Опции запроса
     * @returns {Promise<Object>} Результат запроса
     */
    async function makeApiRequest(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        console.log(`API запрос: ${options.method || 'GET'} ${url}`);
        
        // Формируем параметры запроса
        const fetchOptions = {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'same-origin'  // Важно для работы с сессионными куками
        };
        
        // Добавляем тело запроса, если оно есть
        if (options.body) {
            fetchOptions.body = JSON.stringify(options.body);
            console.log(`Тело запроса:`, options.body);
        }
        
        try {
            // Выполняем запрос
            const response = await fetch(url, fetchOptions);
            
            // Логируем заголовки ответа
            const headers = {};
            response.headers.forEach((value, key) => {
                headers[key] = value;
            });
            console.log(`Заголовки ответа:`, headers);
            
            // Получаем текст ответа
            const responseText = await response.text();
            console.log(`Статус ответа: ${response.status}, Текст:`, responseText.substring(0, 500));
            
            // Пытаемся распарсить JSON
            let responseData;
            try {
                responseData = JSON.parse(responseText);
            } catch (e) {
                console.error('Ошибка при разборе JSON ответа:', e);
                throw new Error(`Ошибка формата ответа: ${responseText.substring(0, 100)}...`);
            }
            
            // Проверяем статус ответа
            if (!response.ok) {
                const errorMessage = responseData.message || responseData.error || `Ошибка ${response.status}`;
                console.error(`Ошибка API: ${errorMessage}`);
                throw new Error(errorMessage);
            }
            
            // Сбрасываем флаг ошибки соединения
            connectionErrorShown = false;
            
            return responseData;
        } catch (error) {
            // Если это ошибка сети и мы ещё не показывали уведомление
            if (error.name === 'TypeError' && error.message.includes('fetch') && !connectionErrorShown) {
                console.error('Ошибка соединения с сервером:', error);
                if (typeof window.showAlert === 'function') {
                    window.showAlert('Ошибка соединения с сервером. Проверьте подключение к интернету.', 'danger');
                    connectionErrorShown = true;
                }
            } else {
                console.error('Ошибка API запроса:', error);
            }
            throw error;
        }
    }
    
    /**
     * Получить список всех серверов
     * @returns {Promise<Object>} Результат запроса
     */
    async function fetchServers() {
        return makeApiRequest('/servers');
    }
    
    /**
     * Получить детальную информацию о сервере
     * @param {number} serverId - ID сервера
     * @returns {Promise<Object>} Информация о сервере
     */
    async function fetchServerDetails(serverId) {
        return makeApiRequest(`/servers/${serverId}`);
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
        
        // Создаем копию данных для безопасной модификации
        const data = {...serverData};
        
        // Преобразуем числовые значения
        data.port = parseInt(data.port, 10);
        data.geolocation_id = parseInt(data.geolocation_id, 10);
        if (data.max_peers) data.max_peers = parseInt(data.max_peers, 10);
        
        // Проверяем корректность числовых значений
        if (isNaN(data.port)) {
            throw new Error('Поле port должно быть числом');
        }
        if (isNaN(data.geolocation_id)) {
            throw new Error('Поле geolocation_id должно быть числом');
        }
        
        // Добавляем имя сервера, если оно не указано
        if (!data.name) {
            data.name = `Сервер ${data.endpoint}:${data.port}`;
        }
        
        // Добавляем локацию, если не указана
        if (!data.location) {
            data.location = `${data.endpoint}:${data.port}`;
        }
        
        // Устанавливаем API URL, если не указан
        if (!data.api_url && data.endpoint) {
            data.api_url = `http://${data.endpoint}:${data.port}/api`;
        }
        
        // Генерируем API ключ, если не указан
        if (!data.api_key) {
            data.api_key = generateApiKey();
        }
        
        return makeApiRequest('/servers', {
            method: 'POST',
            body: data
        });
    }
    
    /**
     * Обновить информацию о сервере
     * @param {number} serverId - ID сервера
     * @param {Object} updateData - Данные для обновления
     * @returns {Promise<Object>} Результат операции
     */
    async function updateServer(serverId, updateData) {
        // Создаем копию данных для безопасной модификации
        const data = {...updateData};
        
        // Преобразуем числовые значения, если они указаны
        if ('port' in data) data.port = parseInt(data.port, 10);
        if ('geolocation_id' in data) data.geolocation_id = parseInt(data.geolocation_id, 10);
        if ('max_peers' in data) data.max_peers = parseInt(data.max_peers, 10);
        
        return makeApiRequest(`/servers/${serverId}`, {
            method: 'PUT',
            body: data
        });
    }
    
    /**
     * Удалить сервер
     * @param {number} serverId - ID сервера
     * @returns {Promise<Object>} Результат операции
     */
    async function deleteServer(serverId) {
        return makeApiRequest(`/servers/${serverId}/delete`, {
            method: 'POST'
        });
    }
    
    /**
     * Получить метрики сервера
     * @param {number} serverId - ID сервера
     * @param {number} hours - Временной диапазон в часах
     * @returns {Promise<Object>} Метрики сервера
     */
    async function fetchServerMetrics(serverId, hours = 24) {
        return makeApiRequest(`/server_metrics/${serverId}?hours=${hours}`);
    }
    
    /**
     * Получить список геолокаций
     * @returns {Promise<Object>} Список геолокаций
     */
    async function fetchGeolocations() {
        return makeApiRequest('/geolocations');
    }
    
    /**
     * Добавить новую геолокацию
     * @param {Object} geoData - Данные новой геолокации
     * @returns {Promise<Object>} Результат операции
     */
    async function addGeolocation(geoData) {
        // Проверяем обязательные поля
        const requiredFields = ['code', 'name'];
        for (const field of requiredFields) {
            if (!geoData[field]) {
                throw new Error(`Отсутствует обязательное поле: ${field}`);
            }
        }
        
        // Создаем копию данных для безопасной модификации
        const data = {...geoData};
        
        // Добавляем поле available, если оно отсутствует
        if (!('available' in data)) {
            data.available = true;
        }
        
        // Добавляем описание, если оно отсутствует
        if (!data.description) {
            data.description = `Серверы в регионе ${data.name}`;
        }
        
        return makeApiRequest('/geolocations', {
            method: 'POST',
            body: data
        });
    }
    
    /**
     * Обновить геолокацию
     * @param {number} geoId - ID геолокации
     * @param {Object} updateData - Данные для обновления
     * @returns {Promise<Object>} Результат операции
     */
    async function updateGeolocation(geoId, updateData) {
        return makeApiRequest(`/geolocations/${geoId}`, {
            method: 'PUT',
            body: updateData
        });
    }
    
    /**
     * Удалить геолокацию
     * @param {number} geoId - ID геолокации
     * @returns {Promise<Object>} Результат операции
     */
    async function deleteGeolocation(geoId) {
        return makeApiRequest(`/geolocations/${geoId}`, {
            method: 'DELETE'
        });
    }
    
    /**
     * Проверить соединение с сервером
     * @param {number} serverId - ID сервера
     * @returns {Promise<Object>} Результат проверки
     */
    async function testServerConnection(serverId) {
        return makeApiRequest(`/servers/${serverId}/test`);
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
    
    // Экспортируем API функции в глобальное пространство имен
    window.Api = {
        makeApiRequest,
        fetchServers,
        fetchServerDetails,
        addServer,
        updateServer,
        deleteServer,
        fetchServerMetrics,
        fetchGeolocations,
        addGeolocation,
        updateGeolocation,
        deleteGeolocation,
        testServerConnection,
        generateApiKey
    };
    
    console.log('API модуль успешно загружен');
})();