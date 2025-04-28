// Script for editing servers
document.addEventListener('DOMContentLoaded', function() {
    // Get form element
    const serverForm = document.getElementById('server-form');
    
    // Get server ID from URL
    const serverId = window.location.pathname.split('/').pop();
    
    // Load server data and populate form
    loadServerData(serverId);
    
    // Load geolocations for dropdown
    loadGeolocations();
    
    // Add form submit handler
    if (serverForm) {
        serverForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            // Validate form
            if (!validateForm()) {
                return;
            }
            
            // Get form data
            const formData = {
                name: document.getElementById('name').value,
                location: document.getElementById('location').value,
                api_url: document.getElementById('api-url').value,
                geolocation_id: document.getElementById('geolocation-id').value,
                auth_type: document.getElementById('auth-type').value,
                max_peers: document.getElementById('max-peers').value,
                is_active: document.getElementById('is-active').checked
            };
            
            // Add authentication data based on selected auth type
            switch (formData.auth_type) {
                case 'api_key':
                    formData.api_key = document.getElementById('api-key').value;
                    break;
                case 'oauth':
                    formData.oauth_client_id = document.getElementById('oauth-client-id').value;
                    formData.oauth_client_secret = document.getElementById('oauth-client-secret').value;
                    formData.oauth_token_url = document.getElementById('oauth-token-url').value;
                    break;
                case 'hmac':
                    formData.hmac_secret = document.getElementById('hmac-secret').value;
                    break;
            }
            
            // Update server
            updateServer(serverId, formData);
        });
    }
    
    // Set auth fields visibility based on selected auth type
    const authTypeSelect = document.getElementById('auth-type');
    if (authTypeSelect) {
        authTypeSelect.addEventListener('change', function() {
            updateAuthFieldsVisibility(this.value);
        });
    }
});

/**
 * Load server data and populate form
 */
function loadServerData(serverId) {
    // Show loading overlay
    const formContent = document.getElementById('form-content');
    const loadingOverlay = document.getElementById('loading-overlay');
    
    if (formContent) formContent.classList.add('d-none');
    if (loadingOverlay) loadingOverlay.classList.remove('d-none');
    
    // Fetch server data
    fetch(`/api/servers/${serverId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.server) {
                populateForm(data.server);
            } else {
                showAlert('error', 'Ошибка', 'Не удалось загрузить данные сервера');
            }
        })
        .catch(error => {
            console.error('Error loading server data:', error);
            showAlert('error', 'Ошибка загрузки', error.message);
        })
        .finally(() => {
            // Hide loading overlay
            if (formContent) formContent.classList.remove('d-none');
            if (loadingOverlay) loadingOverlay.classList.add('d-none');
        });
}

/**
 * Populate form with server data
 */
function populateForm(server) {
    // Basic fields
    const nameField = document.getElementById('name');
    const locationField = document.getElementById('location');
    const apiUrlField = document.getElementById('api-url');
    const geolocationSelect = document.getElementById('geolocation-id');
    const authTypeSelect = document.getElementById('auth-type');
    const maxPeersField = document.getElementById('max-peers');
    const isActiveField = document.getElementById('is-active');
    
    if (nameField) nameField.value = server.name || '';
    if (locationField) locationField.value = server.location || '';
    if (apiUrlField) apiUrlField.value = server.api_url || '';
    if (geolocationSelect) {
        // Will be populated when geolocations are loaded
        geolocationSelect.dataset.selectedValue = server.geolocation_id;
    }
    if (authTypeSelect) authTypeSelect.value = server.auth_type || 'api_key';
    if (maxPeersField) maxPeersField.value = server.max_peers || 100;
    if (isActiveField) isActiveField.checked = server.is_active || false;
    
    // Auth fields
    document.getElementById('api-key').value = server.api_key || '';
    document.getElementById('oauth-client-id').value = server.oauth_client_id || '';
    document.getElementById('oauth-client-secret').value = server.oauth_client_secret || '';
    document.getElementById('oauth-token-url').value = server.oauth_token_url || '';
    document.getElementById('hmac-secret').value = server.hmac_secret || '';
    
    // Update auth fields visibility
    updateAuthFieldsVisibility(server.auth_type || 'api_key');
    
    // Update page title
    document.getElementById('server-name').textContent = server.name || `Сервер ${server.id}`;
}

/**
 * Load geolocations for dropdown
 */
function loadGeolocations() {
    const geolocationSelect = document.getElementById('geolocation-id');
    if (!geolocationSelect) return;
    
    // Show loading indicator
    geolocationSelect.innerHTML = '<option value="">Загрузка...</option>';
    
    // Remember selected value (if any)
    const selectedValue = geolocationSelect.dataset.selectedValue;
    
    // Fetch geolocations from API
    fetch('/api/geolocations')
        .then(response => response.json())
        .then(data => {
            if (data.geolocations && Array.isArray(data.geolocations)) {
                geolocationSelect.innerHTML = '<option value="">Выберите геолокацию</option>';
                
                data.geolocations.forEach(geolocation => {
                    const option = document.createElement('option');
                    option.value = geolocation.id;
                    option.textContent = geolocation.name;
                    
                    // Select the previously selected value
                    if (selectedValue && selectedValue == geolocation.id) {
                        option.selected = true;
                    }
                    
                    geolocationSelect.appendChild(option);
                });
            } else {
                geolocationSelect.innerHTML = '<option value="">Нет доступных геолокаций</option>';
            }
        })
        .catch(error => {
            console.error('Error loading geolocations:', error);
            geolocationSelect.innerHTML = '<option value="">Ошибка загрузки</option>';
            showAlert('error', 'Ошибка загрузки геолокаций', error.message);
        });
}

/**
 * Show/hide authentication fields based on selected auth type
 */
function updateAuthFieldsVisibility(authType) {
    // Hide all auth fields
    document.querySelectorAll('.auth-fields').forEach(field => {
        field.classList.add('d-none');
    });
    
    // Show fields for selected auth type
    const selectedFields = document.getElementById(`${authType}-fields`);
    if (selectedFields) {
        selectedFields.classList.remove('d-none');
    }
}

/**
 * Validate form data
 */
function validateForm() {
    let isValid = true;
    
    // Reset validation messages
    document.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');
    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    
    // Required fields validation
    const requiredFields = ['name', 'location', 'api-url', 'geolocation-id'];
    requiredFields.forEach(field => {
        const element = document.getElementById(field);
        if (!element.value.trim()) {
            element.classList.add('is-invalid');
            const feedbackEl = element.nextElementSibling;
            if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
                feedbackEl.textContent = 'Это поле обязательно для заполнения';
            }
            isValid = false;
        }
    });
    
    // Auth fields validation based on selected auth type
    const authType = document.getElementById('auth-type').value;
    switch (authType) {
        case 'api_key':
            const apiKeyEl = document.getElementById('api-key');
            if (!apiKeyEl.value.trim()) {
                apiKeyEl.classList.add('is-invalid');
                const feedbackEl = apiKeyEl.nextElementSibling;
                if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
                    feedbackEl.textContent = 'API ключ обязателен для этого типа аутентификации';
                }
                isValid = false;
            }
            break;
        case 'oauth':
            const oauthFields = ['oauth-client-id', 'oauth-client-secret', 'oauth-token-url'];
            oauthFields.forEach(field => {
                const element = document.getElementById(field);
                if (!element.value.trim()) {
                    element.classList.add('is-invalid');
                    const feedbackEl = element.nextElementSibling;
                    if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
                        feedbackEl.textContent = 'Это поле обязательно для OAuth аутентификации';
                    }
                    isValid = false;
                }
            });
            break;
        case 'hmac':
            const hmacSecretEl = document.getElementById('hmac-secret');
            if (!hmacSecretEl.value.trim()) {
                hmacSecretEl.classList.add('is-invalid');
                const feedbackEl = hmacSecretEl.nextElementSibling;
                if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
                    feedbackEl.textContent = 'Секретный ключ обязателен для HMAC аутентификации';
                }
                isValid = false;
            }
            break;
    }
    
    // URL format validation
    const apiUrlEl = document.getElementById('api-url');
    if (apiUrlEl.value.trim() && !isValidUrl(apiUrlEl.value)) {
        apiUrlEl.classList.add('is-invalid');
        const feedbackEl = apiUrlEl.nextElementSibling;
        if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
            feedbackEl.textContent = 'Введите корректный URL (например, http://example.com)';
        }
        isValid = false;
    }
    
    // OAuth Token URL validation if present
    const oauthTokenUrlEl = document.getElementById('oauth-token-url');
    if (oauthTokenUrlEl && oauthTokenUrlEl.value.trim() && !isValidUrl(oauthTokenUrlEl.value)) {
        oauthTokenUrlEl.classList.add('is-invalid');
        const feedbackEl = oauthTokenUrlEl.nextElementSibling;
        if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
            feedbackEl.textContent = 'Введите корректный URL для OAuth токена';
        }
        isValid = false;
    }
    
    return isValid;
}

/**
 * Validate URL format
 */
function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * Update server via API
 */
function updateServer(serverId, formData) {
    // Show loading state
    const submitBtn = document.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Сохранение...';
    
    // Send API request
    fetch(`/api/servers/${serverId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Ошибка при обновлении сервера');
            });
        }
        return response.json();
    })
    .then(data => {
        // Show success message
        showAlert('success', 'Сервер обновлен', 'Сервер успешно обновлен. Перенаправление на страницу сервера...');
        
        // Redirect to server details page after a short delay
        setTimeout(() => {
            window.location.href = `/servers/details/${serverId}`;
        }, 1500);
    })
    .catch(error => {
        console.error('Error updating server:', error);
        showAlert('error', 'Ошибка', error.message || 'Неизвестная ошибка при обновлении сервера');
        
        // Reset button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    });
}