class NotificationManager {
    constructor() {
        this.container = document.getElementById('notificationContainer');
        this.template = document.getElementById('notificationTemplate');
        this.notifications = new Set();
        this.checkUpdatesInterval = 60000; // Check every minute
        this.lastCheckTime = new Date().toISOString();
        
        if (this.container && this.template) {
            this.init();
        }
    }

    init() {
        // Start checking for updates
        this.startUpdateCheck();
        
        // Setup event delegation for notification close buttons
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('notification-close')) {
                const notification = e.target.closest('.notification');
                if (notification) {
                    this.removeNotification(notification);
                }
            }
        });
    }

    startUpdateCheck() {
        this.checkForUpdates();
        setInterval(() => this.checkForUpdates(), this.checkUpdatesInterval);
    }

    async checkForUpdates() {
        try {
            const response = await fetch(`/api/article-updates?since=${this.lastCheckTime}`);
            if (!response.ok) throw new Error('Failed to fetch updates');
            
            const updates = await response.json();
            this.lastCheckTime = new Date().toISOString();
            
            updates.forEach(update => {
                this.showNotification({
                    title: 'Artículo Actualizado',
                    message: `"${update.titular}" ha sido actualizado.`,
                    type: 'update',
                    time: update.updated_on
                });
            });
        } catch (error) {
            console.error('Error checking for updates:', error);
        }
    }

    showNotification({ title, message, type = 'update', time = new Date() }) {
        if (!this.container || !this.template) return;

        const notification = this.template.content.cloneNode(true).querySelector('.notification');
        
        // Set notification content
        notification.querySelector('.notification-title').textContent = title;
        notification.querySelector('.notification-body').textContent = message;
        notification.querySelector('.notification-time').textContent = this.formatTime(time);
        
        // Add type class
        notification.classList.add(type);
        
        // Add to container
        this.container.appendChild(notification);
        
        // Trigger animation
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Auto remove after 5 seconds
        setTimeout(() => this.removeNotification(notification), 5000);
        
        this.notifications.add(notification);
    }

    removeNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
            this.notifications.delete(notification);
        }, 300);
    }

    formatTime(time) {
        const date = new Date(time);
        return date.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
    }
}

// Initialize notification manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});
