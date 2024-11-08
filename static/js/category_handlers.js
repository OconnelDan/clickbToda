function initializeTabNavigation() {
    const categoryTabs = document.getElementById('categoryTabs');
    const subcategoryTabs = document.getElementById('subcategoryTabs');
    
    if (!categoryTabs || !subcategoryTabs) return;
    
    let selectedCategoryId = null;
    
    categoryTabs.addEventListener('click', function(e) {
        const tabButton = e.target.closest('[data-bs-toggle="tab"]');
        if (!tabButton) return;
        
        selectedCategoryId = tabButton.dataset.categoryId;
        if (!selectedCategoryId) {
            subcategoryTabs.innerHTML = '';
            return;
        }
        
        fetch(`/api/subcategories?category_id=${selectedCategoryId}`)
            .then(response => response.json())
            .then(subcategories => {
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
                        const subcategoryId = this.dataset.subcategoryId;
                        loadArticlesForCategoryAndSubcategory(selectedCategoryId, subcategoryId);
                    });
                });
            })
            .catch(error => console.error('Error loading subcategories:', error));
    });
}

function loadArticlesForCategoryAndSubcategory(categoryId, subcategoryId) {
    const timeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
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
    
    fetch(`/api/articles?category_id=${categoryId}&subcategory_id=${subcategoryId}&time_filter=${timeFilter}`)
        .then(response => response.json())
        .then(data => {
            updateDisplay(data);
        })
        .catch(error => {
            console.error('Error loading articles:', error);
            showError('Failed to load articles');
        });
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

        document.querySelectorAll('.article-card').forEach(card => {
            card.style.cursor = 'pointer';
            card.classList.add('article-card-clickable');
            card.addEventListener('click', function() {
                const url = this.dataset.articleUrl;
                if (url) {
                    window.open(url, '_blank');
                }
            });
        });
        
        initializeCarousels();
        initializeScrollButtons();
        
    } catch (error) {
        console.error('Error updating display:', error);
        showError('Failed to update display', error);
    }
}

function showError(message, error = null, retryCallback = null) {
    console.error('Error:', message, error);
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;

    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        <h4 class="alert-heading">${message}</h4>
        ${error ? `<p class="text-muted">Technical details: ${error.message || error}</p>` : ''}
        ${retryCallback ? '<button class="btn btn-outline-danger btn-sm mt-2" onclick="retryCallback()">Retry</button>' : ''}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    eventsContent.innerHTML = '';
    eventsContent.appendChild(errorDiv);
}

document.addEventListener('DOMContentLoaded', function() {
    initializeTabNavigation();
});
