// JavaScript logic
/**
 * Utility functions for the application
 */

// Format date string to a more readable format
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Format number with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Truncate text to a certain length
function truncateText(text, maxLength = 100) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    
    return text.substring(0, maxLength) + '...';
}

// Highlight search terms in text
function highlightText(text, searchTerm) {
    if (!text || !searchTerm) return text;
    
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

// Extract domain from URL
function extractDomain(url) {
    if (!url) return '';
    
    try {
        const urlObj = new URL(url);
        return urlObj.hostname;
    } catch (e) {
        return '';
    }
}

// Show notification
function showNotification(message, type = 'success') {
    const notificationContainer = document.getElementById('notification-container');
    
    if (!notificationContainer) {
        // Create notification container if it doesn't exist
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.role = 'alert';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to container
    document.getElementById('notification-container').appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 150);
    }, 5000);
}

// Send API request
async function apiRequest(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(`/api${endpoint}`, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'API request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API request error:', error);
        showNotification(error.message || 'API request failed', 'danger');
        throw error;
    }
}

// Initialize sidebar action buttons
document.addEventListener('DOMContentLoaded', function() {
    // Extract history button
    const extractHistoryBtn = document.getElementById('extractHistoryBtn');
    if (extractHistoryBtn) {
        extractHistoryBtn.addEventListener('click', async function() {
            try {
                extractHistoryBtn.disabled = true;
                extractHistoryBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i> Extracting...';
                
                const result = await apiRequest('/extract', 'POST');
                showNotification(result.message);
            } catch (error) {
                // Error is already handled in apiRequest
            } finally {
                extractHistoryBtn.disabled = false;
                extractHistoryBtn.innerHTML = '<i class="bi bi-download me-2"></i> Extract History';
            }
        });
    }
    
    // Scrape content button
    const scrapeContentBtn = document.getElementById('scrapeContentBtn');
    if (scrapeContentBtn) {
        scrapeContentBtn.addEventListener('click', async function() {
            try {
                scrapeContentBtn.disabled = true;
                scrapeContentBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i> Scraping...';
                
                const result = await apiRequest('/scrape', 'POST');
                showNotification(result.message);
            } catch (error) {
                // Error is already handled in apiRequest
            } finally {
                scrapeContentBtn.disabled = false;
                scrapeContentBtn.innerHTML = '<i class="bi bi-cloud-download me-2"></i> Scrape Content';
            }
        });
    }
    
    // Build index button
    const buildIndexBtn = document.getElementById('buildIndexBtn');
    if (buildIndexBtn) {
        buildIndexBtn.addEventListener('click', async function() {
            try {
                buildIndexBtn.disabled = true;
                buildIndexBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i> Building...';
                
                const result = await apiRequest('/index', 'POST');
                showNotification(result.message);
            } catch (error) {
                // Error is already handled in apiRequest
            } finally {
                buildIndexBtn.disabled = false;
                buildIndexBtn.innerHTML = '<i class="bi bi-database-add me-2"></i> Build Index';
            }
        });
    }
});