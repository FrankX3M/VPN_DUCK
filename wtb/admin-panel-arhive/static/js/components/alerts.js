/**
 * Модуль для отображения уведомлений
 */
(function() {
    console.log('Загружен модуль alerts.js');
    
    /**
     * Показывает уведомление
     * @param {string} message - Сообщение для отображения
     * @param {string} type - Тип уведомления (success, danger, warning, info)
     * @param {number} timeout - Время в мс до автоскрытия сообщения (по умолчанию 5000)
     */
    function showAlert(message, type = 'info', timeout = 5000) {
        console.log(`Отображение уведомления (${type}): ${message}`);
        
        // Пытаемся найти контейнер
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
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        
        // Добавляем HTML содержимое уведомления
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Добавляем уведомление в контейнер
        alertsContainer.appendChild(alertDiv);
        
        // Автоматически скрываем уведомление через указанное время
        setTimeout(() => {
            try {
                // Пробуем использовать Bootstrap API если доступен
                if (window.bootstrap && bootstrap.Alert) {
                    const bsAlert = new bootstrap.Alert(alertDiv);
                    bsAlert.close();
                } else {
                    // Ручное удаление, если Bootstrap недоступен
                    alertDiv.classList.remove('show');
                    setTimeout(() => {
                        if (alertsContainer.contains(alertDiv)) {
                            alertsContainer.removeChild(alertDiv);
                        }
                    }, 300);
                }
            } catch (e) {
                console.error('Ошибка при закрытии уведомления:', e);
                // Запасной вариант
                if (alertsContainer.contains(alertDiv)) {
                    alertsContainer.removeChild(alertDiv);
                }
            }
        }, timeout);
        
        return alertDiv;
    }

    // Экспортируем функцию в глобальное пространство имен
    window.showAlert = showAlert;
    
    console.log('Модуль alerts.js успешно загружен');
})();