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

    posturasContent.innerHTML = '';
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
