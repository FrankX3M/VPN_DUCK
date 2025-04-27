/**
 * Модуль для главной страницы (дашборда)
 */
(function() {
    /**
     * Инициализация страницы
     */
    function initPage() {
        // Загрузка данных при загрузке страницы
        loadDashboardData();
        
        // Настройка обработчиков событий
        setupEventListeners();
    }
    
    /**
     * Настройка обработчиков событий
     */
    function setupEventListeners() {
        // Кнопка обновления дашборда
        document.getElementById('refreshDashboard')?.addEventListener('click', function() {
            loadDashboardData();
        });
        
        // Кнопка миграции пользователей
        document.getElementById('migrateUsersBtn')?.addEventListener('click', function() {
            window.Modals.setButtonLoading(this, 'Выполняется...');
            
            window.Utils.apiRequest('/api/servers/migrate_users', {
                method: 'POST'
            })
            .then(data => {
                if (data.status === 'success') {
                    window.showAlert(`Миграция выполнена успешно. Перемещено пользователей: ${data.migrated}`, 'success');
                    loadDashboardData();
                } else {
                    window.showAlert(`Ошибка: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                window.showAlert('Ошибка соединения с сервером', 'danger');
            })
            .finally(() => {
                window.Modals.resetButton(this, '<div class="d-flex align-items-center"><i class="bi bi-arrows-move me-3 text-warning"></i><div><h6 class="mb-0">Миграция пользователей</h6><small class="text-muted">Перенос с неактивных серверов</small></div></div>');
            });
        });
        
        // Кнопка анализа метрик
        document.getElementById('analyzeMetricsBtn')?.addEventListener('click', function() {
            window.Modals.setButtonLoading(this, 'Выполняется...');
            
            window.Utils.apiRequest('/api/metrics/analyze', {
                method: 'POST'
            })
            .then(data => {
                if (data.status === 'success') {
                    window.showAlert(`Анализ метрик выполнен успешно. Обновлено серверов: ${data.updated_servers}`, 'success');
                    loadDashboardData();
                } else {
                    window.showAlert(`Ошибка: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                window.showAlert('Ошибка соединения с сервером', 'danger');
            })
            .finally(() => {
                window.Modals.resetButton(this, '<div class="d-flex align-items-center"><i class="bi bi-bar-chart me-3 text-info"></i><div><h6 class="mb-0">Анализ метрик</h6><small class="text-muted">Обновление рейтингов серверов</small></div></div>');
            });
        });
    }
    
    /**
     * Загрузка данных для дашборда
     */
/**
 * Загрузка данных для дашборда
 */
    function loadDashboardData() {
        try {
            window.Utils.apiRequest('/api/dashboard/summary')
                .then(data => {
                    if (data.status === 'success') {
                        updateDashboardStats(data.summary);
                        loadServers();
                    } else {
                        window.showAlert(`Ошибка: ${data.message || 'Неизвестная ошибка'}`, 'danger');
                    }
                })
                .catch(error => {
                    console.error('Ошибка загрузки данных дашборда:', error);
                    window.showAlert('Ошибка соединения с сервером', 'danger');
                    
                    // Очищаем индикатор загрузки, если он есть
                    const loadingIndicator = document.querySelector('.dashboard-loading');
                    if (loadingIndicator) {
                        loadingIndicator.innerHTML = '<p class="text-danger">Ошибка загрузки данных</p>';
                    }
                });
        } catch (e) {
            console.error('Критическая ошибка при загрузке дашборда:', e);
            window.showAlert('Произошла непредвиденная ошибка', 'danger');
        }
    }
    
    /**
     * Обновление статистики на дашборде
     * @param {Object} summary - Сводные данные
     */
    function updateDashboardStats(summary) {
        document.getElementById('activeServers').textContent = summary.active_servers;
        document.getElementById('totalServers').textContent = `Всего: ${summary.total_servers}`;
        
        document.getElementById('activeGeolocations').textContent = summary.active_geolocations;
        document.getElementById('totalGeolocations').textContent = `Всего: ${summary.total_geolocations}`;
        
        document.getElementById('wireguardStatus').textContent = summary.wireguard_status === 'running' ? 'Active' : 'Inactive';
        document.getElementById('peersCount').textContent = `Активные пиры: ${summary.peers_count}`;
        
        document.getElementById('avgLatency').textContent = `${summary.avg_latency} мс`;
        document.getElementById('avgPacketLoss').textContent = `Потеря пакетов: ${summary.avg_packet_loss}%`;
    }
    
    /**
     * Загрузка списка серверов
     */
    function loadServers() {
        window.Utils.apiRequest('/api/servers')
            .then(data => {
                if (data.status === 'success') {
                    updateServersTable(data.servers);
                } else {
                    window.showAlert(`Ошибка: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                window.showAlert('Ошибка соединения с сервером', 'danger');
            });
    }
    
    /**
     * Обновление таблицы серверов
     * @param {Array} servers - Массив серверов
     */
    function updateServersTable(servers) {
        const tableBody = document.getElementById('serversTable');
        if (!tableBody) return;
        
        tableBody.innerHTML = '';
        
        if (servers.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Нет доступных серверов</td></tr>';
            return;
        }
        
        servers.forEach(server => {
            let statusClass = 'secondary';
            if (server.status === 'active') statusClass = 'success';
            if (server.status === 'inactive') statusClass = 'danger';
            if (server.status === 'degraded') statusClass = 'warning';
            
            const avgLatency = server.avg_latency || '-';
            const avgPacketLoss = server.avg_packet_loss || '-';
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${server.id}</td>
                <td>${server.geolocation_name || '-'}</td>
                <td>${server.endpoint}:${server.port}</td>
                <td><span class="badge bg-${statusClass}">${server.status}</span></td>
                <td>${avgLatency} ${avgLatency !== '-' ? 'мс' : ''}</td>
                <td>${avgPacketLoss} ${avgPacketLoss !== '-' ? '%' : ''}</td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', initPage);
})();