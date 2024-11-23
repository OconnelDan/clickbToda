let articleModal;
document.addEventListener('DOMContentLoaded', function() {
    const modalElement = document.getElementById('articleModal');
    if (modalElement) {
        articleModal = new bootstrap.Modal(modalElement);
    }
    loadMapData();

    // Add time filter change handler
    document.querySelector('.time-filter-group').addEventListener('change', function(e) {
        if (e.target.matches('input[type="radio"]')) {
            loadMapData();
        }
    });
});

function loadMapData() {
    const timeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
    const plotContainer = document.getElementById('tsne-plot');
    
    // Show loading state with improved visibility
    plotContainer.innerHTML = `
        <div class="map-loading-container">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Generando visualización...</span>
            </div>
            <div class="loading-steps">
                <p class="mb-2">Procesando datos y generando el mapa...</p>
                <div class="progress">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 100%"></div>
                </div>
            </div>
        </div>
    `;
    
    fetch(`/api/mapa-data?time_filter=${timeFilter}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data.error === 'no_articles') {
                showError(data.message || 'No hay suficientes datos para generar la visualización.');
                return;
            }
            
            if (!data.points || data.points.length === 0) {
                showError('No hay suficientes artículos con embeddings válidos para generar la visualización.');
                return;
            }
            
            // Update articles count in the UI
            const countBadge = document.querySelector('.badge.bg-info');
            if (countBadge) {
                countBadge.textContent = `Artículos visualizados: ${data.points.length}`;
            }
            
            createVisualization(data);
        })
        .catch(error => {
            console.error('Error loading map data:', error);
            showError('Error al cargar los datos del mapa. Por favor, intente nuevamente.');
        });
}

function createVisualization(data) {
    const { points, clusters } = data;
    
    // Create scatter plot for articles
    // Group points by category
    const categories = [...new Set(points.map(p => p.categoria || 'Sin categoría'))];
    const traces = categories.map(cat => {
        const catPoints = points.filter(p => (p.categoria || 'Sin categoría') === cat);
        return {
            name: cat,
            x: catPoints.map(p => p.coordinates[0]),
            y: catPoints.map(p => p.coordinates[1]),
            mode: 'markers',
            type: 'scatter',
            marker: {
                size: 8,
                opacity: 0.7
            },
            text: catPoints.map(p => 
                `<b>${p.titular}</b><br>` +
                `<b>Periódico:</b> ${p.periodico}<br>` +
                `<b>Categoría:</b> ${p.categoria || 'N/A'}<br>` +
                `<b>Subcategoría:</b> ${p.subcategoria || 'N/A'}<br>` +
                `<b>Keywords:</b> ${p.keywords || 'N/A'}<br>` +
                `<b>Resumen:</b> ${p.resumen || 'N/A'}`
            ),
            hoverinfo: 'text',
            hovertemplate: '%{text}<extra></extra>'
        };
    });

    // Create annotations for cluster keywords
    const annotations = clusters.map(cluster => ({
        x: cluster.center[0],
        y: cluster.center[1],
        text: cluster.keyword,
        showarrow: false,
        font: {
            size: 12,
            color: 'rgba(255, 255, 255, 0.5)'
        },
        bgcolor: 'rgba(0, 0, 0, 0)',  // Removed background
        borderpad: 0,
        borderwidth: 0,
        layer: 'below'  // Place text below points
    }));

    const layout = {
        title: 'Mapa de Artículos por Categoría',
        showlegend: true,
        legend: {
            title: {
                text: 'Categorías'
            },
            x: 1.05,
            y: 0.5
        },
        hovermode: 'closest',
        margin: {
            l: 50,
            r: 50,
            b: 50,
            t: 50,
            pad: 4
        },
        xaxis: {
            showgrid: false,
            zeroline: false,
            showticklabels: false,
            title: ''
        },
        yaxis: {
            showgrid: false,
            zeroline: false,
            showticklabels: false,
            title: ''
        },
        plot_bgcolor: 'rgba(0,0,0,0)',
        paper_bgcolor: 'rgba(0,0,0,0)',
        annotations: annotations
    };

    const config = {
        responsive: true,
        scrollZoom: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['select2d', 'lasso2d'],
        displaylogo: false
    };

    Plotly.newPlot('tsne-plot', traces, layout, config)
        .then(() => {
            // Remove loading container after plot is created
            const loadingContainer = document.querySelector('.map-loading-container');
            if (loadingContainer) {
                loadingContainer.remove();
            }
            
            // Add click handler for points
            document.getElementById('tsne-plot').on('plotly_click', function(data) {
                const point = data.points[0];
                const articleData = points[point.pointIndex];
                if (articleModal && articleData) {
                    articleModal.show();
                    fetchArticleDetails(articleData.id);
                }
            });
        })
        .catch(error => {
            console.error('Error creating visualization:', error);
            showError('Error al crear la visualización. Por favor, intente nuevamente.');
        });
}

function showError(message) {
    const plotContainer = document.getElementById('tsne-plot');
    plotContainer.innerHTML = `
        <div class="alert alert-danger" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); max-width: 80%;">
            <h4 class="alert-heading">Error</h4>
            <p>${message}</p>
            <button class="btn btn-outline-danger btn-sm mt-2" onclick="loadMapData()">
                Reintentar
            </button>
        </div>
    `;
}
