/**
 * Statistics page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load statistics data
    loadStatsData();
    
    // Set up refresh button
    const refreshBtn = document.getElementById('refreshStatsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadStatsData);
    }
});

async function loadStatsData() {
    try {
        // Fetch statistics
        const statsData = await apiRequest('/stats');
        
        // Render statistics
        renderStatCards(statsData);
        renderCharts(statsData);
        renderMostVisitedTable(statsData);
        
    } catch (error) {
        console.error('Error loading statistics:', error);
        showNotification('Error loading statistics', 'danger');
    }
}

function renderStatCards(data) {
    // Calculate total pages
    const totalPages = data.domains.reduce((total, domain) => total + domain.count, 0);
    document.getElementById('total-pages').textContent = formatNumber(totalPages);
    
    // Calculate unique domains
    const uniqueDomains = data.domains.length;
    document.getElementById('unique-domains').textContent = formatNumber(uniqueDomains);
    
    // Calculate average pages per day
    const dailyData = data.daily;
    const avgPages = dailyData.length > 0 
        ? Math.round(dailyData.reduce((total, day) => total + day.count, 0) / dailyData.length) 
        : 0;
    document.getElementById('avg-pages-day').textContent = formatNumber(avgPages);
}

function renderCharts(data) {
    // Daily activity chart
    const dailyCtx = document.getElementById('dailyActivityChart').getContext('2d');
    
    new Chart(dailyCtx, {
        type: 'bar',
        data: {
            labels: data.daily.map(d => d.date),
            datasets: [{
                label: 'Pages Visited',
                data: data.daily.map(d => d.count),
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    
    // Hourly activity chart
    const hourlyCtx = document.getElementById('hourlyActivityChart').getContext('2d');
    
    new Chart(hourlyCtx, {
        type: 'line',
        data: {
            labels: data.hourly.map(h => `${h.hour}:00`),
            datasets: [{
                label: 'Pages Visited',
                data: data.hourly.map(h => h.count),
                fill: true,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderMostVisitedTable(data) {
    // Fetch most visited pages
    fetch('/api/recent?limit=10')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('most-visited-table');
            
            if (!data.items || data.items.length === 0) {
                container.innerHTML = '<tr><td colspan="4" class="text-center">No data available</td></tr>';
                return;
            }
            
            // Sort by visit count
            const sortedItems = data.items.sort((a, b) => b.visit_count - a.visit_count);
            
            let html = '';
            
            sortedItems.forEach(item => {
                html += `
                    <tr>
                        <td>${item.title || 'Untitled'}</td>
                        <td>
                            <a href="${item.url}" target="_blank" title="${item.url}">
                                ${truncateText(item.url, 50)}
                            </a>
                        </td>
                        <td>${item.visit_count}</td>
                        <td>${formatDate(item.last_visit_time)}</td>
                    </tr>
                `;
            });
            
            container.innerHTML = html;
        })
        .catch(error => {
            console.error('Error fetching most visited pages:', error);
            document.getElementById('most-visited-table').innerHTML = 
                '<tr><td colspan="4" class="text-center text-danger">Error loading data</td></tr>';
        });
}