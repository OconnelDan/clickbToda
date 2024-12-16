document.addEventListener('DOMContentLoaded', function() {
    initializeSwipeReveal();
});

function initializeSwipeReveal() {
    const eventArticles = document.querySelectorAll('.event-articles');
    
    eventArticles.forEach(container => {
        let startX;
        let currentX;
        let isRevealed = false;
        const row = container.querySelector('.row');

        container.addEventListener('touchstart', e => {
            startX = e.touches[0].clientX;
            row.style.transition = 'none';
        }, { passive: true });

        container.addEventListener('touchmove', e => {
            if (!startX) return;
            
            currentX = e.touches[0].clientX;
            const diff = startX - currentX;
            const maxSwipe = container.offsetWidth / 2;
            
            // Limitar el deslizamiento
            const swipeAmount = Math.max(0, Math.min(diff, maxSwipe));
            
            if (!isRevealed) {
                row.style.transform = `translateX(-${swipeAmount}px)`;
            } else {
                row.style.transform = `translateX(-${maxSwipe - swipeAmount}px)`;
            }
        }, { passive: true });

        container.addEventListener('touchend', e => {
            if (!startX || !currentX) return;
            
            const diff = startX - currentX;
            const threshold = container.offsetWidth / 4;
            row.style.transition = 'transform 0.3s ease-out';

            if (!isRevealed && diff > threshold) {
                // Revelar carrusel
                row.style.transform = `translateX(-50%)`;
                isRevealed = true;
            } else if (isRevealed && diff < -threshold) {
                // Ocultar carrusel
                row.style.transform = 'translateX(0)';
                isRevealed = false;
            } else {
                // Volver a la posición original
                row.style.transform = isRevealed ? 'translateX(-50%)' : 'translateX(0)';
            }

            startX = null;
            currentX = null;
        });
    });
}
