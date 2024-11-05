document.addEventListener('DOMContentLoaded', function() {
    initializeTabNavigation();
    showAllCategories();
});

// ... [previous code remains the same until updateDisplay function] ...

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
                                                                <a href="${article.url || '#'}" target="_blank" rel="noopener noreferrer" class="card-link">
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
                                                                </a>
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
