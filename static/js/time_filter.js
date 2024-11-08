document.addEventListener('DOMContentLoaded', function() {
    const timeFilter = document.querySelector('.toggle-slider');
    const eventsContent = document.getElementById('events-content');
    
    if (!timeFilter) return;

    // Initialize the slider position based on checked input
    const checkedInput = timeFilter.querySelector('input[type="radio"]:checked');
    if (checkedInput) {
        const slider = timeFilter.querySelector('.slider');
        const transform = getSliderTransform(checkedInput.id);
        if (slider && transform !== null) {
            slider.style.transform = `translateX(${transform})`;
        }
    }

    timeFilter.addEventListener('change', function(e) {
        if (!e.target.matches('input[type="radio"]')) return;
        
        // Update slider position
        const slider = timeFilter.querySelector('.slider');
        const transform = getSliderTransform(e.target.id);
        if (slider && transform !== null) {
            slider.style.transform = `translateX(${transform})`;
        }
        
        // Update navigation first
        updateNavigation();
        
        // Then show loading state and reload articles
        if (eventsContent) {
            eventsContent.innerHTML = `
                <div class="text-center my-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Loading articles...</p>
                </div>
            `;
        }
        
        const timeRange = e.target.value;
        reloadArticles(timeRange);
    });
});

function getSliderTransform(inputId) {
    switch(inputId) {
        case '24h': return '0';
        case '48h': return '4rem';
        case '72h': return '8rem';
        default: return null;
    }
}