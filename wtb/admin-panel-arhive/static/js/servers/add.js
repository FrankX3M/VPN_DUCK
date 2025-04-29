/**
 * Модуль для страницы добавления нового сервера
 */
(function() {
    console.log('Загружен модуль servers/add.js');
    
    // Переменные для отслеживания состояния
    let isSubmitting = false;
    let retryCount = 0;
    const MAX_RETRIES = 3;
    
    /**
     * Инициализация страницы
     */
    function initPage() {
        console.log('Инициализация страницы добавления сервера');
        
        // Проверяем наличие API модуля
        if (!window.Api || !window.Utils) {
            console.error('API модуль или модуль Utils не загружен. Проверьте порядок загрузки скриптов.');
            showDebugInfo('Ошибка инициализации: API модуль или Utils не загружен');
            return;
        }
        
        // Генерируем начальный API ключ
        generateApiKey();
        
        // Обработчики событий
        setupEventListeners();
        
        // Проверка загрузки геолокаций
        checkGeolocationOptions();
    }
    
    /**
     * Проверка доступности опций геолокации
     */
    function checkGeolocationOptions() {
        const geoSelect = document.getElementById('geolocation_id');
        if (!geoSelect) {
            console.warn('Элемент выбора геолокации не найден на странице');
            return;
        }
        
        // Если опций недостаточно, загружаем геолокации
        if (geoSelect.options.length <= 1) {
            console.log('Недостаточно опций геолокации, загружаем список');
            loadGeolocations();
        }
    }
    
    /**
     * Загрузка списка геолокаций
     */
    function loadGeolocations() {
        if (!window.Api || typeof window.Api.fetchGeolocations !== 'function') {
            console.error('Функция fetchGeolocations не определена');
            showAlert('Ошибка: API модуль не загружен корректно', 'danger');
            return;
        }
        
        window.Api.fetchGeolocations()
            .then(data => {
                if (data.status === 'success') {
                    updateGeolocationOptions(data.geolocations);
                } else {
                    showAlert(`Ошибка: ${data.message || 'Неизвестная ошибка при загрузке геолокаций'}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке геолокаций:', error);
                
                // Если ошибка не связана с сетью, показываем её
                if (error.name !== 'TypeError' || !error.message.includes('fetch')) {
                    showAlert('Ошибка загрузки геолокаций: ' + error.message, 'danger');
                }
                
                // Пробуем создать фиктивные опции для тестирования
                const mockGeolocations = [
                    { id: 1, name: 'Россия (тест)', code: 'ru' },
                    { id: 2, name: 'США (тест)', code: 'us' },
                    { id: 3, name: 'Европа (тест)', code: 'eu' }
                ];
                updateGeolocationOptions(mockGeolocations);
            });
    }
    
    /**
     * Обновление опций выбора геолокации
     */
    function updateGeolocationOptions(geolocations) {
        const geoSelect = document.getElementById('geolocation_id');
        if (!geoSelect) {
            console.warn('Элемент выбора геолокации не найден на странице');
            return;
        }
        
        // Сохраняем текущее выбранное значение
        const selectedValue = geoSelect.value;
        
        // Очищаем текущие опции
        geoSelect.innerHTML = '<option value="">Выберите геолокацию</option>';
        
        // Добавляем новые опции
        if (Array.isArray(geolocations)) {
            geolocations.forEach(geo => {
                if (geo && geo.id && geo.name) {
                    const option = document.createElement('option');
                    option.value = geo.id;
                    option.textContent = geo.name;
                    geoSelect.appendChild(option);
                }
            });
            
            console.log(`Добавлено ${geolocations.length} опций геолокации`);
            
            // Показываем опции в отладочной информации
            showDebugInfo({
                action: 'updateGeolocationOptions',
                geolocations_count: geolocations.length,
                geolocations: geolocations.map(g => ({ id: g.id, name: g.name, code: g.code }))
            });
        } else {
            console.warn('Получены некорректные данные геолокаций:', geolocations);
            showDebugInfo({
                action: 'updateGeolocationOptions_error',
                message: 'Получены некорректные данные геолокаций',
                data: geolocations
            });
        }
        
        // Восстанавливаем выбранное значение, если оно существует
        if (selectedValue && Array.from(geoSelect.options).some(opt => opt.value === selectedValue)) {
            geoSelect.value = selectedValue;
        }
    }
    
    /**
     * Настройка обработчиков событий
     */
    function setupEventListeners() {
        console.log('Настройка обработчиков событий');
        
        // Обработчик отправки формы
        const form = document.getElementById('addServerForm');
        if (form) {
            form.addEventListener('submit', handleFormSubmit);
        } else {
            console.error('Форма добавления сервера не найдена на странице');
            
            // Проверяем наличие всех необходимых элементов
            checkRequiredElements();
        }
        
        // Обработчик кнопки генерации API ключа
        const generateBtn = document.getElementById('generateApiKeyBtn');
        if (generateBtn) {
            generateBtn.addEventListener('click', generateApiKey);
        }
        
        // Обработчик кнопки копирования API ключа
        const copyBtn = document.getElementById('copyApiKeyBtn');
        if (copyBtn) {
            copyBtn.addEventListener('click', copyApiKey);
        }
        
        // Автоматическое обновление API URL при изменении endpoint и порта
        const endpointInput = document.getElementById('endpoint');
        const portInput = document.getElementById('port');
        const apiUrlInput = document.getElementById('api_url');
        
        if (endpointInput && portInput && apiUrlInput) {
            const updateApiUrl = () => {
                const endpoint = endpointInput.value.trim();
                const port = portInput.value.trim();
                if (endpoint) {
                    apiUrlInput.value = `http://${endpoint}${port ? ':' + port : ''}/api`;
                }
            };
            
            endpointInput.addEventListener('input', updateApiUrl);
            portInput.addEventListener('input', updateApiUrl);
        }
    }
    
    /**
     * Проверяет наличие всех необходимых элементов на странице
     */
    function checkRequiredElements() {
        const requiredIds = [
            'addServerForm', 'endpoint', 'port', 'address', 'public_key', 
            'geolocation_id', 'api_key', 'api_key_display', 'api_url', 
            'max_peers', 'active', 'server_name'
        ];
        
        const missingElements = [];
        
        requiredIds.forEach(id => {
            if (!document.getElementById(id)) {
                missingElements.push(id);
            }
        });
        
        if (missingElements.length > 0) {
            console.error('Отсутствуют необходимые элементы:', missingElements);
            showDebugInfo({
                action: 'checkRequiredElements',
                missing_elements: missingElements
            });
            
            // Создаем отсутствующие элементы для тестирования
            createMissingElements(missingElements);
        }
    }
    
    /**
     * Создает отсутствующие элементы для тестирования
     */
    function createMissingElements(missingIds) {
        // Если отсутствует форма, создаем её
        if (missingIds.includes('addServerForm')) {
            const formContainer = document.querySelector('main') || document.body;
            
            const formHtml = `
            <div class="container mt-4">
                <h1>Добавление нового сервера</h1>
                <form id="addServerForm" class="mt-4">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="server_name" class="form-label">Имя сервера</label>
                            <input type="text" class="form-control" id="server_name" name="server_name" placeholder="Например: Сервер Россия">
                            <div class="form-text">Произвольное имя для идентификации сервера</div>
                        </div>
                        <div class="col-md-6">
                            <label for="geolocation_id" class="form-label">Геолокация</label>
                            <select class="form-select" id="geolocation_id" name="geolocation_id" required>
                                <option value="">Выберите геолокацию</option>
                            </select>
                            <div class="form-text">Географическое расположение сервера</div>
                        </div>
                    </div>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="endpoint" class="form-label">Внешний IP (Endpoint)</label>
                            <input type="text" class="form-control" id="endpoint" name="endpoint" required>
                            <div class="form-text">Внешний IP-адрес сервера</div>
                        </div>
                        <div class="col-md-6">
                            <label for="port" class="form-label">Порт</label>
                            <input type="number" class="form-control" id="port" name="port" value="51820" required>
                            <div class="form-text">Порт для подключения WireGuard</div>
                        </div>
                    </div>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="address" class="form-label">Внутренний IP</label>
                            <input type="text" class="form-control" id="address" name="address" placeholder="10.0.0.1/24" required>
                            <div class="form-text">Внутренний IP-адрес сервера с маской сети</div>
                        </div>
                        <div class="col-md-6">
                            <label for="public_key" class="form-label">Публичный ключ</label>
                            <input type="text" class="form-control" id="public_key" name="public_key" required>
                            <div class="form-text">Публичный ключ WireGuard</div>
                        </div>
                    </div>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="api_url" class="form-label">API URL</label>
                            <input type="text" class="form-control" id="api_url" name="api_url">
                            <div class="form-text">URL для доступа к API сервера (заполняется автоматически)</div>
                        </div>
                        <div class="col-md-6">
                            <label for="max_peers" class="form-label">Максимум пиров</label>
                            <input type="number" class="form-control" id="max_peers" name="max_peers" value="100">
                            <div class="form-text">Максимальное количество подключений</div>
                        </div>
                    </div>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="api_key_display" class="form-label">API Ключ</label>
                            <div class="input-group">
                                <input type="text" class="form-control" id="api_key_display" readonly>
                                <input type="hidden" id="api_key" name="api_key">
                                <button class="btn btn-outline-secondary" type="button" id="generateApiKeyBtn">
                                    <i class="bi bi-arrow-repeat"></i>
                                </button>
                                <button class="btn btn-outline-secondary" type="button" id="copyApiKeyBtn">
                                    <i class="bi bi-clipboard"></i>
                                </button>
                            </div>
                            <div class="form-text">API ключ для авторизации сервера</div>
                        </div>
                        <div class="col-md-6 d-flex align-items-end">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="active" name="active" checked>
                                <label class="form-check-label" for="active">Активен</label>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <button type="submit" class="btn btn-primary">Добавить сервер</button>
                        <a href="/servers" class="btn btn-secondary">Отмена</a>
                    </div>
                </form>
            </div>
            
            <!-- Отладочная информация -->
            <div id="debug-container" class="container mt-3">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">Отладочная информация</h5>
                        <button class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('debug-container').style.display='none'">Скрыть</button>
                    </div>
                    <div class="card-body">
                        <pre id="debug-info" style="max-height: 300px; overflow: auto;"></pre>
                    </div>
                </div>
            </div>
            `;
            
            const formDiv = document.createElement('div');
            formDiv.innerHTML = formHtml;
            formContainer.appendChild(formDiv);
            
            // Переназначаем обработчики
            setupEventListeners();
        } else {
            // Создаем отдельные отсутствующие элементы
            const form = document.getElementById('addServerForm');
            if (form) {
                missingIds.forEach(id => {
                    if (!document.getElementById(id)) {
                        switch(id) {
                            case 'server_name':
                                insertFormField(form, 'text', 'server_name', 'Имя сервера', 'Например: Сервер Россия');
                                break;
                            case 'api_key':
                            case 'api_key_display':
                                if (!document.getElementById('api_key') && !document.getElementById('api_key_display')) {
                                    insertApiKeyFields(form);
                                }
                                break;
                            // Другие случаи по необходимости
                        }
                    }
                });
            }
        }
        
        // Обновляем обработчики событий
        setupEventListeners();
    }
    
    /**
     * Вставляет поле формы с указанными параметрами
     */
    function insertFormField(form, type, id, label, placeholder) {
        const div = document.createElement('div');
        div.className = 'mb-3';
        div.innerHTML = `
            <label for="${id}" class="form-label">${label}</label>
            <input type="${type}" class="form-control" id="${id}" name="${id}" placeholder="${placeholder}">
        `;
        form.insertBefore(div, form.firstChild);
    }
    
    /**
     * Вставляет поля для API ключа
     */
    function insertApiKeyFields(form) {
        const div = document.createElement('div');
        div.className = 'mb-3';
        div.innerHTML = `
            <label for="api_key_display" class="form-label">API Ключ</label>
            <div class="input-group">
                <input type="text" class="form-control" id="api_key_display" readonly>
                <input type="hidden" id="api_key" name="api_key">
                <button class="btn btn-outline-secondary" type="button" id="generateApiKeyBtn">
                    <i class="bi bi-arrow-repeat"></i>
                </button>
                <button class="btn btn-outline-secondary" type="button" id="copyApiKeyBtn">
                    <i class="bi bi-clipboard"></i>
                </button>
            </div>
        `;
        form.appendChild(div);
        
        // Добавляем обработчики событий для новых кнопок
        document.getElementById('generateApiKeyBtn')?.addEventListener('click', generateApiKey);
        document.getElementById('copyApiKeyBtn')?.addEventListener('click', copyApiKey);
    }
    
    /**
     * Обработчик отправки формы
     * @param {Event} event - Событие отправки формы
     */
    function handleFormSubmit(event) {
        event.preventDefault();
        
        // Предотвращаем повторную отправку
        if (isSubmitting) {
            console.log('Форма уже отправляется, игнорируем повторную отправку');
            return;
        }
        
        isSubmitting = true;
        
        // Получаем все поля формы
        const endpoint = document.getElementById('endpoint')?.value.trim();
        const port = document.getElementById('port')?.value.trim();
        const address = document.getElementById('address')?.value.trim();
        const publicKey = document.getElementById('public_key')?.value.trim();
        const geoId = document.getElementById('geolocation_id')?.value;
        const apiKey = document.getElementById('api_key')?.value;
        const apiUrl = document.getElementById('api_url')?.value.trim();
        const maxPeers = document.getElementById('max_peers')?.value;
        const active = document.getElementById('active')?.checked !== false;
        const serverName = document.getElementById('server_name')?.value.trim() || `Сервер ${endpoint}:${port}`;
        
        // Проверка заполнения обязательных полей
        const requiredFields = ['endpoint', 'port', 'address', 'public_key', 'geolocation_id'];
        let isValid = true;
        
        requiredFields.forEach(field => {
            const input = document.getElementById(field);
            if (!input || !input.value.trim()) {
                if (input) {
                    input.classList.add('is-invalid');
                }
                isValid = false;
            } else {
                if (input) {
                    input.classList.remove('is-invalid');
                }
            }
        });
        
        if (!isValid) {
            showAlert('Пожалуйста, заполните все обязательные поля', 'warning');
            isSubmitting = false;
            return;
        }
        
        // Подготовка данных для отправки
        const formData = {
            name: serverName,
            endpoint: endpoint,
            port: parseInt(port),
            address: address,
            public_key: publicKey,
            geolocation_id: parseInt(geoId),
            api_key: apiKey,
            api_url: apiUrl || `http://${endpoint}:${port}/api`,
            max_peers: parseInt(maxPeers || '0'),
            status: active ? 'active' : 'inactive',
            location: `${endpoint}:${port}` // Добавляем местоположение серверу
        };
        
        // Отладочная информация
        showDebugInfo({
            action: 'submitForm',
            formData: formData
        });
        
        // Отключаем кнопку отправки
        const submitBtn = event.submitter || document.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Добавление...';
        }
        
        console.log('Отправка данных сервера:', formData);
        
        // Отправка данных на сервер
        if (!window.Api || typeof window.Api.addServer !== 'function') {
            console.error('Функция addServer не определена');
            showAlert('Ошибка: API модуль не загружен корректно', 'danger');
            resetSubmitButton(submitBtn);
            isSubmitting = false;
            return;
        }
        
        window.Api.addServer(formData)
            .then(data => {
                if (data.status === 'success') {
                    // Показываем сообщение об успехе
                    showAlert('Сервер успешно добавлен!', 'success');
                    
                    // Отладочная информация
                    showDebugInfo({
                        action: 'serverAdded',
                        response: data
                    });
                    
                    // Сбрасываем форму
                    document.getElementById('addServerForm').reset();
                    
                    // Генерируем новый API ключ
                    generateApiKey();
                    
                    // Перенаправляем на страницу со списком серверов через некоторое время
                    setTimeout(() => {
                        window.location.href = '/servers';
                    }, 2000);
                } else {
                    handleApiError(data, submitBtn);
                }
            })
            .catch(error => {
                console.error('Ошибка при добавлении сервера:', error);
                
                // Отладочная информация
                showDebugInfo({
                    action: 'addServerError',
                    error: error.message,
                    stack: error.stack
                });
                
                // Если превышено максимальное количество попыток
                if (retryCount >= MAX_RETRIES) {
                    showAlert(`Ошибка: ${error.message || 'Ошибка соединения с сервером'}`, 'danger');
                    resetSubmitButton(submitBtn);
                    isSubmitting = false;
                    retryCount = 0;
                } else {
                    // Увеличиваем счетчик попыток и пробуем снова
                    retryCount++;
                    showAlert(`Повторная попытка (${retryCount}/${MAX_RETRIES})...`, 'warning');
                    
                    setTimeout(() => {
                        isSubmitting = false;
                        handleFormSubmit(event);
                    }, 1000 * retryCount);
                }
            });
    }
    
    /**
     * Обрабатывает ошибки API
     */
    function handleApiError(response, submitBtn) {
        // Анализируем сообщение об ошибке
        let errorMsg = response.message || response.error || 'Неизвестная ошибка при добавлении сервера';
        let detailsMsg = '';
        
        // Если есть дополнительные детали, извлекаем их
        if (response.details) {
            try {
                const details = JSON.parse(response.details);
                if (details.error) {
                    detailsMsg = details.error;
                }
            } catch (e) {
                detailsMsg = response.details;
            }
        }
        
        // Отладочная информация
        showDebugInfo({
            action: 'apiError',
            response: response,
            errorMsg: errorMsg,
            detailsMsg: detailsMsg
        });
        
        // Показываем сообщение об ошибке
        showAlert(`Ошибка: ${errorMsg}${detailsMsg ? ' - ' + detailsMsg : ''}`, 'danger');
        
        // Восстанавливаем кнопку
        resetSubmitButton(submitBtn);
        isSubmitting = false;
    }
    
    /**
     * Сбрасывает состояние кнопки отправки
     */
    function resetSubmitButton(submitBtn) {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Добавить сервер';
        }
    }
    
    /**
     * Генерирует новый API ключ
     */
    function generateApiKey() {
        console.log('Генерация нового API ключа');
        
        let apiKey = '';
        if (typeof window.Api === 'object' && typeof window.Api.generateApiKey === 'function') {
            apiKey = window.Api.generateApiKey();
        } else if (typeof window.Utils === 'object' && typeof window.Utils.generateApiKey === 'function') {
            apiKey = window.Utils.generateApiKey();
        } else {
            // Резервная функция генерации ключа
            const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
            const length = 32;
            for (let i = 0; i < length; i++) {
                apiKey += characters.charAt(Math.floor(Math.random() * characters.length));
            }
        }
        
        // Обновляем значения в полях формы
        const apiKeyInput = document.getElementById('api_key');
        const apiKeyDisplay = document.getElementById('api_key_display');
        
        if (apiKeyInput) {
            apiKeyInput.value = apiKey;
        }
        
        if (apiKeyDisplay) {
            apiKeyDisplay.value = apiKey;
        }
    }
    
    /**
     * Копирует API ключ в буфер обмена
     */
    function copyApiKey() {
        const apiKeyDisplay = document.getElementById('api_key_display');
        if (!apiKeyDisplay) {
            console.warn('Элемент отображения API ключа не найден');
            return;
        }
        
        if (typeof window.Utils === 'object' && typeof window.Utils.copyToClipboard === 'function') {
            window.Utils.copyToClipboard(apiKeyDisplay.value)
                .then(success => {
                    if (success) {
                        showCopiedIndicator();
                    }
                });
        } else {
            // Резервный метод копирования
            navigator.clipboard.writeText(apiKeyDisplay.value)
                .then(() => {
                    showCopiedIndicator();
                })
                .catch(err => {
                    console.error('Не удалось скопировать: ', err);
                    showAlert('Не удалось скопировать API ключ', 'warning');
                });
        }
    }
    
    /**
     * Показывает индикатор успешного копирования
     */
    function showCopiedIndicator() {
        const copyBtn = document.getElementById('copyApiKeyBtn');
        if (!copyBtn) return;
        
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i class="bi bi-check"></i> Скопировано';
        
        setTimeout(() => {
            copyBtn.innerHTML = originalText;
        }, 2000);
    }
    
    /**
     * Показывает отладочную информацию
     */
    function showDebugInfo(info) {
        const debugInfoEl = document.getElementById('debug-info');
        const debugContainer = document.getElementById('debug-container');
        
        if (debugInfoEl && debugContainer) {
            const timestamp = new Date().toISOString();
            const formattedInfo = typeof info === 'object' 
                ? JSON.stringify({...info, timestamp}, null, 2) 
                : `${timestamp}: ${info}`;
            
            debugInfoEl.textContent += formattedInfo + '\n\n';
            debugContainer.style.display = 'block';
            
            // Прокручиваем к последней записи
            debugInfoEl.scrollTop = debugInfoEl.scrollHeight;
        }
    }
    
    /**
     * Показывает сообщения для пользователя
     */
    function showAlert(message, type = 'info') {
        console.log(`Показ уведомления (${type}): ${message}`);
        
        // Проверяем наличие глобальной функции
        if (typeof window.showAlert === 'function') {
            window.showAlert(message, type);
            return;
        }
        
        // Запасной вариант, если глобальная функция не доступна
        let alertsContainer = document.querySelector('.flash-messages');
        
        // Если контейнер не найден, создаем его
        if (!alertsContainer) {
            alertsContainer = document.createElement('div');
            alertsContainer.className = 'flash-messages';
            alertsContainer.style.position = 'fixed';
            alertsContainer.style.top = '20px';
            alertsContainer.style.right = '20px';
            alertsContainer.style.zIndex = '9999';
            document.body.appendChild(alertsContainer);
        }
        
        // Создаем уведомление
        const alertHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertsContainer.innerHTML += alertHTML;
        
        // Автоматически скрываем уведомление через 5 секунд
        setTimeout(() => {
            const alerts = alertsContainer.querySelectorAll('.alert');
            alerts.forEach(alert => {
                try {
                    if (window.bootstrap && bootstrap.Alert) {
                        const bsAlert = new bootstrap.Alert(alert);
                        bsAlert.close();
                    } else {
                        alert.classList.remove('show');
                        setTimeout(() => {
                            if (alertsContainer.contains(alert)) {
                                alertsContainer.removeChild(alert);
                            }
                        }, 300);
                    }
                } catch (e) {
                    // В случае ошибки просто удаляем элемент
                    if (alertsContainer.contains(alert)) {
                        alertsContainer.removeChild(alert);
                    }
                }
            });
        }, 5000);
    }
    
    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', initPage);
})();