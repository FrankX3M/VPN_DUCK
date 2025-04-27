/**
 * Модуль для страницы добавления нового сервера
 */
(function() {
    /**
     * Инициализация страницы
     */
    function initPage() {
        // Генерируем начальный API ключ
        generateApiKey();
        
        // Обработчики событий
        setupEventListeners();
    }
    
    /**
     * Настройка обработчиков событий
     */
    function setupEventListeners() {
        // Обработчик отправки формы
        document.getElementById('addServerForm')?.addEventListener('submit', handleFormSubmit);
        
        // Обработчик кнопки генерации API ключа
        document.getElementById('generateApiKeyBtn')?.addEventListener('click', generateApiKey);
        
        // Обработчик кнопки копирования API ключа
        document.getElementById('copyApiKeyBtn')?.addEventListener('click', copyApiKey);
    }
    
    /**
     * Обработчик отправки формы
     * @param {Event} event - Событие отправки формы
     */
    function handleFormSubmit(event) {
        event.preventDefault();
        
        // Проверка заполнения обязательных полей
        const requiredFields = ['endpoint', 'port', 'address', 'public_key', 'geolocation_id'];
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
        
        // Подготовка данных для отправки
        const formData = {
            endpoint: document.getElementById('endpoint').value.trim(),
            port: parseInt(document.getElementById('port').value),
            address: document.getElementById('address').value.trim(),
            public_key: document.getElementById('public_key').value.trim(),
            geolocation_id: parseInt(document.getElementById('geolocation_id').value),
            api_key: document.getElementById('api_key').value,
            max_peers: parseInt(document.getElementById('max_peers').value || '0'),
            active: document.getElementById('active').checked
        };
        
        // Отключаем кнопку отправки
        const submitBtn = event.submitter || document.querySelector('button[type="submit"]');
        if (submitBtn) {
            window.Modals.setButtonLoading(submitBtn, 'Добавление...');
        }
        
        // Отправка данных на сервер
        window.Utils.apiRequest('/api/servers', {
            method: 'POST',
            body: formData
        })
        .then(data => {
            if (data.status === 'success') {
                // Показываем сообщение об успехе
                window.showAlert('Сервер успешно добавлен!', 'success');
                
                // Перенаправляем на страницу со списком серверов через 2 секунды
                setTimeout(() => {
                    window.location.href = '/servers';
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
            if (submitBtn) {
                window.Modals.resetButton(submitBtn, 'Добавить сервер');
            }
        });
    }
    
    /**
     * Генерирует новый API ключ
     */
    function generateApiKey() {
        const apiKey = window.Utils.generateApiKey();
        document.getElementById('api_key').value = apiKey;
        document.getElementById('api_key_display').value = apiKey;
    }
    
    /**
     * Копирует API ключ в буфер обмена
     */
    function copyApiKey() {
        const apiKeyDisplay = document.getElementById('api_key_display');
        
        window.Utils.copyToClipboard(apiKeyDisplay.value)
            .then(success => {
                if (success) {
                    // Показываем индикатор копирования
                    const copyBtn = document.getElementById('copyApiKeyBtn');
                    const originalText = copyBtn.innerHTML;
                    copyBtn.innerHTML = '<i class="bi bi-check"></i> Скопировано';
                    
                    setTimeout(() => {
                        copyBtn.innerHTML = originalText;
                    }, 2000);
                }
            });
    }
    
    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', initPage);
})();