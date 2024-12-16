document.addEventListener('DOMContentLoaded', function() {
    initializeArticleReveal();
});

function initializeArticleReveal() {
    const eventArticles = document.querySelectorAll('.event-articles');
    
    eventArticles.forEach(container => {
        const row = container.querySelector('.row');
        const eventInfo = container.querySelector('.event-info');
        let isExpanded = false;
        
        // Añadir el manejador de clic al evento
        eventInfo.addEventListener('click', () => {
            isExpanded = !isExpanded;
            row.style.transform = isExpanded ? 'translateX(-50%)' : 'translateX(0)';
            
            // Actualizar la flecha
            const arrow = eventInfo.querySelector('.arrow-indicator');
            if (arrow) {
                arrow.style.transform = isExpanded ? 'rotate(-180deg)' : 'rotate(0)';
            }
        });
    });
}
