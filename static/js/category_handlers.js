document.addEventListener('DOMContentLoaded', function() {
    const categorySelector = document.getElementById('categorySelector');
    const subcategorySelector = document.getElementById('subcategorySelector');
    
    // Load all events initially without date filter
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

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.container').firstChild);
}

function fetchSubcategories(categoryId) {
    fetch(`/api/subcategories?category_id=${categoryId}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch subcategories');
            return response.json();
        })
        .then(data => {
            updateSubcategorySelector(data);
        })
        .catch(error => {
            console.error('Error fetching subcategories:', error);
            showError('Failed to load subcategories. Please try again.');
        });
}

function updateSubcategorySelector(subcategories) {
    const subcategorySelector = document.getElementById('subcategorySelector');
    subcategorySelector.innerHTML = '<option value="">Select Subcategory</option>';
    subcategorySelector.disabled = false;
    
    subcategories.forEach(subcategory => {
        const option = document.createElement('option');
        option.value = subcategory.id;
        option.textContent = subcategory.subnombre;
        subcategorySelector.appendChild(option);
    });
}

function resetSubcategorySelector() {
    const subcategorySelector = document.getElementById('subcategorySelector');
    subcategorySelector.innerHTML = '<option value="">Select Subcategory</option>';
    subcategorySelector.disabled = true;
}

function showAllCategories() {
    fetch('/api/articles')
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch articles');
            return response.json();
        })
        .then(data => {
            if (!data.categories) throw new Error('Invalid response format');
            
            document.querySelectorAll('.category-section').forEach(section => {
                const categoryId = section.dataset.categoryId;
                const categoryData = data.categories.find(c => c.categoria_id.toString() === categoryId);
                
                if (categoryData) {
                    section.style.display = 'block';
                    updateEventsDisplay(categoryData, categoryId);
                } else {
                    section.style.display = 'none';
                }
            });
        })
        .catch(error => {
            console.error('Error loading events:', error);
            showError('Failed to load articles. Please try refreshing the page.');
        });
}

function loadEventsByCategory(categoryId) {
    fetch(`/api/articles?category_id=${categoryId}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch articles');
            return response.json();
        })
        .then(data => {
            if (!data.categories || !data.categories.length) {
                throw new Error('No articles found for this category');
            }
            const categoryData = data.categories[0];
            updateEventsDisplay(categoryData, categoryId);
        })
        .catch(error => {
            console.error('Error loading events:', error);
            showError('Failed to load articles. Please try again.');
        });
}

function loadEventsBySubcategory(categoryId, subcategoryId) {
    fetch(`/api/articles?category_id=${categoryId}&subcategory_id=${subcategoryId}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch articles');
            return response.json();
        })
        .then(data => {
            if (!data.categories || !data.categories.length) {
                throw new Error('No articles found for this subcategory');
            }
            const categoryData = data.categories[0];
            updateEventsDisplay(categoryData, categoryId);
        })
        .catch(error => {
            console.error('Error loading events:', error);
            showError('Failed to load articles. Please try again.');
        });
}

function updateEventsDisplay(categoryData, categoryId) {
    const categorySection = document.querySelector(`.category-section[data-category-id="${categoryId}"]`);
    if (!categorySection) return;
    
    const eventsContainer = categorySection.querySelector('.events-container');
    
    if (categoryData.events && categoryData.events.length > 0) {
        eventsContainer.innerHTML = categoryData.events.map(event => `
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
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } else {
        eventsContainer.innerHTML = '<div class="alert alert-info">No events found</div>';
    }
}
