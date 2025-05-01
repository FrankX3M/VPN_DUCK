// Добавить в начало файла
document.addEventListener('DOMContentLoaded', function() {
    // Получить данные сервера из API и заполнить форму
    const serverId = window.location.pathname.split('/').pop();
    
    fetch(`/api/servers/${serverId}`)
        .then(response => response.json())
        .then(server => {
            // Заполняем форму данными
            document.getElementById('name').value = server.name || '';
            document.getElementById('endpoint').value = server.endpoint || '';
            document.getElementById('port').value = server.port || '';
            document.getElementById('address').value = server.address || '';
            document.getElementById('public_key').value = server.public_key || '';
            document.getElementById('geolocation_id').value = server.geolocation_id || '';
            document.getElementById('status').value = server.status || 'active';
            document.getElementById('api_key').value = server.api_key || '';
            document.getElementById('api_url').value = server.api_url || '';
        })
        .catch(error => {
            console.error('Error loading server details:', error);
            window.showAlert('Ошибка загрузки данных сервера', 'danger');
        });
});