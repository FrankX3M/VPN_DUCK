// Add this code to static/js/minimal.js
// This is the minimal JavaScript needed after migrating most functionality to server-side Python

document.addEventListener('DOMContentLoaded', function() {
    // Copy to clipboard functionality
    document.querySelectorAll('.copy-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-copy');
            if (textToCopy) {
                navigator.clipboard.writeText(textToCopy).then(function() {
                    // Show feedback
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '<i class="bi bi-check"></i> Copied';
                    
                    setTimeout(function() {
                        btn.innerHTML = originalText;
                    }, 2000);
                });
            }
        });
    });
    
    // Confirmation dialogs
    document.querySelectorAll('.confirm-action').forEach(function(element) {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-dismiss alerts
    document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
        setTimeout(function() {
            // Add fade class then remove after animation
            alert.classList.add('fade');
            setTimeout(function() {
                alert.remove();
            }, 500);
        }, 5000);
    });
    
    // Auto-submit form when view mode changes
    document.querySelectorAll('input[name="view"]').forEach(function(radio) {
        radio.addEventListener('change', function() {
            if (this.checked) {
                this.closest('form').submit();
            }
        });
    });
    
    // Responsive tabs
    const resizeTabs = function() {
        const tabContainers = document.querySelectorAll('.nav-tabs');
        tabContainers.forEach(function(container) {
            const availableWidth = container.offsetWidth;
            const tabs = container.querySelectorAll('.nav-link');
            const tabCount = tabs.length;
            
            if (availableWidth < (tabCount * 100)) {
                container.classList.add('flex-column');
            } else {
                container.classList.remove('flex-column');
            }
        });
    };
    
    // Call on page load and window resize
    resizeTabs();
    window.addEventListener('resize', resizeTabs);
});