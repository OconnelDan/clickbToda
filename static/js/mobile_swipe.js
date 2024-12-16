document.addEventListener('DOMContentLoaded', function() {
    initializeSwipeReveal();
});

function initializeSwipeReveal() {
    const eventArticles = document.querySelectorAll('.event-articles');
    
    eventArticles.forEach(container => {
        let startX = null;
        let currentX = null;
        let isDragging = false;
        const row = container.querySelector('.row');
        
        container.addEventListener('touchstart', e => {
            if (e.touches.length !== 1) return;
            startX = e.touches[0].clientX;
            isDragging = true;
            row.style.transition = 'none';
        }, { passive: true });
        
        container.addEventListener('touchmove', e => {
            if (!isDragging || !startX) return;
            
            currentX = e.touches[0].clientX;
            const diff = startX - currentX;
            const maxSwipe = container.offsetWidth;
            const percentage = Math.min(100, Math.max(0, (diff / maxSwipe) * 100));
            
            row.style.transform = `translateX(-${percentage}%)`;
            
            // Prevenir el scroll vertical durante el deslizamiento horizontal
            if (Math.abs(diff) > 10) {
                e.preventDefault();
            }
        }, { passive: false });
        
        container.addEventListener('touchend', () => {
            if (!isDragging) return;
            
            const diff = startX - currentX;
            const threshold = container.offsetWidth * 0.3; // 30% del ancho
            
            row.style.transition = 'transform 0.3s ease';
            
            if (diff > threshold) {
                // Mostrar artículos
                row.style.transform = 'translateX(-100%)';
            } else {
                // Volver a la posición inicial
                row.style.transform = 'translateX(0)';
            }
            
            startX = null;
            currentX = null;
            isDragging = false;
        });
        
        container.addEventListener('touchcancel', () => {
            if (!isDragging) return;
            
            row.style.transition = 'transform 0.3s ease';
            row.style.transform = 'translateX(0)';
            
            startX = null;
            currentX = null;
            isDragging = false;
        });
    });
}