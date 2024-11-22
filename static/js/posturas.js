document.addEventListener('DOMContentLoaded', function() {
    // Initialize article modal
    const modalElement = document.getElementById('articleModal');
    if (modalElement) {
        articleModal = new bootstrap.Modal(modalElement);
    }
    
    // Initialize category navigation
    initializeTabNavigation();
    loadDefaultCategory();
});

function loadPosturas(categoryId = null, subcategoryId = null) {
    const posturasContent = document.getElementById('posturas-content');
    const timeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
    
    let url = '/api/posturas';
    const params = new URLSearchParams();
    
    if (categoryId) params.append('category_id', categoryId);
    if (subcategoryId) params.append('subcategory_id', subcategoryId);
    params.append('time_filter', timeFilter);
    
    url += `?${params.toString()}`;
    
    showLoading();
    
    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            updatePosturasDisplay(data);
        })
        .catch(error => {
            console.error('Error loading posturas:', error);
            showError('Error al cargar las posturas. Por favor, intente nuevamente.');
        });
}

function updatePosturasDisplay(data) {
    const posturasContent = document.getElementById('posturas-content');
    hideLoading();
    
    if (!Array.isArray(data) || data.length === 0) {
        posturasContent.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info">
                    No hay posturas disponibles en este momento.
                </div>
            </div>
        `;
        return;
    }

    posturasContent.innerHTML = data.map(evento => `
        <div class="evento-card mb-4">
            <div class="card">
                <div class="card-header">
                    <div class="d-flex justify-content-between align-items-center">
                        <h3 class="card-title mb-0">${evento.titulo || 'Sin título'}</h3>
                        <div>
                            <span class="badge bg-primary me-2">${evento.categoria_nombre || ''}</span>
                            <span class="badge bg-secondary">${evento.subcategoria_nombre || ''}</span>
                        </div>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <div class="evento-info">
                                <p class="evento-descripcion">${evento.descripcion || ''}</p>
                                <small class="text-muted">${evento.fecha || ''}</small>
                            </div>
                        </div>
                        <div class="col-md-8">
                            <div class="posturas-container">
                                ${evento.posturas.map(postura => `
                                    <div class="postura-box mb-3">
                                        <h4 class="h5 mb-3">${postura.titulo || ''}</h4>
                                        <div class="row">
                                            <div class="col-md-6 border-end">
                                                <div class="opinion-box p-3">
                                                    <span class="badge bg-success mb-2">Perspectiva 1</span>
                                                    <p class="mb-3">${postura.opinion_conjunto_1 || ''}</p>
                                                    <div class="articles-list">
                                                        ${(postura.articulos_ids_conjunto_1 || []).map(id => `
                                                            <button class="btn btn-article article-link m-1" 
                                                                    data-article-id="${id}">
                                                                <img src="/static/img/default-newspaper.svg" 
                                                                     class="newspaper-logo-small" 
                                                                     alt="Logo periódico"
                                                                     data-article-id="${id}">
                                                            </button>
                                                        `).join('')}
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="col-md-6">
                                                <div class="opinion-box p-3">
                                                    <span class="badge bg-danger mb-2">Perspectiva 2</span>
                                                    <p class="mb-3">${postura.opinion_conjunto_2 || ''}</p>
                                                    <div class="articles-list">
                                                        ${(postura.articulos_ids_conjunto_2 || []).map(id => `
                                                            <button class="btn btn-article article-link m-1" 
                                                                    data-article-id="${id}">
                                                                <img src="/static/img/default-newspaper.svg" 
                                                                     class="newspaper-logo-small" 
                                                                     alt="Logo periódico"
                                                                     data-article-id="${id}">
                                                            </button>
                                                        `).join('')}
                                                    </div>
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
        </div>
    `).join('');

    // Add click handlers for article links
    document.querySelectorAll('.article-link').forEach(button => {
        button.addEventListener('click', function() {
            const articleId = this.dataset.articleId;
            if (articleModal) {
                articleModal.show();
            }
            fetchArticleDetails(articleId);
        });
    });
}

function showLoading() {
    const posturasContent = document.getElementById('posturas-content');
    posturasContent.innerHTML = `
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="mt-2">Cargando posturas...</p>
        </div>
    `;
}

function hideLoading() {
    const loadingDiv = document.querySelector('#posturas-content .text-center');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

function showError(message) {
    const posturasContent = document.getElementById('posturas-content');
    posturasContent.innerHTML = `
        <div class="col-12">
            <div class="alert alert-danger">
                ${message}
            </div>
        </div>
    `;
}

// Override category handlers for posturas page
function loadCategoryContent(categoryId) {
    if (!categoryId) {
        console.error('No category ID provided');
        showError('Invalid category selection');
        return;
    }

    loadPosturas(categoryId);
}

function loadArticlesForSubcategory(subcategoryId) {
    if (!subcategoryId) {
        console.error('No subcategory ID provided');
        return;
    }

    loadPosturas(null, subcategoryId);
}
