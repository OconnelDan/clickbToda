document.addEventListener('DOMContentLoaded', function() {
    initializeTabNavigation();
    loadDefaultCategory();
});

function initializeTabNavigation() {
    const categoryTabs = document.getElementById('categoryTabs');
    const subcategoryTabs = document.getElementById('subcategoryTabs');
    
    if (!categoryTabs || !subcategoryTabs) return;
    
    let selectedCategoryId = null;
    let lastLoadedCategoryId = null;
    
    // Add touch scrolling for navigation bars
    [categoryTabs, subcategoryTabs].forEach(container => {
        let touchStartX = 0;
        let startScrollLeft = 0;
        
        container.addEventListener('touchstart', e => {
            touchStartX = e.touches[0].clientX;
            startScrollLeft = container.scrollLeft;
            container.style.scrollBehavior = 'auto';
        }, { passive: true });
        
        container.addEventListener('touchmove', e => {
            const touchCurrentX = e.touches[0].clientX;
            const diff = touchStartX - touchCurrentX;
            container.scrollLeft = startScrollLeft + diff;
        }, { passive: true });
        
        container.addEventListener('touchend', () => {
            container.style.scrollBehavior = 'smooth';
        });
    });
    
    // Category tab click handler
    categoryTabs.addEventListener('click', function(e) {
        const tabButton = e.target.closest('[data-bs-toggle="tab"]');
        if (!tabButton) return;
        
        selectedCategoryId = tabButton.dataset.categoryId;
        if (!selectedCategoryId) return;
        
        // Remove active class from all tabs and add to selected
        categoryTabs.querySelectorAll('.nav-link').forEach(tab => tab.classList.remove('active'));
        tabButton.classList.add('active');
        
        showLoadingState();
        loadCategoryContent(selectedCategoryId);
    });
}

function loadDefaultCategory() {
    const categoryTabs = document.querySelectorAll('#categoryTabs .nav-link');
    if (categoryTabs.length > 0) {
        // Remove active class from any previously active tabs
        categoryTabs.forEach(tab => tab.classList.remove('active'));
        // Set the first category as active
        categoryTabs[0].classList.add('active');
        // Load content for the first category
        const categoryId = categoryTabs[0].dataset.categoryId;
        if (categoryId) {
            loadCategoryContent(categoryId);
        }
    }
}

function loadCategoryContent(categoryId) {
    if (!categoryId) {
        console.error('No category ID provided');
        showError('Invalid category selection');
        return;
    }

    const timeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
    const subcategoryTabs = document.getElementById('subcategoryTabs');
    
    // Clear existing subcategories
    subcategoryTabs.innerHTML = '';
    
    // Show loading state before fetching
    showLoadingState();
    
    // Fetch subcategories and articles simultaneously
    Promise.all([
        fetch(`/api/subcategories?category_id=${categoryId}`).then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        }),
        fetch(`/api/articles?category_id=${categoryId}&time_filter=${timeFilter}`).then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
    ])
    .then(([subcategories, articlesData]) => {
        updateSubcategoryTabs(subcategories);
        updateDisplay(articlesData);
        hideLoadingState();
    })
    .catch(error => {
        console.error('Error loading category content:', error);
        showError(`Failed to load category content: ${error.message}`);
        hideLoadingState();
    });
}

function updateSubcategoryTabs(subcategories) {
    const subcategoryTabs = document.getElementById('subcategoryTabs');
    if (!subcategoryTabs) return;
    
    if (!Array.isArray(subcategories)) {
        console.error('Invalid subcategories data:', subcategories);
        return;
    }
    
    subcategoryTabs.innerHTML = subcategories.map(subcat => `
        <li class="nav-item" role="presentation">
            <button class="nav-link" 
                    data-bs-toggle="pill"
                    data-subcategory-id="${subcat.id}"
                    type="button">
                ${subcat.nombre}
                <span class="badge bg-secondary ms-1">${subcat.article_count || 0}</span>
            </button>
        </li>
    `).join('');
    
    // Initialize subcategory click handlers
    subcategoryTabs.querySelectorAll('[data-subcategory-id]').forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all subcategory tabs
            subcategoryTabs.querySelectorAll('.nav-link').forEach(tab => tab.classList.remove('active'));
            // Add active class to clicked tab
            this.classList.add('active');
            
            const subcategoryId = this.dataset.subcategoryId;
            loadArticlesForSubcategory(subcategoryId);
        });
    });
}

function loadArticlesForSubcategory(subcategoryId) {
    if (!subcategoryId) {
        console.error('No subcategory ID provided');
        return;
    }

    const timeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
    showLoadingState();
    
    fetch(`/api/articles?subcategory_id=${subcategoryId}&time_filter=${timeFilter}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            updateDisplay(data);
            hideLoadingState();
        })
        .catch(error => {
            console.error('Error loading subcategory articles:', error);
            showError(`Failed to load articles: ${error.message}`);
            hideLoadingState();
        });
}

function showLoadingState() {
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;
    
    eventsContent.innerHTML = `
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading content...</p>
        </div>
    `;
}

function hideLoadingState() {
    const loadingDiv = document.querySelector('#events-content .text-center');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

function showError(message, error = null) {
    console.error('Error:', message, error);
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;

    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        <h4 class="alert-heading">Error</h4>
        <p>${message}</p>
        ${error ? `<p class="text-muted small">Technical details: ${error.message || error}</p>` : ''}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    eventsContent.innerHTML = '';
    eventsContent.appendChild(errorDiv);
}

function updateDisplay(data) {
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;

    try {
        if (!data || !data.categories) {
            throw new Error('Invalid response format');
        }
        
        if (data.categories.length === 0) {
            eventsContent.innerHTML = `
                <div class="alert alert-info">
                    <h4 class="alert-heading">No articles found</h4>
                    <p>Try selecting a different category or time range.</p>
                </div>
            `;
            return;
        }

        const fragment = document.createDocumentFragment();
        
        data.categories.forEach(category => {
            const categorySection = document.createElement('div');
            categorySection.className = 'category-section mb-5';
            categorySection.dataset.categoryId = category.categoria_id || '';
            categorySection.dataset.loaded = 'true';
            
            categorySection.innerHTML = `
                <h2 class="mb-3">${category.nombre || 'Unnamed Category'}</h2>
                <div class="category-content">
                    ${(category.subcategories || []).map(subcategory => `
                        <div class="subcategory-section mb-4">
                            ${subcategory.nombre ? 
                                `<h3 class="h4 mb-3">${subcategory.nombre}</h3>` : 
                                ''}
                            <div class="events-container">
                                ${(subcategory.events || []).map(event => `
                                    <div class="event-articles mb-4">
                                        <div class="row">
                                            <div class="col-md-3">
                                                <div class="event-info">
                                                    <h4 class="event-title">${event.titulo || 'Untitled Event'}</h4>
                                                    <p class="event-description">${event.descripcion || ''}</p>
                                                    <div class="event-meta">
                                                        <small class="text-muted">${event.fecha_evento || ''}</small>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="col-md-9">
                                                <div class="articles-carousel">
                                                    <div class="carousel-wrapper">
                                                        ${(event.articles || []).map(article => `
                                                            <div class="article-card" data-article-id="${article.id}" data-article-url="${article.url || ''}" role="button">
                                                                <div class="card h-100">
                                                                    <div class="card-body">
                                                                        <img src="${article.periodico_logo || '/static/img/default-newspaper.svg'}" 
                                                                             class="newspaper-logo mb-2" alt="Newspaper logo">
                                                                        <h5 class="card-title article-title ${article.paywall ? 'text-muted' : ''}">
                                                                            ${article.titular || 'No Title'}
                                                                        </h5>
                                                                        ${article.gpt_opinion ? `<div class="article-opinion">${article.gpt_opinion}</div>` : ''}
                                                                        ${article.paywall ? '<span class="badge bg-secondary">Paywall</span>' : ''}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        `).join('')}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            
            fragment.appendChild(categorySection);
        });
        
        eventsContent.innerHTML = '';
        eventsContent.appendChild(fragment);

        // Initialize article cards
        document.querySelectorAll('.article-card').forEach(card => {
            card.style.cursor = 'pointer';
            card.classList.add('article-card-clickable');
        });
        
        initializeCarousels();
        initializeScrollButtons();
        
    } catch (error) {
        console.error('Error updating display:', error);
        showError('Failed to update display', error);
    }
}
