document.addEventListener('DOMContentLoaded', function() {
    loadPosturas();
});

function loadPosturas() {
    const posturasContent = document.getElementById('posturas-content');
    
    fetch('/api/posturas')
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
    
    if (!data || data.length === 0) {
        posturasContent.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info">
                    No hay posturas disponibles en este momento.
                </div>
            </div>
        `;
        return;
    }

    posturasContent.innerHTML = data.map(postura => `
        <div class="postura-card mb-4">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">${postura.titulo}</h3>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 border-end">
                            <div class="opinion-box p-3">
                                <h4 class="h5 mb-3">Perspectiva 1</h4>
                                <p>${postura.opinion_conjunto_1}</p>
                                <div class="articles-list mt-3">
                                    ${postura.articulos_ids_conjunto_1.map(id => `
                                        <button class="btn btn-link article-link" 
                                                data-article-id="${id}">
                                            Ver artículo
                                        </button>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="opinion-box p-3">
                                <h4 class="h5 mb-3">Perspectiva 2</h4>
                                <p>${postura.opinion_conjunto_2}</p>
                                <div class="articles-list mt-3">
                                    ${postura.articulos_ids_conjunto_2.map(id => `
                                        <button class="btn btn-link article-link" 
                                                data-article-id="${id}">
                                            Ver artículo
                                        </button>
                                    `).join('')}
                                </div>
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
            const articleModal = new bootstrap.Modal(document.getElementById('articleModal'));
            articleModal.show();
            fetchArticleDetails(articleId);
        });
    });
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
