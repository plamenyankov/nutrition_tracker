/**
 * Zyra Cycle - Analytics Page JavaScript
 * Handles KPIs, charts, and body weight tracking
 */

// ============== Chart References ==============
let cyclingChart = null;
let readinessChart = null;
let efficiencyChart = null;
let vo2Chart = null;
let fatigueChart = null;
let aerobicChart = null;
let weightSparklineChart = null;

// ============== Initialize Analytics Page ==============
function initAnalyticsPage(cyclingChartData, readinessChartData) {
    initPerformanceChart(cyclingChartData);
    initReadinessChart(readinessChartData);
    loadAnalyticsKpis();
    loadEfficiencyVo2Charts();
    loadBodyWeights();
    initWeightSaveButton();
    
    console.log('📊 Analytics page initialized');
}

// ============== KPIs ==============
async function loadAnalyticsKpis() {
    try {
        const response = await fetch('/cycling-readiness/api/analytics/kpis');
        const data = await response.json();
        
        if (data.success && data.kpis) {
            renderAnalyticsKpis(data.kpis);
        }
    } catch (err) {
        console.error('Error loading KPIs:', err);
    }
}

function renderAnalyticsKpis(kpis) {
    // KPI 1: Acute Load (7-day TSS)
    const acuteLoad = kpis.acute_load_7d || {};
    const acuteCard = document.getElementById('kpiAcuteLoad');
    const acuteValue = document.getElementById('kpiAcuteValue');
    const acuteSubtitle = document.getElementById('kpiAcuteSubtitle');
    const acuteBadge = document.getElementById('kpiAcuteBadge');
    
    if (acuteLoad.tss !== null && acuteLoad.tss !== undefined) {
        acuteValue.textContent = Math.round(acuteLoad.tss);
        acuteSubtitle.textContent = `${acuteLoad.avg_per_day} TSS/day avg`;
        acuteBadge.textContent = acuteLoad.level;
        acuteBadge.className = `kpi-badge ${acuteLoad.level}`;
        acuteCard.className = `kpi-card load-${acuteLoad.level}`;
    } else {
        acuteValue.textContent = '--';
    }
    
    // KPI 2: Chronic Load (42-day)
    const chronicLoad = kpis.chronic_load_42d || {};
    const chronicValue = document.getElementById('kpiChronicValue');
    const chronicSubtitle = document.getElementById('kpiChronicSubtitle');
    
    if (chronicLoad.weekly_tss !== null && chronicLoad.weekly_tss !== undefined) {
        chronicValue.textContent = Math.round(chronicLoad.weekly_tss);
        chronicSubtitle.textContent = `${chronicLoad.workout_days} workouts in 6 weeks`;
    } else {
        chronicValue.textContent = '--';
    }
    
    // KPI 3: HRV Trend
    const hrvTrend = kpis.hrv_trend || {};
    const hrvCard = document.getElementById('kpiHrvTrend');
    const hrvValue = document.getElementById('kpiHrvValue');
    const hrvSubtitle = document.getElementById('kpiHrvSubtitle');
    const hrvTrendArrow = document.getElementById('kpiHrvTrendArrow');
    
    if (hrvTrend.today !== null && hrvTrend.today !== undefined) {
        hrvValue.textContent = Math.round(hrvTrend.today) + ' ms';
        hrvSubtitle.textContent = hrvTrend.baseline_30d ? `Baseline: ${Math.round(hrvTrend.baseline_30d)} ms` : 'vs 30-day baseline';
        
        const arrow = hrvTrend.direction === 'up' ? '↑' : hrvTrend.direction === 'down' ? '↓' : '→';
        const pct = hrvTrend.delta_percent !== null ? `${hrvTrend.delta_percent > 0 ? '+' : ''}${hrvTrend.delta_percent}%` : '';
        hrvTrendArrow.innerHTML = `<span class="trend-arrow">${arrow}</span><span class="trend-pct">${pct}</span>`;
        hrvTrendArrow.className = `kpi-trend ${hrvTrend.direction}`;
        
        if (hrvTrend.direction === 'up') {
            hrvCard.classList.add('hrv-good');
        }
    } else {
        hrvValue.textContent = '--';
    }
    
    // KPI 4: RHR Trend
    const rhrTrend = kpis.rhr_trend || {};
    const rhrCard = document.getElementById('kpiRhrTrend');
    const rhrValue = document.getElementById('kpiRhrValue');
    const rhrSubtitle = document.getElementById('kpiRhrSubtitle');
    const rhrTrendArrow = document.getElementById('kpiRhrTrendArrow');
    
    if (rhrTrend.today !== null && rhrTrend.today !== undefined) {
        rhrValue.textContent = rhrTrend.today + ' bpm';
        rhrSubtitle.textContent = rhrTrend.baseline_30d ? `Baseline: ${Math.round(rhrTrend.baseline_30d)} bpm` : 'vs 30-day baseline';
        
        const arrow = rhrTrend.direction === 'up' ? '↑' : rhrTrend.direction === 'down' ? '↓' : '→';
        const pct = rhrTrend.delta_percent !== null ? `${rhrTrend.delta_percent > 0 ? '+' : ''}${rhrTrend.delta_percent}%` : '';
        rhrTrendArrow.innerHTML = `<span class="trend-arrow">${arrow}</span><span class="trend-pct">${pct}</span>`;
        
        const trendClass = rhrTrend.direction === 'up' ? 'down' : rhrTrend.direction === 'down' ? 'up' : 'flat';
        rhrTrendArrow.className = `kpi-trend ${trendClass}`;
        
        if (rhrTrend.direction === 'up') {
            rhrCard.classList.add('rhr-elevated');
        }
    } else {
        rhrValue.textContent = '--';
    }
    
    // KPI 5: Z2 Power Trend
    const powerTrend = kpis.z2_power_trend || {};
    const powerCard = document.getElementById('kpiPowerTrend');
    const powerValue = document.getElementById('kpiPowerValue');
    const powerSubtitle = document.getElementById('kpiPowerSubtitle');
    const powerTrendArrow = document.getElementById('kpiPowerTrendArrow');
    
    if (powerTrend.avg_7d !== null && powerTrend.avg_7d !== undefined) {
        powerValue.textContent = Math.round(powerTrend.avg_7d) + 'W';
        powerSubtitle.textContent = powerTrend.avg_30d ? `30d avg: ${Math.round(powerTrend.avg_30d)}W` : '7d vs 30d avg';
        
        const arrow = powerTrend.direction === 'up' ? '↑' : powerTrend.direction === 'down' ? '↓' : '→';
        const pct = powerTrend.delta_percent !== null ? `${powerTrend.delta_percent > 0 ? '+' : ''}${powerTrend.delta_percent}%` : '';
        powerTrendArrow.innerHTML = `<span class="trend-arrow">${arrow}</span><span class="trend-pct">${pct}</span>`;
        powerTrendArrow.className = `kpi-trend ${powerTrend.direction}`;
        
        if (powerTrend.direction === 'up') {
            powerCard.classList.add('power-up');
        }
    } else if (powerTrend.avg_30d !== null && powerTrend.avg_30d !== undefined) {
        powerValue.textContent = Math.round(powerTrend.avg_30d) + 'W';
        powerSubtitle.textContent = '30-day average';
    } else {
        powerValue.textContent = '--';
    }
}

// ============== Performance Trends Chart ==============
function initPerformanceChart(data) {
    const canvas = document.getElementById('cyclingChart');
    if (!canvas || !data?.dates || data.dates.length === 0) return;
    
    if (cyclingChart) cyclingChart.destroy();
    
    cyclingChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [
                {
                    label: 'Avg Power (W)',
                    data: data.avg_power,
                    borderColor: '#00E676',
                    backgroundColor: 'rgba(0, 230, 118, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: 'Avg HR (bpm)',
                    data: data.avg_hr,
                    borderColor: '#FF5252',
                    backgroundColor: 'rgba(255, 82, 82, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y1'
                },
                {
                    label: 'TSS',
                    data: data.tss,
                    borderColor: '#0077FF',
                    backgroundColor: 'rgba(0, 119, 255, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y2'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: 'rgba(255,255,255,0.7)', font: { size: 10 } }
                }
            },
            scales: {
                x: {
                    ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    title: { display: true, text: 'Power (W)', color: '#00E676', font: { size: 10 } },
                    ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    title: { display: true, text: 'HR (bpm)', color: '#FF5252', font: { size: 10 } },
                    ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } },
                    grid: { display: false }
                },
                y2: {
                    type: 'linear',
                    position: 'right',
                    title: { display: true, text: 'TSS', color: '#0077FF', font: { size: 10 } },
                    ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } },
                    grid: { display: false }
                }
            }
        }
    });
}

// ============== Readiness Trend Chart ==============
function initReadinessChart(data) {
    const canvas = document.getElementById('readinessChart');
    if (!canvas || !data?.dates || data.dates.length === 0) return;
    
    if (readinessChart) readinessChart.destroy();
    
    readinessChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [{
                label: 'Readiness Score',
                data: data.scores,
                borderColor: '#00FFC6',
                backgroundColor: 'rgba(0, 255, 198, 0.15)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: 'rgba(255,255,255,0.7)', font: { size: 10 } }
                }
            },
            scales: {
                x: {
                    ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    min: 0,
                    max: 100,
                    ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

// ============== Efficiency & VO2 Charts ==============
async function loadEfficiencyVo2Charts() {
    try {
        const response = await fetch('/cycling-readiness/api/analytics/efficiency-vo2');
        const data = await response.json();
        
        if (data.success) {
            renderEfficiencyChart(data.efficiency_timeseries, data.efficiency_rolling_7d);
            renderVo2Chart(data.vo2_weekly);
            renderFatigueChart(data.fatigue_ratio);
            renderAerobicEfficiencyChart(data.aerobic_efficiency);
        }
    } catch (err) {
        console.error('Error loading efficiency/VO2 data:', err);
    }
}

function renderEfficiencyChart(timeseries, rolling) {
    const chartContainer = document.getElementById('efficiencyChartContainer');
    const emptyState = document.getElementById('efficiencyChartEmpty');
    const canvas = document.getElementById('efficiencyChart');
    
    if (!timeseries || timeseries.length < 3) {
        if (chartContainer) chartContainer.style.display = 'none';
        if (emptyState) emptyState.style.display = 'flex';
        return;
    }
    
    if (chartContainer) chartContainer.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    
    const dates = timeseries.map(d => d.date);
    const eiValues = timeseries.map(d => d.efficiency_index);
    const rollingDates = rolling.map(d => d.date);
    
    if (efficiencyChart) efficiencyChart.destroy();
    
    efficiencyChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Session EI',
                    data: eiValues,
                    borderColor: 'rgba(0, 255, 198, 0.5)',
                    backgroundColor: 'rgba(0, 255, 198, 0.1)',
                    pointRadius: 4,
                    tension: 0,
                    fill: false
                },
                {
                    label: '7-Day Rolling Avg',
                    data: rollingDates.map(d => {
                        const idx = dates.indexOf(d);
                        return idx >= 0 ? (rolling.find(r => r.date === d)?.rolling_ei || null) : null;
                    }),
                    borderColor: '#00FFC6',
                    backgroundColor: 'rgba(0, 255, 198, 0.15)',
                    pointRadius: 0,
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: 'rgba(255,255,255,0.7)', font: { size: 10 } } },
                tooltip: {
                    callbacks: {
                        afterBody: function(context) {
                            const dataIndex = context[0].dataIndex;
                            const entry = timeseries[dataIndex];
                            if (entry) {
                                return [`Power: ${entry.avg_power_w}W`, `HR: ${entry.avg_hr} bpm`];
                            }
                            return [];
                        }
                    }
                }
            },
            scales: {
                x: { ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: 'W per bpm', color: 'rgba(255,255,255,0.6)' }, ticks: { color: 'rgba(255,255,255,0.4)' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

function renderVo2Chart(weeklyData) {
    const chartContainer = document.getElementById('vo2ChartContainer');
    const emptyState = document.getElementById('vo2ChartEmpty');
    const canvas = document.getElementById('vo2Chart');
    
    if (!weeklyData || weeklyData.length < 2) {
        if (chartContainer) chartContainer.style.display = 'none';
        if (emptyState) emptyState.style.display = 'flex';
        return;
    }
    
    if (chartContainer) chartContainer.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    
    const hasVo2Index = weeklyData.some(d => d.vo2_index !== null);
    const labels = weeklyData.map(d => d.week_label);
    const values = hasVo2Index ? weeklyData.map(d => d.vo2_index) : weeklyData.map(d => d.peak_power_w);
    
    if (vo2Chart) vo2Chart.destroy();
    
    vo2Chart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: hasVo2Index ? 'VO₂ Index (W/kg)' : 'Peak Power (W)',
                data: values,
                borderColor: '#FF7043',
                backgroundColor: 'rgba(255, 112, 67, 0.15)',
                pointRadius: 6,
                borderWidth: 3,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            const entry = weeklyData[idx];
                            const lines = [];
                            if (entry.vo2_index !== null) lines.push(`VO₂ Index: ${entry.vo2_index} W/kg`);
                            lines.push(`Peak Power: ${entry.peak_power_w}W`);
                            if (entry.weight_kg) lines.push(`Weight: ${entry.weight_kg} kg`);
                            return lines;
                        }
                    }
                }
            },
            scales: {
                x: { ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: hasVo2Index ? 'W/kg' : 'Watts', color: 'rgba(255,255,255,0.6)' }, ticks: { color: 'rgba(255,255,255,0.4)' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

function renderFatigueChart(fatigueData) {
    const chartContainer = document.getElementById('fatigueChartContainer');
    const emptyState = document.getElementById('fatigueChartEmpty');
    const canvas = document.getElementById('fatigueChart');
    
    if (!fatigueData || fatigueData.length < 3) {
        if (chartContainer) chartContainer.style.display = 'none';
        if (emptyState) emptyState.style.display = 'flex';
        return;
    }
    
    if (chartContainer) chartContainer.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    
    if (fatigueChart) fatigueChart.destroy();
    
    fatigueChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: fatigueData.map(d => d.date),
            datasets: [{
                label: 'HR Drift %',
                data: fatigueData.map(d => d.fatigue_ratio),
                borderColor: '#FF7043',
                backgroundColor: 'rgba(255, 112, 67, 0.15)',
                pointRadius: 4,
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const entry = fatigueData[context.dataIndex];
                            return [`HR Drift: ${entry.fatigue_ratio}%`, `Avg HR: ${entry.avg_hr} bpm`, `Max HR: ${entry.max_hr} bpm`];
                        }
                    }
                }
            },
            scales: {
                x: { ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: 'HR Drift %', color: 'rgba(255,255,255,0.6)' }, ticks: { color: 'rgba(255,255,255,0.4)' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

function renderAerobicEfficiencyChart(aerobicData) {
    const chartContainer = document.getElementById('aerobicChartContainer');
    const emptyState = document.getElementById('aerobicChartEmpty');
    const canvas = document.getElementById('aerobicChart');
    
    if (!aerobicData || aerobicData.length < 3) {
        if (chartContainer) chartContainer.style.display = 'none';
        if (emptyState) emptyState.style.display = 'flex';
        return;
    }
    
    if (chartContainer) chartContainer.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    
    if (aerobicChart) aerobicChart.destroy();
    
    aerobicChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: aerobicData.map(d => d.date),
            datasets: [{
                label: 'Aerobic Efficiency',
                data: aerobicData.map(d => d.aerobic_efficiency),
                borderColor: '#7C4DFF',
                backgroundColor: 'rgba(124, 77, 255, 0.15)',
                pointRadius: 4,
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const entry = aerobicData[context.dataIndex];
                            return [`Efficiency: ${entry.aerobic_efficiency} W/ms`, `Power: ${entry.avg_power_w}W`, `HRV: ${entry.hrv_avg} ms`];
                        }
                    }
                }
            },
            scales: {
                x: { ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: 'W per ms HRV', color: 'rgba(255,255,255,0.6)' }, ticks: { color: 'rgba(255,255,255,0.4)' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

// ============== Body Weight ==============
async function loadBodyWeights() {
    try {
        const response = await fetch('/cycling-readiness/api/analytics/weights');
        const data = await response.json();
        
        if (data.success && data.weights) {
            renderWeightSparkline(data.weights);
            updateLatestWeight(data.weights);
        }
    } catch (err) {
        console.error('Error loading body weights:', err);
    }
}

function updateLatestWeight(weights) {
    const latestValue = document.getElementById('weightLatestValue');
    if (weights && weights.length > 0) {
        const latest = weights[weights.length - 1];
        latestValue.textContent = `${latest.weight_kg} kg`;
    } else {
        latestValue.textContent = '--';
    }
}

function renderWeightSparkline(weights) {
    const container = document.getElementById('weightSparklineContainer');
    const emptyState = document.getElementById('weightChartEmpty');
    const canvas = document.getElementById('weightSparkline');
    
    if (!weights || weights.length < 2) {
        if (container) container.style.display = 'none';
        if (emptyState) emptyState.style.display = 'flex';
        return;
    }
    
    if (container) container.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    
    if (weightSparklineChart) weightSparklineChart.destroy();
    
    weightSparklineChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: weights.map(w => w.date),
            datasets: [{
                data: weights.map(w => w.weight_kg),
                borderColor: '#26A69A',
                backgroundColor: 'rgba(38, 166, 154, 0.15)',
                pointRadius: 3,
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 }, maxTicksLimit: 4 }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

function initWeightSaveButton() {
    const saveBtn = document.getElementById('saveWeightBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveBodyWeight);
    }
}

async function saveBodyWeight() {
    const dateInput = document.getElementById('weightDate');
    const weightInput = document.getElementById('weightValue');
    const statusEl = document.getElementById('weightSaveStatus');
    
    const date = dateInput?.value;
    const weight = parseFloat(weightInput?.value);
    
    if (!date || isNaN(weight)) {
        statusEl.textContent = 'Please enter both date and weight';
        statusEl.className = 'weight-save-status error';
        return;
    }
    
    try {
        const response = await fetch('/cycling-readiness/api/analytics/weights', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, weight_kg: weight })
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusEl.textContent = `Saved ${weight} kg for ${date}`;
            statusEl.className = 'weight-save-status success';
            weightInput.value = '';
            loadBodyWeights();
            loadEfficiencyVo2Charts();
        } else {
            statusEl.textContent = data.error || 'Failed to save';
            statusEl.className = 'weight-save-status error';
        }
    } catch (err) {
        console.error('Error saving weight:', err);
        statusEl.textContent = 'Error saving weight';
        statusEl.className = 'weight-save-status error';
    }
}

// Export for global use
window.initAnalyticsPage = initAnalyticsPage;

