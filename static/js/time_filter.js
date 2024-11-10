document.addEventListener('DOMContentLoaded', function() {
    const timeFilter = document.querySelector('.toggle-slider');
    
    if (!timeFilter) return;

    // Set default time filter to 72h
    const defaultFilter = timeFilter.querySelector('input[value="72h"]');
    if (defaultFilter) {
        defaultFilter.checked = true;
        const slider = timeFilter.querySelector('.slider');
        if (slider) {
            slider.style.transform = `translateX(${getSliderTransform('72h')})`;
        }
    }

    timeFilter.addEventListener('change', function(e) {
        if (!e.target.matches('input[type="radio"]')) return;
        
        // Reload the entire page to get fresh category counts
        window.location.href = '/?time_filter=' + e.target.value;
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