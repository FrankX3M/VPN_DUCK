/**
 * Модуль для работы с фильтрами и сортировкой
 */
(function() {
    /**
     * Фильтрует элементы по выбранным критериям
     * @param {Array} items - Массив элементов для фильтрации
     * @param {Object} filters - Объект с фильтрами
     * @returns {Array} Отфильтрованный массив
     */
    function filterItems(items, filters) {
        return items.filter(item => {
            let passFilter = true;
            
            // Проверяем каждый фильтр
            Object.entries(filters).forEach(([key, value]) => {
                if (value === 'all') return;
                
                if (key === 'status' && item.status !== value) {
                    passFilter = false;
                }
                
                if (key === 'geolocation' && item.geolocation_id != value) {
                    passFilter = false;
                }
                
                if (key === 'load') {
                    const load = item.load || 0;
                    if (value === 'low' && load >= 30) passFilter = false;
                    if (value === 'medium' && (load < 30 || load > 70)) passFilter = false;
                    if (value === 'high' && load <= 70) passFilter = false;
                }
            });
            
            return passFilter;
        });
    }
    
    /**
     * Сортирует элементы по указанному критерию
     * @param {Array} items - Массив элементов для сортировки
     * @param {string} sortBy - Критерий сортировки
     * @returns {Array} Отсортированный массив
     */
    function sortItems(items, sortBy) {
        const itemsCopy = [...items];
        
        switch (sortBy) {
            case 'id':
                itemsCopy.sort((a, b) => a.id - b.id);
                break;
            case 'geo':
                itemsCopy.sort((a, b) => {
                    const geoA = a.geolocation_name || '';
                    const geoB = b.geolocation_name || '';
                    return geoA.localeCompare(geoB);
                });
                break;
            case 'status':
                itemsCopy.sort((a, b) => {
                    const order = { 'active': 0, 'degraded': 1, 'inactive': 2 };
                    return order[a.status] - order[b.status];
                });
                break;
            case 'load':
                itemsCopy.sort((a, b) => (a.load || 0) - (b.load || 0));
                break;
            case 'latency':
                itemsCopy.sort((a, b) => (a.avg_latency || 999) - (b.avg_latency || 999));
                break;
        }
        
        return itemsCopy;
    }
    
    // Экспортируем функции
    window.Filters = {
        filter: filterItems,
        sort: sortItems
    };
})();