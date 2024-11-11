document.addEventListener('DOMContentLoaded', function() {
    const timeFilter = document.querySelector('.toggle-slider');
    
    if (!timeFilter) return;

    // Get initial time filter from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const currentFilter = urlParams.get('time_filter') || '72h';

    // Set the correct radio button based on URL parameter
    const selectedFilter = timeFilter.querySelector(`input[value="${currentFilter}"]`);
    if (selectedFilter) {
        selectedFilter.checked = true;
        const slider = timeFilter.querySelector('.slider');
        if (slider) {
            slider.style.transform = `translateX(${getSliderTransform(currentFilter)})`;
        }
    } else {
        // Fallback to 72h if no valid filter is found
        const defaultFilter = timeFilter.querySelector('input[value="72h"]');
        if (defaultFilter) {
            defaultFilter.checked = true;
            const slider = timeFilter.querySelector('.slider');
            if (slider) {
                slider.style.transform = `translateX(${getSliderTransform('72h')})`;
            }
        }
    }

    timeFilter.addEventListener('change', function(e) {
        if (!e.target.matches('input[type="radio"]')) return;
        
        // Update URL without page reload
        const newUrl = new URL(window.location);
        newUrl.searchParams.set('time_filter', e.target.value);
        window.history.pushState({}, '', newUrl);

        // Move slider
        const slider = timeFilter.querySelector('.slider');
        if (slider) {
            slider.style.transform = `translateX(${getSliderTransform(e.target.value)})`;
        }

        // Reload the content through API
        if (typeof loadCategoryContent === 'function') {
            const activeCategoryTab = document.querySelector('#categoryTabs .nav-link.active');
            if (activeCategoryTab) {
                const categoryId = activeCategoryTab.dataset.categoryId;
                if (categoryId) {
                    loadCategoryContent(categoryId);
                }
            }
        }
    });
});

function getSliderTransform(value) {
    switch(value) {
        case '24h': return '0';
        case '48h': return '4rem';
        case '72h': return '8rem';
        default: return '8rem';
    }
}
