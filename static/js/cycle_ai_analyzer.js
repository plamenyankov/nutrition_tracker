/**
 * AI Analyzer Page JavaScript
 * 
 * Handles:
 * - Loading analysis history for KPIs and list
 * - Computing KPIs from history data
 * - Rendering history list with clickable rows
 * - Loading detailed analysis for selected workout
 * - URL-based navigation and state management
 */

// ============== Constants ==============

const EXECUTION_LABELS = {
    'excellent': { text: 'Excellent', class: 'label-excellent' },
    'good': { text: 'Good', class: 'label-good' },
    'ok': { text: 'OK', class: 'label-ok' },
    'too_easy': { text: 'Too Easy', class: 'label-too-easy' },
    'overreached': { text: 'Overreached', class: 'label-overreached' }
};

const FATIGUE_BADGES = {
    'low': { text: 'Low Fatigue Risk', class: 'fatigue-low' },
    'medium': { text: 'Medium Fatigue Risk', class: 'fatigue-medium' },
    'high': { text: 'High Fatigue Risk', class: 'fatigue-high' }
};

// Zone mappings for HR and Power ranges (based on typical athlete profile)
const ZONE_RANGES = {
    'rest': { 
        hr: { min: 0, max: 100 }, 
        power: { min: 0, max: 0 },
        duration: { min: 0, max: 0 },
        label: 'Rest'
    },
    'recovery_spin_z1': { 
        hr: { min: 110, max: 125 }, 
        power: { min: 44, max: 59 },
        duration: { min: 20, max: 30 },
        label: 'Z1'
    },
    'easy_endurance_z1': { 
        hr: { min: 110, max: 125 }, 
        power: { min: 44, max: 65 },
        duration: { min: 30, max: 60 },
        label: 'Z1'
    },
    'steady_endurance_z2': { 
        hr: { min: 125, max: 140 }, 
        power: { min: 65, max: 85 },
        duration: { min: 45, max: 90 },
        label: 'Z2'
    },
    'progressive_endurance': { 
        hr: { min: 120, max: 145 }, 
        power: { min: 60, max: 90 },
        duration: { min: 45, max: 75 },
        label: 'Z1-Z2'
    },
    'norwegian_4x4': { 
        hr: { min: 160, max: 185 }, 
        power: { min: 150, max: 200 },
        duration: { min: 45, max: 60 },
        label: 'Z4-Z5'
    },
    'threshold_3x8': { 
        hr: { min: 150, max: 170 }, 
        power: { min: 120, max: 160 },
        duration: { min: 40, max: 55 },
        label: 'Z3-Z4'
    },
    'vo2max_intervals': { 
        hr: { min: 165, max: 190 }, 
        power: { min: 160, max: 220 },
        duration: { min: 35, max: 50 },
        label: 'Z5'
    },
    'cadence_drills': { 
        hr: { min: 115, max: 135 }, 
        power: { min: 50, max: 75 },
        duration: { min: 30, max: 45 },
        label: 'Z1-Z2'
    },
    'hybrid_endurance': { 
        hr: { min: 120, max: 145 }, 
        power: { min: 55, max: 85 },
        duration: { min: 45, max: 75 },
        label: 'Z1-Z2'
    }
};

// ============== State ==============

let currentWorkoutId = null;
let isLoading = false;
let historyData = [];

// ============== DOM Elements ==============

const elements = {
    // KPI elements
    kpiAvgExecution: null,
    kpiAvgCompliance: null,
    kpiOverreached: null,
    kpiGoodExecution: null,
    // History elements
    historyLoading: null,
    historyEmpty: null,
    historyList: null,
    // Analysis elements
    loading: null,
    empty: null,
    error: null,
    content: null,
    errorText: null,
    // Score elements
    overallScore: null,
    executionLabel: null,
    fatigueBadge: null,
    intensityScore: null,
    intensityBar: null,
    durationScore: null,
    durationBar: null,
    hrResponseScore: null,
    hrResponseBar: null,
    // Physiology elements
    physiologyCard: null,
    physiologyContent: null,
    // Comparison elements
    coachComparisonContent: null,
    // Summary elements
    summaryShort: null,
    summaryDetailed: null,
    // Action items elements
    actionItemsCard: null,
    actionItemsContent: null,
    // Plan vs Reality elements
    planVsRealityCard: null,
    planVsRealityContent: null,
    // Meta elements
    promptVersion: null,
    regenerateBtn: null
};

// ============== Initialization ==============

document.addEventListener('DOMContentLoaded', function() {
    initElements();
    initEventListeners();
    
    // Get workout ID from URL
    currentWorkoutId = window.ANALYZER_CONFIG?.workoutId || getWorkoutIdFromUrl();
    
    // Load history (which will also load KPIs and potentially auto-select first item)
    loadHistory();
});

// Handle browser back/forward navigation
window.addEventListener('popstate', function(event) {
    const newWorkoutId = getWorkoutIdFromUrl();
    if (newWorkoutId !== currentWorkoutId) {
        currentWorkoutId = newWorkoutId;
        updateHistorySelection(currentWorkoutId);
        if (currentWorkoutId) {
            loadAnalysis(currentWorkoutId, false);
        } else {
            showEmpty();
        }
    }
});

function initElements() {
    // KPI elements
    elements.kpiAvgExecution = document.getElementById('kpiAvgExecution');
    elements.kpiAvgCompliance = document.getElementById('kpiAvgCompliance');
    elements.kpiOverreached = document.getElementById('kpiOverreached');
    elements.kpiGoodExecution = document.getElementById('kpiGoodExecution');
    
    // History elements
    elements.historyLoading = document.getElementById('historyLoading');
    elements.historyEmpty = document.getElementById('historyEmpty');
    elements.historyList = document.getElementById('historyList');
    
    // Analysis elements
    elements.loading = document.getElementById('analysisLoading');
    elements.empty = document.getElementById('analysisEmpty');
    elements.error = document.getElementById('analysisError');
    elements.content = document.getElementById('analysisContent');
    elements.errorText = document.getElementById('analysisErrorText');
    
    elements.overallScore = document.getElementById('overallScore');
    elements.executionLabel = document.getElementById('executionLabel');
    elements.fatigueBadge = document.getElementById('fatigueBadge');
    elements.intensityScore = document.getElementById('intensityScore');
    elements.intensityBar = document.getElementById('intensityBar');
    elements.durationScore = document.getElementById('durationScore');
    elements.durationBar = document.getElementById('durationBar');
    elements.hrResponseScore = document.getElementById('hrResponseScore');
    elements.hrResponseBar = document.getElementById('hrResponseBar');
    
    // Physiology elements
    elements.physiologyCard = document.getElementById('physiologyCard');
    elements.physiologyContent = document.getElementById('physiologyContent');
    
    elements.coachComparisonContent = document.getElementById('coachComparisonContent');
    
    elements.summaryShort = document.getElementById('summaryShort');
    elements.summaryDetailed = document.getElementById('summaryDetailed');
    
    // Action items elements
    elements.actionItemsCard = document.getElementById('actionItemsCard');
    elements.actionItemsContent = document.getElementById('actionItemsContent');
    
    // Plan vs Reality elements
    elements.planVsRealityCard = document.getElementById('planVsRealityCard');
    elements.planVsRealityContent = document.getElementById('planVsRealityContent');
    
    elements.promptVersion = document.getElementById('promptVersion');
    elements.regenerateBtn = document.getElementById('regenerateBtn');
}

function initEventListeners() {
    // Regenerate button
    if (elements.regenerateBtn) {
        elements.regenerateBtn.addEventListener('click', function() {
            if (currentWorkoutId && !isLoading) {
                loadAnalysis(currentWorkoutId, true);
            }
        });
    }
}

// ============== URL Helpers ==============

function getWorkoutIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('workout_id');
    return id ? parseInt(id, 10) : null;
}

function updateUrl(workoutId) {
    const url = new URL(window.location);
    if (workoutId) {
        url.searchParams.set('workout_id', workoutId);
    } else {
        url.searchParams.delete('workout_id');
    }
    window.history.pushState({}, '', url);
}

// ============== History Loading ==============

async function loadHistory() {
    showHistoryLoading();
    
    try {
        const response = await fetch('/cycling-readiness/api/ai/analysis/history?limit=50');
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to load history');
        }
        
        historyData = data.analyses || [];
        
        // Compute and render KPIs
        computeAndRenderKPIs(historyData);
        
        // Render history list
        renderHistoryList(historyData);
        
        // If we have a workout ID from URL, load that analysis
        if (currentWorkoutId) {
            updateHistorySelection(currentWorkoutId);
            loadAnalysis(currentWorkoutId, false);
        } else if (historyData.length > 0) {
            // Auto-select the most recent analysis
            const firstItem = historyData[0];
            currentWorkoutId = firstItem.workout_id;
            updateUrl(currentWorkoutId);
            updateHistorySelection(currentWorkoutId);
            loadAnalysis(currentWorkoutId, false);
        } else {
            showEmpty();
        }
        
    } catch (error) {
        console.error('[AI Analyzer] Error loading history:', error);
        showHistoryEmpty();
        showEmpty();
    }
}

function showHistoryLoading() {
    if (elements.historyLoading) elements.historyLoading.style.display = 'flex';
    if (elements.historyEmpty) elements.historyEmpty.style.display = 'none';
    if (elements.historyList) elements.historyList.style.display = 'none';
}

function showHistoryEmpty() {
    if (elements.historyLoading) elements.historyLoading.style.display = 'none';
    if (elements.historyEmpty) elements.historyEmpty.style.display = 'flex';
    if (elements.historyList) elements.historyList.style.display = 'none';
}

function showHistoryList() {
    if (elements.historyLoading) elements.historyLoading.style.display = 'none';
    if (elements.historyEmpty) elements.historyEmpty.style.display = 'none';
    if (elements.historyList) elements.historyList.style.display = 'block';
}

// ============== KPI Computation ==============

function computeAndRenderKPIs(analyses) {
    // Filter to last 30 days
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    const recentAnalyses = analyses.filter(a => {
        const date = new Date(a.date);
        return date >= thirtyDaysAgo;
    });
    
    // KPI 1: Average Execution Score
    const executionScores = recentAnalyses
        .filter(a => a.overall_score != null)
        .map(a => a.overall_score);
    
    const avgExecution = executionScores.length > 0
        ? Math.round(executionScores.reduce((a, b) => a + b, 0) / executionScores.length)
        : null;
    
    if (elements.kpiAvgExecution) {
        elements.kpiAvgExecution.textContent = avgExecution ?? '--';
        elements.kpiAvgExecution.className = 'kpi-value ' + getScoreColorClass(avgExecution);
    }
    
    // KPI 2: Average Compliance Score
    const complianceScores = recentAnalyses
        .filter(a => a.compliance_score != null && a.compliance_score > 0)
        .map(a => a.compliance_score);
    
    const avgCompliance = complianceScores.length > 0
        ? Math.round(complianceScores.reduce((a, b) => a + b, 0) / complianceScores.length)
        : null;
    
    if (elements.kpiAvgCompliance) {
        elements.kpiAvgCompliance.textContent = avgCompliance ?? '--';
        elements.kpiAvgCompliance.className = 'kpi-value ' + getScoreColorClass(avgCompliance);
    }
    
    // KPI 3: Overreached / High-fatigue Count
    const overreachedCount = recentAnalyses.filter(a => 
        a.execution_label === 'overreached' || a.fatigue_risk === 'high'
    ).length;
    
    if (elements.kpiOverreached) {
        elements.kpiOverreached.textContent = overreachedCount;
        elements.kpiOverreached.className = 'kpi-value ' + (overreachedCount > 3 ? 'kpi-warning' : '');
    }
    
    // KPI 4: Good/Excellent Execution Rate
    const goodOrExcellent = recentAnalyses.filter(a => 
        a.execution_label === 'good' || a.execution_label === 'excellent'
    ).length;
    
    const goodRate = recentAnalyses.length > 0
        ? Math.round((goodOrExcellent / recentAnalyses.length) * 100)
        : null;
    
    if (elements.kpiGoodExecution) {
        elements.kpiGoodExecution.textContent = goodRate != null ? `${goodRate}%` : '--';
        elements.kpiGoodExecution.className = 'kpi-value ' + (goodRate >= 70 ? 'kpi-good' : '');
    }
}

// ============== History List Rendering ==============

function renderHistoryList(analyses) {
    if (!elements.historyList) return;
    
    if (analyses.length === 0) {
        showHistoryEmpty();
        return;
    }
    
    const html = analyses.map(a => {
        const labelInfo = EXECUTION_LABELS[a.execution_label] || { text: a.execution_label || '--', class: '' };
        const fatigueInfo = FATIGUE_BADGES[a.fatigue_risk] || { text: '', class: '' };
        
        const workoutSummary = a.workout_summary || {};
        const duration = workoutSummary.duration_min ? `${workoutSummary.duration_min}m` : '--';
        const power = workoutSummary.avg_power_w ? `${Math.round(workoutSummary.avg_power_w)}W` : '--';
        
        return `
            <div class="history-item" data-workout-id="${a.workout_id}">
                <div class="history-item-main">
                    <div class="history-date">${formatDate(a.date)}</div>
                    <div class="history-labels">
                        <span class="history-label ${labelInfo.class}">${labelInfo.text}</span>
                        ${a.fatigue_risk === 'high' ? `<span class="history-fatigue fatigue-high">High</span>` : ''}
                    </div>
                </div>
                <div class="history-item-details">
                    <span class="history-score ${getScoreColorClass(a.overall_score)}">${a.overall_score ?? '--'}</span>
                    <span class="history-stats"><i class="fas fa-clock"></i> ${duration}</span>
                    <span class="history-stats"><i class="fas fa-bolt"></i> ${power}</span>
                </div>
            </div>
        `;
    }).join('');
    
    elements.historyList.innerHTML = html;
    showHistoryList();
    
    // Add click handlers
    elements.historyList.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', function() {
            const workoutId = parseInt(this.dataset.workoutId, 10);
            selectHistoryItem(workoutId);
        });
    });
}

function selectHistoryItem(workoutId) {
    if (workoutId === currentWorkoutId) return;
    
    currentWorkoutId = workoutId;
    updateUrl(workoutId);
    updateHistorySelection(workoutId);
    loadAnalysis(workoutId, false);
}

function updateHistorySelection(workoutId) {
    if (!elements.historyList) return;
    
    // Remove previous selection
    elements.historyList.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add selection to current
    if (workoutId) {
        const selectedItem = elements.historyList.querySelector(`[data-workout-id="${workoutId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
            // Scroll into view if needed
            selectedItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
}

function formatDate(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ============== Analysis UI State Management ==============

function showLoading() {
    if (elements.loading) elements.loading.style.display = 'flex';
    if (elements.empty) elements.empty.style.display = 'none';
    if (elements.error) elements.error.style.display = 'none';
    if (elements.content) elements.content.style.display = 'none';
}

function showEmpty() {
    if (elements.loading) elements.loading.style.display = 'none';
    if (elements.empty) elements.empty.style.display = 'flex';
    if (elements.error) elements.error.style.display = 'none';
    if (elements.content) elements.content.style.display = 'none';
}

function showError(message) {
    if (elements.loading) elements.loading.style.display = 'none';
    if (elements.empty) elements.empty.style.display = 'none';
    if (elements.error) elements.error.style.display = 'flex';
    if (elements.content) elements.content.style.display = 'none';
    if (elements.errorText) elements.errorText.textContent = message || 'Could not load analysis for this workout.';
}

function showContent() {
    if (elements.loading) elements.loading.style.display = 'none';
    if (elements.empty) elements.empty.style.display = 'none';
    if (elements.error) elements.error.style.display = 'none';
    if (elements.content) elements.content.style.display = 'block';
}

// ============== API Calls ==============

async function loadAnalysis(workoutId, forceRegenerate = false) {
    if (isLoading) return;
    
    isLoading = true;
    showLoading();
    
    try {
        const response = await fetch('/cycling-readiness/api/ai/analysis/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                workout_id: workoutId,
                force_regenerate: forceRegenerate
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to load analysis');
        }
        
        renderAnalysis(data.analysis);
        showContent();
        
        // If this was a new analysis, refresh history to update the list
        if (!data.cached) {
            loadHistory();
        }
        
    } catch (error) {
        console.error('[AI Analyzer] Error loading analysis:', error);
        showError(error.message || 'Could not load analysis for this workout.');
    } finally {
        isLoading = false;
    }
}

// Global function for retry button
window.retryAnalysis = function() {
    if (currentWorkoutId) {
        loadAnalysis(currentWorkoutId, false);
    }
};

// ============== Rendering ==============

function renderAnalysis(analysis) {
    if (!analysis) {
        showError('No analysis data received.');
        return;
    }
    
    const scores = analysis.scores || {};
    const dimensionScores = scores.dimension_scores || {};
    const coachComparison = analysis.coach_comparison || {};
    const summary = analysis.summary || {};
    const raw = analysis.raw || {};
    
    // Physiology and action items are now top-level in the response
    const physiology = analysis.physiology || null;
    const actionItems = analysis.action_items || [];
    
    // Overall score
    if (elements.overallScore) {
        elements.overallScore.textContent = scores.overall_score ?? '--';
        elements.overallScore.className = 'score-number ' + getScoreColorClass(scores.overall_score);
    }
    
    // Execution label
    if (elements.executionLabel) {
        const labelInfo = EXECUTION_LABELS[scores.label] || { text: scores.label || '--', class: '' };
        elements.executionLabel.textContent = labelInfo.text;
        elements.executionLabel.className = 'execution-label ' + labelInfo.class;
    }
    
    // Fatigue badge
    if (elements.fatigueBadge) {
        const fatigueInfo = FATIGUE_BADGES[scores.fatigue_risk] || { text: scores.fatigue_risk || '--', class: '' };
        elements.fatigueBadge.textContent = fatigueInfo.text;
        elements.fatigueBadge.className = 'fatigue-badge ' + fatigueInfo.class;
    }
    
    // Dimension scores
    renderDimensionScore('intensity', dimensionScores.intensity);
    renderDimensionScore('duration', dimensionScores.duration);
    renderDimensionScore('hrResponse', dimensionScores.hr_response);
    
    // Physiology insights
    renderPhysiologyInsights(physiology);
    
    // Coach comparison (with deviation chips)
    renderCoachComparison(coachComparison);
    
    // Plan vs Reality micro-charts
    // Get workout summary from history data if available
    const workoutSummary = getWorkoutSummaryFromHistory(currentWorkoutId);
    renderPlanVsReality(coachComparison, workoutSummary);
    
    // Summary
    if (elements.summaryShort) {
        elements.summaryShort.textContent = summary.short_text || 'No summary available.';
    }
    if (elements.summaryDetailed) {
        elements.summaryDetailed.textContent = summary.detailed_text || '';
    }
    
    // Action items
    renderActionItems(actionItems);
    
    // Metadata
    if (elements.promptVersion) {
        elements.promptVersion.textContent = raw.prompt_version || 'unknown';
    }
}

function renderDimensionScore(dimension, score) {
    const scoreEl = elements[dimension + 'Score'];
    const barEl = elements[dimension + 'Bar'];
    
    if (scoreEl) {
        scoreEl.textContent = score ?? '--';
    }
    if (barEl) {
        const width = Math.min(100, Math.max(0, score || 0));
        barEl.style.width = width + '%';
        barEl.className = 'dimension-fill ' + getScoreColorClass(score);
    }
}

// ============== Physiology Insights ==============

function renderPhysiologyInsights(physiology) {
    if (!elements.physiologyCard || !elements.physiologyContent) return;
    
    // Hide if no physiology data
    if (!physiology || typeof physiology !== 'object') {
        elements.physiologyCard.style.display = 'none';
        return;
    }
    
    // Build physiology rows
    const rows = [];
    
    if (physiology.hrv_state) {
        rows.push({
            icon: 'fa-wave-square',
            label: 'HRV State',
            value: physiology.hrv_state
        });
    }
    
    if (physiology.rhr_state) {
        rows.push({
            icon: 'fa-heart',
            label: 'RHR State',
            value: physiology.rhr_state
        });
    }
    
    if (physiology.recovery_status) {
        rows.push({
            icon: 'fa-battery-three-quarters',
            label: 'Recovery',
            value: physiology.recovery_status
        });
    }
    
    if (physiology.cardiac_efficiency) {
        rows.push({
            icon: 'fa-bolt',
            label: 'Efficiency',
            value: physiology.cardiac_efficiency
        });
    }
    
    // Hide if no rows
    if (rows.length === 0) {
        elements.physiologyCard.style.display = 'none';
        return;
    }
    
    // Render rows
    elements.physiologyContent.innerHTML = rows.map(row => `
        <div class="physiology-row">
            <div class="physiology-icon"><i class="fas ${row.icon}"></i></div>
            <div class="physiology-label">${escapeHtml(row.label)}</div>
            <div class="physiology-value">${escapeHtml(row.value)}</div>
        </div>
    `).join('');
    
    elements.physiologyCard.style.display = 'block';
}

// ============== Deviation Chips Parser ==============

function parseDeviationChips(notes) {
    if (!notes || typeof notes !== 'string') return [];
    
    const chips = [];
    const notesLower = notes.toLowerCase();
    
    // Duration deviations
    if ((notesLower.includes('minutes') || notesLower.includes('min') || notesLower.includes('duration')) && 
        (notesLower.includes('exceeded') || notesLower.includes('longer') || notesLower.includes('extended'))) {
        chips.push({ text: '+Duration', class: 'chip-duration' });
    }
    
    // Power deviations
    if (notesLower.includes('power') && 
        (notesLower.includes('exceeded') || notesLower.includes('higher') || notesLower.includes('above'))) {
        chips.push({ text: 'Power ↑', class: 'chip-power' });
    }
    
    // Heart rate deviations
    if ((notesLower.includes('heart rate') || notesLower.includes('hr')) && 
        (notesLower.includes('exceeded') || notesLower.includes('higher') || notesLower.includes('elevated') || notesLower.includes('above'))) {
        chips.push({ text: 'HR ↑', class: 'chip-hr' });
    }
    
    // Intensity deviations
    if (notesLower.includes('intense') || notesLower.includes('too hard') || 
        notesLower.includes('beyond z1') || notesLower.includes('beyond z2') ||
        notesLower.includes('intensity') && (notesLower.includes('exceeded') || notesLower.includes('higher'))) {
        chips.push({ text: 'Intensity ↑', class: 'chip-intensity' });
    }
    
    return chips;
}

function renderCoachComparison(comparison) {
    if (!elements.coachComparisonContent) return;
    
    if (!comparison.has_coach_plan) {
        elements.coachComparisonContent.innerHTML = `
            <div class="no-coach-plan">
                <i class="fas fa-info-circle me-2"></i>
                No AI Coach plan was generated for this day.
            </div>
        `;
        return;
    }
    
    const planType = comparison.plan_type || 'Unknown';
    const complianceScore = comparison.compliance_score ?? '--';
    const notes = comparison.notes || '';
    
    // Format plan type for display
    const planTypeDisplay = planType
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
    
    // Parse deviation chips from notes
    const deviationChips = parseDeviationChips(notes);
    const chipsHtml = deviationChips.length > 0 
        ? `<div class="deviation-chips">${deviationChips.map(c => 
            `<span class="deviation-chip ${c.class}">${escapeHtml(c.text)}</span>`
          ).join('')}</div>` 
        : '';
    
    elements.coachComparisonContent.innerHTML = `
        <div class="coach-plan-info">
            <div class="plan-type">
                <span class="plan-label">Plan:</span>
                <span class="plan-value">${escapeHtml(planTypeDisplay)}</span>
            </div>
            <div class="compliance-score">
                <span class="compliance-label">Compliance:</span>
                <span class="compliance-value ${getComplianceClass(complianceScore)}">${complianceScore}/100</span>
            </div>
        </div>
        ${chipsHtml}
        ${notes ? `<div class="comparison-notes">${escapeHtml(notes)}</div>` : ''}
    `;
}

// ============== Action Items ==============

function renderActionItems(actionItems) {
    if (!elements.actionItemsCard || !elements.actionItemsContent) return;
    
    // Hide if no action items
    if (!actionItems || !Array.isArray(actionItems) || actionItems.length === 0) {
        elements.actionItemsCard.style.display = 'none';
        return;
    }
    
    // Render action items as checklist
    elements.actionItemsContent.innerHTML = `
        <ul class="action-items-list">
            ${actionItems.map(item => `
                <li class="action-item">
                    <i class="fas fa-chevron-right action-item-icon"></i>
                    <span class="action-item-text">${escapeHtml(item)}</span>
                </li>
            `).join('')}
        </ul>
    `;
    
    elements.actionItemsCard.style.display = 'block';
}

// ============== Plan vs Reality ==============

/**
 * Get workout summary from history data for the given workout ID
 */
function getWorkoutSummaryFromHistory(workoutId) {
    if (!workoutId || !historyData || historyData.length === 0) return null;
    
    const workout = historyData.find(h => h.workout_id == workoutId);
    return workout ? workout.workout_summary : null;
}

/**
 * Extract planned duration from coach notes
 * Looks for patterns like "extended by X minutes" or "shortened by X minutes"
 */
function extractPlannedDurationFromNotes(notes, actualDuration) {
    if (!notes || !actualDuration) return null;
    
    // Try to find "extended by X minutes" pattern
    const extendedMatch = notes.match(/extended\s+by\s+(\d+)\s*min/i);
    if (extendedMatch) {
        return actualDuration - parseInt(extendedMatch[1]);
    }
    
    // Try to find "shortened by X minutes" pattern
    const shortenedMatch = notes.match(/shortened\s+by\s+(\d+)\s*min/i);
    if (shortenedMatch) {
        return actualDuration + parseInt(shortenedMatch[1]);
    }
    
    // Try to find "X minutes longer" pattern
    const longerMatch = notes.match(/(\d+)\s*min(?:utes?)?\s+longer/i);
    if (longerMatch) {
        return actualDuration - parseInt(longerMatch[1]);
    }
    
    // Try to find "X minutes shorter" pattern
    const shorterMatch = notes.match(/(\d+)\s*min(?:utes?)?\s+shorter/i);
    if (shorterMatch) {
        return actualDuration + parseInt(shorterMatch[1]);
    }
    
    return null;
}

/**
 * Calculate delta percentage between actual and planned values
 */
function calculateDelta(actual, planned) {
    if (!actual || !planned || planned === 0) return null;
    return Math.round(((actual - planned) / planned) * 100);
}

/**
 * Determine if a value is within, above, or below the planned range
 */
function getComparisonStatus(actual, min, max) {
    if (actual === null || actual === undefined) return 'unknown';
    if (min === null || max === null) return 'unknown';
    
    if (actual < min) return 'below';
    if (actual > max) return 'above';
    return 'within';
}

/**
 * Get color class based on comparison status
 */
function getComparisonColorClass(status, metric) {
    // For HR and Power, being "within" is green, "above" can be yellow or red
    switch (status) {
        case 'within': return 'comparison-good';
        case 'above': return 'comparison-warn';
        case 'below': return 'comparison-low';
        default: return '';
    }
}

/**
 * Get zone ranges for a plan type
 */
function getZoneRanges(planType) {
    if (!planType) return null;
    
    // Normalize plan type
    const normalizedType = planType.toLowerCase().replace(/\s+/g, '_');
    
    // Direct match
    if (ZONE_RANGES[normalizedType]) {
        return ZONE_RANGES[normalizedType];
    }
    
    // Partial matches
    if (normalizedType.includes('z1') || normalizedType.includes('recovery') || normalizedType.includes('easy')) {
        return ZONE_RANGES['recovery_spin_z1'];
    }
    if (normalizedType.includes('z2') || normalizedType.includes('endurance') || normalizedType.includes('steady')) {
        return ZONE_RANGES['steady_endurance_z2'];
    }
    if (normalizedType.includes('norwegian') || normalizedType.includes('4x4')) {
        return ZONE_RANGES['norwegian_4x4'];
    }
    if (normalizedType.includes('threshold') || normalizedType.includes('tempo')) {
        return ZONE_RANGES['threshold_3x8'];
    }
    if (normalizedType.includes('vo2') || normalizedType.includes('interval')) {
        return ZONE_RANGES['vo2max_intervals'];
    }
    
    return null;
}

/**
 * Render the Plan vs Reality micro-charts
 */
function renderPlanVsReality(coachComparison, workoutSummary) {
    if (!elements.planVsRealityCard || !elements.planVsRealityContent) return;
    
    // Hide if no coach plan or no workout data
    if (!coachComparison || !coachComparison.has_coach_plan || !workoutSummary) {
        elements.planVsRealityCard.style.display = 'none';
        return;
    }
    
    const planType = coachComparison.plan_type;
    const notes = coachComparison.notes || '';
    const zoneRanges = getZoneRanges(planType);
    
    const actualDuration = workoutSummary.duration_min;
    const actualPower = workoutSummary.avg_power_w;
    const actualHR = workoutSummary.avg_hr_bpm;
    
    let chartsHtml = '';
    let hasAnyChart = false;
    
    // Duration chart
    const plannedDuration = extractPlannedDurationFromNotes(notes, actualDuration) 
        || (zoneRanges ? Math.round((zoneRanges.duration.min + zoneRanges.duration.max) / 2) : null);
    
    if (actualDuration) {
        hasAnyChart = true;
        const durationDelta = plannedDuration ? calculateDelta(actualDuration, plannedDuration) : null;
        chartsHtml += renderDurationChart(actualDuration, plannedDuration, durationDelta);
    }
    
    // Power chart
    if (actualPower && zoneRanges && zoneRanges.power) {
        hasAnyChart = true;
        const powerStatus = getComparisonStatus(actualPower, zoneRanges.power.min, zoneRanges.power.max);
        const powerMid = Math.round((zoneRanges.power.min + zoneRanges.power.max) / 2);
        const powerDelta = calculateDelta(actualPower, powerMid);
        chartsHtml += renderPowerChart(actualPower, zoneRanges.power, zoneRanges.label, powerStatus, powerDelta);
    } else if (actualPower) {
        // Show actual power without planned range
        hasAnyChart = true;
        chartsHtml += renderPowerChart(actualPower, null, null, 'unknown', null);
    }
    
    // HR chart
    if (actualHR && zoneRanges && zoneRanges.hr) {
        hasAnyChart = true;
        const hrStatus = getComparisonStatus(actualHR, zoneRanges.hr.min, zoneRanges.hr.max);
        const hrMid = Math.round((zoneRanges.hr.min + zoneRanges.hr.max) / 2);
        const hrDelta = calculateDelta(actualHR, hrMid);
        chartsHtml += renderHRChart(actualHR, zoneRanges.hr, zoneRanges.label, hrStatus, hrDelta);
    } else if (actualHR) {
        // Show actual HR without planned range
        hasAnyChart = true;
        chartsHtml += renderHRChart(actualHR, null, null, 'unknown', null);
    }
    
    if (!hasAnyChart) {
        elements.planVsRealityCard.style.display = 'none';
        return;
    }
    
    elements.planVsRealityContent.innerHTML = `
        <div class="micro-charts-grid">
            ${chartsHtml}
        </div>
    `;
    elements.planVsRealityCard.style.display = 'block';
}

/**
 * Render duration comparison chart
 */
function renderDurationChart(actual, planned, delta) {
    const maxDuration = Math.max(actual, planned || 0, 60); // At least 60 min scale
    const actualWidth = Math.min((actual / maxDuration) * 100, 100);
    const plannedWidth = planned ? Math.min((planned / maxDuration) * 100, 100) : 0;
    
    const deltaHtml = delta !== null 
        ? `<span class="delta-badge ${delta > 0 ? 'delta-positive' : delta < 0 ? 'delta-negative' : 'delta-neutral'}">${delta > 0 ? '+' : ''}${delta}%</span>` 
        : '';
    
    const plannedHtml = planned 
        ? `
            <div class="chart-row">
                <div class="chart-label">Planned</div>
                <div class="chart-bar-container">
                    <div class="chart-bar bar-planned" style="width: ${plannedWidth}%"></div>
                </div>
                <div class="chart-value">${planned} min</div>
            </div>
        ` 
        : `<div class="chart-row"><div class="chart-label">Planned</div><div class="chart-value-muted">n/a</div></div>`;
    
    return `
        <div class="micro-chart duration-chart">
            <div class="chart-title">
                <i class="fas fa-clock"></i> Duration ${deltaHtml}
            </div>
            ${plannedHtml}
            <div class="chart-row">
                <div class="chart-label">Actual</div>
                <div class="chart-bar-container">
                    <div class="chart-bar bar-actual" style="width: ${actualWidth}%"></div>
                </div>
                <div class="chart-value">${actual} min</div>
            </div>
        </div>
    `;
}

/**
 * Render power comparison chart
 */
function renderPowerChart(actual, plannedRange, zoneLabel, status, delta) {
    const maxPower = Math.max(actual, plannedRange ? plannedRange.max : 0, 100) * 1.2;
    const actualWidth = Math.min((actual / maxPower) * 100, 100);
    
    const deltaHtml = delta !== null 
        ? `<span class="delta-badge ${status === 'within' ? 'delta-neutral' : status === 'above' ? 'delta-positive' : 'delta-negative'}">${delta > 0 ? '+' : ''}${delta}%</span>` 
        : '';
    
    const statusClass = getComparisonColorClass(status, 'power');
    
    let rangeHtml = '';
    if (plannedRange) {
        const rangeStart = (plannedRange.min / maxPower) * 100;
        const rangeWidth = ((plannedRange.max - plannedRange.min) / maxPower) * 100;
        rangeHtml = `
            <div class="chart-row">
                <div class="chart-label">Planned</div>
                <div class="chart-bar-container">
                    <div class="chart-range" style="left: ${rangeStart}%; width: ${rangeWidth}%"></div>
                </div>
                <div class="chart-value">${plannedRange.min}–${plannedRange.max}W ${zoneLabel ? `(${zoneLabel})` : ''}</div>
            </div>
        `;
    } else {
        rangeHtml = `<div class="chart-row"><div class="chart-label">Planned</div><div class="chart-value-muted">n/a</div></div>`;
    }
    
    return `
        <div class="micro-chart power-chart">
            <div class="chart-title">
                <i class="fas fa-bolt"></i> Power (W) ${deltaHtml}
            </div>
            ${rangeHtml}
            <div class="chart-row">
                <div class="chart-label">Actual</div>
                <div class="chart-bar-container">
                    <div class="chart-bar bar-actual ${statusClass}" style="width: ${actualWidth}%"></div>
                </div>
                <div class="chart-value">${actual}W</div>
            </div>
        </div>
    `;
}

/**
 * Render HR comparison chart
 */
function renderHRChart(actual, plannedRange, zoneLabel, status, delta) {
    const maxHR = Math.max(actual, plannedRange ? plannedRange.max : 0, 180) * 1.1;
    const actualWidth = Math.min((actual / maxHR) * 100, 100);
    
    const deltaHtml = delta !== null 
        ? `<span class="delta-badge ${status === 'within' ? 'delta-neutral' : status === 'above' ? 'delta-positive' : 'delta-negative'}">${delta > 0 ? '+' : ''}${delta}%</span>` 
        : '';
    
    const statusClass = getComparisonColorClass(status, 'hr');
    
    let rangeHtml = '';
    if (plannedRange) {
        const rangeStart = (plannedRange.min / maxHR) * 100;
        const rangeWidth = ((plannedRange.max - plannedRange.min) / maxHR) * 100;
        rangeHtml = `
            <div class="chart-row">
                <div class="chart-label">Planned</div>
                <div class="chart-bar-container">
                    <div class="chart-range" style="left: ${rangeStart}%; width: ${rangeWidth}%"></div>
                </div>
                <div class="chart-value">${plannedRange.min}–${plannedRange.max} bpm ${zoneLabel ? `(${zoneLabel})` : ''}</div>
            </div>
        `;
    } else {
        rangeHtml = `<div class="chart-row"><div class="chart-label">Planned</div><div class="chart-value-muted">n/a</div></div>`;
    }
    
    return `
        <div class="micro-chart hr-chart">
            <div class="chart-title">
                <i class="fas fa-heartbeat"></i> Heart Rate (bpm) ${deltaHtml}
            </div>
            ${rangeHtml}
            <div class="chart-row">
                <div class="chart-label">Actual</div>
                <div class="chart-bar-container">
                    <div class="chart-bar bar-actual ${statusClass}" style="width: ${actualWidth}%"></div>
                </div>
                <div class="chart-value">${actual} bpm</div>
            </div>
        </div>
    `;
}

// ============== Utility Functions ==============

function getScoreColorClass(score) {
    if (score === null || score === undefined) return '';
    if (score >= 80) return 'score-excellent';
    if (score >= 65) return 'score-good';
    if (score >= 50) return 'score-ok';
    return 'score-low';
}

function getComplianceClass(score) {
    if (score === null || score === undefined || score === '--') return '';
    if (score >= 80) return 'compliance-high';
    if (score >= 60) return 'compliance-medium';
    return 'compliance-low';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
