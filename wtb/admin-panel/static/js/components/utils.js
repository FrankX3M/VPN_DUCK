/**
 * Модуль с вспомогательными функциями
 */
(function() {
    /**
     * Генерирует случайный API ключ
     * @param {number} length - Длина ключа
     * @returns {string} Сгенерированный ключ
     */
    function generateApiKey(length = 32) {
        const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        const charactersLength = characters.length;
        
        for (let i = 0; i < length; i++) {
            result += characters.charAt(Math.floor(Math.random() * charactersLength));
        }
        
        return result;
    }
    
    /**
     * Копирует текст в буфер обмена
     * @param {string} text - Текст для копирования
     * @returns {Promise<boolean>} Результат операции
     */
    function copyToClipboard(text) {
        return navigator.clipboard.writeText(text)
            .then(() => {
                window.showAlert('Текст скопирован в буфер обмена', 'success');
                return true;
            })
            .catch(err => {
                console.error('Не удалось скопировать: ', err);
                window.showAlert('Не удалось скопировать текст', 'danger');
                return false;
            });
    }
    
    /**
     * Отправляет API запрос с обработкой ошибок
    /**
     * Отправляет API запрос с обработкой ошибок
     * @param {string} url - URL для запроса
     * @param {Object} options - Опции запроса
     * @returns {Promise<Object>} Результат запроса
     */
    async function apiRequest(url, options = {}) {
        const fetchOptions = {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };
        
        if (options.body) {
            fetchOptions.body = JSON.stringify(options.body);
        }
        
        try {
            const response = await fetch(url, fetchOptions);
            
            // Проверяем статус ответа
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ошибка! Статус: ${response.status}, Текст: ${errorText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API запрос завершился с ошибкой:', error);
            throw error;
        }
    }
})();