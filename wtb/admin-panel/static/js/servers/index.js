/**
 * Основной JavaScript для страницы серверов
 */
document.addEventListener('DOMContentLoaded', function() {
    // Импортируем API функции
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
        document.getElementById('refreshServers')?.addEventListener('click', loadServers);
        
        // Переключение вида отображения
        document.getElementById('tableViewBtn')?.addEventListener('click', () => setViewMode('table'));
        document.getElementById('cardViewBtn')?.addEventListener('click', () => setViewMode('card'));
        
        // Поиск и фильтрация
        document.getElementById('serverSearch')?.addEventListener('input', filterServers);
        document.getElementById('geolocationFilter')?.addEventListener('change', filterServers);
        document.getElementById('statusFilter')?.addEventListener('change', filterServers);
        
        // Переключатель расширенной информации
        document.getElementById('showAdvanced')?.addEventListener('change', function() {
            showAdvanced = this.checked;
            updateServersView();
        });
        
        // Обработчик удаления сервера
        document.getElementById('confirmDeleteBtn')?.addEventListener('click', function() {
            if (selectedServerId) {
                handleDeleteServer(selectedServerId);
            }
        });
        
        // Обработчики для модального окна добавления сервера
        initServerModal();
    }
    
    /**
     * Настраивает подсказки
     */
    function setupTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
    
    /**
     * Загружает список геолокаций
     */
    function loadGeolocations() {
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
        
        fetchServers()
            .then(data => {
                if (data.status === 'success') {
                    serversData = data.servers;
                    updateStatistics(data.servers);
                    updateServersView();
                } else {
                    showAlert(`Ошибка: ${data.message}`, 'danger');
                    if (tableBody) {
                        tableBody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Ошибка загрузки данных</td></tr>';
                    }
                    if (loadingIndicator) {
                        loadingIndicator.innerHTML = '<p class="text-danger">Ошибка загрузки данных</p>';
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('Ошибка соединения с сервером', 'danger');
                if (tableBody) {
                    tableBody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Ошибка соединения с сервером</td></tr>';
                }
                if (loadingIndicator) {
                    loadingIndicator.innerHTML = '<p class="text-danger">Ошибка соединения с сервером</p>';
                }
            });
    }
    
    // Остальные функции остаются без изменений...
    
    /**
     * Показывает уведомление
     */
    function showAlert(message, type) {
        const alertsContainer = document.querySelector('.flash-messages');
        if (!alertsContainer) {
            console.error('Контейнер для уведомлений не найден');
            alert(message);
            return;
        }
        
        const alertHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertsContainer.innerHTML += alertHTML;
        
        // Автоматически скрываем уведомление через 5 секунд
        setTimeout(() => {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(alert => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);
    }
    
    // Экспортируем функции для возможного использования в других модулях
    window.ServersPage = {
        refresh: loadServers,
        filterServers,
        setViewMode,
        showAlert
    };
/**
 * Обновляет отображение серверов на странице
 */
function updateServersView() {
    const tableBody = document.getElementById('serversTableBody');
    const cardContainer = document.getElementById('cardView');
    
    // Скрываем индикаторы загрузки
    const loadingIndicator = document.getElementById('cardsLoadingIndicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
    
    // Проверяем, есть ли данные для отображения
    if (serversData.length === 0) {
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
        renderTableView(tableBody);
    } else if (viewMode === 'card' && cardContainer) {
        renderCardView(cardContainer);
    }
    
    // Добавляем обработчики событий для кнопок
    
    
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
    document.getElementById('addServerBtn')?.addEventListener('click', function() {
        window.location.href = '/servers/add';
    });
    }

/**
 * Отображает серверы в виде таблицы
 */
function renderTableView(tableBody) {
    tableBody.innerHTML = '';
    
    serversData.forEach(server => {
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
function renderCardView(cardContainer) {
    cardContainer.innerHTML = '';
    
    serversData.forEach(server => {
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
});
