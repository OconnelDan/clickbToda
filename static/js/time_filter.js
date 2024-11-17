document.addEventListener('DOMContentLoaded', function() {
    const timeFilterGroup = document.querySelector('.time-filter-group');
    if (!timeFilterGroup) return;

    // Set default time filter to 72h
    const defaultFilter = timeFilterGroup.querySelector('input[value="72h"]');
    if (defaultFilter) {
        defaultFilter.checked = true;
    }

    timeFilterGroup.addEventListener('change', function(e) {
        if (!e.target.matches('input[type="radio"]')) return;
        
        // Update navigation first
        updateNavigation();
        
        // Then show loading state and reload articles
        const eventsContent = document.getElementById('events-content');
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
        
        // Get current active category
        const activeCategory = document.querySelector('#categoryTabs .nav-link.active');
        const activeSubcategory = document.querySelector('#subcategoryTabs .nav-link.active');
        
        // If a subcategory is active, reload its articles
        if (activeSubcategory && activeSubcategory.dataset.subcategoryId) {
            loadArticlesForSubcategory(activeSubcategory.dataset.subcategoryId);
        }
        // Otherwise, reload the active category's content
        else if (activeCategory && activeCategory.dataset.categoryId) {
            loadCategoryContent(activeCategory.dataset.categoryId);
        }
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

function reloadArticles(timeRange) {
    const activeCategory = document.querySelector('#categoryTabs .nav-link.active');
    const activeSubcategory = document.querySelector('#subcategoryTabs .nav-link.active');
    
    if (activeSubcategory && activeSubcategory.dataset.subcategoryId) {
        loadArticlesForSubcategory(activeSubcategory.dataset.subcategoryId);
    } else if (activeCategory && activeCategory.dataset.categoryId) {
        loadCategoryContent(activeCategory.dataset.categoryId);
    }
}