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
        
        // Inicio del toque
        container.addEventListener('touchstart', e => {
            if (e.touches.length !== 1) return;
            startX = e.touches[0].clientX;
            isDragging = true;
            row.style.transition = 'none';
        }, { passive: true });
        
        // Durante el deslizamiento
        container.addEventListener('touchmove', e => {
            if (!isDragging || !startX) return;
            
            currentX = e.touches[0].clientX;
            const diff = startX - currentX;
            const maxSwipe = container.offsetWidth;
            const percentage = Math.min(100, Math.max(0, (diff / maxSwipe) * 100));
            
            // Aplica la transformación
            row.style.transform = `translateX(-${percentage}%)`;
            
            // Previene el scroll vertical durante el deslizamiento horizontal
            if (Math.abs(diff) > 10) {
                e.preventDefault();
            }
        }, { passive: false });
        
        // Fin del toque
        container.addEventListener('touchend', () => {
            if (!isDragging || !startX || !currentX) return;
            
            const diff = startX - currentX;
            const threshold = container.offsetWidth * 0.2; // 20% del ancho para activar
            
            row.style.transition = 'transform 0.3s ease-out';
            
            if (diff > threshold) {
                // Mostrar artículos
                row.style.transform = 'translateX(-50%)';
            } else {
                // Volver a mostrar evento
                row.style.transform = 'translateX(0)';
            }
            
            // Reiniciar variables
            startX = null;
            currentX = null;
            isDragging = false;
        });
        
        // Cancelar toque
        container.addEventListener('touchcancel', () => {
            if (!isDragging) return;
            
            row.style.transition = 'transform 0.3s ease-out';
            row.style.transform = 'translateX(0)';
            
            startX = null;
            currentX = null;
            isDragging = false;
        });
        
        // Deslizar hacia la derecha para volver al evento
        container.addEventListener('touchmove', e => {
            if (!isDragging || !startX) return;
            
            currentX = e.touches[0].clientX;
            const diff = currentX - startX;
            
            if (diff > 0 && getComputedStyle(row).transform.includes('matrix')) {
                const percentage = Math.max(0, 50 - (diff / container.offsetWidth) * 50);
                row.style.transform = `translateX(-${percentage}%)`;
            }
        }, { passive: true });
    });
}
