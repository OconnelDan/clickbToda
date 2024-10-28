document.addEventListener('DOMContentLoaded', function() {
    initializeTabNavigation();
    showAllCategories();
});

function initializeTabNavigation() {
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

    // Handle subcategory clicks with animation
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (subcategoryNav) {
        subcategoryNav.addEventListener('click', function(e) {
            const tabButton = e.target.closest('[role="tab"]');
            if (!tabButton) return;

            // Animate the transition
            const allSubcategoryTabs = subcategoryNav.querySelectorAll('[role="tab"]');
            allSubcategoryTabs.forEach(tab => {
                tab.classList.remove('active');
                tab.style.transition = 'all 0.3s ease';
            });
            
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

function showLoadingIndicator(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="text-center my-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading content...</p>
            </div>
        `;
    }
}

function showError(message, error = null) {
    console.error('Error:', message, error);
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
            console.log('Subcategories data:', data);
            if (data && data.length > 0) {
                updateSubcategoryTabs(data);
                // Add fade-in animation
                subcategoryNav.style.opacity = '0';
                subcategoryNav.style.display = 'block';
                setTimeout(() => {
                    subcategoryNav.style.transition = 'opacity 0.3s ease';
                    subcategoryNav.style.opacity = '1';
                }, 10);
            } else {
                hideSubcategoryTabs();
            }
        })
        .catch(error => {
            console.error('Error fetching subcategories:', error);
            hideSubcategoryTabs();
            showError('Failed to load subcategories', error);
        });
}

function updateSubcategoryTabs(subcategories) {
    const subcategoryTabs = document.getElementById('subcategoryTabs');
    if (!subcategoryTabs) return;

    // Create a Set to store unique subcategory names
    const uniqueSubcategories = new Set();
    const filteredSubcategories = subcategories.filter(subcat => {
        const key = `${subcat.id}-${subcat.subnombre}`;
        if (!uniqueSubcategories.has(key)) {
            uniqueSubcategories.add(key);
            return true;
        }
        return false;
    });

    subcategoryTabs.innerHTML = `
        <li class="nav-item" role="presentation">
            <button class="nav-link active" role="tab" data-subcategory-id="">
                All
            </button>
        </li>
        ${filteredSubcategories.map(subcategory => `
            <li class="nav-item" role="presentation">
                <button class="nav-link" role="tab" data-subcategory-id="${subcategory.id}">
                    ${subcategory.subnombre || 'Unnamed'}
                </button>
            </li>
        `).join('')}
    `;
}

function hideSubcategoryTabs() {
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (subcategoryNav) {
        subcategoryNav.style.transition = 'opacity 0.3s ease';
        subcategoryNav.style.opacity = '0';
        setTimeout(() => {
            subcategoryNav.style.display = 'none';
            subcategoryNav.innerHTML = '';
        }, 300);
    }
}

function showAllCategories() {
    showLoadingIndicator('events-content');
    
    fetch('/api/articles')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Received data structure:', data);
            
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid response format: response is not an object');
            }
            
            if (!Array.isArray(data.categories)) {
                throw new Error('Invalid response format: missing or invalid categories array');
            }
            
            // Validate data structure
            data.categories.forEach((category, index) => {
                if (!category.categoria_id || !category.nombre) {
                    console.warn(`Invalid category at index ${index}:`, category);
                }
            });

            updateDisplay(data);
            hideSubcategoryTabs();
        })
        .catch(error => {
            console.error('Error loading events:', error);
            const eventsContent = document.getElementById('events-content');
            if (eventsContent) {
                eventsContent.innerHTML = `
                    <div class="alert alert-warning">
                        <h4 class="alert-heading">Unable to load articles</h4>
                        <p>${error.message || 'An unexpected error occurred'}</p>
                        <hr>
                        <button onclick="showAllCategories()" class="btn btn-outline-warning">Try Again</button>
                    </div>
                `;
            }
            showError('Failed to load articles', error);
        });
}

function loadEventsByCategory(categoryId) {
    if (!categoryId) {
        console.error('Invalid category ID');
        return;
    }
    
    showLoadingIndicator('events-content');
    
    fetch(`/api/articles?category_id=${categoryId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log('Category events data:', data);
            if (!data.categories) throw new Error('Invalid response format: missing categories');
            updateDisplay(data);
        })
        .catch(error => {
            console.error('Error loading category events:', error);
            showError(`Failed to load events for category ${categoryId}`, error);
            showAllCategories();
        });
}

function loadEventsBySubcategory(categoryId, subcategoryId) {
    if (!categoryId || !subcategoryId) {
        console.error('Invalid category or subcategory ID');
        return;
    }
    
    showLoadingIndicator('events-content');
    
    fetch(`/api/articles?category_id=${categoryId}&subcategory_id=${subcategoryId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log('Subcategory events data:', data);
            if (!data.categories) throw new Error('Invalid response format: missing categories');
            updateDisplay(data);
        })
        .catch(error => {
            console.error('Error loading subcategory events:', error);
            showError(`Failed to load events for subcategory ${subcategoryId}`, error);
            loadEventsByCategory(categoryId);
        });
}

function updateDisplay(data) {
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) {
        console.error('Events content container not found');
        return;
    }

    try {
        console.log('Updating display with data:', data);
        
        if (!data.categories || !Array.isArray(data.categories) || data.categories.length === 0) {
            eventsContent.innerHTML = `
                <div class="alert alert-info">
                    <h4 class="alert-heading">No Content Available</h4>
                    <p>No articles found for the selected criteria.</p>
                </div>
            `;
            return;
        }

        eventsContent.innerHTML = data.categories.map(category => `
            <div class="category-section mb-5" data-category-id="${category.categoria_id || ''}"">
                <h2 class="mb-3">${category.nombre || 'Unnamed Category'}</h2>
                <div class="category-content">
                    ${(category.subcategories || []).map(subcategory => `
                        <div class="subcategory-section mb-4">
                            ${subcategory.subnombre ? 
                                `<h3 class="h4 mb-3">${subcategory.subnombre}</h3>` : 
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
                                                            <div class="article-card">
                                                                <div class="card h-100">
                                                                    <div class="card-body">
                                                                        <img src="${article.periodico_logo || '/static/img/default-newspaper.svg'}" 
                                                                             class="newspaper-logo mb-2" alt="Newspaper logo">
                                                                        <h5 class="card-title article-title ${article.paywall ? 'text-muted' : ''}">
                                                                            ${article.titular || 'No Title'}
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
    } catch (error) {
        console.error('Error updating display:', error);
        showError('Failed to render content', error);
        eventsContent.innerHTML = `
            <div class="alert alert-danger">
                <h4 class="alert-heading">Error Displaying Content</h4>
                <p>An error occurred while trying to display the content. Please try refreshing the page.</p>
                <hr>
                <button onclick="location.reload()" class="btn btn-outline-danger">Refresh Page</button>
            </div>
        `;
    }
}
