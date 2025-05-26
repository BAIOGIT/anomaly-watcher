// Global chart instance
let sensorChart = null;

// Initialize chart when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    loadChartData();
    
    // Set up event listeners
    const categoryFilter = document.getElementById('categoryFilter');
    const timeRange = document.getElementById('timeRange');
    const refreshBtn = document.getElementById('refreshBtn');
    const resetDbBtn = document.getElementById('resetDbBtn');
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', loadChartData);
    }
    
    if (timeRange) {
        timeRange.addEventListener('change', loadChartData);
    }
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadChartData);
    }
    
    // Set up reset button
    if (resetDbBtn) {
        resetDbBtn.addEventListener('click', showResetConfirmation);
    }
    
    // Set up modal handlers
    setupResetModal();
    
    // Auto-refresh every 30 seconds
    setInterval(loadChartData, 30000);
});

function initializeChart() {
    const ctx = document.getElementById('sensorChart').getContext('2d');
    
    sensorChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm',
                            second: 'HH:mm:ss'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Value'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        filter: function(legendItem, chartData) {
                            // Hide anomaly datasets from legend to reduce clutter
                            return !legendItem.text.includes('Anomalies');
                        }
                    }
                },
                tooltip: {
                    mode: 'nearest',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            if (context.length > 0) {
                                const dataPoint = context[0];
                                return new Date(dataPoint.parsed.x).toLocaleString();
                            }
                            return '';
                        },
                        label: function(context) {
                            const dataPoint = context.raw;
                            const dataset = context.dataset;
                            
                            // Check if this is an anomaly point
                            if (dataset.type === 'scatter' && dataPoint.anomalyScore) {
                                return [
                                    `🚨 ANOMALY DETECTED`,
                                    `Sensor: ${dataPoint.sensorId}`,
                                    `Category: ${dataPoint.category}`,
                                    `Value: ${dataPoint.y}`,
                                    `Location: ${dataPoint.location || 'unknown'}`,
                                    `Anomaly Score: ${dataPoint.anomalyScore.toFixed(3)}`,
                                    `Model: ${dataPoint.modelName}`,
                                    `Type: ${dataPoint.anomalyType || 'unknown'}`
                                ];
                            } else {
                                // Regular sensor data
                                return `${dataset.label}: ${dataPoint.y}`;
                            }
                        },
                        labelColor: function(context) {
                            if (context.dataset.type === 'scatter') {
                                return {
                                    borderColor: 'rgba(255, 0, 0, 1)',
                                    backgroundColor: 'rgba(255, 0, 0, 0.8)'
                                };
                            }
                            return {
                                borderColor: context.dataset.borderColor,
                                backgroundColor: context.dataset.backgroundColor
                            };
                        }
                    }
                }
            }
        }
    });
}

async function loadChartData() {
    try {
        const categoryElement = document.getElementById('categoryFilter');
        const timeRangeElement = document.getElementById('timeRange');
        
        const category = categoryElement ? categoryElement.value : '';
        const hours = timeRangeElement ? timeRangeElement.value : '24';
        
        // Dynamic interval based on time range
        let interval = 60;
        if (hours > 24) interval = 3600;
        else if (hours > 6) interval = 900;
        else if (hours > 2) interval = 300;
        
        // Build API URLs
        let timeseriesUrl = `/api/sensor-timeseries?hours=${hours}&interval=${interval}`;
        let anomaliesUrl = `/api/anomalies-timeseries?hours=${hours}`;
        
        if (category) {
            timeseriesUrl += `&category=${category}`;
            anomaliesUrl += `&category=${category}`;
        }
        
        console.log('Fetching data from:', { timeseriesUrl, anomaliesUrl });
        
        // Fetch both timeseries and anomaly data in parallel
        const [timeseriesResponse, anomaliesResponse] = await Promise.all([
            fetch(timeseriesUrl),
            fetch(anomaliesUrl)
        ]);
        
        if (!timeseriesResponse.ok) {
            throw new Error(`Timeseries API error! status: ${timeseriesResponse.status}`);
        }
        if (!anomaliesResponse.ok) {
            console.warn(`Anomalies API warning! status: ${anomaliesResponse.status}`);
            // Continue without anomalies if the API fails
            const timeseriesData = await timeseriesResponse.json();
            updateChart(timeseriesData, []);
            return;
        }
        
        const timeseriesData = await timeseriesResponse.json();
        const anomaliesData = await anomaliesResponse.json();
        
        console.log('Received data:', { 
            timeseries: timeseriesData.length, 
            anomalies: anomaliesData.length 
        });
        
        updateChart(timeseriesData, anomaliesData);
        
    } catch (error) {
        console.error('Error loading chart data:', error);
        showError('Failed to load chart data: ' + error.message);
    }
}

function updateChart(timeSeriesData, anomaliesData = []) {
    if (!sensorChart) return;

    const groupedData = {};
    const anomalyDatasets = {};
    let allTimestamps = [];

    // Process regular time series data (line charts)
    timeSeriesData.forEach(point => {
        const timestamp = new Date(point.time_bucket);
        allTimestamps.push(timestamp);

        if (!groupedData[point.sensor_id]) {
            groupedData[point.sensor_id] = {
                label: `${capitalize(point.category)}: ${point.unit}`,
                data: [],
                borderColor: getColorForCategory(point.category),
                backgroundColor: getColorForCategory(point.category, 0.1),
                fill: false,
                tension: 0.2,
                type: 'line'
            };
        }

        groupedData[point.sensor_id].data.push({
            x: timestamp,
            y: point.avg_value
        });
    });

    // Process anomaly data (scatter points)
    anomaliesData.forEach(anomaly => {
        const timestamp = new Date(anomaly.timestamp);
        const datasetKey = `${anomaly.sensor_id}_anomalies`;

        if (!anomalyDatasets[datasetKey]) {
            anomalyDatasets[datasetKey] = {
                label: `${capitalize(anomaly.category)} Anomalies`,
                data: [],
                backgroundColor: 'rgba(255, 0, 0, 0.08)',
                borderColor: 'rgba(255, 0, 0, 1)',
                borderWidth: 1,
                pointRadius: 8,
                pointHoverRadius: 8,
                type: 'scatter',
                showLine: false,
                yAxisID: 'y',
                order: 1 // Ensure anomalies are drawn on top
            };
        }

        anomalyDatasets[datasetKey].data.push({
            x: timestamp,
            y: anomaly.value,
            // Store anomaly details for tooltip
            anomalyScore: anomaly.anomaly_score,
            modelName: anomaly.model_name,
            anomalyType: anomaly.anomaly_type,
            sensorId: anomaly.sensor_id,
            category: anomaly.category,
            location: anomaly.location
        });
    });

    // Sort line chart data points by time
    Object.values(groupedData).forEach(dataset => {
        dataset.data.sort((a, b) => a.x - b.x);
    });

    // Set x-axis range if data exists
    const minTime = allTimestamps.length ? Math.min(...allTimestamps.map(d => d.getTime())) : null;
    const maxTime = allTimestamps.length ? Math.max(...allTimestamps.map(d => d.getTime())) : null;

    sensorChart.options.scales.x.min = minTime ? new Date(minTime) : undefined;
    sensorChart.options.scales.x.max = maxTime ? new Date(maxTime) : undefined;

    // Combine line charts and anomaly scatter plots
    const allDatasets = [...Object.values(groupedData), ...Object.values(anomalyDatasets)];
    sensorChart.data.datasets = allDatasets;
    
    sensorChart.update();
    updateStats(timeSeriesData, anomaliesData);
}


function getColorForCategory(category, alpha = 1) {
    const colors = {
        'oven': `rgba(255, 99, 132, ${alpha})`,
        'heater': `rgba(54, 162, 235, ${alpha})`,
        'lamp': `rgba(255, 205, 86, ${alpha})`,
        'fan': `rgba(75, 192, 192, ${alpha})`,
        'pm': `rgba(153, 102, 255, ${alpha})`
    };
    return colors[category] || `rgba(128, 128, 128, ${alpha})`;
}

function updateStats(data, anomalies = []) {
    const uniqueSensors = new Set(data.map(d => d.sensor_id)).size;
    document.getElementById('totalSensors').textContent = uniqueSensors;
    
    // Update anomaly count in the existing alerts stat card
    const alertsElement = document.getElementById('activeAlerts');
    if (alertsElement) {
        alertsElement.textContent = anomalies.length;
    }
}

function showError(message) {
    // Simple error display - you can enhance this
    console.error(message);
    // You could also show a toast notification or alert
}

// Utility function to capitalize the first letter of a string
function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// Utility function to generate random colors (fallback)
function getRandomColor(alpha = 1) {
    const r = Math.floor(Math.random() * 255);
    const g = Math.floor(Math.random() * 255);
    const b = Math.floor(Math.random() * 255);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

function debugTimeRange() {
    const timeRange = document.getElementById('timeRange');
    console.log('Time range element:', timeRange);
    console.log('Current value:', timeRange.value);
    console.log('All options:', Array.from(timeRange.options).map(opt => ({value: opt.value, text: opt.text, selected: opt.selected})));
}

function showResetConfirmation() {
    const modal = document.getElementById('resetModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function setupResetModal() {
    const modal = document.getElementById('resetModal');
    const confirmBtn = document.getElementById('confirmReset');
    const cancelBtn = document.getElementById('cancelReset');
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }
    
    if (confirmBtn) {
        confirmBtn.addEventListener('click', performDatabaseReset);
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

async function performDatabaseReset() {
    const modal = document.getElementById('resetModal');
    const confirmBtn = document.getElementById('confirmReset');
    const originalText = confirmBtn.textContent;
    
    try {
        // Show loading state
        confirmBtn.innerHTML = '<span class="loading-spinner"></span>Resetting...';
        confirmBtn.disabled = true;
        
        // Make API call to reset database
        const response = await fetch('/api/reset-database', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            throw new Error(`Reset failed: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // Show success message
        showMessage('Database reset successfully!', 'success');
        
        // Close modal
        modal.style.display = 'none';
        
        // Refresh the chart to show empty state
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Database reset error:', error);
        showMessage('Database reset failed: ' + error.message, 'error');
    } finally {
        // Restore button state
        confirmBtn.textContent = originalText;
        confirmBtn.disabled = false;
    }
}

function showMessage(message, type = 'info') {
    // Create or update message display
    let messageDiv = document.getElementById('messageDisplay');
    if (!messageDiv) {
        messageDiv = document.createElement('div');
        messageDiv.id = 'messageDisplay';
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 4px;
            color: white;
            font-weight: bold;
            z-index: 1001;
            max-width: 400px;
        `;
        document.body.appendChild(messageDiv);
    }
    
    // Set style based on type
    if (type === 'success') {
        messageDiv.style.backgroundColor = '#28a745';
        messageDiv.textContent = '✅ ' + message;
    } else if (type === 'error') {
        messageDiv.style.backgroundColor = '#dc3545';
        messageDiv.textContent = '❌ ' + message;
    } else {
        messageDiv.style.backgroundColor = '#17a2b8';
        messageDiv.textContent = 'ℹ️ ' + message;
    }
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (messageDiv) messageDiv.remove();
    }, 5000);
}