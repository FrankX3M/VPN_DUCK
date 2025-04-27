/**
 * Основной JavaScript для страницы серверов
 */
document.addEventListener('DOMContentLoaded', function() {
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
    
    // Инициализация страницы
    initPage();
    
    /**
     * Инициализирует страницу
     */
    function initPage() {
        // Загрузка данных
        loadGeolocations();
        loadServers();
        
        // Обработчики событий
        setupEventListeners();
        
        // Инициализация подсказок
        setupTooltips();
    }
    
    /**
     * Настраивает обработчики событий
     */
    function setupEventListeners() {
        // Обновление данных
        const refreshBtn = document.getElementById('refreshServers');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', loadServers);
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
            showAdvancedCheckbox.addEventListener('change', function() {
                showAdvanced = this.checked;
                updateServersView();
            });
        }
        
        // Обработчик удаления сервера
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', function() {
                if (selectedServerId) {
                    handleDeleteServer(selectedServerId);
                }
            });
        }
    }
    
    /**
     * Настраивает подсказки
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
        if (typeof fetchGeolocations !== 'function') {
            console.error('Функция fetchGeolocations не определена');
            return;
        }
        
        fetchGeolocations()
            .then(data => {
                if (data.status === 'success') {
                    geolocationsData = data.geolocations;
                    updateGeolocationFilter(data.geolocations);
                } else {
                    showAlert(`Ошибка: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('Ошибка соединения с сервером', 'danger');
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
        geolocations.forEach(geo => {
            const option = document.createElement('option');
            option.value = geo.id;
            option.textContent = geo.name;
            filterContainer.appendChild(option);
        });
        
        // Восстанавливаем выбранное значение, если оно существует
        if (geolocations.some(geo => geo.id == selectedValue)) {
            filterContainer.value = selectedValue;
        }
    }
    
    /**
     * Загружает список серверов
     */
    function loadServers() {
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
        
        if (typeof fetchServers !== 'function') {
            console.error('Функция fetchServers не определена');
            showLoadingError(tableBody, loadingIndicator);
            return;
        }
        
        fetchServers()
            .then(data => {
                if (data.status === 'success') {
                    serversData = data.servers;
                    updateServerStatistics(data.servers);
                    updateServersView();
                } else {
                    showAlert(`Ошибка: ${data.message}`, 'danger');
                    showLoadingError(tableBody, loadingIndicator);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('Ошибка соединения с сервером', 'danger');
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
            loadingIndicator.innerHTML = '<p class="text-danger">Ошибка загрузки данных</p>';
        }
    }
    
    /**
     * Обновляет статистику серверов
     */
    function updateServerStatistics(servers) {
        // Подсчитываем основные показатели
        const totalServers = servers.length;
        const activeServers = servers.filter(s => s.status === 'active').length;
        const inactiveServers = servers.filter(s => s.status === 'inactive').length;
        const degradedServers = servers.filter(s => s.status === 'degraded').length;
        
        // Обновляем элементы статистики
        updateElementContent('totalServersCount', totalServers);
        updateElementContent('activeServersCount', activeServers);
        updateElementContent('inactiveServersCount', inactiveServers);
        updateElementContent('degradedServersCount', degradedServers);
    }
    
    /**
     * Обновляет содержимое элемента по ID
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
        const searchInput = document.getElementById('serverSearch');
        const geoFilter = document.getElementById('geolocationFilter');
        const statusFilter = document.getElementById('statusFilter');
        
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
        const geoId = geoFilter ? geoFilter.value : 'all';
        const status = statusFilter ? statusFilter.value : 'all';
        
        // Применяем фильтры
        let filteredData = serversData.filter(server => {
            // Фильтр по поисковому запросу
            const matchesSearch = 
                server.endpoint.toLowerCase().includes(searchTerm) || 
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
    }
    
    /**
     * Устанавливает режим отображения
     */
    function setViewMode(mode) {
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
        const tableBody = document.getElementById('serversTableBody');
        const cardContainer = document.getElementById('cardView');
        
        // Скрываем индикаторы загрузки
        const loadingIndicator = document.getElementById('cardsLoadingIndicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        
        // Проверяем, есть ли данные для отображения
        if (!data || data.length === 0) {
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
            renderCardView(cardContainer, data);
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
                window.location.href = `/servers/${serverId}`;
            });
        });

        document.querySelectorAll('.edit-server-btn').forEach(button => {
            button.addEventListener('click', function() {
                const serverId = this.dataset.serverId;
                window.location.href = `/servers/edit/${serverId}`;
            });
        });

        document.querySelectorAll('.delete-server-btn').forEach(button => {
            button.addEventListener('click', function() {
                const serverId = this.dataset.serverId;
                const serverName = this.dataset.serverName;
                openDeleteModal(serverId, serverName);
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
        selectedServerId = serverId;
        
        const nameEl = document.getElementById('deleteServerName');
        if (nameEl) {
            nameEl.textContent = serverName;
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
        // Отключаем кнопку
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Удаление...';
        }
        
        if (typeof deleteServer !== 'function') {
            console.error('Функция deleteServer не определена');
            showAlert('Ошибка: функция удаления не найдена', 'danger');
            return;
        }
        
        deleteServer(serverId)
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
                    showAlert(`Ошибка: ${result.message}`, 'danger');
                    // Восстанавливаем кнопку
                    if (confirmBtn) {
                        confirmBtn.disabled = false;
                        confirmBtn.innerHTML = 'Удалить сервер';
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('Ошибка соединения с сервером', 'danger');
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
     * Отображает серверы в виде таблицы
     */
    function renderTableView(tableBody, servers) {
        tableBody.innerHTML = '';
        
        servers.forEach(server => {
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
                <td>${server.id}</td>
                <td>
                    <span class="status-dot status-${server.status}"></span>
                    ${server.geolocation_name || 'Неизвестно'}
                </td>
                <td>${server.endpoint}:${server.port}</td>
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
                                data-server-name="Сервер #${server.id}" 
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
     */
    function renderCardView(cardContainer, servers) {
        cardContainer.innerHTML = '';
        
        servers.forEach(server => {
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
            cardCol.innerHTML = `
                <div class="card shadow-sm server-card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <span class="status-dot status-${server.status}"></span>
                            Сервер #${server.id}
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
                            <span>${server.endpoint}:${server.port}</span>
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
                        </div>
                        
                        ${showAdvanced ? `
                        <div class="mt-3 border-top pt-2">
                            <small class="d-block mb-1"><strong>Внутренний IP:</strong> ${server.address}</small>
                            <small class="d-block mb-1"><strong>Публичный ключ:</strong> <code>${server.public_key ? server.public_key.substring(0, 12) + '...' : 'Н/Д'}</code></small>
                        </div>
                        ` : ''}
                        
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
                                    data-server-name="Сервер #${server.id}" 
                                    title="Удалить">
                                <i class="bi bi-trash me-1"></i> Удалить
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            cardContainer.appendChild(cardCol);
        });
    }
    
    /**
     * Показывает уведомление
     */
    function showAlert(message, type) {
        // Проверяем наличие глобальной функции
        if (typeof window.showAlert === 'function') {
            window.showAlert(message, type);
            return;
        }
        
        // Ищем контейнер для уведомлений
        let alertsContainer = document.querySelector('.flash-messages');
        
        // Если контейнер не найден, создаем его
        if (!alertsContainer) {
            console.log('Создаем контейнер для уведомлений');
            alertsContainer = document.createElement('div');
            alertsContainer.className = 'flash-messages';
            alertsContainer.style.position = 'fixed';
            alertsContainer.style.top = '20px';
            alertsContainer.style.right = '20px';
            alertsContainer.style.zIndex = '1050';
            alertsContainer.style.maxWidth = '350px';
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
        
        // Автоматически скрываем уведомление через указанное время
        setTimeout(() => {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(alert => {
                try {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                } catch (e) {
                    // Если bootstrap не загружен или возникла ошибка, удаляем элемент вручную
                    alert.remove();
                }
            });
        }, 5000);
    }
    
    /**
     * Создает резервные API функции, если оригинальные не доступны
     */
    function createBackupApiFunctions() {
        return {
            fetchServers: function() {
                return fetch('/api/servers')
                    .then(response => response.json())
                    .catch(error => {
                        console.error('Error fetching servers:', error);
                        return { status: 'error', message: 'Ошибка загрузки серверов' };
                    });
            },
            fetchGeolocations: function() {
                return fetch('/api/geolocations')
                    .then(response => response.json())
                    .catch(error => {
                        console.error('Error fetching geolocations:', error);
                        return { status: 'error', message: 'Ошибка загрузки геолокаций' };
                    });
            },
            deleteServer: function(serverId) {
                return fetch(`/api/servers/${serverId}/delete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(response => response.json())
                .catch(error => {
                    console.error('Error deleting server:', error);
                    return { status: 'error', message: 'Ошибка удаления сервера' };
                });
            }
        };
    }
    
    // Экспортируем функции для возможного использования в других модулях
    window.ServersPage = {
        refresh: loadServers,
        filterServers: filterServers,
        setViewMode: setViewMode,
        showAlert: showAlert
    };
});