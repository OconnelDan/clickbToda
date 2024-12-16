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

        // Asegurarse de que inicialmente esté en la posición correcta
        row.style.transform = 'translateX(0)';

        container.addEventListener('touchstart', e => {
            if (e.touches.length !== 1) return;
            
            startX = e.touches[0].clientX;
            currentX = startX;
            isSwiping = true;
            row.style.transition = 'none';
        }, { passive: true });

        container.addEventListener('touchmove', e => {
            if (!isSwiping || !startX) return;
            
            currentX = e.touches[0].clientX;
            const diff = startX - currentX;
            const maxSwipe = container.offsetWidth / 2;
            
            // Calcular el porcentaje de deslizamiento
            let percentage = (diff / maxSwipe) * 100;
            percentage = Math.max(0, Math.min(percentage, 100));
            
            if (!isRevealed) {
                row.style.transform = `translateX(-${percentage}%)`;
            } else {
                row.style.transform = `translateX(-${100 - percentage}%)`;
            }
        }, { passive: true });

        container.addEventListener('touchend', () => {
            if (!isSwiping) return;
            
            const diff = startX - currentX;
            const threshold = container.offsetWidth / 3; // Hacer el umbral más sensible
            row.style.transition = 'transform 0.3s cubic-bezier(0.4, 0.0, 0.2, 1)';

            if (!isRevealed && diff > threshold) {
                // Revelar carrusel
                row.style.transform = 'translateX(-100%)';
                isRevealed = true;
            } else if (isRevealed && diff < -threshold) {
                // Ocultar carrusel
                row.style.transform = 'translateX(0)';
                isRevealed = false;
            } else {
                // Volver a la posición original
                row.style.transform = isRevealed ? 'translateX(-100%)' : 'translateX(0)';
            }

            // Reiniciar variables
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
