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

    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (subcategoryNav) {
        subcategoryNav.addEventListener('click', function(e) {
            const tabButton = e.target.closest('[role="tab"]');
            if (!tabButton) return;

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

function showLoadingState() {
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
}

function showError(message, error = null, retryCallback = null) {
    console.error('Error:', message, error);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        ${message}
        ${error ? `<br><small class="text-muted">Technical details: ${error.message || error}</small>` : ''}
        ${retryCallback ? '<button class="btn btn-outline-danger btn-sm ms-3" onclick="retryCallback()">Retry</button>' : ''}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(errorDiv, container.firstChild);
        if (!retryCallback) {
            setTimeout(() => errorDiv.remove(), 5000);
        }
    }
}

function fetchWithRetry(url, options = {}, retries = 3, delay = 1000) {
    return new Promise((resolve, reject) => {
        const attempt = async (attemptNumber) => {
            try {
                const response = await fetch(url, options);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                resolve(response);
            } catch (error) {
                console.error(`Attempt ${attemptNumber} failed:`, error);
                if (attemptNumber < retries) {
                    setTimeout(() => attempt(attemptNumber + 1), delay);
                } else {
                    reject(error);
                }
            }
        };
        attempt(1);
    });
}

function fetchSubcategories(categoryId) {
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (!subcategoryNav) return;

    fetchWithRetry(`/api/subcategories?category_id=${categoryId}`)
        .then(response => response.json())
        .then(subcategories => {
            return fetchWithRetry(`/api/articles?category_id=${categoryId}`)
                .then(response => response.json())
                .then(data => {
                    const subcatsWithEvents = new Set();
                    data.categories[0]?.subcategories.forEach(subcat => {
                        if (subcat.events && subcat.events.length > 0) {
                            subcatsWithEvents.add(subcat.subcategoria_id);
                        }
                    });

                    const filteredSubcats = subcategories.filter(subcat => 
                        subcatsWithEvents.has(subcat.id)
                    );

                    if (filteredSubcats.length > 0) {
                        updateSubcategoryTabs(filteredSubcats);
                        requestAnimationFrame(() => {
                            subcategoryNav.classList.add('visible');
                        });
                    } else {
                        hideSubcategoryTabs();
                    }
                });
        })
        .catch(error => {
            console.error('Error fetching subcategories:', error);
            hideSubcategoryTabs();
            showError('Error loading subcategories', error, () => fetchSubcategories(categoryId));
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
                    ${subcategory.nombre || 'Unnamed'}
                </button>
            </li>
        `).join('')}
    `;

    initializeScrollButtons();
}

function hideSubcategoryTabs() {
    const subcategoryNav = document.querySelector('.subcategory-nav');
    if (!subcategoryNav) return;
    
    subcategoryNav.classList.remove('visible');
}

function showAllCategories() {
    showLoadingState();
    
    fetchWithRetry('/api/articles')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid response format: response is not an object');
            }
            if (!Array.isArray(data.categories)) {
                throw new Error('Invalid response format: missing or invalid categories array');
            }
            
            updateDisplay(data);
            hideSubcategoryTabs();
        })
        .catch(error => {
            console.error('Error loading events:', error);
            showError('Failed to load articles', error, showAllCategories);
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
        });
}

function loadEventsByCategory(categoryId) {
    if (!categoryId) {
        console.error('Invalid category ID');
        return;
    }
    
    showLoadingState();
    
    fetchWithRetry(`/api/articles?category_id=${categoryId}`)
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
            showError(`Failed to load events for category ${categoryId}`, error, () => loadEventsByCategory(categoryId));
            showAllCategories();
        });
}

function loadEventsBySubcategory(categoryId, subcategoryId) {
    if (!categoryId || !subcategoryId) {
        console.error('Invalid category or subcategory ID');
        return;
    }
    
    showLoadingState();
    
    fetchWithRetry(`/api/articles?category_id=${categoryId}&subcategory_id=${subcategoryId}`)
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
            showError(`Failed to load events for subcategory ${subcategoryId}`, error, () => loadEventsBySubcategory(categoryId, subcategoryId));
            loadEventsByCategory(categoryId);
        });
}

function updateDisplay(data) {
    const eventsContent = document.getElementById('events-content');
    if (!eventsContent) return;

    try {
        if (!data || !data.categories) {
            showLoadingState();
            return;
        }
        
        if (data.categories.length === 0) {
            eventsContent.innerHTML = `
                <div class="alert alert-info">
                    <h4 class="alert-heading">Loading Content...</h4>
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Please wait while we fetch the latest articles...</p>
                </div>
            `;
            setTimeout(() => reloadArticles(), 2000);
            return;
        }

        const fragment = document.createDocumentFragment();
        
        data.categories.forEach(category => {
            const categorySection = document.createElement('div');
            categorySection.className = 'category-section mb-5';
            categorySection.dataset.categoryId = category.categoria_id || '';
            
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
        });

        initializeCarousels();
    } catch (error) {
        console.error('Error updating display:', error);
        showError('Error loading content. Retrying...');
        setTimeout(() => reloadArticles(), 2000);
    }
}