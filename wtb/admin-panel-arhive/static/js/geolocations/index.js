/**
 * Модуль для страницы управления геолокациями
 */
(function() {
    console.log('Загружен модуль geolocations/index.js');
    
    // Глобальные переменные
    let geolocationsData = [];
    let selectedGeoId = null;
    
    /**
     * Инициализация страницы
     */
    function initPage() {
        console.log('Инициализация страницы геолокаций');
        
        // Проверяем наличие API модуля
        if (!window.Api || !window.Utils) {
            console.error('API модуль или модуль Utils не загружен. Проверьте порядок загрузки скриптов.');
            showAlert('Ошибка: требуемые модули не загружены', 'danger');
            return;
        }
        
        // Загрузка данных
        loadGeolocations();
        
        // Обработчики событий
        setupEventListeners();
        
        // Инициализация модальных окон
        ensureGeolocationModalsExist();
    }
    
    /**
     * Настраивает обработчики событий
     */
    function setupEventListeners() {
        console.log('Настройка обработчиков событий');
        
        // Обновление данных
        const refreshBtn = document.getElementById('refreshGeolocations');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', loadGeolocations);
        }
        
        // Обработчик кнопки добавления геолокации
        const addBtn = document.getElementById('addGeolocationBtn');
        if (addBtn) {
            addBtn.addEventListener('click', showAddGeolocationModal);
        }
        
        // Обработчик сохранения новой геолокации
        const saveNewGeoBtn = document.getElementById('saveNewGeolocationBtn');
        if (saveNewGeoBtn) {
            saveNewGeoBtn.addEventListener('click', handleAddGeolocation);
        }
        
        // Обработчик сохранения изменений в геолокации
        const saveEditGeoBtn = document.getElementById('saveGeolocationChangesBtn');
        if (saveEditGeoBtn) {
            saveEditGeoBtn.addEventListener('click', handleUpdateGeolocation);
        }
        
        // Обработчик удаления геолокации
        const confirmDeleteBtn = document.getElementById('confirmDeleteGeoBtn');
        if (confirmDeleteBtn) {
            confirmDeleteBtn.addEventListener('click', handleDeleteGeolocation);
        }
    }
    
    /**
     * Обеспечивает наличие необходимых модальных окон
     */
    function ensureGeolocationModalsExist() {
        // Модальное окно добавления геолокации
        if (!document.getElementById('addGeolocationModal')) {
            createAddGeolocationModal();
        }
        
        // Модальное окно редактирования геолокации
        if (!document.getElementById('editGeolocationModal')) {
            createEditGeolocationModal();
        }
        
        // Модальное окно удаления геолокации
        if (!document.getElementById('deleteGeolocationModal')) {
            createDeleteGeolocationModal();
        }
    }
    
    /**
     * Создает модальное окно добавления геолокации
     */
    function createAddGeolocationModal() {
        const modalHtml = `
        <div class="modal fade" id="addGeolocationModal" tabindex="-1" aria-labelledby="addGeolocationModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="addGeolocationModalLabel">Добавление геолокации</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addGeolocationForm">
                            <div class="mb-3">
                                <label for="new_code" class="form-label">Код</label>
                                <input type="text" class="form-control" id="new_code" required>
                                <div class="form-text">Например: ru, us, de (2-3 символа)</div>
                            </div>
                            <div class="mb-3">
                                <label for="new_name" class="form-label">Название</label>
                                <input type="text" class="form-control" id="new_name" required>
                                <div class="form-text">Название геолокации</div>
                            </div>
                            <div class="mb-3 form-check">
                                <input type="checkbox" class="form-check-input" id="new_available" checked>
                                <label class="form-check-label" for="new_available">Доступна</label>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button type="button" class="btn btn-primary" id="saveNewGeolocationBtn">Добавить</button>
                    </div>
                </div>
            </div>
        </div>`;
        
        const modalDiv = document.createElement('div');
        modalDiv.innerHTML = modalHtml;
        document.body.appendChild(modalDiv.firstElementChild);
        
        // Добавляем обработчик для кнопки сохранения
        document.getElementById('saveNewGeolocationBtn').addEventListener('click', handleAddGeolocation);
    }
    
    /**
     * Создает модальное окно редактирования геолокации
     */
    function createEditGeolocationModal() {
        const modalHtml = `
        <div class="modal fade" id="editGeolocationModal" tabindex="-1" aria-labelledby="editGeolocationModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="editGeolocationModalLabel">Редактирование геолокации</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editGeolocationForm">
                            <input type="hidden" id="edit_geo_id">
                            <div class="mb-3">
                                <label for="edit_code" class="form-label">Код</label>
                                <input type="text" class="form-control" id="edit_code" required>
                                <div class="form-text">Например: ru, us, de (2-3 символа)</div>
                            </div>
                            <div class="mb-3">
                                <label for="edit_name" class="form-label">Название</label>
                                <input type="text" class="form-control" id="edit_name" required>
                                <div class="form-text">Название геолокации</div>
                            </div>
                            <div class="mb-3 form-check">
                                <input type="checkbox" class="form-check-input" id="edit_available">
                                <label class="form-check-label" for="edit_available">Доступна</label>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button type="button" class="btn btn-primary" id="saveGeolocationChangesBtn">Сохранить</button>
                    </div>
                </div>
            </div>
        </div>`;
        
        const modalDiv = document.createElement('div');
        modalDiv.innerHTML = modalHtml;
        document.body.appendChild(modalDiv.firstElementChild);
        
        // Добавляем обработчик для кнопки сохранения
        document.getElementById('saveGeolocationChangesBtn').addEventListener('click', handleUpdateGeolocation);
    }
    
    /**
     * Создает модальное окно удаления геолокации
     */
    function createDeleteGeolocationModal() {
        const modalHtml = `
        <div class="modal fade" id="deleteGeolocationModal" tabindex="-1" aria-labelledby="deleteGeolocationModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="deleteGeolocationModalLabel">Подтверждение удаления</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p>Вы действительно хотите удалить геолокацию <strong id="deleteGeoName"></strong>?</p>
                        <p id="deleteGeoWarning" class="text-danger">Это действие нельзя отменить. Все серверы, связанные с этой геолокацией, будут помечены как неактивные.</p>
                        <input type="hidden" id="delete_geo_id">
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button type="button" class="btn btn-danger" id="confirmDeleteGeoBtn">Удалить</button>
                    </div>
                </div>
            </div>
        </div>`;
        
        const modalDiv = document.createElement('div');
        modalDiv.innerHTML = modalHtml;
        document.body.appendChild(modalDiv.firstElementChild);
        
        // Добавляем обработчик для кнопки удаления
        document.getElementById('confirmDeleteGeoBtn').addEventListener('click', handleDeleteGeolocation);
    }
    
    /**
     * Загружает список геолокаций
     */
    function loadGeolocations() {
        console.log('Загрузка списка геолокаций');
        
        // Показываем индикатор загрузки
        const tableBody = document.getElementById('geolocationsTableBody');
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Загрузка данных...</td></tr>';
        }
        
        if (!window.Api || typeof window.Api.fetchGeolocations !== 'function') {
            console.error('Функция fetchGeolocations не определена. Проверьте загрузку модуля API.');
            showAlert('Ошибка: API модуль не загружен корректно', 'danger');
            return;
        }
        
        window.Api.fetchGeolocations()
            .then(data => {
                if (data.status === 'success') {
                    geolocationsData = Array.isArray(data.geolocations) ? data.geolocations : [];
                    renderGeolocationsTable(geolocationsData);
                    console.log(`Загружено ${geolocationsData.length} геолокаций`);
                } else {
                    showAlert(`Ошибка: ${data.message || 'Неизвестная ошибка при загрузке геолокаций'}`, 'danger');
                    showLoadingError(tableBody);
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке геолокаций:', error);
                showAlert('Ошибка соединения с сервером при загрузке геолокаций', 'danger');
                showLoadingError(tableBody);
            });
    }
    
    /**
     * Показывает сообщение об ошибке загрузки
     */
    function showLoadingError(tableBody) {
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Ошибка загрузки данных</td></tr>';
        }
    }
    
    /**
     * Отображает список геолокаций в таблице
     */
    function renderGeolocationsTable(geolocations) {
        const tableBody = document.getElementById('geolocationsTableBody');
        if (!tableBody) {
            console.error('Контейнер для таблицы геолокаций не найден на странице');
            return;
        }
        
        tableBody.innerHTML = '';
        
        if (!Array.isArray(geolocations) || geolocations.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Нет доступных геолокаций</td></tr>';
            return;
        }
        
        geolocations.forEach(geo => {
            const row = document.createElement('tr');
            row.setAttribute('data-geo-id', geo.id);
            
            row.innerHTML = `
                <td>${geo.id}</td>
                <td>${geo.code}</td>
                <td>${geo.name}</td>
                <td>
                    <span class="badge bg-${geo.available ? 'success' : 'secondary'}">
                        ${geo.available ? 'Доступна' : 'Недоступна'}
                    </span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary edit-geo-btn" data-geo-id="${geo.id}" title="Редактировать">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-danger delete-geo-btn" 
                                data-geo-id="${geo.id}" 
                                data-geo-name="${geo.name}" 
                                title="Удалить">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
        
        // Добавляем обработчики для кнопок
        addTableButtonEventListeners();
    }
    
    /**
     * Добавляет обработчики событий для кнопок в таблице
     */
    function addTableButtonEventListeners() {
        // Обработчики для кнопок редактирования
        document.querySelectorAll('.edit-geo-btn').forEach(button => {
            button.addEventListener('click', function() {
                const geoId = this.dataset.geoId;
                if (geoId) {
                    showEditGeolocationModal(geoId);
                }
            });
        });
        
        // Обработчики для кнопок удаления
        document.querySelectorAll('.delete-geo-btn').forEach(button => {
            button.addEventListener('click', function() {
                const geoId = this.dataset.geoId;
                const geoName = this.dataset.geoName;
                if (geoId) {
                    showDeleteGeolocationModal(geoId, geoName);
                }
            });
        });
    }
    
    /**
     * Показывает модальное окно добавления геолокации
     */
    function showAddGeolocationModal() {
        // Сбрасываем форму
        const form = document.getElementById('addGeolocationForm');
        if (form) form.reset();
        
        // Открываем модальное окно
        try {
            const modal = new bootstrap.Modal(document.getElementById('addGeolocationModal'));
            modal.show();
        } catch (error) {
            console.error('Ошибка при открытии модального окна добавления:', error);
            showAlert('Ошибка при открытии модального окна', 'danger');
        }
    }
    
    /**
     * Показывает модальное окно редактирования геолокации
     */
    function showEditGeolocationModal(geoId) {
        console.log(`Открытие модального окна редактирования для геолокации ${geoId}`);
        
        // Находим геолокацию по ID
        const geo = geolocationsData.find(g => g.id == geoId);
        if (!geo) {
            console.error(`Геолокация с ID ${geoId} не найдена в данных`);
            showAlert('Ошибка: геолокация не найдена', 'danger');
            return;
        }
        
        // Заполняем форму данными
        document.getElementById('edit_geo_id').value = geo.id;
        document.getElementById('edit_code').value = geo.code;
        document.getElementById('edit_name').value = geo.name;
        document.getElementById('edit_available').checked = geo.available;
        
        // Открываем модальное окно
        try {
            const modal = new bootstrap.Modal(document.getElementById('editGeolocationModal'));
            modal.show();
        } catch (error) {
            console.error('Ошибка при открытии модального окна редактирования:', error);
            showAlert('Ошибка при открытии модального окна', 'danger');
        }
    }
    
    /**
     * Показывает модальное окно удаления геолокации
     */
    function showDeleteGeolocationModal(geoId, geoName) {
        console.log(`Открытие модального окна удаления для геолокации ${geoId}`);
        
        // Сохраняем ID для последующего удаления
        selectedGeoId = geoId;
        document.getElementById('delete_geo_id').value = geoId;
        
        // Устанавливаем имя геолокации
        const nameEl = document.getElementById('deleteGeoName');
        if (nameEl) {
            nameEl.textContent = geoName || `Геолокация #${geoId}`;
        }
        
        // Открываем модальное окно
        try {
            const modal = new bootstrap.Modal(document.getElementById('deleteGeolocationModal'));
            modal.show();
        } catch (error) {
            console.error('Ошибка при открытии модального окна удаления:', error);
            showAlert('Ошибка при открытии модального окна', 'danger');
        }
    }
    
    /**
     * Обрабатывает добавление новой геолокации
     */
    function handleAddGeolocation() {
        console.log('Обработка добавления новой геолокации');
        
        // Получаем данные формы
        const code = document.getElementById('new_code')?.value.trim();
        const name = document.getElementById('new_name')?.value.trim();
        const available = document.getElementById('new_available')?.checked !== false;
        
        // Проверяем обязательные поля
        if (!code || !name) {
            showAlert('Пожалуйста, заполните все обязательные поля', 'warning');
            return;
        }
        
        // Отключаем кнопку на время запроса
        const saveBtn = document.getElementById('saveNewGeolocationBtn');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Добавление...';
        }
        
        // Подготовка данных для отправки
        const geoData = {
            code: code,
            name: name,
            available: available
        };
        
        console.log('Отправка данных геолокации:', geoData);
        
        // Отправка данных на сервер
        if (!window.Api || typeof window.Api.addGeolocation !== 'function') {
            console.error('Функция addGeolocation не определена');
            showAlert('Ошибка: API модуль не загружен корректно', 'danger');
            resetSaveButton(saveBtn, 'Добавить');
            return;
        }
        
        window.Api.addGeolocation(geoData)
            .then(data => {
                if (data.status === 'success') {
                    // Показываем сообщение об успехе
                    showAlert('Геолокация успешно добавлена!', 'success');
                    
                    // Закрываем модальное окно
                    closeModal('addGeolocationModal');
                    
                    // Обновляем список геолокаций
                    loadGeolocations();
                } else {
                    showAlert(`Ошибка: ${data.message || 'Неизвестная ошибка при добавлении геолокации'}`, 'danger');
                    resetSaveButton(saveBtn, 'Добавить');
                }
            })
            .catch(error => {
                console.error('Ошибка при добавлении геолокации:', error);
                showAlert(`Ошибка: ${error.message || 'Ошибка соединения с сервером'}`, 'danger');
                resetSaveButton(saveBtn, 'Добавить');
            });
    }
    
    /**
     * Обрабатывает обновление геолокации
     */
    function handleUpdateGeolocation() {
        console.log('Обработка обновления геолокации');
        
        // Получаем данные формы
        const geoId = document.getElementById('edit_geo_id')?.value;
        const code = document.getElementById('edit_code')?.value.trim();
        const name = document.getElementById('edit_name')?.value.trim();
        const available = document.getElementById('edit_available')?.checked !== false;
        
        // Проверяем обязательные поля
        if (!geoId || !code || !name) {
            showAlert('Пожалуйста, заполните все обязательные поля', 'warning');
            return;
        }
        
        // Отключаем кнопку на время запроса
        const saveBtn = document.getElementById('saveGeolocationChangesBtn');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Сохранение...';
        }
        
        // Подготовка данных для отправки
        const geoData = {
            code: code,
            name: name,
            available: available
        };
        
        console.log(`Обновление геолокации ${geoId}:`, geoData);
        
        // Отправка данных на сервер
        if (!window.Api || typeof window.Api.updateGeolocation !== 'function') {
            console.error('Функция updateGeolocation не определена');
            showAlert('Ошибка: API модуль не загружен корректно', 'danger');
            resetSaveButton(saveBtn, 'Сохранить');
            return;
        }
        
        window.Api.updateGeolocation(geoId, geoData)
            .then(data => {
                if (data.status === 'success') {
                    // Показываем сообщение об успехе
                    showAlert('Геолокация успешно обновлена!', 'success');
                    
                    // Закрываем модальное окно
                    closeModal('editGeolocationModal');
                    
                    // Обновляем список геолокаций
                    loadGeolocations();
                } else {
                    showAlert(`Ошибка: ${data.message || 'Неизвестная ошибка при обновлении геолокации'}`, 'danger');
                    resetSaveButton(saveBtn, 'Сохранить');
                }
            })
            .catch(error => {
                console.error('Ошибка при обновлении геолокации:', error);
                showAlert(`Ошибка: ${error.message || 'Ошибка соединения с сервером'}`, 'danger');
                resetSaveButton(saveBtn, 'Сохранить');
            });
    }
    
    /**
     * Обрабатывает удаление геолокации
     */
    function handleDeleteGeolocation() {
        console.log('Обработка удаления геолокации');
        
        const geoId = document.getElementById('delete_geo_id')?.value || selectedGeoId;
        if (!geoId) {
            showAlert('Ошибка: ID геолокации не определен', 'danger');
            return;
        }
        
        // Отключаем кнопку на время запроса
        const deleteBtn = document.getElementById('confirmDeleteGeoBtn');
        if (deleteBtn) {
            deleteBtn.disabled = true;
            deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Удаление...';
        }
        
        console.log(`Удаление геолокации ${geoId}`);
        
        // Отправка запроса на сервер
        if (!window.Api || typeof window.Api.deleteGeolocation !== 'function') {
            console.error('Функция deleteGeolocation не определена');
            showAlert('Ошибка: API модуль не загружен корректно', 'danger');
            resetDeleteButton(deleteBtn);
            return;
        }
        
        window.Api.deleteGeolocation(geoId)
            .then(data => {
                if (data.status === 'success') {
                    // Показываем сообщение об успехе
                    showAlert('Геолокация успешно удалена!', 'success');
                    
                    // Закрываем модальное окно
                    closeModal('deleteGeolocationModal');
                    
                    // Обновляем список геолокаций
                    loadGeolocations();
                } else {
                    showAlert(`Ошибка: ${data.message || 'Неизвестная ошибка при удалении геолокации'}`, 'danger');
                    resetDeleteButton(deleteBtn);
                }
            })
            .catch(error => {
                console.error('Ошибка при удалении геолокации:', error);
                showAlert(`Ошибка: ${error.message || 'Ошибка соединения с сервером'}`, 'danger');
                resetDeleteButton(deleteBtn);
            });
    }
    
    /**
     * Сбрасывает состояние кнопки сохранения
     */
    function resetSaveButton(button, text = 'Сохранить') {
        if (button) {
            button.disabled = false;
            button.innerHTML = text;
        }
    }
    
    /**
     * Сбрасывает состояние кнопки удаления
     */
    function resetDeleteButton(button) {
        if (button) {
            button.disabled = false;
            button.innerHTML = 'Удалить';
        }
    }
    
    /**
     * Закрывает модальное окно по ID
     */
    function closeModal(modalId) {
        try {
            const modalElement = document.getElementById(modalId);
            if (modalElement) {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) {
                    modal.hide();
                }
            }
        } catch (error) {
            console.error(`Ошибка при закрытии модального окна ${modalId}:`, error);
        }
    }
    
    /**
     * Показывает уведомление пользователю
     */
    function showAlert(message, type = 'info') {
        console.log(`Показ уведомления (${type}): ${message}`);
        
        // Проверяем наличие глобальной функции
        if (typeof window.showAlert === 'function') {
            window.showAlert(message, type);
            return;
        }
        
        // Запасной вариант, если глобальная функция не доступна
        let alertsContainer = document.querySelector('.flash-messages');
        
        // Если контейнер не найден, создаем его
        if (!alertsContainer) {
            alertsContainer = document.createElement('div');
            alertsContainer.className = 'flash-messages';
            alertsContainer.style.position = 'fixed';
            alertsContainer.style.top = '20px';
            alertsContainer.style.right = '20px';
            alertsContainer.style.zIndex = '9999';
            document.body.appendChild(alertsContainer);
        }
        
        // Создаем уведомление
        const alertHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertsContainer.innerHTML += alertHTML;
        
        // Автоматически скрываем уведомление через 5 секунд
        setTimeout(() => {
            const alerts = alertsContainer.querySelectorAll('.alert');
            alerts.forEach(alert => {
                try {
                    if (window.bootstrap && bootstrap.Alert) {
                        const bsAlert = new bootstrap.Alert(alert);
                        bsAlert.close();
                    } else {
                        alert.classList.remove('show');
                        setTimeout(() => {
                            if (alertsContainer.contains(alert)) {
                                alertsContainer.removeChild(alert);
                            }
                        }, 300);
                    }
                } catch (e) {
                    // В случае ошибки просто удаляем элемент
                    if (alertsContainer.contains(alert)) {
                        alertsContainer.removeChild(alert);
                    }
                }
            });
        }, 5000);
    }
    
    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', initPage);
})();