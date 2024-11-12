document.addEventListener('DOMContentLoaded', function() {
    const timeFilter = document.querySelector('.toggle-slider');
    const eventsContent = document.getElementById('events-content');
    
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
        
        // Get current active category
        const activeCategory = document.querySelector('#categoryTabs .nav-link.active');
        const activeSubcategory = document.querySelector('#subcategoryTabs .nav-link.active');
        
        const timeRange = e.target.value;
        
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
