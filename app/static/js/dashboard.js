// Global variables
let currentPage = 1;
let currentFilters = {};
let regionalChart = null;
let successChart = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupNavigation();
    loadDashboardData();
});

function initializeDashboard() {
    console.log('Initializing Wayground Tender Monitor Dashboard...');
    showTab('dashboard');
}

function setupNavigation() {
    // Setup tab navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabName = this.getAttribute('href').substring(1);
            showTab(tabName);
            
            // Update active nav
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
        tab.style.display = 'none';
    });
    
    // Show selected tab
    const selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
        selectedTab.style.display = 'block';
        
        // Load tab-specific data
        switch(tabName) {
            case 'dashboard':
                loadDashboardData();
                break;
            case 'tenders':
                loadTendersData();
                break;
            case 'analysis':
                loadAnalysisData();
                break;
        }
    }
}

// Dashboard Functions
async function loadDashboardData() {
    try {
        // Load overview stats
        const overview = await fetchAPI('/api/dashboard/overview');
        updateKPICards(overview);
        
        // Load alerts
        const alerts = await fetchAPI('/api/dashboard/alerts');
        displayAlerts(alerts.alerts);
        
        // Load top opportunities
        const opportunities = await fetchAPI('/api/dashboard/top-opportunities');
        displayTopOpportunities(opportunities.top_opportunities);
        
        // Load urgent tenders
        const urgent = await fetchAPI('/api/dashboard/urgent-tenders');
        displayUrgentTenders(urgent.urgent_tenders);
        
        // Load regional distribution
        const regional = await fetchAPI('/api/dashboard/regional-distribution');
        createRegionalChart(regional.regional_distribution);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showAlert('Error loading dashboard data', 'danger');
    }
}

function updateKPICards(data) {
    document.getElementById('total-tenders').textContent = data.total_tenders || 0;
    document.getElementById('recommended-tenders').textContent = data.recommended_tenders || 0;
    document.getElementById('urgent-opportunities').textContent = data.urgent_opportunities || 0;
    document.getElementById('avg-ai-score').textContent = (data.average_ai_score || 0).toFixed(2);
}

function displayAlerts(alerts) {
    const container = document.getElementById('alerts-container');
    container.innerHTML = '';
    
    alerts.forEach(alert => {
        const alertClass = alert.type === 'critical' ? 'danger' : 
                          alert.type === 'opportunity' ? 'warning' : 'info';
        
        const alertHTML = `
            <div class="alert alert-${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas fa-${alert.type === 'critical' ? 'exclamation-triangle' : 
                                    alert.type === 'opportunity' ? 'star' : 'info-circle'} me-2"></i>
                <strong>${alert.title}:</strong> ${alert.message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', alertHTML);
    });
}

function displayTopOpportunities(opportunities) {
    const container = document.getElementById('top-opportunities-list');
    
    if (!opportunities || opportunities.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No opportunities found</div>';
        return;
    }
    
    const opportunitiesHTML = opportunities.map(opp => `
        <div class="opportunity-item mb-3 p-3 border rounded">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${opp.title}</h6>
                    <small class="text-muted">${opp.organization} | ${opp.country}</small>
                    <div class="mt-1">
                        <span class="badge bg-primary">Score: ${opp.ai_score.toFixed(2)}</span>
                        ${opp.value ? `<span class="badge bg-success">${formatCurrency(opp.value, opp.currency)}</span>` : ''}
                        ${opp.success_probability ? `<span class="badge bg-info">${(opp.success_probability * 100).toFixed(0)}% Success</span>` : ''}
                    </div>
                </div>
                <button class="btn btn-sm btn-outline-primary" onclick="viewTenderDetails('${opp.tender_id}')">
                    View
                </button>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = opportunitiesHTML;
}

function displayUrgentTenders(urgent) {
    const container = document.getElementById('urgent-tenders-list');
    
    if (!urgent || urgent.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No urgent tenders</div>';
        return;
    }
    
    const urgentHTML = urgent.map(tender => `
        <div class="urgent-tender-item mb-2 p-3 border-start border-${getUrgencyColor(tender.urgency_level)} border-3 bg-light">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${tender.title}</strong>
                    <div class="small text-muted">${tender.organization} | ${tender.country}</div>
                    <div class="small">
                        <span class="badge bg-${getUrgencyColor(tender.urgency_level)}">
                            ${tender.days_remaining} day${tender.days_remaining !== 1 ? 's' : ''} left
                        </span>
                        <span class="badge bg-primary">Score: ${tender.ai_score.toFixed(2)}</span>
                    </div>
                </div>
                <button class="btn btn-sm btn-primary" onclick="viewTenderDetails('${tender.tender_id}')">
                    View Details
                </button>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = urgentHTML;
}

function createRegionalChart(data) {
    const ctx = document.getElementById('regional-chart').getContext('2d');
    
    if (regionalChart) {
        regionalChart.destroy();
    }
    
    const regions = Object.keys(data);
    const counts = regions.map(r => data[r].total_tenders);
    const recommended = regions.map(r => data[r].recommended_count);
    
    regionalChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: regions,
            datasets: [{
                label: 'Total Tenders',
                data: counts,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }, {
                label: 'Recommended',
                data: recommended,
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Tenders Functions
async function loadTendersData() {
    try {
        const params = new URLSearchParams({
            skip: (currentPage - 1) * 20,
            limit: 20,
            ...currentFilters
        });
        
        const response = await fetchAPI(`/api/tenders/?${params}`);
        displayTendersTable(response);
        
    } catch (error) {
        console.error('Error loading tenders:', error);
        showAlert('Error loading tenders', 'danger');
    }
}

function displayTendersTable(tenders) {
    const tbody = document.getElementById('tenders-table-body');
    
    if (!tenders || tenders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No tenders found</td></tr>';
        return;
    }
    
    const tendersHTML = tenders.map(tender => `
        <tr>
            <td>
                <div class="tender-title" title="${tender.title}">
                    ${truncateText(tender.title, 50)}
                </div>
            </td>
            <td>${tender.organization}</td>
            <td>
                <span class="flag-icon flag-icon-${getCountryCode(tender.country)}"></span>
                ${tender.country}
            </td>
            <td>${tender.value ? formatCurrency(tender.value, tender.currency) : 'N/A'}</td>
            <td>
                <span class="badge bg-${getScoreColor(tender.ai_score)}">
                    ${tender.ai_score.toFixed(2)}
                </span>
            </td>
            <td>
                ${tender.recommended ? 
                    '<span class="badge bg-success"><i class="fas fa-check"></i> Yes</span>' : 
                    '<span class="badge bg-secondary"><i class="fas fa-times"></i> No</span>'}
            </td>
            <td>${tender.closing_date ? formatDate(tender.closing_date) : 'N/A'}</td>
            <td><span class="badge bg-${getStatusColor(tender.status)}">${tender.status}</span></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="viewTenderDetails('${tender.tender_id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-outline-secondary" onclick="analyzeTender('${tender.tender_id}')">
                        <i class="fas fa-brain"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    tbody.innerHTML = tendersHTML;
}

function applyFilters() {
    const status = document.getElementById('status-filter').value;
    const region = document.getElementById('region-filter').value;
    const recommended = document.getElementById('recommended-filter').value;
    const minScore = document.getElementById('min-score-filter').value;
    
    currentFilters = {};
    if (status) currentFilters.status = status;
    if (region) currentFilters.region = region;
    if (recommended) currentFilters.recommended = recommended === 'true';
    if (minScore) currentFilters.min_score = parseFloat(minScore);
    
    currentPage = 1;
    loadTendersData();
}

function clearFilters() {
    document.getElementById('status-filter').value = '';
    document.getElementById('region-filter').value = '';
    document.getElementById('recommended-filter').value = '';
    document.getElementById('min-score-filter').value = '';
    
    currentFilters = {};
    currentPage = 1;
    loadTendersData();
}

// Analysis Functions
async function loadAnalysisData() {
    try {
        // Load insights
        const insights = await fetchAPI('/api/analysis/insights');
        displayAnalysisInsights(insights);
        
        // Load keyword analysis
        const keywords = await fetchAPI('/api/analysis/keyword-analysis');
        displayKeywordAnalysis(keywords);
        
        // Load competition analysis
        const competition = await fetchAPI('/api/analysis/competition-analysis');
        displayCompetitionAnalysis(competition);
        
        // Load performance metrics
        const performance = await fetchAPI('/api/dashboard/performance-metrics');
        displayPerformanceMetrics(performance);
        
    } catch (error) {
        console.error('Error loading analysis data:', error);
        showAlert('Error loading analysis data', 'danger');
    }
}

function displayKeywordAnalysis(data) {
    const container = document.getElementById('keyword-analysis');
    const keywords = Object.entries(data.keyword_performance).slice(0, 5);
    
    const keywordHTML = keywords.map(([keyword, stats]) => `
        <div class="keyword-stat mb-2">
            <div class="d-flex justify-content-between">
                <span class="fw-bold">${keyword}</span>
                <span class="badge bg-primary">${stats.avg_score.toFixed(2)}</span>
            </div>
            <div class="progress" style="height: 5px;">
                <div class="progress-bar" style="width: ${stats.recommendation_rate * 100}%"></div>
            </div>
            <small class="text-muted">${stats.total_occurrences} occurrences, ${(stats.recommendation_rate * 100).toFixed(0)}% recommended</small>
        </div>
    `).join('');
    
    container.innerHTML = keywordHTML;
}

function displayCompetitionAnalysis(data) {
    const container = document.getElementById('competition-analysis');
    const ranges = Object.entries(data.value_range_analysis);
    
    const competitionHTML = ranges.map(([range, stats]) => `
        <div class="competition-stat mb-2">
            <div class="d-flex justify-content-between">
                <span class="fw-bold">${range}</span>
                <span class="badge bg-info">${stats.count}</span>
            </div>
            <div class="small text-muted">
                Avg Score: ${stats.avg_score.toFixed(2)} | 
                Recommended: ${(stats.recommendation_rate * 100).toFixed(0)}%
            </div>
        </div>
    `).join('');
    
    container.innerHTML = competitionHTML;
}

function displayPerformanceMetrics(data) {
    const container = document.getElementById('performance-metrics');
    const periods = Object.entries(data.performance_metrics);
    
    const metricsHTML = `
        <div class="row">
            ${periods.map(([period, metrics]) => `
                <div class="col-md-4">
                    <div class="metric-card p-3 border rounded">
                        <h6>${period.replace('_', ' ').toUpperCase()}</h6>
                        <div class="metric-item">
                            <span class="metric-label">Total:</span>
                            <span class="metric-value">${metrics.total_tenders}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Recommended:</span>
                            <span class="metric-value">${metrics.recommended_count}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Avg Score:</span>
                            <span class="metric-value">${metrics.average_score.toFixed(2)}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Recommendation Rate:</span>
                            <span class="metric-value">${(metrics.recommendation_rate * 100).toFixed(0)}%</span>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    container.innerHTML = metricsHTML;
}

// Utility Functions
async function fetchAPI(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

async function postAPI(url, data) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    });
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

function showAlert(message, type = 'info') {
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const container = document.getElementById('alerts-container');
    container.insertAdjacentHTML('beforeend', alertHTML);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alerts = container.querySelectorAll('.alert');
        if (alerts.length > 0) {
            alerts[0].remove();
        }
    }, 5000);
}

function formatCurrency(value, currency = 'GBP') {
    const symbols = { 'GBP': '£', 'USD': '$', 'EUR': '€', 'AUD': 'A$' };
    const symbol = symbols[currency] || currency;
    
    if (value >= 1000000) {
        return `${symbol}${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
        return `${symbol}${(value / 1000).toFixed(0)}K`;
    } else {
        return `${symbol}${value.toLocaleString()}`;
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', { 
        day: '2-digit', 
        month: 'short', 
        year: 'numeric' 
    });
}

function truncateText(text, maxLength) {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

function getScoreColor(score) {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    if (score >= 0.4) return 'info';
    return 'secondary';
}

function getStatusColor(status) {
    const colors = {
        'new': 'primary',
        'reviewed': 'info',
        'applied': 'success',
        'rejected': 'danger'
    };
    return colors[status] || 'secondary';
}

function getUrgencyColor(urgency) {
    const colors = {
        'critical': 'danger',
        'high': 'warning',
        'medium': 'info'
    };
    return colors[urgency] || 'secondary';
}

function getCountryCode(country) {
    const codes = {
        'United Kingdom': 'gb',
        'Australia': 'au',
        'Singapore': 'sg',
        'India': 'in',
        'Germany': 'de',
        'France': 'fr',
        'Spain': 'es',
        'Italy': 'it'
    };
    return codes[country] || 'unknown';
}

// Action Functions
async function triggerSearch() {
    try {
        showAlert('Starting tender search...', 'info');
        const response = await postAPI('/api/tenders/search', {});
        showAlert(response.message, 'success');
        
        // Refresh data after a delay
        setTimeout(() => {
            loadDashboardData();
            if (document.getElementById('tenders').classList.contains('active')) {
                loadTendersData();
            }
        }, 5000);
        
    } catch (error) {
        console.error('Error triggering search:', error);
        showAlert('Error starting tender search', 'danger');
    }
}

async function viewTenderDetails(tenderId) {
    try {
        const tender = await fetchAPI(`/api/tenders/${tenderId}`);
        
        const modalTitle = document.getElementById('tenderModalTitle');
        const modalBody = document.getElementById('tenderModalBody');
        
        modalTitle.textContent = tender.title;
        
        const detailsHTML = `
            <div class="tender-details">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <strong>Organization:</strong> ${tender.organization}
                    </div>
                    <div class="col-md-6">
                        <strong>Country:</strong> ${tender.country}
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6">
                        <strong>Value:</strong> ${tender.value ? formatCurrency(tender.value, tender.currency) : 'N/A'}
                    </div>
                    <div class="col-md-6">
                        <strong>Closing Date:</strong> ${tender.closing_date ? formatDate(tender.closing_date) : 'N/A'}
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6">
                        <strong>AI Score:</strong> 
                        <span class="badge bg-${getScoreColor(tender.ai_score)}">${tender.ai_score.toFixed(2)}</span>
                    </div>
                    <div class="col-md-6">
                        <strong>Recommended:</strong> 
                        ${tender.recommended ? 
                            '<span class="badge bg-success">Yes</span>' : 
                            '<span class="badge bg-secondary">No</span>'}
                    </div>
                </div>
                <div class="mb-3">
                    <strong>Description:</strong>
                    <p class="mt-2">${tender.description}</p>
                </div>
                ${tender.keywords && tender.keywords.length > 0 ? `
                    <div class="mb-3">
                        <strong>Keywords:</strong>
                        <div class="mt-2">
                            ${tender.keywords.map(k => `<span class="badge bg-info me-1">${k}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
                ${tender.reason ? `
                    <div class="mb-3">
                        <strong>AI Recommendation Reason:</strong>
                        <p class="mt-2">${tender.reason}</p>
                    </div>
                ` : ''}
                <div class="mb-3">
                    <strong>Status:</strong> 
                    <span class="badge bg-${getStatusColor(tender.status)}">${tender.status}</span>
                </div>
                <div class="mb-3">
                    <a href="${tender.tender_url}" target="_blank" class="btn btn-outline-primary">
                        <i class="fas fa-external-link-alt me-1"></i> View Original Tender
                    </a>
                </div>
            </div>
        `;
        
        modalBody.innerHTML = detailsHTML;
        
        // Store tender ID for potential status update
        document.getElementById('tenderModal').setAttribute('data-tender-id', tenderId);
        
        const modal = new bootstrap.Modal(document.getElementById('tenderModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading tender details:', error);
        showAlert('Error loading tender details', 'danger');
    }
}

async function analyzeTender(tenderId) {
    try {
        showAlert('Analyzing tender with AI...', 'info');
        const response = await postAPI(`/api/tenders/analyze/${tenderId}`, {});
        showAlert(response.message, 'success');
        
        // Refresh the tenders table
        if (document.getElementById('tenders').classList.contains('active')) {
            loadTendersData();
        }
        
    } catch (error) {
        console.error('Error analyzing tender:', error);
        showAlert('Error analyzing tender', 'danger');
    }
}