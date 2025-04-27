/**
 * Модуль для страницы управления геолокациями
 */
(function() {
    // Переменные для хранения данных
    let geolocationsData = [];
    let deleteGeoId = null;
    
    // Инициализация страницы
    function initPage() {
        // Загрузка данных
        loadGeolocations();
        
        // Обработчики событий
        setupEventListeners();
    }
    
    // Функция настройки обработчиков событий
    function setupEventListeners() {
        // Кнопка обновления списка геолокаций
        document.getElementById('refreshGeolocations')?.addEventListener('click', function() {
            loadGeolocations();
        });
        
        // Кнопка добавления геолокации
        document.getElementById('addGeolocationBtn')?.addEventListener('click', function() {
            addGeolocation();
        });
        
        // Кнопка обновления геолокации
        document.getElementById('updateGeolocationBtn')?.addEventListener('click', function() {
            const geoId = document.getElementById('edit_geo_id').value;
            updateGeolocation(geoId);
        });
    }
    
    // Функция загрузки списка геолокаций
    function loadGeolocations() {
        fetch('/api/geolocations')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                geolocationsData = data.geolocations;
                updateGeolocationsTable(data.geolocations);
            } else {
                window.showAlert(`Ошибка: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            window.showAlert('Ошибка соединения с сервером', 'danger');
        });
    }

    // ... остальные функции из шаблона ...

    // Выполнение инициализации при загрузке DOM
    document.addEventListener('DOMContentLoaded', initPage);
})();