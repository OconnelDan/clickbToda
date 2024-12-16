document.addEventListener('DOMContentLoaded', function() {
    initializeArticleReveal();
});

function initializeArticleReveal() {
    const eventArticles = document.querySelectorAll('.event-articles');
    
    eventArticles.forEach(container => {
        const row = container.querySelector('.row');
        const eventInfo = container.querySelector('.event-info');
        
        // Añadir el manejador de clic al evento
        eventInfo.addEventListener('click', () => {
            // Si ya está transformado, volver a la posición inicial
            if (row.style.transform === 'translateX(-50%)') {
                row.style.transform = 'translateX(0)';
            } else {
                // Si no está transformado, mostrar los artículos
                row.style.transform = 'translateX(-50%)';
            }
        });
    });
}