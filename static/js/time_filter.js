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
        
        // Show loading state
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
        const currentDate = new Date();
        let filterDate = new Date();
        
        switch(timeRange) {
            case '24h':
                filterDate.setHours(currentDate.getHours() - 24);
                break;
            case '48h':
                filterDate.setHours(currentDate.getHours() - 48);
                break;
            case '72h':
                filterDate.setHours(currentDate.getHours() - 72);
                break;
        }
        
        // Format date as YYYY-MM-DD HH:mm:ss
        const formattedDate = filterDate.toISOString().slice(0, 19).replace('T', ' ');
        
        // Reload articles with new date filter
        reloadArticles(formattedDate);
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
