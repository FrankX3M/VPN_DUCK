/**
 * Модуль с вспомогательными функциями
 */
(function() {
    console.log('Загружен модуль utils.js');
    
    // Создаем объект Utils для глобального доступа
    window.Utils = window.Utils || {};

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
        if (!text) {
            console.warn('Пустой текст для копирования');
            return Promise.resolve(false);
        }
        
        return navigator.clipboard.writeText(text)
            .then(() => {
                console.log('Текст скопирован в буфер обмена:', text.substring(0, 20) + (text.length > 20 ? '...' : ''));
                
                if (typeof window.showAlert === 'function') {
                    window.showAlert('Текст скопирован в буфер обмена', 'success');
                }
                return true;
            })
            .catch(err => {
                console.error('Не удалось скопировать текст: ', err);
                
                if (typeof window.showAlert === 'function') {
                    window.showAlert('Не удалось скопировать текст', 'danger');
                }
                return false;
            });
    }
    
    /**
     * Отправляет API запрос с обработкой ошибок
     * @param {string} url - URL для запроса
     * @param {Object} options - Опции запроса
     * @returns {Promise<Object>} Результат запроса
     */
    async function apiRequest(url, options = {}) {
        console.log(`API запрос: ${options.method || 'GET'} ${url}`);
        
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
            
            let responseData;
            try {
                responseData = await response.json();
            } catch (e) {
                console.error('Ошибка при разборе JSON ответа:', e);
                throw new Error(`Ошибка формата ответа: ${e.message}`);
            }
            
            // Проверяем статус ответа
            if (!response.ok) {
                const errorMessage = responseData.message || responseData.error || `HTTP ошибка! Статус: ${response.status}`;
                throw new Error(errorMessage);
            }
            
            return responseData;
        } catch (error) {
            console.error('API запрос завершился с ошибкой:', error);
            throw error;
        }
    }
    
    /**
     * Форматирует дату в удобный для чтения формат
     * @param {Date|string} date - Дата для форматирования
     * @returns {string} Отформатированная дата
     */
    function formatDate(date) {
        if (!date) return '';
        
        const d = new Date(date);
        if (isNaN(d.getTime())) return '';
        
        return d.toLocaleString();
    }
    
    /**
     * Форматирует размер в байтах в человекочитаемый формат
     * @param {number} bytes - Размер в байтах
     * @param {number} decimals - Количество знаков после запятой
     * @returns {string} Отформатированный размер
     */
    function formatSize(bytes, decimals = 2) {
        if (bytes === 0) return '0 Байт';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Байт', 'КБ', 'МБ', 'ГБ', 'ТБ', 'ПБ', 'ЭБ', 'ЗБ', 'ЙБ'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    /**
     * Проверяет, является ли строка валидным IP-адресом
     * @param {string} ip - Строка для проверки
     * @returns {boolean} Результат проверки
     */
    function isValidIpAddress(ip) {
        const regexPattern = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        return regexPattern.test(ip);
    }
    
    /**
     * Проверяет, является ли строка валидным URL
     * @param {string} url - Строка для проверки
     * @returns {boolean} Результат проверки
     */
    function isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch (e) {
            return false;
        }
    }
    
    // Экспортируем функции в глобальный объект Utils
    window.Utils.generateApiKey = generateApiKey;
    window.Utils.copyToClipboard = copyToClipboard;
    window.Utils.apiRequest = apiRequest;
    window.Utils.formatDate = formatDate;
    window.Utils.formatSize = formatSize;
    window.Utils.isValidIpAddress = isValidIpAddress;
    window.Utils.isValidUrl = isValidUrl;

    console.log('Модуль Utils успешно загружен');
})();