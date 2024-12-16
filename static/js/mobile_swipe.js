document.addEventListener('DOMContentLoaded', function() {
    initializeEventSwipe();
});

function initializeEventSwipe() {
    const eventArticles = document.querySelectorAll('.event-articles');
    
    eventArticles.forEach(container => {
        const row = container.querySelector('.row');
        const eventInfo = container.querySelector('.event-info');
        let startX;
        let currentX;
        let isSliding = false;
        let isDragging = false;
        let startTranslateX = 0;
        
        // Solo aplicar en móvil
        if (window.innerWidth > 767) return;

        function setTransform(translateX) {
            row.style.transform = `translateX(${translateX}%)`;
        }

        function resetTransition() {
            row.style.transition = 'transform 0.3s ease-out';
        }

        function snapToPosition(diff) {
            resetTransition();
            if (Math.abs(diff) > window.innerWidth * 0.2) {
                setTransform(diff < 0 ? -100 : 0);
            } else {
                setTransform(0);
            }
        }

        // Eventos táctiles
        container.addEventListener('touchstart', e => {
            startX = e.touches[0].clientX;
            currentX = startX;
            isSliding = true;
            startTranslateX = row.style.transform ? 
                parseInt(row.style.transform.match(/-?\d+/)[0]) : 0;
            row.style.transition = 'none';
        }, { passive: true });

        container.addEventListener('touchmove', e => {
            if (!isSliding) return;
            
            currentX = e.touches[0].clientX;
            const diff = ((currentX - startX) / window.innerWidth) * 100;
            const newTranslate = Math.max(-100, Math.min(0, startTranslateX + diff));
            
            setTransform(newTranslate);
        }, { passive: true });

        container.addEventListener('touchend', () => {
            if (!isSliding) return;
            
            const diff = currentX - startX;
            snapToPosition(diff);
            isSliding = false;
        });

        // Click del evento
        eventInfo.addEventListener('click', () => {
            resetTransition();
            const currentTransform = row.style.transform;
            if (currentTransform.includes('-100')) {
                setTransform(0);
            } else {
                setTransform(-100);
            }
        });
    });
}
