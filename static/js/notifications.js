class NotificationSystem {
    constructor() {
        this.container = document.getElementById('notificationContainer');
        this.template = document.getElementById('notificationTemplate');
        this.notifications = new Set();
        this.init();
    }

    init() {
        // Handle notification close clicks
        this.container.addEventListener('click', (e) => {
            if (e.target.matches('.notification-close')) {
                const notification = e.target.closest('.notification');
                if (notification) {
                    this.removeNotification(notification);
                }
            }
        });

        // Start checking for updates
        this.checkForUpdates();
    }

    async checkForUpdates() {
        try {
            const response = await fetch('/api/updates');
            if (response.ok) {
                const updates = await response.json();
                updates.forEach(update => {
                    this.showNotification({
                        title: update.title,
                        message: update.message,
                        type: update.type,
                        timestamp: update.timestamp
                    });
                });
            }
        } catch (error) {
            console.error('Error checking for updates:', error);
        }
        
        // Check again in 5 minutes
        setTimeout(() => this.checkForUpdates(), 5 * 60 * 1000);
    }

    showNotification({ title, message, type = 'info', timestamp }) {
        if (!this.template) return;

        const notification = this.template.content.cloneNode(true).querySelector('.notification');
        
        // Set notification content
        notification.querySelector('.notification-title').textContent = title;
        notification.querySelector('.notification-body').textContent = message;
        notification.querySelector('.notification-time').textContent = this.formatTimestamp(timestamp);
        
        // Add type class
        notification.classList.add(type);
        
        // Add to container
        this.container.appendChild(notification);
        this.notifications.add(notification);

        // Animate in
        requestAnimationFrame(() => {
            notification.classList.add('show');
        });

        // Auto remove after 10 seconds
        setTimeout(() => {
            if (this.notifications.has(notification)) {
                this.removeNotification(notification);
            }
        }, 10000);
    }

    removeNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode === this.container) {
                this.container.removeChild(notification);
            }
            this.notifications.delete(notification);
        }, 300);
    }

    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    }
}

// Initialize notification system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.notificationSystem = new NotificationSystem();
});
