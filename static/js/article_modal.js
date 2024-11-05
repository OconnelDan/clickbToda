document.addEventListener('DOMContentLoaded', function() {
    const articleModal = new bootstrap.Modal(document.getElementById('articleModal'));
    
    // Add click event listeners to all article cards
    document.addEventListener('click', function(event) {
        const articleCard = event.target.closest('.article-card');
        if (!articleCard) return;
        
        event.preventDefault();
        const articleId = articleCard.dataset.articleId;
        const articleUrl = articleCard.dataset.articleUrl;
        
        // Fetch article details
        fetch(`/api/article/${articleId}`)
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch article details');
                return response.json();
            })
            .then(article => {
                // Update modal content
                document.getElementById('modalNewspaperLogo').src = article.periodico_logo || '/static/img/default-newspaper.svg';
                document.getElementById('articleModalLabel').textContent = article.titular;
                document.getElementById('articleSubtitle').textContent = article.subtitular || '';
                document.getElementById('articleDate').textContent = article.fecha_publicacion || '';
                document.getElementById('articleAuthor').textContent = article.periodista || '';
                document.getElementById('articleContent').innerHTML = `
                    <p>${article.gpt_resumen || ''}</p>
                    ${article.cuerpo ? `<p>${article.cuerpo}</p>` : ''}
                `;
                document.getElementById('articleLink').href = articleUrl;
                
                // Show/hide paywall warning
                const paywallWarning = document.getElementById('paywallWarning');
                if (article.paywall) {
                    paywallWarning.classList.remove('d-none');
                } else {
                    paywallWarning.classList.add('d-none');
                }
                
                // Show the modal
                articleModal.show();
            })
            .catch(error => {
                console.error('Error loading article details:', error);
                // Show error message
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-danger alert-dismissible fade show';
                errorDiv.innerHTML = `
                    Failed to load article details. Please try again.
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.container').firstChild);
            });
    });
});
