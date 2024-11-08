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
        
        const selectedFilter = e.target.value;
        updateCategoryData(selectedFilter);
        reloadArticles();
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

function updateCategoryData(timeFilter) {
    // Show loading state
    const categoryTabs = document.getElementById('categoryTabs');
    if (!categoryTabs) return;
    
    categoryTabs.innerHTML = `
        <div class="text-center">
            <div class="spinner-border spinner-border-sm text-primary" role="status">
                <span class="visually-hidden">Loading categories...</span>
            </div>
        </div>
    `;
    
    fetch(`/api/categories/hierarchy?time_filter=${timeFilter}`)
        .then(response => response.json())
        .then(categories => {
            categoryTabs.innerHTML = `
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="all-categories-tab" 
                            data-bs-toggle="tab" data-bs-target="#all-categories" 
                            type="button" role="tab">
                        All Categories
                    </button>
                </li>
                ${categories.map(cat => `
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="category-${cat.categoria_id}-tab" 
                                data-bs-toggle="tab" data-bs-target="#category-${cat.categoria_id}" 
                                type="button" role="tab" data-category-id="${cat.categoria_id}">
                            ${cat.nombre}
                            <span class="badge bg-secondary ms-1">${cat.article_count}</span>
                        </button>
                    </li>
                `).join('')}
            `;
            
            // Re-initialize category click handlers
            initializeSubcategoryHandlers();
        })
        .catch(error => {
            console.error('Error updating category data:', error);
            categoryTabs.innerHTML = `
                <div class="alert alert-danger">
                    Failed to load categories. Please try again.
                </div>
            `;
        });
}

function reloadArticles() {
    const activeTab = document.querySelector('#categoryTabs .nav-link.active');
    const categoryId = activeTab ? activeTab.dataset.categoryId : null;
    const timeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
    
    // Show loading state
    document.getElementById('events-content').innerHTML = `
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading articles...</p>
        </div>
    `;
    
    let url = '/api/articles';
    const params = new URLSearchParams();
    
    if (categoryId) params.append('category_id', categoryId);
    params.append('time_filter', timeFilter);
    
    if (params.toString()) url += `?${params.toString()}`;
    
    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch articles');
            return response.json();
        })
        .then(data => {
            updateDisplay(data);
            initializeCarousels();
        })
        .catch(error => {
            console.error('Error loading articles:', error);
            document.getElementById('events-content').innerHTML = `
                <div class="alert alert-danger">
                    Failed to load articles. Please try again.
                </div>
            `;
        });
}
