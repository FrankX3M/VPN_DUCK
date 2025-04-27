/**
 * Модуль для отображения уведомлений
 */
(function() {
    /**
     * Показывает уведомление
     * @param {string} message - Сообщение для отображения
     * @param {string} type - Тип уведомления (success, danger, warning, info)
     * @param {number} timeout - Время в мс до автоскрытия сообщения
     */
    function showAlert(message, type, timeout = 5000) {
        // Ищем контейнер для уведомлений
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
        
        const alertHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertsContainer.innerHTML += alertHTML;
        
        // Автоматически скрываем уведомление через указанное время
        setTimeout(() => {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(alert => {
                try {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                } catch (e) {
                    // Если bootstrap не загружен или возникла ошибка, удаляем элемент вручную
                    alert.remove();
                }
            });
        }, timeout);
    }

    // Экспортируем функцию в глобальное пространство имен
    window.showAlert = showAlert;
})();