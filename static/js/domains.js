/**
 * Domains page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load domains data
    loadDomainsData();
    
    // Set up refresh button
    const refreshBtn = document.getElementById('refreshDomainsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDomainsData);
    }
});

async function loadDomainsData() {
    try {
        // Load statistics
        const statsData = await apiRequest('/stats');
        renderDomainChart(statsData.domains);
        
    } catch (error) {
        console.error('Error loading domains data:', error);
        showNotification('Error loading domains data', 'danger');
    }
}

function renderDomainChart(domainsData) {
    // Get top domains for chart
    const topDomains = domainsData.slice(0, 10);
    
    // Prepare data for pie chart
    const labels = topDomains.map(d => d.domain);
    const data = topDomains.map(d => d.count);
    
    // Generate colors
    const backgroundColors = generateColors(topDomains.length);
    
    // Create pie chart
    const ctx = document.getElementById('domainsPieChart').getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

function generateColors(count) {
    // Generate a nice color palette
    const colors = [];
    const baseHues = [0, 60, 120, 180, 240, 300]; // Red, Yellow, Green, Cyan, Blue, Magenta
    
    for (let i = 0; i < count; i++) {
        const hue = baseHues[i % baseHues.length];
        const lightness = 50 + (Math.floor(i / baseHues.length) * 10);
        colors.push(`hsl(${hue}, 70%, ${lightness}%)`);
    }
    
    return colors;
}