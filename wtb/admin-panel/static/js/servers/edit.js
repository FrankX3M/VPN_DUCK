/**
 * Модуль для страницы редактирования сервера
 */
(function() {
    /**
     * Инициализация страницы
     */
    function initPage() {
        // Настройка обработчиков событий
        setupEventListeners();
    }
    
    /**
     * Настройка обработчиков событий
     */
    function setupEventListeners() {
        // Обработчик сохранения изменений
        document.getElementById('saveChangesBtn')?.addEventListener('click', saveChanges);
        
        // Обработчик удаления сервера
        document.getElementById('confirmDeleteBtn')?.addEventListener('click', function() {
            window.Modals.setButtonLoading(this, 'Удаление...');
            deleteServer();
        });
        
        // Обработчик копирования API ключа
        const apiKeyField = document.getElementById('api_key');
        if (apiKeyField) {
            apiKeyField.nextElementSibling?.addEventListener('click', function() {
                window.Utils.copyToClipboard(apiKeyField.value);
            });
        }
    }
    
    /**
     * Сохраняет изменения сервера
     */
    function saveChanges() {
        // Проверка заполнения обязательных полей
        const requiredFields = ['endpoint', 'port', 'address', 'geolocation_id'];
        let isValid = true;
        
        requiredFields.forEach(field => {
            const input = document.getElementById(field);
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
                isValid = false;
            } else {
                input.classList.remove('is-invalid');
            }
        });
        
        if (!isValid) {
            window.showAlert('Пожалуйста, заполните все обязательные поля', 'warning');
            return;
        }
        
        // Отключаем кнопку на время запроса
        const saveButton = document.getElementById('saveChangesBtn');
        window.Modals.setButtonLoading(saveButton, 'Сохранение...');
        
        // Получаем данные формы
        const serverId = document.getElementById('server_id').value;
        const formData = {
            endpoint: document.getElementById('endpoint').value.trim(),
            port: parseInt(document.getElementById('port').value),
            address: document.getElementById('address').value.trim(),
            geolocation_id: parseInt(document.getElementById('geolocation_id').value),
            status: document.getElementById('status').value,
            max_peers: parseInt(document.getElementById('max_peers').value || '0')
        };
        
        // Отправляем запрос на обновление сервера
        window.Utils.apiRequest(`/api/servers/${serverId}`, {
            method: 'PUT',
            body: formData
        })
        .then(data => {
            if (data.status === 'success') {
                // Показываем сообщение об успехе
                window.showAlert('Сервер успешно обновлен', 'success');
                
                // Перенаправляем на страницу детализации сервера через 2 секунды
                setTimeout(() => {
                    window.location.href = `/servers/${serverId}`;
                }, 2000);
            } else {
                window.showAlert(`Ошибка: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            window.showAlert('Ошибка соединения с сервером', 'danger');
        })
        .finally(() => {
            // Возвращаем кнопку в исходное состояние
            window.Modals.resetButton(saveButton, 'Сохранить изменения');
        });
    }
    
    /**
     * Удаляет сервер
     */
    function deleteServer() {
        const serverId = document.getElementById('server_id').value;
        
        window.Utils.apiRequest(`/api/servers/${serverId}/delete`, {
            method: 'POST'
        })
        .then(data => {
            if (data.status === 'success') {
                // Показываем сообщение об успехе
                window.showAlert('Сервер успешно удален', 'success');
                
                // Перенаправляем на страницу со списком серверов через 2 секунды
                setTimeout(() => {
                    window.location.href = '/servers';
                }, 2000);
            } else {
                window.showAlert(`Ошибка: ${data.message}`, 'danger');
                
                // Возвращаем кнопку в исходное состояние
                window.Modals.resetButton(document.getElementById('confirmDeleteBtn'), 'Удалить сервер');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            window.showAlert('Ошибка соединения с сервером', 'danger');
            
            // Возвращаем кнопку в исходное состояние
            window.Modals.resetButton(document.getElementById('confirmDeleteBtn'), 'Удалить сервер');
        });
    }
    
    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', initPage);
})();