document.addEventListener('DOMContentLoaded', function() {
    initializePopovers();
});

function initializePopovers() {
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => {
        return new bootstrap.Popover(popoverTriggerEl, {
            placement: 'auto',
            delay: { show: 200, hide: 100 },
            container: 'body'
        });
    });

    // Destroy popovers when cards are removed/replaced
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.removedNodes.length) {
                mutation.removedNodes.forEach(function(node) {
                    if (node.querySelector) {
                        const popovers = node.querySelectorAll('[data-bs-toggle="popover"]');
                        popovers.forEach(el => {
                            const popover = bootstrap.Popover.getInstance(el);
                            if (popover) {
                                popover.dispose();
                            }
                        });
                    }
                });
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// Function to reinitialize popovers after dynamic content updates
function reinitializePopovers() {
    const existingPopovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    existingPopovers.forEach(el => {
        const popover = bootstrap.Popover.getInstance(el);
        if (popover) {
            popover.dispose();
        }
    });
    initializePopovers();
}

// Add the function to the window object so it can be called from other scripts
window.reinitializePopovers = reinitializePopovers;
