/**
 * Модуль для главной страницы
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM загружен, инициализация главной страницы');
    
    // Глобальные переменные
    let systemData = null;
    let activityChart = null;
    
    // Проверка наличия компонентов
    checkDOMElements();
    
    // Инициализация
    initPage();
    
    /**
     * Проверка наличия ключевых DOM-элементов
     */
    function checkDOMElements() {
        console.log('Проверка наличия ключевых DOM-элементов:');
        
        const elements = [
            'totalServersCount',
            'activeServersCount',
            'activeLocationsCount',
            'averageLoadText',
            'averageLoadBar',
            'systemStatusIndicator',
            'systemStatusText',
            'refreshStatusBtn',
            'databaseServiceStatus',
            'wireguardProxyStatus',
            'metricsCollectorStatus',
            'telegramBotStatus',
            'lastUpdateTime',
            'migrateUsersBtn',
            'activityChart',
            'refreshChart',
            'view6h',
            'view24h',
            'view7d'
        ];
        
        elements.forEach(id => {
            const element = document.getElementById(id);
            console.log(`Элемент #${id}: ${element ? 'найден' : 'НЕ НАЙДЕН'}`);
        });
    }
    
    /**
     * Инициализация страницы
     */
    function initPage() {
        console.log('Инициализация главной страницы');
        
        // Загрузка данных
        loadDashboardSummary();
        
        // Обработчики событий
        setupEventListeners();
        
        // Инициализация графика
        initActivityChart();
    }
    
    /**
     * Настройка обработчиков событий
     */
    function setupEventListeners() {
        // Обновление статуса
        const refreshStatusBtn = document.getElementById('refreshStatusBtn');
        if (refreshStatusBtn) {
            refreshStatusBtn.addEventListener('click', loadDashboardSummary);
        }
        
        // Обработчик кнопки миграции пользователей
        const migrateUsersBtn = document.getElementById('migrateUsersBtn');
        if (migrateUsersBtn) {
            migrateUsersBtn.addEventListener('click', function() {
                const migrateModal = new bootstrap.Modal(document.getElementById('migrateUsersModal'));
                migrateModal.show();
            });
        }
        
        // Кнопка подтверждения миграции
        const confirmMigrateBtn = document.getElementById('confirmMigrateBtn');
        if (confirmMigrateBtn) {
            confirmMigrateBtn.addEventListener('click', migrateUsers);
        }
        
        // Обработчики фильтров графика
        document.getElementById('view6h')?.addEventListener('click', () => updateActivityChart(6));
        document.getElementById('view24h')?.addEventListener('click', () => updateActivityChart(24));
        document.getElementById('view7d')?.addEventListener('click', () => updateActivityChart(168));
        document.getElementById('refreshChart')?.addEventListener('click', () => updateActivityChart());
    }
    
    /**
     * Загрузка сводных данных для дашборда
     */
    function loadDashboardSummary() {
        console.log('Загрузка сводных данных для дашборда');
        
        // Обновляем статус кнопки
        const refreshBtn = document.getElementById('refreshStatusBtn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Обновление...';
        }
        
        fetch('/api/dashboard/summary')
            .then(response => {
                console.log('Статус ответа:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Получены данные:', data);
                
                if (data.status === 'success') {
                    systemData = data.summary;
                    updateDashboardUI(systemData);
                } else {
                    console.error('Ошибка API:', data.message);
                    window.showAlert(`Ошибка: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке данных:', error);
                window.showAlert('Ошибка соединения с сервером', 'danger');
            })
            .finally(() => {
                // Восстанавливаем кнопку
                if (refreshBtn) {
                    refreshBtn.disabled = false;
                    refreshBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Обновить статус';
                }
            });
    }
    
    /**
     * Обновление UI дашборда
     */
    function updateDashboardUI(data) {
        // Обновляем счетчики
        updateElementContent('totalServersCount', data.total_servers || 0);
        updateElementContent('activeServersCount', data.active_servers || 0);
        updateElementContent('activeLocationsCount', data.active_geolocations || 0);
        
        // Обновляем средний уровень нагрузки
        const averageLoad = Math.round(data.avg_load || 0);
        updateElementContent('averageLoadText', `${averageLoad}%`);
        
        const loadBar = document.getElementById('averageLoadBar');
        if (loadBar) {
            loadBar.style.width = `${averageLoad}%`;
            loadBar.setAttribute('aria-valuenow', averageLoad);
            
            // Определяем класс в зависимости от нагрузки
            loadBar.className = 'progress-bar';
            if (averageLoad > 80) {
                loadBar.classList.add('bg-danger');
            } else if (averageLoad > 50) {
                loadBar.classList.add('bg-warning');
            } else {
                loadBar.classList.add('bg-success');
            }
        }
        
        // Обновляем индикатор статуса системы
        const statusIndicator = document.getElementById('systemStatusIndicator');
        const statusText = document.getElementById('systemStatusText');
        
        if (statusIndicator && statusText) {
            // Определяем общий статус системы
            let statusClass = 'status-green';
            let statusMessage = 'Система работает нормально';
            
            if (data.active_servers < data.total_servers * 0.5 || data.wireguard_status !== 'running') {
                statusClass = 'status-red';
                statusMessage = 'Критические проблемы в системе';
            } else if (data.avg_packet_loss > 5 || data.degraded_servers > 0) {
                statusClass = 'status-yellow';
                statusMessage = 'Есть проблемы в работе системы';
            }
            
            // Обновляем классы и текст
            statusIndicator.className = 'status-indicator';
            statusIndicator.classList.add(statusClass);
            statusText.textContent = statusMessage;
        }
        
        // Обновляем статусы сервисов
        updateServiceStatus('databaseServiceStatus', true);
        updateServiceStatus('wireguardProxyStatus', data.wireguard_status === 'running');
        updateServiceStatus('metricsCollectorStatus', true);
        
        // Обновляем время последнего обновления
        updateElementContent('lastUpdateTime', new Date().toLocaleString());
    }
    
    /**
     * Обновляет индикатор статуса сервиса
     */
    function updateServiceStatus(elementId, isActive) {
        const element = document.getElementById(elementId);
        if (element) {
            element.className = 'badge';
            if (isActive) {
                element.classList.add('bg-success');
                element.textContent = 'Работает';
            } else {
                element.classList.add('bg-danger');
                element.textContent = 'Не работает';
            }
        }
    }
    
    /**
     * Обновляет содержимое элемента
     */
    function updateElementContent(elementId, content) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = content;
        } else {
            console.warn(`Элемент ${elementId} не найден`);
        }
    }
    
    /**
     * Инициализирует график активности
     */
    function initActivityChart() {
        const ctx = document.getElementById('activityChart');
        if (!ctx) {
            console.warn('Элемент activityChart не найден');
            return;
        }
        
        activityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Активные серверы',
                        data: [],
                        borderColor: 'rgba(78, 115, 223, 1)',
                        backgroundColor: 'rgba(78, 115, 223, 0.1)',
                        borderWidth: 2,
                        pointRadius: 3,
                        tension: 0.3
                    },
                    {
                        label: 'Задержка (мс)',
                        data: [],
                        borderColor: 'rgba(28, 200, 138, 1)',
                        backgroundColor: 'rgba(28, 200, 138, 0.1)',
                        borderWidth: 2,
                        pointRadius: 3,
                        tension: 0.3,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Кол-во серверов'
                        }
                    },
                    y1: {
                        position: 'right',
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Задержка (мс)'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
        
        // Загрузим данные для графика
        updateActivityChart(24);
    }
    
    /**
     * Обновляет данные на графике активности
     */
    function updateActivityChart(hours = 24) {
        // TODO: Реализовать получение данных активности через API
        
        // Временные данные для примера
        const labels = [];
        const activeServers = [];
        const latency = [];
        
        // Генерируем временные данные
        const now = new Date();
        for (let i = 0; i < hours; i++) {
            const time = new Date(now.getTime() - (hours - i) * 60 * 60 * 1000);
            labels.push(time.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}));
            
            // Случайные данные для демонстрации
            activeServers.push(Math.floor(Math.random() * 5) + 3);
            latency.push(Math.floor(Math.random() * 50) + 20);
        }
        
        // Обновляем данные графика
        activityChart.data.labels = labels;
        activityChart.data.datasets[0].data = activeServers;
        activityChart.data.datasets[1].data = latency;
        activityChart.update();
    }
    
    /**
     * Выполняет миграцию пользователей
     */
    function migrateUsers() {
        const confirmBtn = document.getElementById('confirmMigrateBtn');
        if (confirmBtn) {
            window.Modals.setButtonLoading(confirmBtn, 'Миграция...');
        }
        
        fetch('/api/servers/migrate_users', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                window.showAlert(`Успешно мигрировано ${data.migrated} пользователей`, 'success');
                
                // Закрываем модальное окно
                const migrateModal = bootstrap.Modal.getInstance(document.getElementById('migrateUsersModal'));
                if (migrateModal) {
                    migrateModal.hide();
                }
                
                // Обновляем данные
                setTimeout(loadDashboardSummary, 1000);
            } else {
                window.showAlert(`Ошибка: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Ошибка при миграции пользователей:', error);
            window.showAlert('Ошибка соединения с сервером', 'danger');
        })
        .finally(() => {
            // Восстанавливаем кнопку
            if (confirmBtn) {
                window.Modals.resetButton(confirmBtn, 'Начать миграцию');
            }
        });
    }
});