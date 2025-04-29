document.addEventListener('DOMContentLoaded', function() {
    // Получаем ID сервера из URL
    const serverId = window.location.pathname.split('/').pop();
    let serverData = null;
    const charts = {};
    
    // Получаем ссылки на элементы DOM
    const serverNameEl = document.getElementById('server-name');
    const serverLoadingEl = document.getElementById('server-loading');
    const serverInfoEl = document.getElementById('server-info');
    const metricsLoadingEl = document.getElementById('metrics-loading');
    const currentMetricsEl = document.getElementById('current-metrics');
    const historyLoadingEl = document.getElementById('history-loading');
    const historyErrorEl = document.getElementById('history-error');
    const metricsHistoryEl = document.getElementById('metrics-history');
    const mockedDataAlertEl = document.getElementById('mocked-data-alert');
    const editServerBtn = document.getElementById('edit-server-btn');
    
    // Настройка кнопок управления
    editServerBtn.href = `/servers/edit/${serverId}`;
    
    // Загрузка данных о сервере
    loadServerData();
    
    // Настройка обработчиков событий
    setupEventHandlers();
    
    /**
     * Загрузка данных о сервере и обновление интерфейса
     */
    function loadServerData() {
        // Сброс UI в состояние загрузки
        serverNameEl.textContent = 'Загрузка данных сервера...';
        serverLoadingEl.classList.remove('d-none');
        serverInfoEl.classList.add('d-none');
        metricsLoadingEl.classList.remove('d-none');
        currentMetricsEl.classList.add('d-none');
        historyLoadingEl.classList.remove('d-none');
        metricsHistoryEl.classList.add('d-none');
        historyErrorEl.classList.add('d-none');
        mockedDataAlertEl.classList.add('d-none');
        
        // Получение информации о сервере
        fetch(`/api/servers/${serverId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                serverData = data;
                updateServerInfo(data);
                
                // Загрузка текущих метрик после получения основной информации
                return fetch(`/api/servers/${serverId}/status`);
            })
            .then(response => {
                if (!response.ok) {
                    return { status: 'unknown', error: `HTTP error! status: ${response.status}` };
                }
                return response.json();
            })
            .then(data => {
                updateMetrics(data);
                
                // Загрузка истории метрик
                loadMetricsHistory(24); // Загружаем историю за 24 часа по умолчанию
            })
            .catch(error => {
                console.error('Error loading server data:', error);
                showAlert('error', 'Ошибка при загрузке данных сервера', error.message);
                
                // В случае ошибки показываем карточку с основной информацией
                serverLoadingEl.classList.add('d-none');
                serverInfoEl.classList.remove('d-none');
                metricsLoadingEl.classList.add('d-none');
                currentMetricsEl.classList.remove('d-none');
                historyLoadingEl.classList.add('d-none');
                historyErrorEl.classList.remove('d-none');
            });
    }
    
    /**
     * Обновление информации о сервере
     */
    function updateServerInfo(data) {
        // Обновление названия сервера
        serverNameEl.textContent = data.name || `Сервер ${data.id}`;
        
        // Обновление основной информации
        document.getElementById('server-id').textContent = data.id;
        document.getElementById('server-location').textContent = data.location || 'Не указано';
        document.getElementById('server-endpoint').textContent = data.endpoint || data.api_url || 'Не указано';
        document.getElementById('server-auth-type').textContent = data.auth_type || 'Не указано';
        
        // Форматирование дат
        const addedDate = data.created_at ? new Date(data.created_at) : null;
        document.getElementById('server-added-date').textContent = addedDate ? addedDate.toLocaleString() : 'Не указано';
        
        // Обновление ссылок и кнопок
        document.getElementById('edit-server-btn').href = `/servers/edit/${data.id}`;
        document.getElementById('restart-server-name').textContent = data.name || `Сервер ${data.id}`;
        document.getElementById('delete-server-name').textContent = data.name || `Сервер ${data.id}`;
        
        // Показываем информацию о сервере
        serverLoadingEl.classList.add('d-none');
        serverInfoEl.classList.remove('d-none');
    }
    
    /**
     * Обновление метрик сервера
     */
    function updateMetrics(data) {
        // Проверка наличия флага мокированных данных
        if (data.mocked) {
            mockedDataAlertEl.classList.remove('d-none');
        } else {
            mockedDataAlertEl.classList.add('d-none');
        }
        
        // Обновление статуса
        const statusEl = document.getElementById('server-status');
        const statusDot = statusEl.querySelector('.status-dot');
        
        statusDot.className = 'status-dot';
        
        switch (data.status) {
            case 'active':
            case 'online':
                statusDot.classList.add('status-active');
                statusEl.innerHTML = statusDot.outerHTML + 'Активен';
                break;
            case 'inactive':
            case 'offline':
                statusDot.classList.add('status-inactive');
                statusEl.innerHTML = statusDot.outerHTML + 'Неактивен';
                break;
            case 'degraded':
                statusDot.classList.add('status-degraded');
                statusEl.innerHTML = statusDot.outerHTML + 'Ограниченная работа';
                if (data.mocked) {
                    statusEl.innerHTML += '<span class="mocked-data-indicator">Симуляция</span>';
                }
                break;
            default:
                statusDot.classList.add('status-unknown');
                statusEl.innerHTML = statusDot.outerHTML + 'Неизвестно';
        }
        
        // Обновление основных метрик
        document.getElementById('peers-count').textContent = data.peers_count || 0;
        document.getElementById('server-load').textContent = (data.load || 0) + '%';
        
        // Обновление CPU
        const cpuUsage = data.cpu_usage || 0;
        document.getElementById('cpu-usage').textContent = cpuUsage + '%';
        const cpuBar = document.getElementById('cpu-usage-bar');
        cpuBar.style.width = cpuUsage + '%';
        if (cpuUsage > 80) {
            cpuBar.className = 'progress-bar bg-danger';
        } else if (cpuUsage > 50) {
            cpuBar.className = 'progress-bar bg-warning';
        } else {
            cpuBar.className = 'progress-bar bg-primary';
        }
        
        // Обновление памяти
        const memoryUsage = data.memory_usage || 0;
        document.getElementById('memory-usage').textContent = memoryUsage + '%';
        const memoryBar = document.getElementById('memory-usage-bar');
        memoryBar.style.width = memoryUsage + '%';
        if (memoryUsage > 80) {
            memoryBar.className = 'progress-bar bg-danger';
        } else if (memoryUsage > 50) {
            memoryBar.className = 'progress-bar bg-warning';
        } else {
            memoryBar.className = 'progress-bar bg-success';
        }
        
        // Обновление потери пакетов
        const packetLoss = data.packet_loss || 0;
        document.getElementById('packet-loss').textContent = packetLoss + '%';
        const packetLossBar = document.getElementById('packet-loss-bar');
        packetLossBar.style.width = packetLoss + '%';
        if (packetLoss > 10) {
            packetLossBar.className = 'progress-bar bg-danger';
        } else if (packetLoss > 5) {
            packetLossBar.className = 'progress-bar bg-warning';
        } else {
            packetLossBar.className = 'progress-bar bg-success';
        }
        
        // Обновление времени работы
        const uptime = data.uptime || 0;
        document.getElementById('uptime').textContent = formatUptime(uptime);
        
        // Обновление задержки
        document.getElementById('latency').textContent = (data.latency_ms || 0) + ' мс';
        
        // Обновление версии WireGuard
        document.getElementById('wg-version').textContent = data.version || 'Н/Д';
        
        // Обновление времени последней проверки
        const lastCheck = data.last_check ? new Date(data.last_check) : null;
        document.getElementById('server-last-check').textContent = lastCheck ? lastCheck.toLocaleString() : 'Не указано';
        document.getElementById('last-update').textContent = lastCheck ? lastCheck.toLocaleString() : 'Не указано';
        
        // Показываем информацию о метриках
        metricsLoadingEl.classList.add('d-none');
        currentMetricsEl.classList.remove('d-none');
    }
    
    /**
     * Загрузка истории метрик
     */
    function loadMetricsHistory(hours) {
        // Показываем индикатор загрузки
        historyLoadingEl.classList.remove('d-none');
        metricsHistoryEl.classList.add('d-none');
        historyErrorEl.classList.add('d-none');
        
        // Запрос данных истории метрик
        fetch(`/api/servers/${serverId}/metrics?hours=${hours}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.metrics && data.metrics.length > 0) {
                    updateMetricsCharts(data.metrics);
                    
                    // Показываем графики
                    historyLoadingEl.classList.add('d-none');
                    metricsHistoryEl.classList.remove('d-none');
                } else {
                    // Если нет данных метрик
                    historyLoadingEl.classList.add('d-none');
                    historyErrorEl.classList.remove('d-none');
                }
            })
            .catch(error => {
                console.error('Error loading metrics history:', error);
                
                // Показываем ошибку
                historyLoadingEl.classList.add('d-none');
                historyErrorEl.classList.remove('d-none');
            });
    }
    
    /**
     * Обновление графиков метрик
     */
    function updateMetricsCharts(metricsData) {
        // Подготовка данных для графиков
        const timestamps = metricsData.map(item => new Date(item.timestamp));
        const peersData = metricsData.map(item => item.peers_count || 0);
        const loadData = metricsData.map(item => item.load || 0);
        const cpuData = metricsData.map(item => item.cpu_usage || 0);
        const memoryData = metricsData.map(item => item.memory_usage || 0);
        const latencyData = metricsData.map(item => item.latency_ms || 0);
        const packetLossData = metricsData.map(item => item.packet_loss || 0);
        
        // Уничтожаем существующие графики перед созданием новых
        Object.values(charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        
        // Создание графика пиров
        charts.peersChart = new Chart(document.getElementById('peers-chart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Количество пиров',
                    data: peersData,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            tooltipFormat: 'dd.MM.yyyy HH:mm'
                        },
                        title: {
                            display: true,
                            text: 'Время'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Пиры'
                        }
                    }
                }
            }
        });
        
        // Создание графика нагрузки
        charts.loadChart = new Chart(document.getElementById('load-chart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Нагрузка (%)',
                    data: loadData,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            tooltipFormat: 'dd.MM.yyyy HH:mm'
                        },
                        title: {
                            display: true,
                            text: 'Время'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Нагрузка (%)'
                        }
                    }
                }
            }
        });
        
        // Создание графика ресурсов (CPU и память)
        charts.resourcesChart = new Chart(document.getElementById('resources-chart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'CPU (%)',
                    data: cpuData,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1,
                    fill: false
                }, {
                    label: 'Память (%)',
                    data: memoryData,
                    borderColor: 'rgba(153, 102, 255, 1)',
                    backgroundColor: 'rgba(153, 102, 255, 0.2)',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            tooltipFormat: 'dd.MM.yyyy HH:mm'
                        },
                        title: {
                            display: true,
                            text: 'Время'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Использование (%)'
                        }
                    }
                }
            }
        });
        
        // Создание графика задержки и потери пакетов
        charts.latencyChart = new Chart(document.getElementById('latency-chart'), {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Задержка (мс)',
                    data: latencyData,
                    borderColor: 'rgba(255, 159, 64, 1)',
                    backgroundColor: 'rgba(255, 159, 64, 0.2)',
                    tension: 0.1,
                    fill: false,
                    yAxisID: 'y'
                }, {
                    label: 'Потеря пакетов (%)',
                    data: packetLossData,
                    borderColor: 'rgba(255, 206, 86, 1)',
                    backgroundColor: 'rgba(255, 206, 86, 0.2)',
                    tension: 0.1,
                    fill: false,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            tooltipFormat: 'dd.MM.yyyy HH:mm'
                        },
                        title: {
                            display: true,
                            text: 'Время'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Задержка (мс)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            drawOnChartArea: false
                        },
                        title: {
                            display: true,
                            text: 'Потеря пакетов (%)'
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Настройка обработчиков событий
     */
    function setupEventHandlers() {
        // Обработчик для кнопки обновления
        document.getElementById('refresh-btn').addEventListener('click', function() {
            loadServerData();
            showAlert('success', 'Данные обновлены', 'Информация о сервере успешно обновлена.');
        });
        
        // Обработчик для кнопки проверки соединения
        document.getElementById('test-connection-btn').addEventListener('click', function() {
            testServerConnection();
        });
        
        // Обработчик для кнопки перезапуска сервера
        document.getElementById('restart-server-btn').addEventListener('click', function() {
            $('#restart-confirm-modal').modal('show');
        });
        
        // Обработчик для кнопки подтверждения перезапуска
        document.getElementById('confirm-restart-btn').addEventListener('click', function() {
            restartServer();
        });
        
        // Обработчик для кнопки удаления сервера
        document.getElementById('delete-server-btn').addEventListener('click', function() {
            $('#delete-confirm-modal').modal('show');
        });
        
        // Обработчики для поля подтверждения удаления
        document.getElementById('delete-confirm-input').addEventListener('input', function() {
            const confirmBtn = document.getElementById('confirm-delete-btn');
            confirmBtn.disabled = this.value !== 'УДАЛИТЬ';
        });
        
        // Обработчик для кнопки подтверждения удаления
        document.getElementById('confirm-delete-btn').addEventListener('click', function() {
            deleteServer();
        });
        
        // Обработчики для фильтров времени
        document.querySelectorAll('.time-filter').forEach(button => {
            button.addEventListener('click', function() {
                // Удаляем класс active со всех кнопок
                document.querySelectorAll('.time-filter').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                // Добавляем класс active текущей кнопке
                this.classList.add('active');
                
                // Загружаем историю метрик за выбранный период
                const hours = this.getAttribute('data-hours');
                loadMetricsHistory(hours);
            });
        });
    }
    
    /**
     * Проверка соединения с сервером
     */
    function testServerConnection() {
        showAlert('info', 'Проверка соединения', 'Проверка соединения с сервером...');
        
        fetch(`/api/servers/${serverId}/ping`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showAlert('success', 'Соединение установлено', `Сервер доступен. Задержка: ${data.latency_ms} мс`);
                } else {
                    showAlert('error', 'Ошибка соединения', data.message || 'Сервер недоступен');
                }
            })
            .catch(error => {
                console.error('Error testing connection:', error);
                showAlert('error', 'Ошибка проверки соединения', error.message);
            });
    }
    
    /**
     * Перезапуск сервера
     */
    function restartServer() {
        showAlert('info', 'Перезапуск сервера', 'Отправка запроса на перезапуск сервера...');
        
        fetch(`/api/servers/${serverId}/restart`, {
            method: 'POST'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showAlert('success', 'Сервер перезапущен', 'Сервер успешно перезапущен. Обновление данных...');
                    
                    // Закрываем модальное окно
                    $('#restart-confirm-modal').modal('hide');
                    
                    // Ждем немного перед обновлением данных
                    setTimeout(() => {
                        loadServerData();
                    }, 3000);
                } else {
                    showAlert('error', 'Ошибка перезапуска', data.message || 'Не удалось перезапустить сервер');
                    $('#restart-confirm-modal').modal('hide');
                }
            })
            .catch(error => {
                console.error('Error restarting server:', error);
                showAlert('error', 'Ошибка перезапуска', error.message);
                $('#restart-confirm-modal').modal('hide');
            });
    }
    
    /**
     * Удаление сервера
     */
    function deleteServer() {
        showAlert('info', 'Удаление сервера', 'Отправка запроса на удаление сервера...');
        
        fetch(`/api/servers/${serverId}`, {
            method: 'DELETE'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showAlert('success', 'Сервер удален', 'Сервер успешно удален. Перенаправление на список серверов...');
                    
                    // Закрываем модальное окно
                    $('#delete-confirm-modal').modal('hide');
                    
                    // Перенаправляем на список серверов
                    setTimeout(() => {
                        window.location.href = '/servers';
                    }, 2000);
                } else {
                    showAlert('error', 'Ошибка удаления', data.message || 'Не удалось удалить сервер');
                    $('#delete-confirm-modal').modal('hide');
                }
            })
            .catch(error => {
                console.error('Error deleting server:', error);
                showAlert('error', 'Ошибка удаления', error.message);
                $('#delete-confirm-modal').modal('hide');
            });
    }
    
    /**
     * Форматирование времени работы
     */
    function formatUptime(seconds) {
        if (!seconds || seconds <= 0) {
            return 'Н/Д';
        }
        
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        let result = '';
        if (days > 0) {
            result += `${days} д. `;
        }
        
        if (hours > 0 || days > 0) {
            result += `${hours} ч. `;
        }
        
        result += `${minutes} мин.`;
        
        return result;
    }
    
    /**
     * Отображение уведомления
     */
    function showAlert(type, title, message) {
        // Создаем элемент уведомления
        const alertElement = document.createElement('div');
        alertElement.className = `alert alert-${type} alert-dismissible fade show`;
        alertElement.role = 'alert';
        
        // Добавляем содержимое уведомления
        alertElement.innerHTML = `
            <strong>${title}</strong> ${message}
            <button type="button" class="close" data-dismiss="alert" aria-label="Закрыть">
                <span aria-hidden="true">&times;</span>
            </button>
        `;
        
        // Добавляем уведомление в контейнер
        const flashMessagesContainer = document.querySelector('.flash-messages');
        flashMessagesContainer.appendChild(alertElement);
        
        // Автоматически удаляем уведомление через 5 секунд
        setTimeout(() => {
            alertElement.classList.remove('show');
            setTimeout(() => {
                alertElement.remove();
            }, 300);
        }, 5000);
    }
});