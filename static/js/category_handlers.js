// Keep the existing code but modify the article card initialization in updateDisplay function
// Remove URL handling and only add hover effect
document.querySelectorAll('.article-card').forEach(card => {
    // Add hover effect
    card.style.cursor = 'pointer';
    card.classList.add('article-card-clickable');
    
    // Add debug logging
    console.log('Article card initialized:', card.dataset.articleId);
});
