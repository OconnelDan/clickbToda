document.addEventListener('DOMContentLoaded', function() {
    initializeTabNavigation();
    showAllCategories();
});

function initializeTabNavigation() {
    // Initialize Bootstrap tabs
    const tabElements = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabElements.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const categoryId = event.target.dataset.categoryId;
            if (categoryId) {
                fetchSubcategories(categoryId);
                loadEventsByCategory(categoryId);
            } else {
                hideSubcategoryTabs();
                showAllCategories();
            }
        });
    });

    // Handle subcategory clicks
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (subcategoryNav) {
        subcategoryNav.addEventListener('click', function(e) {
            const tabButton = e.target.closest('[role="tab"]');
            if (!tabButton) return;

            // Remove active class from all subcategory tabs
            subcategoryNav.querySelectorAll('[role="tab"]').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Add active class to clicked tab
            tabButton.classList.add('active');

            const categoryId = document.querySelector('#categoryTabs .nav-link.active').dataset.categoryId;
            const subcategoryId = tabButton.dataset.subcategoryId;

            if (categoryId && subcategoryId) {
                loadEventsBySubcategory(categoryId, subcategoryId);
            } else if (categoryId) {
                loadEventsByCategory(categoryId);
            }
        });
    }
}

function showError(message, error = null) {
    console.error('Error:', message, error);
    const existingErrors = document.querySelectorAll('.alert-danger');
    existingErrors.forEach(error => error.remove());
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        ${message}
        ${error ? `<br><small class="text-muted">Technical details: ${error.message || error}</small>` : ''}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(errorDiv, container.firstChild);
        setTimeout(() => errorDiv.remove(), 5000);
    }
}

function fetchSubcategories(categoryId) {
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (!subcategoryNav) return;

    fetch(`/api/subcategories?category_id=${categoryId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data && data.length > 0) {
                updateSubcategoryTabs(data);
                subcategoryNav.style.display = 'block';
            } else {
                hideSubcategoryTabs();
            }
        })
        .catch(error => {
            console.error('Error fetching subcategories:', error);
            hideSubcategoryTabs();
        });
}

function updateSubcategoryTabs(subcategories) {
    const subcategoryTabs = document.getElementById('subcategoryTabs');
    if (!subcategoryTabs) return;

    subcategoryTabs.innerHTML = `
        <li class="nav-item" role="presentation">
            <button class="nav-link active" role="tab" data-subcategory-id="">
                All
            </button>
        </li>
        ${subcategories.map(subcategory => `
            <li class="nav-item" role="presentation">
                <button class="nav-link" role="tab" data-subcategory-id="${subcategory.id}">
                    ${subcategory.subnombre}
                </button>
            </li>
        `).join('')}
    `;
}

function hideSubcategoryTabs() {
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (subcategoryNav) {
        subcategoryNav.style.display = 'none';
        const subcategoryTabs = document.getElementById('subcategoryTabs');
        if (subcategoryTabs) {
            subcategoryTabs.innerHTML = '';
        }
    }
}

function showAllCategories() {
    fetch('/api/articles')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (!data.categories) throw new Error('Invalid response format: missing categories');
            updateDisplay(data);
            hideSubcategoryTabs();
        })
        .catch(error => {
            console.error('Error loading events:', error);
            const eventsContent = document.getElementById('events-content');
            if (eventsContent) {
                eventsContent.innerHTML = `
                    <div class="alert alert-info">
                        Unable to load articles. 
                        <button onclick="showAllCategories()" class="btn btn-link">Try Again</button>
                    </div>
                `;
            }
        });
}

function loadEventsByCategory(categoryId) {
    if (!categoryId) return;
    
    fetch(`/api/articles?category_id=${categoryId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (!data.categories) throw new Error('Invalid response format: missing categories');
            updateDisplay(data);
        })
        .catch(error => {
            console.error('Error loading category events:', error);
            showAllCategories();
        });
}

function loadEventsBySubcategory(categoryId, subcategoryId) {
    if (!categoryId || !subcategoryId) return;
    
    fetch(`/api/articles?category_id=${categoryId}&subcategory_id=${subcategoryId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (!data.categories) throw new Error('Invalid response format: missing categories');
            updateDisplay(data);
        })
        .catch(error => {
            console.error('Error loading subcategory events:', error);
            loadEventsByCategory(categoryId);
        });
}

function updateDisplay(data) {
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;

    if (!data.categories || data.categories.length === 0) {
        eventsContent.innerHTML = `
            <div class="alert alert-info">
                No articles found for the selected criteria.
            </div>
        `;
        return;
    }

    eventsContent.innerHTML = data.categories.map(category => `
        <div class="category-section mb-5" data-category-id="${category.categoria_id}">
            <h2 class="mb-3">${category.nombre}</h2>
            <div class="category-content">
                ${category.subcategories.map(subcategory => `
                    <div class="subcategory-section mb-4">
                        ${subcategory.subnombre ? 
                            `<h3 class="h4 mb-3">${subcategory.subnombre}</h3>` : 
                            ''}
                        <div class="events-container">
                            ${subcategory.events.map(event => `
                                <div class="event-articles mb-4">
                                    <div class="row">
                                        <div class="col-md-3">
                                            <div class="event-info">
                                                <h4 class="event-title">${event.titulo}</h4>
                                                <p class="event-description">${event.descripcion || ''}</p>
                                                <div class="event-meta">
                                                    <small class="text-muted">${event.fecha_evento || ''}</small>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="col-md-9">
                                            <div class="articles-carousel">
                                                <div class="carousel-wrapper">
                                                    ${event.articles.map(article => `
                                                        <div class="article-card">
                                                            <div class="card h-100">
                                                                <div class="card-body">
                                                                    <img src="${article.periodico_logo || '/static/img/default-newspaper.svg'}" 
                                                                         class="newspaper-logo mb-2" alt="Newspaper logo">
                                                                    <h5 class="card-title article-title ${article.paywall ? 'text-muted' : ''}">
                                                                        ${article.titular}
                                                                    </h5>
                                                                    ${article.paywall ? '<span class="badge bg-secondary">Paywall</span>' : ''}
                                                                    <div class="article-meta mt-2">
                                                                        <small class="text-muted">${article.fecha_publicacion || ''}</small>
                                                                    </div>
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
        </div>
    `).join('');

    initializeCarousels();
}
