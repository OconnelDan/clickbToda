document.addEventListener('DOMContentLoaded', function() {
    const categorySelector = document.getElementById('categorySelector');
    const subcategorySelector = document.getElementById('subcategorySelector');
    
    // Load all events initially without filters
    showAllCategories();
    
    // Initialize the category selector
    categorySelector.addEventListener('change', function() {
        const selectedCategoryId = this.value;
        if (selectedCategoryId) {
            fetchSubcategories(selectedCategoryId);
            loadEventsByCategory(selectedCategoryId);
        } else {
            resetSubcategorySelector();
            showAllCategories();
        }
    });
    
    // Handle subcategory selection
    subcategorySelector.addEventListener('change', function() {
        const selectedCategoryId = categorySelector.value;
        const selectedSubcategoryId = this.value;
        if (selectedCategoryId && selectedSubcategoryId) {
            loadEventsBySubcategory(selectedCategoryId, selectedSubcategoryId);
        }
    });
});

function showError(message, error = null) {
    console.error('Error:', message, error);
    
    // Remove any existing error messages
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
    container.insertBefore(errorDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

function handleApiError(error, operation) {
    console.error(`Error during ${operation}:`, error);
    
    let userMessage;
    if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        userMessage = `Failed to ${operation}. Server returned an error.`;
        console.error('Response:', error.response);
    } else if (error.request) {
        // The request was made but no response was received
        userMessage = 'Unable to reach the server. Please check your internet connection.';
        console.error('No response received:', error.request);
    } else {
        // Something happened in setting up the request that triggered an Error
        userMessage = 'An unexpected error occurred. Please try again.';
        console.error('Error details:', error.message);
    }
    
    showError(userMessage, error);
    
    // Return empty data structure to prevent undefined errors
    return {
        categories: []
    };
}

function fetchSubcategories(categoryId) {
    fetch(`/api/subcategories?category_id=${categoryId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            updateSubcategorySelector(data);
        })
        .catch(error => {
            handleApiError(error, 'load subcategories');
            resetSubcategorySelector(); // Recovery action
        });
}

function updateSubcategorySelector(subcategories) {
    const subcategorySelector = document.getElementById('subcategorySelector');
    subcategorySelector.innerHTML = '<option value="">Select Subcategory</option>';
    
    if (subcategories && subcategories.length > 0) {
        subcategorySelector.disabled = false;
        subcategories.forEach(subcategory => {
            const option = document.createElement('option');
            option.value = subcategory.id;
            option.textContent = subcategory.subnombre;
            subcategorySelector.appendChild(option);
        });
    } else {
        subcategorySelector.disabled = true;
    }
}

function resetSubcategorySelector() {
    const subcategorySelector = document.getElementById('subcategorySelector');
    subcategorySelector.innerHTML = '<option value="">Select Subcategory</option>';
    subcategorySelector.disabled = true;
}

function showAllCategories() {
    fetch('/api/articles')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data.categories) {
                throw new Error('Invalid response format: missing categories');
            }
            updateDisplay(data);
        })
        .catch(error => {
            handleApiError(error, 'load articles');
            // Show placeholder content
            const eventsContent = document.getElementById('events-content');
            eventsContent.innerHTML = `
                <div class="alert alert-info">
                    Unable to load articles. 
                    <button onclick="showAllCategories()" class="btn btn-link">Try Again</button>
                </div>
            `;
        });
}

function loadEventsByCategory(categoryId) {
    fetch(`/api/articles?category_id=${categoryId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data.categories) {
                throw new Error('Invalid response format: missing categories');
            }
            updateDisplay(data);
        })
        .catch(error => {
            handleApiError(error, 'load category articles');
            // Recovery: show all categories
            showAllCategories();
        });
}

function loadEventsBySubcategory(categoryId, subcategoryId) {
    fetch(`/api/articles?category_id=${categoryId}&subcategory_id=${subcategoryId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data.categories) {
                throw new Error('Invalid response format: missing categories');
            }
            updateDisplay(data);
        })
        .catch(error => {
            handleApiError(error, 'load subcategory articles');
            // Recovery: reload category view
            loadEventsByCategory(categoryId);
        });
}

function updateDisplay(data) {
    const eventsContent = document.getElementById('events-content');
    
    if (!data.categories || data.categories.length === 0) {
        eventsContent.innerHTML = `
            <div class="alert alert-info">
                No articles found for the selected criteria.
            </div>
        `;
        return;
    }
    
    eventsContent.innerHTML = '';

    data.categories.forEach(category => {
        const categorySection = document.createElement('div');
        categorySection.className = 'category-section mb-5';
        categorySection.dataset.categoryId = category.categoria_id;

        categorySection.innerHTML = `
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
        `;

        eventsContent.appendChild(categorySection);
    });

    // Initialize carousels after updating the display
    initializeCarousels();
}
