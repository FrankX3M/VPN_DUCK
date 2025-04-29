/**
 * Модуль для работы с модальными окнами
 */
(function() {
    console.log('Загружен модуль modals.js');
    
    /**
     * Открывает модальное окно для подтверждения удаления сервера
     * @param {number|string} serverId - ID сервера
     * @param {string} serverName - Имя сервера
     */
    function openDeleteModal(serverId, serverName) {
        console.log(`Открытие модального окна удаления для сервера ${serverId}`);
        
        const nameEl = document.getElementById('deleteServerName');
        if (nameEl) {
            nameEl.textContent = serverName || `Сервер #${serverId}`;
        }
        
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        if (confirmBtn) {
            confirmBtn.setAttribute('data-server-id', serverId);
        }
        
        // Открываем модальное окно
        try {
            if (window.bootstrap && bootstrap.Modal) {
                const deleteModal = new bootstrap.Modal(document.getElementById('deleteServerModal'));
                deleteModal.show();
            } else {
                // Резервный вариант, если bootstrap недоступен
                const modal = document.getElementById('deleteServerModal');
                if (modal) {
                    modal.style.display = 'block';
                    modal.classList.add('show');
                    modal.setAttribute('aria-hidden', 'false');
                    document.body.classList.add('modal-open');
                    
                    // Добавляем backdrop
                    const backdrop = document.createElement('div');
                    backdrop.className = 'modal-backdrop fade show';
                    document.body.appendChild(backdrop);
                }
            }
        } catch (error) {
            console.error('Ошибка при открытии модального окна:', error);
        }
    }
    
    /**
     * Закрывает модальное окно по ID
     * @param {string} modalId - ID модального окна
     */
    function closeModal(modalId) {
        console.log(`Закрытие модального окна ${modalId}`);
        
        try {
            const modalElement = document.getElementById(modalId);
            if (modalElement) {
                if (window.bootstrap && bootstrap.Modal) {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) {
                        modal.hide();
                    }
                } else {
                    // Резервный вариант, если bootstrap недоступен
                    modalElement.style.display = 'none';
                    modalElement.classList.remove('show');
                    modalElement.setAttribute('aria-hidden', 'true');
                    document.body.classList.remove('modal-open');
                    
                    // Удаляем backdrop
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.remove();
                    }
                }
            }
        } catch (error) {
            console.error(`Ошибка при закрытии модального окна ${modalId}:`, error);
        }
    }
    
    /**
     * Устанавливает состояние загрузки для кнопки
     * @param {HTMLElement} button - Элемент кнопки
     * @param {string} loadingText - Текст во время загрузки
     */
    function setButtonLoading(button, loadingText) {
        if (!button) {
            console.warn('Кнопка не определена для setButtonLoading');
            return;
        }
        
        // Сохраняем исходный HTML
        if (!button.dataset.originalHtml) {
            button.dataset.originalHtml = button.innerHTML;
        }
        
        // Обновляем кнопку
        button.disabled = true;
        button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${loadingText}`;
    }
    
    /**
     * Восстанавливает исходное состояние кнопки
     * @param {HTMLElement} button - Элемент кнопки
     * @param {string} text - Текст для восстановления (null для использования оригинального)
     */
    function resetButton(button, text = null) {
        if (!button) {
            console.warn('Кнопка не определена для resetButton');
            return;
        }
        
        button.disabled = false;
        button.innerHTML = text || button.dataset.originalHtml || 'Отправить';
    }
    
    /**
     * Инициализирует действия с модальными окнами
     */
    function initModalActions() {
        // Инициализация автоматического сброса формы при закрытии модального окна
        document.addEventListener('hidden.bs.modal', function (event) {
            const modal = event.target;
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
            }
        });
        
        // Инициализация обработчиков кнопок закрытия
        document.querySelectorAll('[data-bs-dismiss="modal"]').forEach(button => {
            button.addEventListener('click', function () {
                const modalId = this.closest('.modal').id;
                closeModal(modalId);
            });
        });
    }
    
    // Экспортируем функции
    window.Modals = {
        open: openDeleteModal,
        close: closeModal,
        setButtonLoading,
        resetButton,
        init: initModalActions
    };
    
    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', initModalActions);
    
    console.log('Модуль modals.js успешно загружен');
})();