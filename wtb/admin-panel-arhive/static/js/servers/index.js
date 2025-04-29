/**
 * Основной JavaScript для страницы серверов
 */
(function() {
    console.log('Загружен модуль servers/index.js');
    
    // Глобальные переменные
    let serversData = [];
    let geolocationsData = [];
    let selectedServerId = null;
    let viewMode = 'table';  // 'table' или 'card'
    let showAdvanced = false;
    
    /**
     * Инициализация страницы
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
        
        // Добавление модального окна удаления
        ensureDeleteModalExists();
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
        
        // Добавить обработчик для кнопки "Добавить сервер"
        const addServerBtn = document.getElementById('addServerBtn');
        if (addServerBtn) {
            addServerBtn.addEventListener('click', function() {
                window.location.href = '/servers/add';
            });
        }
    }
    
    /**
     * Обеспечивает наличие модального окна удаления
     */
    function ensureDeleteModalExists() {
        if (!document.getElementById('deleteServerModal')) {
            const modalHtml = `
            <div class="modal fade" id="deleteServerModal" tabindex="-1" aria-labelledby="deleteServerModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="deleteServerModalLabel">Подтверждение удаления</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p>Вы действительно хотите удалить сервер <strong id="deleteServerName"></strong>?</p>
                            <p id="deleteServerWarning" class="text-danger">Это действие нельзя отменить. Все пиры на этом сервере будут удалены.</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                            <button type="button" class="btn btn-danger" id="confirmDeleteBtn">Удалить сервер</button>
                        </div>
                    </div>
                </div>
            </div>`;
            
            const modalDiv = document.createElement('div');
            modalDiv.innerHTML = modalHtml;
            document.body.appendChild(modalDiv.firstElementChild);
            
            // Добавляем обработчик для новой кнопки удаления
            const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
            if (confirmDeleteBtn) {
                confirmDeleteBtn.addEventListener('click', () => {
                    if (selectedServerId) {
                        handleDeleteServer(selectedServerId);
                    }
                });
            }
        }
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
        
        if (typeof window.Api === 'undefined' || typeof window.Api.fetchGeolocations !== 'function') {
            console.error('Функция fetchGeolocations не определена. Проверьте загрузку модуля API.');
            showAlert('Ошибка: API модуль не загружен корректно', 'danger');
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
        if (!filterContainer) {
            console.warn('Элемент #geolocationFilter не найден на странице');
            return;
        }
        
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
     * Загружает список серверов
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
        
        if (typeof window.Api === 'undefined' || typeof window.Api.fetchServers !== 'function') {
            console.error('Функция fetchServers не определена. Проверьте загрузку модуля API.');
            showAlert('Ошибка: API модуль не загружен корректно', 'danger');
            showLoadingError(tableBody, loadingIndicator);
            return;
        }
        
        window.Api.fetchServers()
            .then(data => {
                if (data.status === 'success') {
                    serversData = Array.isArray(data.servers) ? data.servers : [];
                    
                    // Обновляем статистику
                    updateStatistics(serversData);
                    
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
                showAlert('Ошибка соединения с сервером при загрузке серверов', 'danger');
                showLoadingError(tableBody, loadingIndicator);
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
            loadingIndicator.style.display = 'none';
            const parent = loadingIndicator.parentElement;
            if (parent) {
                parent.innerHTML = '<p class="text-danger text-center">Ошибка загрузки данных</p>';
            }
        }
    }
    
    /**
     * Обновляет статистику серверов на странице
     */
    function updateStatistics(servers) {
        console.log('Обновление статистики серверов');
        
        if (!Array.isArray(servers)) {
            console.warn('Получены некорректные данные для обновления статистики');
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
                (server.name && server.name.toLowerCase().includes(searchTerm)) ||
                (server.id && server.id.toString().includes(searchTerm));
            
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
        
        if (tableContainer) {
            tableContainer.style.display = mode === 'table' ? 'block' : 'none';
            console.log(`Видимость tableView установлена: ${tableContainer.style.display}`);
        }
        
        if (cardContainer) {
            cardContainer.style.display = mode === 'card' ? 'block' : 'none';
            console.log(`Видимость cardView установлена: ${cardContainer.style.display}`);
        }
        
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
            if (window.bootstrap && bootstrap.Modal) {
                const deleteModal = new bootstrap.Modal(document.getElementById('deleteServerModal'));
                deleteModal.show();
            } else {
                // Резервный вариант, если bootstrap недоступен
                const modal = document.getElementById('deleteServerModal');
                if (modal) {
                    modal.style.display = 'block';
                    modal.classList.add('show');
                    modal.setAttribute('aria-hidden', 'false');
                    document.body.classList.add('modal-open');
                    
                    // Добавляем backdrop
                    const backdrop = document.createElement('div');
                    backdrop.className = 'modal-backdrop fade show';
                    document.body.appendChild(backdrop);
                }
            }
        } catch (error) {
            console.error('Ошибка при открытии модального окна:', error);
            showAlert(`Ошибка при открытии модального окна: ${error.message}`, 'danger');
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
        
        if (!window.Api || typeof window.Api.deleteServer !== 'function') {
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
            if (window.bootstrap && bootstrap.Modal) {
                const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteServerModal'));
                if (deleteModal) {
                    deleteModal.hide();
                }
            } else {
                // Резервный вариант, если bootstrap недоступен
                const modal = document.getElementById('deleteServerModal');
                if (modal) {
                    modal.style.display = 'none';
                    modal.classList.remove('show');
                    modal.setAttribute('aria-hidden', 'true');
                    document.body.classList.remove('modal-open');
                    
                    // Удаляем backdrop
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.remove();
                    }
                }
            }
        } catch (error) {
            console.error('Ошибка при закрытии модального окна:', error);
        }
    }
    
    /**
     * Показывает уведомление пользователю
     * @param {string} message - Текст сообщения
     * @param {string} type - Тип сообщения ('success', 'danger', 'warning', 'info')
     */
    function showAlert(message, type = 'info') {
        console.log(`Показ уведомления (${type}): ${message}`);
        
        // Проверяем наличие глобальной функции
        if (typeof window.showAlert === 'function') {
            window.showAlert(message, type);
            return;
        }
        
        // Проверяем наличие контейнера для уведомлений
        let alertContainer = document.querySelector('.flash-messages');
        
        // Если контейнер не найден, создаем его
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.className = 'flash-messages';
            alertContainer.style.position = 'fixed';
            alertContainer.style.top = '20px';
            alertContainer.style.right = '20px';
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
                if (window.bootstrap && bootstrap.Alert) {
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
    
    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', initPage);
})();