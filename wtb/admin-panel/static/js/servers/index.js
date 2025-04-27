/**
 * Основной JavaScript для страницы серверов
 */
console.log('Загружена новая версия index.js - v1.0.2');

// Определяем функции-заглушки до DOMContentLoaded
window.initServerModal = window.initServerModal || function() {
    console.log('Вызвана заглушка для initServerModal');
};
window.updateStatistics = window.updateStatistics || function(servers) {
    console.log('Вызвана заглушка для updateStatistics', servers);
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM загружен, инициализация страницы серверов');
    
    // Проверяем наличие API функций
    if (typeof window.Api === 'undefined') {
        console.warn('API модуль не загружен, используем резервные функции');
        window.Api = createBackupApiFunctions();
    }
    
    // Используем API функции
    const { 
        fetchServers, 
        fetchGeolocations, 
        deleteServer 
    } = window.Api;
    
    // Глобальные переменные
    let serversData = [];
    let geolocationsData = [];
    let selectedServerId = null;
    let viewMode = 'table';  // 'table' или 'card'
    let showAdvanced = false;
    let retryCount = 0;
    const MAX_RETRIES = 3;
    
    // Инициализация страницы
    initPage();
    

    function setViewMode(mode) {
        console.log(`Переключение режима отображения на: ${mode}`);
        
        viewMode = mode;
        
        // Обновляем активную кнопку
        const tableBtn = document.getElementById('tableViewBtn');
        const cardBtn = document.getElementById('cardViewBtn');
        
        if (tableBtn) tableBtn.classList.toggle('active', mode === 'table');
        if (cardBtn) cardBtn.classList.toggle('active', mode === 'card');
        
        // Обновляем видимость контейнеров (исправленный код)
        const tableContainer = document.getElementById('tableView');
        const cardContainer = document.getElementById('cardView');
        
        if (tableContainer) {
            tableContainer.style.display = mode === 'table' ? 'block' : 'none';
            console.log('Установлен display для tableView:', tableContainer.style.display);
        }
        
        if (cardContainer) {
            cardContainer.style.display = mode === 'card' ? 'block' : 'none';
            console.log('Установлен display для cardView:', cardContainer.style.display);
        }
        
        // Обновляем отображение серверов
        updateServersView();
    }


    /**
     * Инициализирует страницу
     */
    function initPage() {
        console.log('Инициализация страницы серверов');
        
        // Загрузка данных
        loadGeolocations();
        loadServers();
        
        // Обработчики событий
        setupEventListeners();
        
        // Инициализация подсказок
        setupTooltips();
    }
    
    /**
     * Создает резервные API функции в случае отсутствия основного API
     * @returns {Object} Объект с резервными API функциями
     */
    function createBackupApiFunctions() {
        return {
            fetchServers: () => {
                console.warn('Используется резервная функция fetchServers');
                return Promise.resolve({ 
                    status: 'success', 
                    servers: [] 
                });
            },
            fetchGeolocations: () => {
                console.warn('Используется резервная функция fetchGeolocations');
                return Promise.resolve({ 
                    status: 'success', 
                    geolocations: [] 
                });
            },
            deleteServer: (id) => {
                console.warn('Используется резервная функция deleteServer', id);
                return Promise.resolve({ 
                    status: 'error', 
                    message: 'API для удаления не реализован' 
                });
            },
            addServer: (data) => {
                console.warn('Используется резервная функция addServer', data);
                return Promise.resolve({ 
                    status: 'error', 
                    message: 'API для добавления не реализован' 
                });
            }
        };
    }
    
    /**
     * Настраивает обработчики событий
     */
    function setupEventListeners() {
        console.log('Настройка обработчиков событий');
        
        // Обновление данных
        const refreshBtn = document.getElementById('refreshServers');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => loadServers());
        }
        
        // Переключение вида отображения
        const tableViewBtn = document.getElementById('tableViewBtn');
        const cardViewBtn = document.getElementById('cardViewBtn');
        
        if (tableViewBtn) {
            tableViewBtn.addEventListener('click', () => setViewMode('table'));
        }
        
        if (cardViewBtn) {
            cardViewBtn.addEventListener('click', () => setViewMode('card'));
        }
        
        // Поиск и фильтрация
        const searchInput = document.getElementById('serverSearch');
        const geoFilter = document.getElementById('geolocationFilter');
        const statusFilter = document.getElementById('statusFilter');
        
        if (searchInput) {
            searchInput.addEventListener('input', filterServers);
        }
        
        if (geoFilter) {
            geoFilter.addEventListener('change', filterServers);
        }
        
        if (statusFilter) {
            statusFilter.addEventListener('change', filterServers);
        }
        
        // Переключатель расширенной информации
        const showAdvancedCheckbox = document.getElementById('showAdvanced');
        if (showAdvancedCheckbox) {
            showAdvancedCheckbox.addEventListener('change', (event) => {
                showAdvanced = event.target.checked;
                updateServersView();
            });
        }
        
        // Обработчик удаления сервера
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', () => {
                if (selectedServerId) {
                    handleDeleteServer(selectedServerId);
                }
            });
        }
        
        // Инициализация модальных окон
        if (typeof window.initServerModal === 'function') {
            window.initServerModal();
        } else {
            initLocalServerModal(); // Используем внутреннюю реализацию, если глобальная недоступна
        }
    }
    
    /**
     * Инициализирует модальные окна на странице (локальная версия)
     */
    function initLocalServerModal() {
        console.log('Инициализация модальных окон (локальная версия)');
        
        // Находим модальное окно, если оно есть на странице
        const serverModal = document.getElementById('serverModal') || document.getElementById('addServerModal');
        if (!serverModal) {
            console.log('Модальные окна не найдены на странице');
            return;
        }
        
        // Например, добавить обработчики для кнопок в модальном окне
        const submitButton = serverModal.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.addEventListener('click', function(event) {
                // Предотвращаем стандартную отправку формы
                event.preventDefault();
                
                // Получаем данные формы
                const form = serverModal.querySelector('form');
                if (form) {
                    // Проверка валидности формы
                    if (!form.checkValidity()) {
                        form.reportValidity();
                        return;
                    }
                    
                    const formData = new FormData(form);
                    const serverData = {};
                    
                    // Преобразуем FormData в объект
                    formData.forEach((value, key) => {
                        serverData[key] = value;
                    });
                    
                    // Дополнительная валидация данных
                    if (!validateServerData(serverData)) {
                        showAlert('Ошибка валидации данных. Проверьте все поля.', 'danger');
                        return;
                    }
                    
                    // Отправляем данные на сервер
                    addServer(serverData);
                }
            });
        }
        
        console.log('Модальные окна инициализированы (локальная версия)');
    }
    
    /**
     * Валидирует данные сервера перед отправкой
     * @param {Object} data - Данные сервера
     * @returns {boolean} - Результат валидации
     */
    function validateServerData(data) {
        // Проверяем обязательные поля
        if (!data.endpoint || !data.port) {
            return false;
        }
        
        // Проверяем корректность порта
        const port = parseInt(data.port);
        if (isNaN(port) || port < 1 || port > 65535) {
            return false;
        }
        
        return true;
    }
    
    /**
     * Настраивает подсказки Bootstrap
     */
    function setupTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        if (tooltipTriggerList.length > 0 && typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
        }
    }
    
    /**
     * Загружает список геолокаций
     */
    function loadGeolocations() {
        console.log('Загрузка списка геолокаций');
        
        if (typeof window.Api.fetchGeolocations !== 'function') {
            console.error('Функция fetchGeolocations не определена');
            showAlert('Ошибка: функция загрузки геолокаций недоступна', 'danger');
            return;
        }
        
        window.Api.fetchGeolocations()
            .then(data => {
                if (data.status === 'success') {
                    geolocationsData = Array.isArray(data.geolocations) ? data.geolocations : [];
                    updateGeolocationFilter(geolocationsData);
                    console.log(`Загружено ${geolocationsData.length} геолокаций`);
                } else {
                    showAlert(`Ошибка: ${data.message || 'Неизвестная ошибка при загрузке геолокаций'}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке геолокаций:', error);
                showAlert('Ошибка соединения с сервером при загрузке геолокаций', 'danger');
            });
    }
    
    /**
     * Обновляет фильтр геолокаций
     */
    function updateGeolocationFilter(geolocations) {
        const filterContainer = document.getElementById('geolocationFilter');
        if (!filterContainer) return;
        
        // Сохраняем текущее выбранное значение
        const selectedValue = filterContainer.value;
        
        // Очищаем текущие опции (кроме первой)
        filterContainer.innerHTML = '<option value="all">Все геолокации</option>';
        
        // Добавляем опции для каждой геолокации
        if (Array.isArray(geolocations)) {
            geolocations.forEach(geo => {
                if (geo && geo.id && geo.name) {
                    const option = document.createElement('option');
                    option.value = geo.id;
                    option.textContent = geo.name;
                    filterContainer.appendChild(option);
                }
            });
        }
        
        // Восстанавливаем выбранное значение, если оно существует
        if (geolocations.some(geo => geo.id == selectedValue)) {
            filterContainer.value = selectedValue;
        }
    }
    
    /**
     * Загружает список серверов с механизмом повторных попыток
     */
    function loadServers() {
        console.log('Загрузка списка серверов');
        
        const tableBody = document.getElementById('serversTableBody');
        const cardContainer = document.getElementById('cardView');
        
        // Показываем индикаторы загрузки
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="8" class="text-center">Загрузка данных...</td></tr>';
        }
        
        const loadingIndicator = document.getElementById('cardsLoadingIndicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = '';
        }
        
        if (typeof window.Api.fetchServers !== 'function') {
            console.error('Функция fetchServers не определена');
            showLoadingError(tableBody, loadingIndicator);
            showAlert('Ошибка: функция загрузки серверов недоступна', 'danger');
            return;
        }
        
        window.Api.fetchServers()
            .then(data => {
                retryCount = 0; // Сбрасываем счетчик повторов при успехе
                
                if (data.status === 'success') {
                    serversData = Array.isArray(data.servers) ? data.servers : [];
                    
                    // Обновляем статистику
                    if (typeof window.updateStatistics === 'function') {
                        window.updateStatistics(serversData);
                    } else {
                        updateLocalStatistics(serversData);
                    }
                    
                    // Обновляем UI
                    updateServersView();
                    
                    console.log(`Загружено ${serversData.length} серверов`);
                } else {
                    showAlert(`Ошибка: ${data.message || 'Неизвестная ошибка при загрузке серверов'}`, 'danger');
                    showLoadingError(tableBody, loadingIndicator);
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке серверов:', error);
                
                // Механизм повторных попыток
                if (retryCount < MAX_RETRIES) {
                    retryCount++;
                    console.log(`Повторная попытка загрузки (${retryCount}/${MAX_RETRIES})...`);
                    
                    if (tableBody) {
                        tableBody.innerHTML = `<tr><td colspan="8" class="text-center">Повторная попытка загрузки (${retryCount}/${MAX_RETRIES})...</td></tr>`;
                    }
                    
                    setTimeout(() => loadServers(), 2000 * retryCount); // Увеличиваем интервал с каждой попыткой
                } else {
                    showAlert('Ошибка соединения с сервером при загрузке списка серверов', 'danger');
                    showLoadingError(tableBody, loadingIndicator);
                    retryCount = 0;
                }
            });
    }
    
    /**
     * Показывает сообщение об ошибке загрузки
     */
    function showLoadingError(tableBody, loadingIndicator) {
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Ошибка загрузки данных</td></tr>';
        }
        if (loadingIndicator) {
            loadingIndicator.innerHTML = '<p class="text-danger">Ошибка загрузки данных</p>';
        }
    }
    
    /**
     * Обновляет статистику серверов на странице (локальная версия)
     */
    function updateLocalStatistics(servers) {
        console.log('Обновление статистики серверов (локальная версия)');
        
        if (!Array.isArray(servers)) {
            console.warn('Нет данных или недопустимый формат для обновления статистики');
            return;
        }
        
        // Подсчитываем статистику
        const total = servers.length;
        const active = servers.filter(s => s && s.status === 'active').length;
        const inactive = servers.filter(s => s && s.status === 'inactive').length;
        const degraded = servers.filter(s => s && s.status === 'degraded').length;
        
        // Обновляем элементы UI с полученной статистикой
        updateElementContent('totalServersCount', total);
        updateElementContent('activeServersCount', active);
        updateElementContent('inactiveServersCount', inactive);
        updateElementContent('degradedServersCount', degraded);
        
        console.log(`Статистика обновлена: всего ${total}, активных ${active}, неактивных ${inactive}, проблемных ${degraded}`);
    }
    
    /**
     * Вспомогательная функция для обновления содержимого элемента
     */
    function updateElementContent(elementId, content) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = content;
        }
    }
    
    /**
     * Фильтрует серверы по заданным критериям
     */
    function filterServers() {
        console.log('Применение фильтров к списку серверов');
        
        const searchInput = document.getElementById('serverSearch');
        const geoFilter = document.getElementById('geolocationFilter');
        const statusFilter = document.getElementById('statusFilter');
        
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
        const geoId = geoFilter ? geoFilter.value : 'all';
        const status = statusFilter ? statusFilter.value : 'all';
        
        // Проверяем, что serversData это массив
        if (!Array.isArray(serversData)) {
            console.error('serversData не является массивом');
            return;
        }
        
        // Применяем фильтры
        let filteredData = serversData.filter(server => {
            // Проверяем, что server это объект
            if (!server || typeof server !== 'object') {
                return false;
            }
            
            // Фильтр по поисковому запросу
            const matchesSearch = 
                (server.endpoint && server.endpoint.toLowerCase().includes(searchTerm)) || 
                (server.geolocation_name && server.geolocation_name.toLowerCase().includes(searchTerm)) ||
                (server.name && server.name.toLowerCase().includes(searchTerm));
            
            // Фильтр по геолокации
            const matchesGeo = geoId === 'all' || server.geolocation_id == geoId;
            
            // Фильтр по статусу
            const matchesStatus = status === 'all' || server.status === status;
            
            return matchesSearch && matchesGeo && matchesStatus;
        });
        
        // Обновляем отображение с отфильтрованными данными
        updateServersViewWithData(filteredData);
        
        console.log(`Отфильтровано ${filteredData.length} серверов из ${serversData.length}`);
    }
    
    /**
     * Устанавливает режим отображения
     */
    function setViewMode(mode) {
        console.log(`Переключение режима отображения на: ${mode}`);
        
        viewMode = mode;
        
        // Обновляем активную кнопку
        const tableBtn = document.getElementById('tableViewBtn');
        const cardBtn = document.getElementById('cardViewBtn');
        
        if (tableBtn) tableBtn.classList.toggle('active', mode === 'table');
        if (cardBtn) cardBtn.classList.toggle('active', mode === 'card');
        
        // Обновляем видимость контейнеров
        const tableContainer = document.getElementById('tableView');
        const cardContainer = document.getElementById('cardView');
        
        if (tableContainer) tableContainer.style.display = mode === 'table' ? '' : 'none';
        if (cardContainer) cardContainer.style.display = mode === 'card' ? '' : 'none';
        
        // Обновляем отображение серверов
        updateServersView();
    }
    
    /**
     * Обновляет отображение серверов на странице
     */
    function updateServersView() {
        updateServersViewWithData(serversData);
    }
    
    /**
     * Обновляет отображение серверов с указанными данными
     */
    function updateServersViewWithData(data) {
        console.log(`Обновление UI с ${Array.isArray(data) ? data.length : 0} серверами, режим: ${viewMode}`);
        
        const tableBody = document.getElementById('serversTableBody');
        const cardContainer = document.getElementById('cardView');
        
        // Скрываем индикаторы загрузки
        const loadingIndicator = document.getElementById('cardsLoadingIndicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        
        // Проверяем, есть ли данные для отображения
        if (!Array.isArray(data) || data.length === 0) {
            if (tableBody) {
                tableBody.innerHTML = '<tr><td colspan="8" class="text-center">Нет доступных серверов</td></tr>';
            }
            if (cardContainer) {
                cardContainer.innerHTML = '<div class="col-12 text-center py-5"><p>Нет доступных серверов</p></div>';
            }
            return;
        }
        
        // Отображаем серверы в зависимости от текущего режима просмотра
        if (viewMode === 'table' && tableBody) {
            renderTableView(tableBody, data);
        } else if (viewMode === 'card' && cardContainer) {
            renderCardView(cardContainer, data, showAdvanced);
        }
        
        // Добавляем обработчики событий для кнопок
        addButtonEventListeners();
    }
    
    /**
     * Добавляет обработчики событий для кнопок
     */
    function addButtonEventListeners() {
        // Обработчики для кнопок в списке серверов
        document.querySelectorAll('.view-server-btn').forEach(button => {
            button.addEventListener('click', function() {
                const serverId = this.dataset.serverId;
                if (serverId) {
                    window.location.href = `/servers/${serverId}`;
                }
            });
        });

        document.querySelectorAll('.edit-server-btn').forEach(button => {
            button.addEventListener('click', function() {
                const serverId = this.dataset.serverId;
                if (serverId) {
                    window.location.href = `/servers/edit/${serverId}`;
                }
            });
        });

        document.querySelectorAll('.delete-server-btn').forEach(button => {
            button.addEventListener('click', function() {
                const serverId = this.dataset.serverId;
                const serverName = this.dataset.serverName;
                if (serverId) {
                    openDeleteModal(serverId, serverName);
                }
            });
        });

        // Добавить обработчик для кнопки "Добавить сервер"
        const addServerBtn = document.getElementById('addServerBtn');
        if (addServerBtn) {
            addServerBtn.addEventListener('click', function() {
                window.location.href = '/servers/add';
            });
        }
    }
    
    /**
     * Открывает модальное окно подтверждения удаления
     */
    function openDeleteModal(serverId, serverName) {
        console.log(`Открытие модального окна удаления для сервера ${serverId}`);
        
        selectedServerId = serverId;
        
        const nameEl = document.getElementById('deleteServerName');
        if (nameEl) {
            nameEl.textContent = serverName || `Сервер #${serverId}`;
        }
        
        // Открываем модальное окно
        try {
            const deleteModal = new bootstrap.Modal(document.getElementById('deleteServerModal'));
            deleteModal.show();
        } catch (error) {
            console.error('Ошибка при открытии модального окна:', error);
            // Резервный вариант, если bootstrap недоступен
            const modal = document.getElementById('deleteServerModal');
            if (modal) {
                modal.style.display = 'block';
                modal.classList.add('show');
            }
        }
    }
    
    /**
     * Обрабатывает удаление сервера
     */
    function handleDeleteServer(serverId) {
        console.log(`Удаление сервера ${serverId}`);
        
        // Отключаем кнопку
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Удаление...';
        }
        
        if (typeof window.Api.deleteServer !== 'function') {
            console.error('Функция deleteServer не определена');
            showAlert('Ошибка: функция удаления не найдена', 'danger');
            
            // Восстанавливаем кнопку
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = 'Удалить сервер';
            }
            
            return;
        }
        
        window.Api.deleteServer(serverId)
            .then(result => {
                if (result.status === 'success') {
                    // Закрываем модальное окно
                    closeDeleteModal();
                    
                    // Показываем сообщение
                    showAlert('Сервер успешно удален', 'success');
                    
                    // Обновляем список серверов
                    setTimeout(() => {
                        loadServers();
                    }, 1000);
                } else {
                    showAlert(`Ошибка: ${result.message || 'Неизвестная ошибка при удалении сервера'}`, 'danger');
                    // Восстанавливаем кнопку
                    if (confirmBtn) {
                        confirmBtn.disabled = false;
                        confirmBtn.innerHTML = 'Удалить сервер';
                    }
                }
            })
            .catch(error => {
                console.error('Ошибка при удалении сервера:', error);
                showAlert('Ошибка соединения с сервером при удалении', 'danger');
                // Восстанавливаем кнопку
                if (confirmBtn) {
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = 'Удалить сервер';
                }
            });
    }
    
    /**
     * Закрывает модальное окно удаления
     */
    function closeDeleteModal() {
        try {
            const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteServerModal'));
            if (deleteModal) {
                deleteModal.hide();
            }
        } catch (error) {
            console.error('Ошибка при закрытии модального окна:', error);
            // Резервный вариант, если bootstrap недоступен
            const modal = document.getElementById('deleteServerModal');
            if (modal) {
                modal.style.display = 'none';
                modal.classList.remove('show');
            }
        }
    }
    
    /**
     * Показывает уведомление пользователю
     * @param {string} message - Текст сообщения
     * @param {string} type - Тип сообщения ('success', 'danger', 'warning', 'info')
     */
    function showAlert(message, type = 'info') {
        console.log(`Показ уведомления (${type}): ${message}`);
        
        // Проверяем наличие контейнера для уведомлений
        let alertContainer = document.getElementById('alertContainer');
        
        // Если контейнер не найден, создаем его
        if (!alertContainer) {
            console.log('Контейнер для уведомлений не найден. Создаем новый.');
            alertContainer = document.createElement('div');
            alertContainer.id = 'alertContainer';
            alertContainer.className = 'position-fixed top-0 end-0 p-3';
            alertContainer.style.zIndex = '9999';
            document.body.appendChild(alertContainer);
        }
        
        // Создаем элемент для уведомления
        const alertElement = document.createElement('div');
        alertElement.className = `alert alert-${type} alert-dismissible fade show`;
        alertElement.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Закрыть"></button>
        `;
        
        // Добавляем уведомление в контейнер
        alertContainer.appendChild(alertElement);
        
        // Настраиваем автоматическое скрытие уведомления
        setTimeout(() => {
            try {
                // Пробуем использовать Bootstrap API если доступен
                if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                    const bsAlert = new bootstrap.Alert(alertElement);
                    bsAlert.close();
                } else {
                    // Ручное удаление, если Bootstrap недоступен
                    alertElement.classList.remove('show');
                    setTimeout(() => {
                        if (alertContainer.contains(alertElement)) {
                            alertContainer.removeChild(alertElement);
                        }
                    }, 300);
                }
            } catch (error) {
                console.error('Ошибка при закрытии уведомления:', error);
                // Резервный вариант
                if (alertContainer.contains(alertElement)) {
                    alertContainer.removeChild(alertElement);
                }
            }
        }, 5000);
    }
    
    /**
     * Добавляет новый сервер
     */
    function addServer(serverData) {
        console.log('Добавление нового сервера:', serverData);
        
        // Проверяем, что у нас есть API функция
        if (!window.Api || typeof window.Api.addServer !== 'function') {
            console.error('API функция addServer не найдена');
            showAlert('Ошибка: функция добавления сервера не доступна', 'danger');
            return;
        }
        
        // Отключаем кнопку отправки, если она есть
        const submitButton = document.querySelector('#addServerModal button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Добавление...';
        }
        
        // Отправляем запрос на добавление сервера
        window.Api.addServer(serverData)
            .then(result => {
                if (result.status === 'success') {
                    showAlert('Сервер успешно добавлен', 'success');
                    
                    // Закрываем модальное окно
                    try {
                        const modal = bootstrap.Modal.getInstance(document.getElementById('addServerModal'));
                        if (modal) modal.hide();
                    } catch (e) {
                        console.error('Ошибка при закрытии модального окна:', e);
                    }
                    
                    // Обновляем список серверов
                    loadServers();
                } else {
                    showAlert(`Ошибка: ${result.message || 'Неизвестная ошибка при добавлении сервера'}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Ошибка при добавлении сервера:', error);
                showAlert('Ошибка соединения с сервером при добавлении сервера', 'danger');
            })
            .finally(() => {
                // Восстанавливаем кнопку отправки
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = 'Добавить сервер';
                }
            });
    }

    /**
     * Отображает серверы в виде таблицы
     */
    function renderTableView(tableBody, servers) {
        tableBody.innerHTML = '';
        
        if (!Array.isArray(servers)) {
            console.error('Ошибка: данные серверов не являются массивом');
            return;
        }
        
        servers.forEach(server => {
            // Проверяем, что server это объект
            if (!server || typeof server !== 'object') {
                return;
            }
            
            // Определение классов статуса
            let statusClass = 'secondary';
            let statusText = 'Неизвестно';
            
            if (server.status === 'active') {
                statusClass = 'success';
                statusText = 'Активен';
            } else if (server.status === 'inactive') {
                statusClass = 'danger';
                statusText = 'Неактивен';
            } else if (server.status === 'degraded') {
                statusClass = 'warning';
                statusText = 'Проблемы';
            }
            
            // Определение класса нагрузки
            let loadClass = 'success';
            const load = server.load || 0;
            
            if (load > 70) {
                loadClass = 'danger';
            } else if (load > 30) {
                loadClass = 'warning';
            }
            
            // Создаем строку таблицы
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${server.id || '-'}</td>
                <td>
                    <span class="status-dot status-${server.status || 'unknown'}"></span>
                    ${server.geolocation_name || 'Неизвестно'}
                </td>
                <td>${server.endpoint || '-'}:${server.port || '-'}</td>
                <td><span class="badge bg-${statusClass}">${statusText}</span></td>
                <td>${server.peers_count || 0}</td>
                <td>
                    <div class="progress">
                        <div class="progress-bar bg-${loadClass}" 
                             role="progressbar" 
                             style="width: ${load}%" 
                             aria-valuenow="${load}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                            ${load}%
                        </div>
                    </div>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-info view-server-btn" data-server-id="${server.id}" title="Подробности">
                            <i class="bi bi-info-circle"></i>
                        </button>
                        <button class="btn btn-outline-primary edit-server-btn" data-server-id="${server.id}" title="Редактировать">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger delete-server-btn" 
                                data-server-id="${server.id}" 
                                data-server-name="${server.name || `Сервер #${server.id}`}" 
                                title="Удалить">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    /**
     * Отображает серверы в виде карточек
     * @param {HTMLElement} cardContainer - Контейнер для карточек
     * @param {Array} servers - Массив серверов
     * @param {boolean} showAdvanced - Показывать ли расширенные данные
     */
    function renderCardView(cardContainer, servers, showAdvanced = false) {
        cardContainer.innerHTML = '';
        
        if (!Array.isArray(servers)) {
            console.error('Ошибка: данные серверов не являются массивом');
            return;
        }
        
        servers.forEach(server => {
            // Проверяем, что server это объект
            if (!server || typeof server !== 'object') {
                return;
            }
            
            // Определение классов статуса
            let statusClass = 'secondary';
            let statusText = 'Неизвестно';
            
            if (server.status === 'active') {
                statusClass = 'success';
                statusText = 'Активен';
            } else if (server.status === 'inactive') {
                statusClass = 'danger';
                statusText = 'Неактивен';
            } else if (server.status === 'degraded') {
                statusClass = 'warning';
                statusText = 'Проблемы';
            }
            
            // Определение класса нагрузки
            let loadClass = 'success';
            const load = server.load || 0;
            
            if (load > 70) {
                loadClass = 'danger';
            } else if (load > 30) {
                loadClass = 'warning';
            }
            
            // Создаем карточку сервера
            const cardCol = document.createElement('div');
            cardCol.className = 'col-lg-4 col-md-6 mb-4';
            
            // Основная часть карточки
            let cardContent = `
                <div class="card shadow-sm server-card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <span class="status-dot status-${server.status || 'unknown'}"></span>
                            Сервер #${server.id || '-'}
                        </h6>
                        <span class="badge bg-${statusClass}">${statusText}</span>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-muted">Геолокация:</span>
                            <span>${server.geolocation_name || 'Неизвестно'}</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-muted">Endpoint:</span>
                            <span>${server.endpoint || '-'}:${server.port || '-'}</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-muted">Пиры:</span>
                            <span>${server.peers_count || 0} / ${server.max_peers || '∞'}</span>
                        </div>
                        <div class="mb-2">
                            <span class="text-muted">Нагрузка:</span>
                            <div class="progress mt-1">
                                <div class="progress-bar bg-${loadClass}" 
                                    role="progressbar" 
                                    style="width: ${load}%" 
                                    aria-valuenow="${load}" 
                                    aria-valuemin="0" 
                                    aria-valuemax="100">
                                    ${load}%
                                </div>
                            </div>
                        </div>`;
            
            // Добавляем расширенную информацию, если включено
            if (showAdvanced) {
                cardContent += `
                        <div class="mt-3 border-top pt-2">
                            <small class="d-block mb-1"><strong>Внутренний IP:</strong> ${server.address || 'Н/Д'}</small>
                            <small class="d-block mb-1"><strong>Публичный ключ:</strong> <code>${server.public_key ? server.public_key.substring(0, 12) + '...' : 'Н/Д'}</code></small>
                        </div>`;
            }
            
            // Добавляем метрики и футер
            cardContent += `
                        <div class="server-metrics mt-3">
                            <div class="d-flex justify-content-between">
                                <small class="text-muted">Задержка: ${server.avg_latency || '-'} мс</small>
                                <small class="text-muted">Потери: ${server.avg_packet_loss || '-'}%</small>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer bg-transparent">
                        <div class="btn-group btn-group-sm w-100">
                            <button class="btn btn-outline-info view-server-btn" data-server-id="${server.id}" title="Подробности">
                                <i class="bi bi-info-circle me-1"></i> Детали
                            </button>
                            <button class="btn btn-outline-primary edit-server-btn" data-server-id="${server.id}" title="Редактировать">
                                <i class="bi bi-pencil me-1"></i> Изменить
                            </button>
                            <button class="btn btn-outline-danger delete-server-btn" 
                                    data-server-id="${server.id}" 
                                    data-server-name="${server.name || `Сервер #${server.id}`}" 
                                    title="Удалить">
                                <i class="bi bi-trash me-1"></i> Удалить
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            cardCol.innerHTML = cardContent;
            cardContainer.appendChild(cardCol);
        });
    }
});
// Обработчики событий для кнопок
// document.addEventListener('click', function(e) {
//     if (e.target.closest('.view-server-btn')) {
//         const serverId = e.target.closest('.view-server-btn').dataset.serverId;
//         viewServerDetails(serverId);
//     } else if (e.target.closest('.edit-server-btn')) {
//         const serverId = e.target.closest('.edit-server-btn').dataset.serverId;
//         editServer(serverId);
//     } else if (e.target.closest('.delete-server-btn')) {
//         const serverId = e.target.closest('.delete-server-btn').dataset.serverId;
//         const serverName = e.target.closest('.delete-server-btn').dataset.serverName;
//         deleteServer(serverId, serverName);
//     }
// });
// // Функции для обработки действий
// function viewServerDetails(serverId) {
//     // Реализация просмотра деталей сервера
//     console.log(`View server details for ID: ${serverId}`);
// }
