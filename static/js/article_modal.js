document.addEventListener('DOMContentLoaded', function() {
    // Initialize the Bootstrap modal
    const articleModal = new bootstrap.Modal(document.getElementById('articleModal'));
    
    // Add click event listeners to all article cards
    document.addEventListener('click', function(event) {
        const articleCard = event.target.closest('.article-card');
        if (!articleCard) return;
        
        event.preventDefault();
        const articleId = articleCard.dataset.articleId;
        
        // Show modal with loading state
        showLoading(true);
        hideError();
        articleModal.show();
        
        // Fetch article details
        fetch(`/api/article/${articleId}`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(article => {
                updateModalContent(article);
                showLoading(false);
            })
            .catch(error => {
                console.error('Error loading article details:', error);
                showError('Failed to load article details. Please try again.');
                showLoading(false);
            });
    });
});

function showLoading(show) {
    const spinner = document.getElementById('articleLoadingSpinner');
    const content = document.getElementById('articleContent');
    
    if (show) {
        spinner.classList.remove('d-none');
        content.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
        content.classList.remove('d-none');
    }
}

function showError(message) {
    const errorDiv = document.getElementById('articleErrorMessage');
    errorDiv.textContent = message;
    errorDiv.classList.remove('d-none');
}

function hideError() {
    const errorDiv = document.getElementById('articleErrorMessage');
    errorDiv.classList.add('d-none');
}

function updateModalContent(article) {
    // Update basic article information
    document.getElementById('modalNewspaperLogo').src = article.periodico_logo || '/static/img/default-newspaper.svg';
    document.getElementById('articleModalLabel').textContent = article.titular;
    document.getElementById('articleSubtitle').textContent = article.subtitular || '';
    document.getElementById('articleDate').textContent = article.fecha_publicacion || '';
    document.getElementById('articleAuthor').textContent = article.periodista || '';
    document.getElementById('articleAgency').textContent = article.agencia || '';
    
    // Update summary and opinion
    document.getElementById('articleSummary').textContent = article.gpt_resumen || 'No summary available';
    document.getElementById('articleOpinion').textContent = article.gpt_opinion || 'No opinion available';
    
    // Update keywords with badges
    const keywordsDiv = document.getElementById('articleKeywords');
    if (article.gpt_palabras_clave) {
        const keywords = article.gpt_palabras_clave.split(',').map(keyword => 
            `<span class="badge bg-secondary me-1">${keyword.trim()}</span>`
        ).join('');
        keywordsDiv.innerHTML = keywords;
    } else {
        keywordsDiv.innerHTML = '<span class="text-muted">No keywords available</span>';
    }
    
    // Update sources count
    document.getElementById('articleSources').textContent = 
        article.gpt_cantidad_fuentes_citadas ? 
        `${article.gpt_cantidad_fuentes_citadas} sources cited` : 
        'No source information available';
    
    // Update article link
    document.getElementById('articleLink').href = article.url;
    
    // Show/hide paywall warning
    const paywallWarning = document.getElementById('paywallWarning');
    if (article.paywall) {
        paywallWarning.classList.remove('d-none');
    } else {
        paywallWarning.classList.add('d-none');
    }
}
