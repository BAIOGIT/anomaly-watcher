// Global chart instance
let sensorChart = null;

// Initialize chart when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    loadChartData();
    
    // Set up event listeners
    document.getElementById('categoryFilter').addEventListener('change', loadChartData);

    const timeRangeElem = document.getElementById('timeRange');
    if (timeRangeElem) {
        timeRangeElem.addEventListener('change', loadChartData);
    }
    const refreshBtnElem = document.getElementById('refreshBtn');
    if (refreshBtnElem) {
        refreshBtnElem.addEventListener('click', loadChartData);
    }
    
    // Auto-refresh every 30 seconds
    setInterval(loadChartData, 5000);
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
                backgroundColor: 'rgba(255, 0, 0, 0.8)',
                borderColor: 'rgba(255, 0, 0, 1)',
                borderWidth: 2,
                pointRadius: 6,
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