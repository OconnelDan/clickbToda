document.addEventListener('DOMContentLoaded', function() {
    // Initialize article modal
    const modalElement = document.getElementById('articleModal');
    if (modalElement) {
        articleModal = new bootstrap.Modal(modalElement);
    }
    
    loadVisualization();
});

function loadVisualization() {
    const container = document.getElementById('visualization-container');
    const timeFilter = document.querySelector('input[name="timeFilter"]:checked').value;
    
    fetch(`/api/visualizacion?time_filter=${timeFilter}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data.error) {
                showError(data.error);
                return;
            }
            
            const trace = {
                x: data.x,
                y: data.y,
                mode: 'markers',
                type: 'scatter',
                text: data.titles,
                hovertemplate: 
                    '<b>%{text}</b><br>' +
                    'Categoría: %{customdata[0]}<br>' +
                    'Subcategoría: %{customdata[1]}<br>' +
                    '<extra></extra>',
                marker: {
                    size: 10,
                    color: data.categories,
                    colorscale: 'Viridis',
                    opacity: 0.7
                },
                customdata: data.categories.map((cat, i) => [cat, data.subcategories[i]])
            };

            const layout = {
                title: 'Visualización de Artículos por Similitud',
                showlegend: false,
                hovermode: 'closest',
                xaxis: {
                    title: 'Dimensión 1',
                    showgrid: false,
                    zeroline: false
                },
                yaxis: {
                    title: 'Dimensión 2',
                    showgrid: false,
                    zeroline: false
                },
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)'
            };

            Plotly.newPlot('visualization-container', [trace], layout);

            // Add click event
            container.on('plotly_click', function(data) {
                const point = data.points[0];
                const articleId = data.ids[point.pointIndex];
                if (articleModal) {
                    articleModal.show();
                    fetchArticleDetails(articleId);
                }
            });
        })
        .catch(error => {
            console.error('Error loading visualization:', error);
            showError('Error al cargar la visualización. Por favor, intente nuevamente.');
        });
}

function showError(message) {
    const container = document.getElementById('visualization-container');
    container.innerHTML = `
        <div class="alert alert-danger">
            ${message}
        </div>
    `;
}
