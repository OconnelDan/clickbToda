document.addEventListener('DOMContentLoaded', function() {
    initializeSwipeReveal();
});

function initializeSwipeReveal() {
    const eventArticles = document.querySelectorAll('.event-articles');
    
    eventArticles.forEach(container => {
        let startX;
        let currentX;
        let isRevealed = false;
        let isSwiping = false;
        const row = container.querySelector('.row');
        
        // Reset initial position
        row.style.transform = 'translateX(0)';
        
        container.addEventListener('touchstart', e => {
            if (e.touches.length !== 1) return;
            
            startX = e.touches[0].clientX;
            currentX = startX;
            isSwiping = true;
            row.style.transition = 'none';
            
            // Prevent default only if necessary
            e.preventDefault();
        }, { passive: false });
        
        container.addEventListener('touchmove', e => {
            if (!isSwiping || startX === null) return;
            
            currentX = e.touches[0].clientX;
            const diff = startX - currentX;
            const maxSwipe = container.offsetWidth / 2;
            
            // Calcular el porcentaje de deslizamiento
            let percentage = (diff / maxSwipe) * 100;
            
            // Limitar el deslizamiento
            percentage = Math.max(-100, Math.min(percentage, 100));
            
            if (!isRevealed) {
                // Deslizando para revelar
                if (percentage > 0) {
                    row.style.transform = `translateX(-${percentage}%)`;
                }
            } else {
                // Deslizando para ocultar
                if (percentage < 0) {
                    row.style.transform = `translateX(-${100 + percentage}%)`;
                }
            }
            
            // Prevent default to avoid scrolling
            e.preventDefault();
        }, { passive: false });
        
        container.addEventListener('touchend', () => {
            if (!isSwiping) return;
            
            const diff = startX - currentX;
            const threshold = container.offsetWidth / 4; // 25% del ancho
            
            row.style.transition = 'transform 0.3s cubic-bezier(0.4, 0.0, 0.2, 1)';
            
            if (!isRevealed && diff > threshold) {
                // Revelar carrusel
                row.style.transform = 'translateX(-100%)';
                isRevealed = true;
            } else if (isRevealed && -diff > threshold) {
                // Ocultar carrusel
                row.style.transform = 'translateX(0)';
                isRevealed = false;
            } else {
                // Volver a la posición original
                row.style.transform = isRevealed ? 'translateX(-100%)' : 'translateX(0)';
            }
            
            // Reset variables
            startX = null;
            currentX = null;
            isSwiping = false;
        });
        
        // Cancelar el deslizamiento si el dedo sale del elemento
        container.addEventListener('touchcancel', () => {
            if (!isSwiping) return;
            
            row.style.transition = 'transform 0.3s cubic-bezier(0.4, 0.0, 0.2, 1)';
            row.style.transform = isRevealed ? 'translateX(-100%)' : 'translateX(0)';
            
            startX = null;
            currentX = null;
            isSwiping = false;
        });
    });
}
