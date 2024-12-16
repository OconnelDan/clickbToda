document.addEventListener('DOMContentLoaded', function() {
    initializeEventSwipe();
});

function initializeEventSwipe() {
    const eventArticles = document.querySelectorAll('.event-articles');
    
    eventArticles.forEach(container => {
        const row = container.querySelector('.row');
        let startX;
        let currentX;
        let isSliding = false;
        
        // Detectar dispositivo móvil
        const isMobile = window.innerWidth <= 767;
        if (!isMobile) return;

        container.addEventListener('touchstart', e => {
            startX = e.touches[0].clientX;
            currentX = startX;
            isSliding = true;
            row.style.transition = 'none';
        }, { passive: true });

        container.addEventListener('touchmove', e => {
            if (!isSliding) return;
            
            currentX = e.touches[0].clientX;
            const diff = currentX - startX;
            const maxSlide = window.innerWidth;
            
            // Limitar el deslizamiento
            const slideX = Math.max(Math.min(diff, 0), -maxSlide);
            row.style.transform = `translateX(${slideX}px)`;
        }, { passive: true });

        container.addEventListener('touchend', () => {
            if (!isSliding) return;
            
            isSliding = false;
            row.style.transition = 'transform 0.3s ease-out';
            
            const diff = currentX - startX;
            const threshold = window.innerWidth * 0.2; // 20% del ancho de la pantalla
            
            if (Math.abs(diff) > threshold) {
                // Si el deslizamiento fue suficiente, mover a la siguiente vista
                if (diff < 0) {
                    // Deslizar a la izquierda para mostrar artículos
                    row.style.transform = 'translateX(-100%)';
                } else {
                    // Deslizar a la derecha para volver al evento
                    row.style.transform = 'translateX(0)';
                }
            } else {
                // Si el deslizamiento no fue suficiente, volver a la posición original
                row.style.transform = 'translateX(0)';
            }
        });

        // Añadir manejador de clic para el indicador
        const eventInfo = container.querySelector('.event-info');
        eventInfo.addEventListener('click', () => {
            row.style.transition = 'transform 0.3s ease-out';
            const currentTransform = row.style.transform;
            if (currentTransform === 'translateX(-100%)') {
                row.style.transform = 'translateX(0)';
            } else {
                row.style.transform = 'translateX(-100%)';
            }
        });
    });
}
