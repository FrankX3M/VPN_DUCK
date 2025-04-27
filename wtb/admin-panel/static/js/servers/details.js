/**
 * Модуль для страницы детализации сервера
 */
(function() {
    // Configuration constants
    const CONFIG = {
        ALERT_TIMEOUT: 5000,
        RELOAD_DELAY: 1000,
        PEERS_LOAD_DELAY: 1000,
        API_BASE_URL: '/api/servers'
    };

    // Server data safely parsed from server-side
    let SERVER_DATA = {
        id: null,
        metrics: null
    };

    /**
     * Инициализация страницы
     */
    function initPage() {
        // Получаем ID сервера из URL
        const urlParts = window.location.pathname.split('/');
        SERVER_DATA.id = urlParts[urlParts.length - 1];
        
        // Загружаем метрики
        loadServerMetrics();
        
        // Инициализируем компоненты
        initMetricsChart();
        initPeersTable();
        initEventListeners();
    }

    /**
     * Инициализация всех обработчиков событий
     */
    function initEventListeners() {
        // Save server changes button
        const saveBtn = document.getElementById('saveServerChangesBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', updateServer);
        }
        
        // Setup delete modal triggers
        setupDeleteModalTriggers();
    }

    /**
     * Настройка триггеров для модального окна удаления
     */
    function setupDeleteModalTriggers() {
        document.querySelectorAll('[data-bs-target="#deleteServerModal"]').forEach(button => {
            button.addEventListener('click', function() {
                const serverId = this.dataset.serverId;
                const serverName = this.dataset.serverName;
                
                const nameEl = document.getElementById('deleteServerName');
                const confirmBtn = document.getElementById('confirmDeleteBtn');
                
                if (nameEl) {
                    nameEl.textContent = serverName;
                }
                
                if (confirmBtn) {
                    confirmBtn.dataset.serverId = serverId;
                    confirmBtn.addEventListener('click', function handleDelete() {
                        // Get server ID from dataset
                        const id = this.dataset.serverId;
                        
                        // Update button state
                        window.Modals.setButtonLoading(this, 'Удаление...');
                        
                        // Call delete function
                        deleteServer(id);
                        
                        // Remove event listener to prevent multiple bindings
                        this.removeEventListener('click', handleDelete);
                    });
                }
            });
        });
    }

    /**
     * Загрузка метрик сервера
     */
    function loadServerMetrics() {
        window.Utils.apiRequest(`${CONFIG.API_BASE_URL}/${SERVER_DATA.id}/metrics`)
            .then(data => {
                if (data.status === 'success') {
                    SERVER_DATA.metrics = data.metrics;
                    initMetricsChart();
                }
            })
            .catch(error => {
                console.error('Failed to load metrics:', error);
            });
    }

    /**
     * Инициализация графика метрик
     */
    function initMetricsChart() {
        const ctx = document.getElementById('serverMetricsChart');
        if (!ctx) return;
        
        const metricsData = SERVER_DATA.metrics || {};
        const history = metricsData.history || [];
        
        if (history.length === 0) {
            // If no data, display message
            ctx.style.display = 'none';
            const noDataMsg = document.createElement('p');
            noDataMsg.className = 'text-center text-muted my-5';
            noDataMsg.textContent = 'Нет данных для отображения';
            ctx.parentNode.appendChild(noDataMsg);
            return;
        }
        
        // Prepare chart data
        const chartData = prepareChartData(history);
        
        // Create chart
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: 'Задержка (мс)',
                        data: chartData.latency,
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderWidth: 2,
                        tension: 0.3,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Потеря пакетов (%)',
                        data: chartData.packetLoss,
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderWidth: 2,
                        tension: 0.3,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
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
                    legend: { position: 'top' },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
    }

    /**
     * Подготовка данных для графика из истории сервера
     * @param {Array} history - Массив точек истории
     * @return {Object} Форматированные данные для графика
     */
    function prepareChartData(history) {
        return {
            labels: history.map(item => {
                const date = new Date(item.hour);
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }),
            latency: history.map(item => item.avg_latency),
            packetLoss: history.map(item => item.avg_packet_loss)
        };
    }

    /**
     * Инициализация таблицы пиров
     */
    function initPeersTable() {
        // В реальной системе здесь будет загрузка пиров с API
        setTimeout(() => {
            const tableBody = document.getElementById('serverPeersTableBody');
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center">Нет данных о пирах</td>
                    </tr>
                `;
            }
        }, CONFIG.PEERS_LOAD_DELAY);
    }

    /**
     * Обновление информации о сервере
     */
    function updateServer() {
        // Get form data
        const formData = {
            endpoint: document.getElementById('edit_endpoint')?.value,
            port: parseInt(document.getElementById('edit_port')?.value || '0'),
            address: document.getElementById('edit_address')?.value,
            geolocation_id: parseInt(document.getElementById('edit_geolocation_id')?.value || '0'),
            status: document.getElementById('edit_status')?.value
        };
        
        // Validate required fields
        if (!formData.endpoint || !formData.port || !formData.address || !formData.geolocation_id) {
            window.showAlert('Пожалуйста, заполните все обязательные поля', 'warning');
            return;
        }
        
        // Get save button and set loading state
        const saveButton = document.getElementById('saveServerChangesBtn');
        if (!saveButton) return;
        
        window.Modals.setButtonLoading(saveButton, 'Сохранение...');
        
        // Send API request
        window.Utils.apiRequest(`${CONFIG.API_BASE_URL}/${SERVER_DATA.id}`, {
            method: 'PUT',
            body: formData
        })
        .then(result => {
            if (result.status === 'success') {
                // Close modal and show success message
                window.Modals.close('editServerModal');
                window.showAlert('Сервер успешно обновлен', 'success');
                
                // Reload page after delay
                setTimeout(() => {
                    window.location.reload();
                }, CONFIG.RELOAD_DELAY);
            } else {
                window.showAlert(`Ошибка: ${result.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            window.showAlert('Ошибка соединения с сервером', 'danger');
        })
        .finally(() => {
            // Reset button state
            window.Modals.resetButton(saveButton, 'Сохранить изменения');
        });
    }

    /**
     * Удаление сервера
     * @param {number|string} serverId - ID сервера для удаления
     */
    function deleteServer(serverId) {
        // Send delete request
        window.Utils.apiRequest(`${CONFIG.API_BASE_URL}/${serverId}/delete`, {
            method: 'POST'
        })
        .then(result => {
            if (result.status === 'success') {
                // Close modal and show success message
                window.Modals.close('deleteServerModal');
                window.showAlert('Сервер успешно удален', 'success');
                
                // Redirect to servers list after delay
                setTimeout(() => {
                    window.location.href = '/servers';
                }, CONFIG.RELOAD_DELAY);
            } else {
                window.showAlert(`Ошибка: ${result.message}`, 'danger');
                // Reset delete button
                window.Modals.resetButton(document.getElementById('confirmDeleteBtn'), 'Удалить сервер');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            window.showAlert('Ошибка соединения с сервером', 'danger');
            // Reset delete button
            window.Modals.resetButton(document.getElementById('confirmDeleteBtn'), 'Удалить сервер');
        });
    }

    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', initPage);
})();