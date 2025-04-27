/**
 * Модуль для работы с модальными окнами
 */
(function() {
    /**
     * Открывает модальное окно для подтверждения удаления сервера
     * @param {number|string} serverId - ID сервера
     * @param {string} serverName - Имя сервера
     */
    function openDeleteModal(serverId, serverName) {
        const nameEl = document.getElementById('deleteServerName');
        if (nameEl) {
            nameEl.textContent = serverName;
        }
        
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        if (confirmBtn) {
            confirmBtn.setAttribute('data-server-id', serverId);
        }
        
        // Открываем модальное окно
        const deleteModal = new bootstrap.Modal(document.getElementById('deleteServerModal'));
        deleteModal.show();
    }
    
    /**
     * Закрывает модальное окно по ID
     * @param {string} modalId - ID модального окна
     */
    function closeModal(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
        }
    }
    
    /**
     * Устанавливает состояние загрузки для кнопки
     * @param {HTMLElement} button - Элемент кнопки
     * @param {string} loadingText - Текст во время загрузки
     */
    function setButtonLoading(button, loadingText) {
        if (!button) return;
        
        button.disabled = true;
        button.dataset.originalHtml = button.innerHTML;
        button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${loadingText}`;
    }
    
    /**
     * Восстанавливает исходное состояние кнопки
     * @param {HTMLElement} button - Элемент кнопки
     * @param {string} text - Текст для восстановления (null для использования оригинального)
     */
    function resetButton(button, text = null) {
        if (!button) return;
        
        button.disabled = false;
        button.innerHTML = text || button.dataset.originalHtml || 'Submit';
    }
    
    // Экспортируем функции
    window.Modals = {
        open: openDeleteModal,
        close: closeModal,
        setButtonLoading,
        resetButton
    };
})();