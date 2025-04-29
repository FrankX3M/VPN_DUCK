/**
 * Модуль для страницы дашборда
 */
(function() {
    // Текущий временной диапазон для метрик
    let currentHours = 24;
    
    // Карты геолокаций и серверов
    let geolocationsMap = {};
    let serversMap = {};
    
    // Графики метрик
    let latencyChart = null;
    let packetLossChart = null;
    
    /**
     * Инициализация страницы
     */
    function initPage() {
        // Активируем кнопку "24 часа" по умолчанию
        document.querySelector('.time-selector[data-hours="24"]')?.classList.add('active');
        
        // Загрузка геолокаций
        loadGeolocations();
        
        // Загрузка данных метрик
        loadMetricsData();
        
        // Обработчики событий
        setupEventListeners();
    }
    
    /**
     * Настройка обработчиков событий
     */
    function setupEventListeners() {
        // Кнопки выбора временного периода
        document.querySelectorAll('.time-selector').forEach(button => {
            button.addEventListener('click', function() {
                // Удаляем класс active со всех кнопок
                document.querySelectorAll('.time-selector').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                // Добавляем класс active на текущую кнопку
                this.classList.add('active');
                
                // Обновляем текущий временной период
                currentHours = parseInt(this.dataset.hours);
                
                // Загружаем данные с новым временным периодом
                loadMetricsData();
            });
        });
        
        // Кнопка обновления метрик
        document.getElementById('refreshMetrics')?.addEventListener('click', function() {
            loadMetricsData();
        });
    }
    
    /**
     * Загрузка геолокаций
     */
    function loadGeolocations() {
        window.Utils.apiRequest('/api/geolocations')
            .then(data => {
                if (data.status === 'success') {
                    // Сохраняем геолокации в карту для быстрого доступа
                    data.geolocations.forEach(geo => {
                        geolocationsMap[geo.id] = geo;
                    });
                    
                    // Заполняем фильтр геолокаций
                    updateGeolocationFilter(data.geolocations);
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
     * Обновление фильтра геолокаций
     * @param {Array} geolocations - Массив геолокаций
     */
    function updateGeolocationFilter(geolocations) {
        const filterContainer = document.getElementById('geolocationFilter');
        if (!filterContainer) return;
        
        // Добавляем кнопки для каждой геолокации
        geolocations.forEach(geo => {
            const button = document.createElement('button');
            button.setAttribute('type', 'button');
            button.classList.add('btn', 'btn-sm', 'btn-outline-primary', 'geo-filter-btn');
            button.dataset.geoId = geo.id;
            button.textContent = geo.name;
            
            // Обработчик клика по кнопке фильтра
            button.addEventListener('click', function() {
                // Удаляем класс active со всех кнопок
                document.querySelectorAll('.geo-filter-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                // Добавляем класс active на текущую кнопку
                this.classList.add('active');
                
                // Фильтруем серверы по геолокации
                filterServersByGeolocation(this.dataset.geoId);
            });
            
            filterContainer.appendChild(button);
        });
        
        // Добавляем обработчик для кнопки "Все"
        document.querySelector('.geo-filter-btn[data-geo-id="all"]')?.addEventListener('click', function() {
            // Удаляем класс active со всех кнопок
            document.querySelectorAll('.geo-filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Добавляем класс active на текущую кнопку
            this.classList.add('active');
            
            // Показываем все серверы
            filterServersByGeolocation('all');
        });
    }
    
    /**
     * Фильтрация серверов по геолокации
     * @param {string} geoId - ID геолокации
     */
    function filterServersByGeolocation(geoId) {
        const cards = document.querySelectorAll('.server-metrics-card');
        
        cards.forEach(card => {
            if (geoId === 'all' || card.dataset.geoId === geoId) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    /**
     * Загрузка данных метрик
     */
    function loadMetricsData() {
        // Сначала загружаем список серверов
        window.Utils.apiRequest('/api/servers')
            .then(data => {
                if (data.status === 'success') {
                    // Сохраняем серверы в карту для быстрого доступа
                    serversMap = {};
                    data.servers.forEach(server => {
                        serversMap[server.id] = server;
                    });
                    
                    // Обновляем контейнер с метриками серверов
                    updateServerMetricsCards(data.servers);
                    
                    // Загружаем метрики для графиков
                    updateGeneralMetricsCharts(data.servers);
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
     * Обновление карточек с метриками серверов
     * @param {Array} servers - Массив серверов
     */
    function updateServerMetricsCards(servers) {
        const container = document.getElementById('serverMetricsContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (servers.length === 0) {
            container.innerHTML = '<div class="col-12 text-center py-5"><p>Нет доступных серверов</p></div>';
            return;
        }
        
        // Сортируем серверы по геолокации и статусу
        servers.sort((a, b) => {
            if (a.geolocation_id !== b.geolocation_id) {
                return a.geolocation_id - b.geolocation_id;
            }
            
            if (a.status !== b.status) {
                if (a.status === 'active') return -1;
                if (b.status === 'active') return 1;
                if (a.status === 'degraded') return -1;
                if (b.status === 'degraded') return 1;
            }
            
            return a.id - b.id;
        });
        
        // Создаем карточку для каждого сервера
        servers.forEach(server => {
            // Получаем название геолокации
            const geoName = server.geolocation_name || 'Неизвестно';
            
            // Определяем классы статуса
            let statusClass = 'secondary';
            if (server.status === 'active') statusClass = 'success';
            if (server.status === 'inactive') statusClass = 'danger';
            if (server.status === 'degraded') statusClass = 'warning';
            
            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-4';
            col.innerHTML = `
                <div class="card server-metrics-card" data-server-id="${server.id}" data-geo-id="${server.geolocation_id}">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">
                            <span class="server-status-dot server-status-${server.status}"></span>
                            Сервер #${server.id}
                        </h5>
                        <span class="badge bg-${statusClass}">${server.status}</span>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <p class="mb-1">
                                <strong>Геолокация:</strong> ${geoName}
                            </p>
                            <p class="mb-1">
                                <strong>Endpoint:</strong> ${server.endpoint}:${server.port}
                            </p>
                            <p class="mb-0">
                                <strong>Публичный ключ:</strong> 
                                <code class="small">${server.public_key ? server.public_key.substr(0, 16) + '...' : 'Н/Д'}</code>
                            </p>
                        </div>
                        <div class="metrics-chart-container">
                            <canvas id="serverChart${server.id}"></canvas>
                        </div>
                        <button class="btn btn-sm btn-primary load-metrics-btn" data-server-id="${server.id}">
                            Загрузить метрики
                        </button>
                    </div>
                </div>
            `;
            
            container.appendChild(col);
        });
        
        // Добавляем обработчики для кнопок загрузки метрик
        document.querySelectorAll('.load-metrics-btn').forEach(button => {
            button.addEventListener('click', function() {
                const serverId = this.dataset.serverId;
                window.Modals.setButtonLoading(this, 'Загрузка...');
                
                loadServerMetrics(serverId, this);
            });
        });
    }
    
    /**
     * Загрузка метрик для конкретного сервера
     * @param {number|string} serverId - ID сервера
     * @param {HTMLElement} button - Кнопка загрузки метрик
     */
    function loadServerMetrics(serverId, button) {
        window.Utils.apiRequest(`/api/server_metrics/${serverId}?hours=${currentHours}`)
            .then(data => {
                if (data.status === 'success') {
                    // Создаем график для сервера
                    createServerMetricsChart(serverId, data.metrics);
                    
                    // Обновляем кнопку
                    window.Modals.resetButton(button, 'Обновить метрики');
                } else {
                    window.showAlert(`Ошибка: ${data.message}`, 'danger');
                    window.Modals.resetButton(button, 'Ошибка загрузки');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                window.showAlert('Ошибка соединения с сервером', 'danger');
                window.Modals.resetButton(button, 'Ошибка загрузки');
            });
    }
    
    /**
     * Создание графика для сервера
     * @param {number|string} serverId - ID сервера
     * @param {Object} metricsData - Данные метрик
     */
    function createServerMetricsChart(serverId, metricsData) {
        const canvas = document.getElementById(`serverChart${serverId}`);
        if (!canvas) return;
        
        // Если уже есть график, уничтожаем его
        if (canvas.chart) {
            canvas.chart.destroy();
        }
        
        // Получаем данные истории метрик
        const history = metricsData.history || [];
        
        // Подготавливаем данные для графика
        const labels = history.map(item => {
            const date = new Date(item.hour);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + 
                   date.toLocaleDateString([], { day: '2-digit', month: '2-digit' });
        });
        
        const latencyData = history.map(item => item.avg_latency);
        const packetLossData = history.map(item => item.avg_packet_loss);
        
        // Создаем график
        const ctx = canvas.getContext('2d');
        canvas.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Задержка (мс)',
                        data: latencyData,
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderWidth: 2,
                        tension: 0.3,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Потеря пакетов (%)',
                        data: packetLossData,
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderWidth: 2,
                        tension: 0.3,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                scales: {
                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Задержка (мс)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        title: {
                            display: true,
                            text: 'Потеря пакетов (%)'
                        },
                        min: 0,
                        max: 100
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
                },
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    /**
     * Обновление общих графиков метрик
     * @param {Array} servers - Массив серверов
     */
    function updateGeneralMetricsCharts(servers) {
        // Фильтруем только активные серверы
        const activeServers = servers.filter(server => server.status === 'active');
        
        if (activeServers.length === 0) {
            return;
        }
        
        // Получаем список уникальных геолокаций
        const geoIds = [...new Set(activeServers.map(server => server.geolocation_id))];
        
        // Подготавливаем данные для графиков
        const datasets = geoIds.map(geoId => {
            const geoServers = activeServers.filter(server => server.geolocation_id === geoId);
            const geoName = geolocationsMap[geoId]?.name || `Геолокация ${geoId}`;
            
            // Вычисляем средние значения метрик для геолокации
            const avgLatency = geoServers.reduce((sum, server) => sum + (server.avg_latency || 0), 0) / geoServers.length;
            const avgPacketLoss = geoServers.reduce((sum, server) => sum + (server.avg_packet_loss || 0), 0) / geoServers.length;
            
            // Генерируем случайный цвет для геолокации
            const r = Math.floor(Math.random() * 255);
            const g = Math.floor(Math.random() * 255);
            const b = Math.floor(Math.random() * 255);
            
            return {
                geoId,
                geoName,
                avgLatency,
                avgPacketLoss,
                color: `rgba(${r}, ${g}, ${b}, 1)`,
                backgroundColor: `rgba(${r}, ${g}, ${b}, 0.2)`
            };
        });
        
        // Создаем график задержки
        createLatencyChart(datasets);
        
        // Создаем график потери пакетов
        createPacketLossChart(datasets);
    }
    
    /**
     * Создание графика задержки
     * @param {Array} datasets - Наборы данных для графика
     */
    function createLatencyChart(datasets) {
        const canvas = document.getElementById('latencyChart');
        if (!canvas) return;
        
        // Если уже есть график, уничтожаем его
        if (latencyChart) {
            latencyChart.destroy();
        }
        
        // Создаем график задержки
        const ctx = canvas.getContext('2d');
        latencyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: datasets.map(ds => ds.geoName),
                datasets: [{
                    label: 'Средняя задержка (мс)',
                    data: datasets.map(ds => ds.avgLatency),
                    backgroundColor: datasets.map(ds => ds.backgroundColor),
                    borderColor: datasets.map(ds => ds.color),
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Задержка (мс)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Задержка: ${context.raw.toFixed(2)} мс`;
                            }
                        }
                    }
                },
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    /**
     * Создание графика потери пакетов
     * @param {Array} datasets - Наборы данных для графика
     */
    function createPacketLossChart(datasets) {
        const canvas = document.getElementById('packetLossChart');
        if (!canvas) return;
        
        // Если уже есть график, уничтожаем его
        if (packetLossChart) {
            packetLossChart.destroy();
        }
        
        // Создаем график потери пакетов
        const ctx = canvas.getContext('2d');
        packetLossChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: datasets.map(ds => ds.geoName),
                datasets: [{
                    label: 'Средняя потеря пакетов (%)',
                    data: datasets.map(ds => ds.avgPacketLoss),
                    backgroundColor: datasets.map(ds => ds.backgroundColor),
                    borderColor: datasets.map(ds => ds.color),
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Потеря пакетов (%)'
                        },
                        max: 10 // Ограничиваем максимальное значение для лучшей видимости
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Потеря пакетов: ${context.raw.toFixed(2)}%`;
                            }
                        }
                    }
                },
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', initPage);
})();