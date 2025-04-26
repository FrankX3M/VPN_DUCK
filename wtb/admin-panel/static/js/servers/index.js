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
});