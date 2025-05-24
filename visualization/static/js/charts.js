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
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
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
        
        // console.log('Loading data with filters:', { category, hours });
        
        // Dynamic interval based on time range (convert to seconds)
        let interval = 60;  // 1 minute = 60 seconds for short ranges
        if (hours > 24) interval = 3600;     // 1 hour = 3600 seconds for longer than 1 day
        else if (hours > 6) interval = 900;  // 15 minutes = 900 seconds for 6+ hours
        else if (hours > 2) interval = 300;  // 5 minutes = 300 seconds for 2+ hours
        
        // console.log('Using interval (seconds):', interval);
        
        // Build API URL
        let apiUrl = `/api/sensor-timeseries?hours=${hours}&interval=${interval}`;
        if (category) {
            apiUrl += `&category=${category}`;
        }
        
        // console.log('API URL:', apiUrl);
        
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        // console.log('Received data points:', data.length);
        // console.log('Sample data:', data.slice(0, 3));
        
        updateChart(data);
        
    } catch (error) {
        console.error('Error loading chart data:', error);
        showError('Failed to load chart data: ' + error.message);
    }
}

function updateChart(timeSeriesData) {
    if (!sensorChart) return;

    const groupedData = {};
    let allTimestamps = [];

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
                tension: 0.2
            };
        }

        groupedData[point.sensor_id].data.push({
            x: timestamp,
            y: point.avg_value
        });
    });

    // Sort data points by time
    Object.values(groupedData).forEach(dataset => {
        dataset.data.sort((a, b) => a.x - b.x);
    });

    // Set x-axis range if data exists
    const minTime = allTimestamps.length ? Math.min(...allTimestamps.map(d => d.getTime())) : null;
    const maxTime = allTimestamps.length ? Math.max(...allTimestamps.map(d => d.getTime())) : null;

    sensorChart.options.scales.x.min = minTime ? new Date(minTime) : undefined;
    sensorChart.options.scales.x.max = maxTime ? new Date(maxTime) : undefined;

    sensorChart.data.datasets = Object.values(groupedData);
    sensorChart.update();

    updateStats(timeSeriesData);
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

function updateStats(data) {
    const uniqueSensors = new Set(data.map(d => d.sensor_id)).size;
    document.getElementById('totalSensors').textContent = uniqueSensors;
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