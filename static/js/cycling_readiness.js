/**
 * Zyra Cycle - Cycling & Readiness Dashboard JavaScript
 * Version: 3.0
 */

// ============== Module State ==============
let hasCardioData = false;
let autoHrvStatus = null;
let autoRhrStatus = null;
let currentReadinessData = null;
let rhrManualOverride = false;
let hrvManualOverride = false;
let originalRhrBpm = null;
let originalHrvLow = null;
let originalHrvHigh = null;
let deleteType = null;
let deleteId = null;
let reviewData = null;
let selectedFiles = [];

// ============== Day Type Constants (CSResponse v1) ==============
const DAY_TYPE_LABELS = {
    'rest': 'Rest Day',
    'recovery_spin_z1': 'Recovery Z1',
    'easy_endurance_z1': 'Easy Z1',
    'steady_endurance_z2': 'Endurance Z2',
    'progressive_endurance': 'Progressive',
    'norwegian_4x4': '4×4 VO2max',
    'threshold_3x8': '3×8 Threshold',
    'vo2max_intervals': 'VO2max Intervals',
    'cadence_drills': 'Cadence Drills',
    'hybrid_endurance': 'Hybrid',
    'other': 'Training'
};

const DAY_TYPE_CLASSES = {
    'rest': 'rest',
    'recovery_spin_z1': 'z1',
    'easy_endurance_z1': 'z1',
    'steady_endurance_z2': 'z2',
    'progressive_endurance': 'z2',
    'norwegian_4x4': 'hard',
    'threshold_3x8': 'hard',
    'vo2max_intervals': 'hard',
    'cadence_drills': 'z2',
    'hybrid_endurance': 'z2',
    'other': ''
};

// ============== Toast Helper ==============
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast-zyra ${type}`;
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ============== Status Message Helper ==============
function showStatus(type, message) {
    const el = document.getElementById('statusMessage');
    el.className = `status-msg ${type}`;
    const icon = type === 'loading' ? 'fa-spinner fa-spin' : type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    el.innerHTML = `<i class="fas ${icon}"></i><span>${message}</span>`;
    el.classList.remove('d-none');
}

function hideStatus() {
    document.getElementById('statusMessage').classList.add('d-none');
}

// ============== Loading Overlay ==============
function showLoading(text = 'Processing screenshots...') {
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.querySelector('.loading-text').textContent = text;
    loadingOverlay.classList.add('active');
}

function hideLoading() { 
    document.getElementById('loadingOverlay').classList.remove('active'); 
}

// ============== Tab Switching ==============
function initTabs() {
    document.querySelectorAll('.cycle-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.cycle-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            document.getElementById(this.dataset.tab + 'Tab').classList.add('active');
        });
    });
}

// ============== Rating Selectors ==============
function initRatingSelectors() {
    document.querySelectorAll('.rating-selector, .status-selector').forEach(selector => {
        selector.querySelectorAll('.rating-option, .status-option').forEach(option => {
            option.addEventListener('click', function() {
                selector.querySelectorAll('.rating-option, .status-option').forEach(o => o.classList.remove('selected'));
                this.classList.add('selected');
                this.querySelector('input').checked = true;
            });
        });
    });
}

// ============== Morning Readiness - Collapse/Expand ==============
window.toggleReadinessForm = function() {
    const card = document.getElementById('morningReadinessCard');
    const summary = document.getElementById('readinessSummary');
    
    if (card.classList.contains('collapsed')) {
        card.classList.remove('collapsed');
        summary.style.display = 'none';
    } else {
        if (currentReadinessData && currentReadinessData.has_readiness) {
            card.classList.add('collapsed');
            summary.style.display = 'flex';
        }
    }
};

window.editReadinessForDate = function() {
    const card = document.getElementById('morningReadinessCard');
    card.classList.remove('collapsed');
    document.getElementById('readinessSummary').style.display = 'none';
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

function updateReadinessSummary(data) {
    if (!data || !data.has_readiness) return;
    
    const r = data.readiness;
    
    const scoreEl = document.getElementById('summaryScore');
    if (r.morning_score) {
        scoreEl.textContent = r.morning_score;
        scoreEl.classList.remove('score-high', 'score-medium', 'score-low');
        if (r.morning_score >= 70) scoreEl.classList.add('score-high');
        else if (r.morning_score >= 40) scoreEl.classList.add('score-medium');
        else scoreEl.classList.add('score-low');
    } else {
        scoreEl.textContent = '--';
    }
    
    document.getElementById('summaryEnergy').textContent = `⚡ ${r.energy || '--'}`;
    
    const moodEmojis = { 1: '😔', 2: '😐', 3: '😊' };
    document.getElementById('summaryMood').textContent = moodEmojis[r.mood] || '😐';
    
    const fatigueLabels = { 1: 'Low', 2: 'Med', 3: 'High' };
    document.getElementById('summaryFatigue').textContent = `💪 ${fatigueLabels[r.muscle_fatigue] || '--'}`;
    
    const hrvArrows = { '-1': '↓', 0: '→', 1: '↑' };
    document.getElementById('summaryHrv').textContent = `HRV ${hrvArrows[r.hrv_status] || '→'}`;
    document.getElementById('summaryRhr').textContent = `RHR ${hrvArrows[r.rhr_status] || '→'}`;
    
    const symptomsEl = document.getElementById('summarySymptoms');
    symptomsEl.style.display = r.symptoms_flag ? 'inline-flex' : 'none';
}

function updateDateLabel(dateStr) {
    const label = document.getElementById('readinessDateLabel');
    if (dateStr) {
        const d = new Date(dateStr + 'T00:00:00');
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const dateOnly = new Date(dateStr + 'T00:00:00');
        
        if (dateOnly.getTime() === today.getTime()) {
            label.textContent = '(Today)';
        } else {
            label.textContent = `(${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })})`;
        }
    }
}

async function loadFullReadinessData(date) {
    try {
        const response = await fetch(`/cycling-readiness/api/readiness/full?date=${date}`);
        const data = await response.json();
        
        if (data.success) {
            currentReadinessData = data;
            hasCardioData = data.has_cardio;
            
            updateDateLabel(date);
            
            const card = document.getElementById('morningReadinessCard');
            const cardioDisplay = document.getElementById('cardioDataDisplay');
            const manualInput = document.getElementById('manualCardioInput');
            const hrvAutoLabel = document.getElementById('hrvAutoLabel');
            const rhrAutoLabel = document.getElementById('rhrAutoLabel');
            
            if (data.cardio) {
                originalRhrBpm = data.cardio.rhr_bpm;
                originalHrvLow = data.cardio.hrv_low_ms;
                originalHrvHigh = data.cardio.hrv_high_ms;
                rhrManualOverride = data.cardio.rhr_manual_override;
                hrvManualOverride = data.cardio.hrv_manual_override;
            }
            
            if (data.has_cardio) {
                cardioDisplay.style.display = 'block';
                manualInput.style.display = 'none';
                
                const rhrDisplay = document.getElementById('displayRhrBpm');
                rhrDisplay.textContent = data.cardio.rhr_bpm ? `${data.cardio.rhr_bpm} bpm` : '--';
                
                const hrvDisplay = document.getElementById('displayHrv');
                if (data.cardio.hrv_low_ms && data.cardio.hrv_high_ms) {
                    if (data.cardio.hrv_low_ms === data.cardio.hrv_high_ms) {
                        hrvDisplay.textContent = `${data.cardio.hrv_low_ms} ms`;
                    } else {
                        hrvDisplay.textContent = `${data.cardio.hrv_low_ms}–${data.cardio.hrv_high_ms} ms`;
                    }
                } else {
                    hrvDisplay.textContent = '--';
                }
                
                updateOverrideChip('rhr', data.cardio.rhr_manual_override);
                updateOverrideChip('hrv', data.cardio.hrv_manual_override);
                
                autoHrvStatus = data.calculated_status.hrv_status;
                autoRhrStatus = data.calculated_status.rhr_status;
                
                if (autoHrvStatus !== null) {
                    selectStatusButton('hrv_status', autoHrvStatus);
                    hrvAutoLabel.style.display = 'inline';
                }
                
                if (autoRhrStatus !== null) {
                    selectStatusButton('rhr_status', autoRhrStatus);
                    rhrAutoLabel.style.display = 'inline';
                }
            } else {
                cardioDisplay.style.display = 'none';
                manualInput.style.display = 'block';
                hrvAutoLabel.style.display = 'none';
                rhrAutoLabel.style.display = 'none';
            }
            
            if (data.has_readiness && data.readiness) {
                prefillReadinessForm(data.readiness);
                updateReadinessSummary(data);
                card.classList.add('collapsed');
                document.getElementById('readinessSummary').style.display = 'flex';
            } else {
                clearReadinessForm();
                card.classList.remove('collapsed');
                document.getElementById('readinessSummary').style.display = 'none';
            }
        }
    } catch (err) {
        console.error('Error loading full readiness data:', err);
    }
}

function selectStatusButton(name, value) {
    const radio = document.querySelector(`[name="${name}"][value="${value}"]`);
    if (radio) {
        document.querySelectorAll(`[name="${name}"]`).forEach(r => {
            r.checked = false;
            r.closest('.status-option').classList.remove('selected');
        });
        radio.checked = true;
        radio.closest('.status-option').classList.add('selected');
    }
}

function updateOverrideChip(type, isManual) {
    const chip = document.getElementById(`${type}AutoChip`);
    if (chip) {
        if (isManual) {
            chip.textContent = 'MANUAL';
            chip.classList.add('manual');
        } else {
            chip.textContent = 'AUTO';
            chip.classList.remove('manual');
        }
    }
}

window.toggleCardioOverride = function(type) {
    const inputDiv = document.getElementById(`${type}OverrideInput`);
    const valueSpan = document.getElementById(`display${type === 'rhr' ? 'RhrBpm' : 'Hrv'}`);
    
    if (inputDiv.style.display === 'none') {
        inputDiv.style.display = 'block';
        valueSpan.style.display = 'none';
        
        if (type === 'rhr' && originalRhrBpm) {
            document.getElementById('overrideRhrBpm').value = originalRhrBpm;
        } else if (type === 'hrv') {
            if (originalHrvLow) document.getElementById('overrideHrvLow').value = originalHrvLow;
            if (originalHrvHigh) document.getElementById('overrideHrvHigh').value = originalHrvHigh;
        }
    } else {
        inputDiv.style.display = 'none';
        valueSpan.style.display = 'block';
    }
};

window.resetCardioToAuto = function(type) {
    const inputDiv = document.getElementById(`${type}OverrideInput`);
    const valueSpan = document.getElementById(`display${type === 'rhr' ? 'RhrBpm' : 'Hrv'}`);
    
    inputDiv.style.display = 'none';
    valueSpan.style.display = 'block';
    
    if (type === 'rhr') {
        document.getElementById('overrideRhrBpm').value = '';
        rhrManualOverride = false;
    } else {
        document.getElementById('overrideHrvLow').value = '';
        document.getElementById('overrideHrvHigh').value = '';
        hrvManualOverride = false;
    }
    
    updateOverrideChip(type, false);
};

function prefillReadinessForm(r) {
    document.getElementById('readinessEntryId').value = r.id || '';
    
    if (r.energy) {
        const energyRadio = document.querySelector(`[name="energy"][value="${r.energy}"]`);
        if (energyRadio) {
            energyRadio.checked = true;
            energyRadio.closest('.rating-option').classList.add('selected');
        }
    }
    
    if (r.mood) {
        const moodRadio = document.querySelector(`[name="mood"][value="${r.mood}"]`);
        if (moodRadio) {
            moodRadio.checked = true;
            moodRadio.closest('.rating-option').classList.add('selected');
        }
    }
    
    if (r.muscle_fatigue) {
        const fatigueRadio = document.querySelector(`[name="muscle_fatigue"][value="${r.muscle_fatigue}"]`);
        if (fatigueRadio) {
            fatigueRadio.checked = true;
            fatigueRadio.closest('.rating-option').classList.add('selected');
        }
    }
    
    if (r.hrv_status !== null && r.hrv_status !== undefined) {
        selectStatusButton('hrv_status', r.hrv_status);
    }
    
    if (r.rhr_status !== null && r.rhr_status !== undefined) {
        selectStatusButton('rhr_status', r.rhr_status);
    }
    
    document.getElementById('symptomsFlag').checked = r.symptoms_flag || false;
}

function clearReadinessForm() {
    document.getElementById('readinessEntryId').value = '';
    
    document.querySelectorAll('#readinessForm input[type="radio"]').forEach(r => {
        r.checked = false;
        const opt = r.closest('.rating-option, .status-option');
        if (opt) opt.classList.remove('selected');
    });
    
    document.getElementById('symptomsFlag').checked = false;
    
    const manualRhr = document.getElementById('manualRhrBpm');
    const manualHrvLow = document.getElementById('manualHrvLow');
    const manualHrvHigh = document.getElementById('manualHrvHigh');
    if (manualRhr) manualRhr.value = '';
    if (manualHrvLow) manualHrvLow.value = '';
    if (manualHrvHigh) manualHrvHigh.value = '';
}

// ============== Readiness History Table ==============
async function loadReadinessHistory() {
    try {
        const response = await fetch('/cycling-readiness/api/readiness?limit=14');
        const data = await response.json();
        
        const tbody = document.getElementById('readinessHistoryBody');
        const emptyState = document.getElementById('readinessHistoryEmpty');
        const table = document.getElementById('readinessHistoryTable');
        
        if (data.entries && data.entries.length > 0) {
            table.style.display = 'table';
            emptyState.style.display = 'none';
            tbody.innerHTML = data.entries.map(e => renderReadinessHistoryRow(e)).join('');
        } else {
            table.style.display = 'none';
            emptyState.style.display = 'block';
        }
    } catch (err) {
        console.error('Error loading readiness history:', err);
    }
}

function renderReadinessHistoryRow(e) {
    const dateStr = e.date;
    const d = new Date(dateStr + 'T00:00:00');
    const dateLabel = d.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
    
    let scoreBadge = '<span class="val-empty">--</span>';
    if (e.morning_score) {
        let scoreClass = e.morning_score >= 70 ? 'score-high' : (e.morning_score >= 40 ? 'score-medium' : 'score-low');
        scoreBadge = `<span class="score-badge ${scoreClass}">${e.morning_score}</span>`;
    }
    
    const moodEmojis = { 1: '😔', 2: '😐', 3: '😊' };
    const moodDisplay = moodEmojis[e.mood] || '<span class="val-empty">--</span>';
    
    const fatigueLabels = { 1: 'Lo', 2: 'Med', 3: 'Hi' };
    const fatigueDisplay = fatigueLabels[e.muscle_fatigue] || '--';
    
    let sleepDisplay = '<span class="val-empty">--</span>';
    if (e.sleep_minutes) {
        sleepDisplay = `${(e.sleep_minutes / 60).toFixed(1)}h`;
    }
    
    let rhrDisplay = '<span class="val-empty">--</span>';
    if (e.rhr_bpm) {
        const rhrClass = e.rhr_manual_override ? 'cardio-value has-override' : 'cardio-value';
        rhrDisplay = `<span class="${rhrClass}">${e.rhr_bpm}</span>`;
    }
    
    let hrvDisplay = '<span class="val-empty">--</span>';
    if (e.hrv_low_ms && e.hrv_high_ms) {
        const hrvClass = e.hrv_manual_override ? 'cardio-value has-override' : 'cardio-value';
        if (e.hrv_low_ms === e.hrv_high_ms) {
            hrvDisplay = `<span class="${hrvClass}">${e.hrv_low_ms}</span>`;
        } else {
            hrvDisplay = `<span class="${hrvClass}">${e.hrv_low_ms}-${e.hrv_high_ms}</span>`;
        }
    }
    
    function statusArrow(val) {
        if (val === 1) return '<span class="status-arrow positive">↑</span>';
        if (val === -1) return '<span class="status-arrow negative">↓</span>';
        return '<span class="status-arrow neutral">→</span>';
    }
    
    const symptomsDisplay = e.symptoms_flag ? '🤒' : '<span class="val-empty">-</span>';
    
    return `
        <tr data-readiness-id="${e.id}" data-date="${dateStr}">
            <td>${dateLabel}</td>
            <td>${scoreBadge}</td>
            <td>${e.energy || '--'}</td>
            <td class="mood-emoji">${moodDisplay}</td>
            <td>${fatigueDisplay}</td>
            <td class="val-time">${sleepDisplay}</td>
            <td>${rhrDisplay}</td>
            <td>${hrvDisplay}</td>
            <td>${statusArrow(e.hrv_status)}</td>
            <td>${statusArrow(e.rhr_status)}</td>
            <td>${symptomsDisplay}</td>
            <td>
                <button class="edit-row-btn" onclick="editReadinessFromHistory('${dateStr}')" title="Edit">
                    <i class="fas fa-pencil-alt"></i>
                </button>
                <button class="btn-delete btn-delete-readiness" data-id="${e.id}" title="Delete">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </td>
        </tr>
    `;
}

window.editReadinessFromHistory = function(dateStr) {
    document.getElementById('readinessDate').value = dateStr;
    
    loadFullReadinessData(dateStr).then(() => {
        const card = document.getElementById('morningReadinessCard');
        card.classList.remove('collapsed');
        document.getElementById('readinessSummary').style.display = 'none';
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
};

// ============== AI Coach Tab ==============
function switchToCoachTab(targetDate = null) {
    document.querySelectorAll('.cycle-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector('[data-tab="coach"]').classList.add('active');
    document.getElementById('coachTab').classList.add('active');
    
    if (targetDate) {
        document.getElementById('coachDate').value = targetDate;
    }
    
    const url = new URL(window.location);
    url.searchParams.set('tab', 'coach');
    if (targetDate) {
        url.searchParams.set('date', targetDate);
    }
    window.history.replaceState({}, '', url);
}

async function fetchCoachRecommendation(date, refresh = false) {
    const loadingEl = document.getElementById('coachLoading');
    const emptyEl = document.getElementById('coachEmpty');
    const contentEl = document.getElementById('coachContent');
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    loadingEl.style.display = 'flex';
    emptyEl.style.display = 'none';
    contentEl.style.display = 'none';
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Analyzing...';
    
    try {
        let url = `/cycling-readiness/api/training-recommendation?date=${date}`;
        if (refresh) {
            url += '&refresh=true';
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        loadingEl.style.display = 'none';
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="fas fa-magic me-1"></i>Analyze This Day';
        
        if (data.success && data.recommendation) {
            renderCoachRecommendation(data.recommendation, date);
            contentEl.style.display = 'block';
        } else {
            emptyEl.style.display = 'block';
            if (data.error) {
                showToast(data.error, 'error');
            }
        }
    } catch (err) {
        console.error('Error fetching AI Coach recommendation:', err);
        loadingEl.style.display = 'none';
        emptyEl.style.display = 'block';
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="fas fa-magic me-1"></i>Analyze This Day';
        showToast('Could not load AI Coach recommendation', 'error');
    }
}

function renderCoachRecommendation(rec, dateStr) {
    const dayTypeBadge = document.getElementById('coachDayTypeBadge');
    dayTypeBadge.textContent = DAY_TYPE_LABELS[rec.day_type] || rec.day_type;
    dayTypeBadge.className = 'day-type-badge ' + (DAY_TYPE_CLASSES[rec.day_type] || '');
    
    const intensityTag = document.getElementById('coachIntensityTag');
    if (rec.session_plan && rec.session_plan.overall_intensity) {
        intensityTag.textContent = rec.session_plan.overall_intensity.replace('_', ' ');
        intensityTag.className = 'intensity-tag ' + rec.session_plan.overall_intensity;
        intensityTag.style.display = 'inline';
    } else {
        intensityTag.style.display = 'none';
    }
    
    const durationEl = document.getElementById('coachDuration');
    if (rec.session_plan && rec.session_plan.duration_minutes) {
        durationEl.textContent = rec.session_plan.duration_minutes + ' min';
    } else if (rec.day_type === 'rest') {
        durationEl.textContent = 'Rest';
    } else {
        durationEl.textContent = '--';
    }
    
    document.getElementById('coachDateLabel').textContent = dateStr;
    document.getElementById('coachReason').textContent = rec.reason_short || '';
    
    // Coach Notes / Analysis Card (new in v2.5)
    const analysisCard = document.getElementById('coachAnalysisCard');
    const analysisText = document.getElementById('coachAnalysisText');
    if (rec.analysis_text && analysisCard) {
        analysisText.textContent = rec.analysis_text;
        analysisCard.style.display = 'block';
    } else if (analysisCard) {
        analysisCard.style.display = 'none';
    }
    
    // Performance Targets Card
    const targetsCard = document.getElementById('coachTargetsCard');
    const targetsGrid = document.getElementById('coachTargetsGrid');
    if (rec.session_plan) {
        const sp = rec.session_plan;
        let targetsHtml = '';
        
        if (sp.expected_avg_hr_bpm) {
            targetsHtml += `
                <div class="target-item">
                    <span class="target-label">Avg HR:</span>
                    <span class="target-value hr">${sp.expected_avg_hr_bpm} bpm</span>
                </div>`;
        }
        
        if (sp.expected_avg_power_w) {
            targetsHtml += `
                <div class="target-item">
                    <span class="target-label">Avg Power:</span>
                    <span class="target-value power">${sp.expected_avg_power_w} W</span>
                </div>`;
        }
        
        if (sp.primary_zone) {
            targetsHtml += `
                <div class="target-item">
                    <span class="target-label">Zone:</span>
                    <span class="target-value zone">${sp.primary_zone}</span>
                </div>`;
        }
        
        if (sp.session_target_power_w_min && sp.session_target_power_w_max) {
            targetsHtml += `
                <div class="target-item">
                    <span class="target-label">Power Range:</span>
                    <span class="target-value power">${sp.session_target_power_w_min}–${sp.session_target_power_w_max} W</span>
                </div>`;
        }
        
        if (targetsHtml) {
            targetsGrid.innerHTML = targetsHtml;
            targetsCard.style.display = 'block';
        } else {
            targetsCard.style.display = 'none';
        }
    } else {
        targetsCard.style.display = 'none';
    }
    
    // Enhanced Intervals (CSResponse v1)
    const intervalsContainer = document.getElementById('coachIntervals');
    const intervalsList = document.getElementById('coachIntervalsList');
    if (rec.session_plan && rec.session_plan.intervals && rec.session_plan.intervals.length > 0) {
        intervalsList.innerHTML = rec.session_plan.intervals.map(interval => {
            // Build duration description
            let durationDesc = '';
            if (interval.repeats) {
                durationDesc = `${interval.repeats}× ${interval.work_minutes || interval.duration_minutes}min`;
                if (interval.rest_minutes) {
                    durationDesc += ` / ${interval.rest_minutes}min rest`;
                }
            } else {
                durationDesc = `${interval.duration_minutes} min`;
            }
            
            // Block name badge (e.g., "4x4 VO2max")
            let blockNameHtml = '';
            if (interval.block_name) {
                blockNameHtml = `<span class="interval-block-name">${interval.block_name}</span>`;
            }
            
            // HR targets
            let hrHtml = '';
            if (interval.target_hr_bpm_min && interval.target_hr_bpm_max) {
                hrHtml = `
                    <div class="interval-metric">
                        <span class="interval-metric-label">HR:</span>
                        <span class="interval-metric-value hr">${interval.target_hr_bpm_min}–${interval.target_hr_bpm_max} bpm</span>
                    </div>`;
            } else if (interval.expected_avg_hr_bpm) {
                hrHtml = `
                    <div class="interval-metric">
                        <span class="interval-metric-label">HR:</span>
                        <span class="interval-metric-value hr">~${interval.expected_avg_hr_bpm} bpm</span>
                    </div>`;
            }
            
            // Power targets
            let powerHtml = '';
            if (interval.target_power_w_min && interval.target_power_w_max) {
                powerHtml = `
                    <div class="interval-metric">
                        <span class="interval-metric-label">Power:</span>
                        <span class="interval-metric-value power">${interval.target_power_w_min}–${interval.target_power_w_max} W</span>
                    </div>`;
            }
            
            // Notes/coaching cues
            let notesHtml = '';
            if (interval.notes) {
                notesHtml = `
                    <div class="interval-notes">
                        <i class="fas fa-info-circle"></i>${interval.notes}
                    </div>`;
            }
            
            // Get interval kind class - handle new types (progressive, threshold, vo2max)
            const kindClass = interval.kind || 'steady';
            const isHardInterval = ['interval', 'threshold', 'vo2max'].includes(kindClass);
            
            return `
                <div class="interval-row ${kindClass} ${isHardInterval ? 'hard-interval' : ''}">
                    <div class="interval-left">
                        <span class="interval-type ${kindClass}">${kindClass}</span>
                        ${blockNameHtml}
                    </div>
                    <div class="interval-center">
                        <span class="interval-duration">${durationDesc}</span>
                        <span class="interval-zone-badge ${interval.target_zone}">${interval.target_zone}</span>
                    </div>
                    <div class="interval-right">
                        ${hrHtml}
                        ${powerHtml}
                    </div>
                    ${notesHtml}
                </div>
            `;
        }).join('');
        intervalsContainer.style.display = 'block';
    } else {
        intervalsContainer.style.display = 'none';
    }
    
    // Flags
    const flagsContainer = document.getElementById('coachFlags');
    if (rec.flags && Object.keys(rec.flags).length > 0) {
        const flagsHtml = Object.entries(rec.flags)
            .filter(([_, v]) => v)
            .map(([key, _]) => {
                const isPositive = ['ok_to_push'].includes(key);
                const isWarning = ['consider_rest_day', 'prioritize_sleep', 'monitor_hrv'].includes(key);
                const className = isPositive ? 'positive' : (isWarning ? 'warning' : '');
                const label = key.replace(/_/g, ' ');
                return `<span class="rec-flag ${className}">${label}</span>`;
            })
            .join('');
        
        if (flagsHtml) {
            flagsContainer.innerHTML = flagsHtml;
            flagsContainer.style.display = 'flex';
        } else {
            flagsContainer.style.display = 'none';
        }
    } else {
        flagsContainer.style.display = 'none';
    }
}

function initCoachTab() {
    document.getElementById('analyzeBtn').addEventListener('click', function() {
        const date = document.getElementById('coachDate').value;
        fetchCoachRecommendation(date, false);
    });

    document.getElementById('coachRefreshBtn').addEventListener('click', function() {
        const date = document.getElementById('coachDate').value;
        fetchCoachRecommendation(date, true);
    });

    document.querySelectorAll('.quick-date-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const date = this.dataset.date;
            if (date) {
                document.getElementById('coachDate').value = date;
                fetchCoachRecommendation(date, false);
            }
        });
    });

    document.querySelectorAll('.btn-coach').forEach(btn => {
        btn.addEventListener('click', function() {
            const date = this.dataset.date;
            if (date) {
                switchToCoachTab(date);
                fetchCoachRecommendation(date, false);
            }
        });
    });
}

window.openCoachForDate = function(dateStr) {
    closeDayViewModal();
    switchToCoachTab(dateStr);
    fetchCoachRecommendation(dateStr, false);
};

function handleUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab');
    const date = urlParams.get('date');
    const today = document.getElementById('readinessDate')?.value || new Date().toISOString().split('T')[0];
    
    if (tab === 'coach') {
        switchToCoachTab(date || today);
        if (date) {
            fetchCoachRecommendation(date, false);
        }
    }
}

// ============== Multi-file Upload ==============
function initFileUpload() {
    const bundleZone = document.getElementById('bundleUploadZone');
    const bundleInput = document.getElementById('bundleImageInput');
    const fileListContainer = document.getElementById('fileListContainer');
    const uploadActions = document.getElementById('uploadActions');
    const extractionResults = document.getElementById('extractionResults');

    function updateFileList() {
        if (selectedFiles.length === 0) {
            fileListContainer.classList.add('d-none');
            uploadActions.classList.add('d-none');
            hideStatus();
            return;
        }

        fileListContainer.classList.remove('d-none');
        uploadActions.classList.remove('d-none');
        fileListContainer.innerHTML = selectedFiles.map((file, idx) => `
            <div class="file-item">
                <i class="fas fa-image"></i>
                <span class="filename">${file.name}</span>
                <span class="remove-file" data-idx="${idx}"><i class="fas fa-times"></i></span>
            </div>
        `).join('');

        fileListContainer.querySelectorAll('.remove-file').forEach(btn => {
            btn.addEventListener('click', function() {
                selectedFiles.splice(parseInt(this.dataset.idx), 1);
                updateFileList();
            });
        });
    }

    bundleZone.addEventListener('click', () => bundleInput.click());
    bundleZone.addEventListener('dragover', (e) => { e.preventDefault(); bundleZone.classList.add('dragover'); });
    bundleZone.addEventListener('dragleave', () => bundleZone.classList.remove('dragover'));
    bundleZone.addEventListener('drop', (e) => {
        e.preventDefault();
        bundleZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            selectedFiles = [...selectedFiles, ...Array.from(e.dataTransfer.files)];
            updateFileList();
        }
    });

    bundleInput.addEventListener('change', function() {
        if (this.files.length) {
            selectedFiles = [...selectedFiles, ...Array.from(this.files)];
            updateFileList();
        }
    });

    // Bundle Upload Form
    document.getElementById('bundleUploadForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        if (selectedFiles.length === 0) {
            showToast('Please select at least one image', 'error');
            return;
        }

        const formData = new FormData();
        selectedFiles.forEach(file => formData.append('images', file));

        showLoading(`Processing ${selectedFiles.length} image(s)...`);
        showStatus('loading', 'Analyzing screenshots...');
        extractionResults.classList.add('d-none');
        document.getElementById('uploadBtn').disabled = true;

        try {
            const response = await fetch('/cycling-readiness/api/cycle/import-bundle', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            hideLoading();
            document.getElementById('uploadBtn').disabled = false;

            if (data.success) {
                const results = data.extraction_results || [];
                const errors = results.filter(r => r.type === 'error').length;

                if (errors > 0 && errors === results.length) {
                    showStatus('error', 'Could not parse screenshots');
                } else if (errors > 0) {
                    showStatus('success', `Merged successfully! (${errors} failed)`);
                } else {
                    showStatus('success', 'Merged successfully!');
                }

                if (results.length > 0) {
                    extractionResults.classList.remove('d-none');
                    extractionResults.innerHTML = results.map(r => {
                        const isCycling = r.type === 'cycling_workout' || r.type === 'cycling_power' || r.type === 'watch_workout';
                        const isSleep = r.type === 'sleep_summary';
                        const isError = r.type === 'error';
                        
                        const typeClass = isCycling ? 'cycling' : isSleep ? 'sleep' : isError ? 'error' : 'unknown';
                        const icon = isCycling ? 'fa-bicycle' : isSleep ? 'fa-moon' : isError ? 'fa-exclamation-triangle' : 'fa-question';
                        const typeName = isCycling ? 'Cycling' : isSleep ? 'Sleep' : isError ? 'Error' : 'Unknown';
                        const confidence = r.confidence ? ` (${Math.round(r.confidence * 100)}%)` : '';
                        
                        return `
                            <div class="extraction-item ${typeClass}">
                                <div class="extraction-icon"><i class="fas ${icon}"></i></div>
                                <div class="extraction-details">
                                    <div class="extraction-type">${typeName}${confidence}</div>
                                    <div class="extraction-filename">${r.filename}</div>
                                </div>
                            </div>
                        `;
                    }).join('');
                }

                selectedFiles = [];
                updateFileList();
                
                if (data.has_missing_data && 
                    (data.missing_fields?.workout?.length > 0 || data.missing_fields?.sleep?.length > 0)) {
                    window.lastImportData = data;
                    showReviewModal(data);
                } else {
                    setTimeout(() => location.reload(), 2500);
                }
            } else {
                showStatus('error', data.error || 'Import failed');
                showToast(data.error || 'Import failed', 'error');
            }
        } catch (err) {
            hideLoading();
            document.getElementById('uploadBtn').disabled = false;
            showStatus('error', 'Error processing images');
            showToast('Error processing images', 'error');
        }
    });
}

// ============== Readiness Form ==============
function initReadinessForm() {
    document.getElementById('readinessForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        const manualRhr = document.getElementById('manualRhrBpm')?.value;
        const manualHrvLow = document.getElementById('manualHrvLow')?.value;
        const manualHrvHigh = document.getElementById('manualHrvHigh')?.value;
        
        const overrideRhr = document.getElementById('overrideRhrBpm')?.value;
        const overrideHrvLow = document.getElementById('overrideHrvLow')?.value;
        const overrideHrvHigh = document.getElementById('overrideHrvHigh')?.value;

        const data = {
            date: document.getElementById('readinessDate').value,
            energy: document.querySelector('[name="energy"]:checked')?.value,
            mood: document.querySelector('[name="mood"]:checked')?.value,
            muscle_fatigue: document.querySelector('[name="muscle_fatigue"]:checked')?.value,
            hrv_status: document.querySelector('[name="hrv_status"]:checked')?.value,
            rhr_status: document.querySelector('[name="rhr_status"]:checked')?.value,
            min_hr_status: 0,
            symptoms_flag: document.getElementById('symptomsFlag').checked
        };

        if (!hasCardioData) {
            if (manualRhr) {
                data.manual_rhr_bpm = parseInt(manualRhr);
            }
            if (manualHrvLow && manualHrvHigh) {
                data.manual_hrv_low_ms = parseInt(manualHrvLow);
                data.manual_hrv_high_ms = parseInt(manualHrvHigh);
            }
        } else {
            const rhrOverrideVisible = document.getElementById('rhrOverrideInput').style.display !== 'none';
            const hrvOverrideVisible = document.getElementById('hrvOverrideInput').style.display !== 'none';
            
            if (rhrOverrideVisible && overrideRhr) {
                data.manual_rhr_bpm = parseInt(overrideRhr);
                data.rhr_manual_override = true;
            }
            if (hrvOverrideVisible && overrideHrvLow && overrideHrvHigh) {
                data.manual_hrv_low_ms = parseInt(overrideHrvLow);
                data.manual_hrv_high_ms = parseInt(overrideHrvHigh);
                data.hrv_manual_override = true;
            }
        }

        if (data.hrv_status === undefined) data.hrv_status = null;
        if (data.rhr_status === undefined) data.rhr_status = null;

        if (!data.energy || !data.mood || !data.muscle_fatigue) {
            showToast('Please fill Energy, Mood, and Fatigue', 'error');
            return;
        }

        try {
            const response = await fetch('/cycling-readiness/api/readiness', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (result.success) {
                showToast(`Saved! Score: ${result.morning_score}`, 'success');
                
                currentReadinessData = {
                    has_readiness: true,
                    readiness: result.readiness,
                    cardio: result.cardio,
                    calculated_status: {
                        hrv_status: result.hrv_status,
                        rhr_status: result.rhr_status
                    }
                };
                
                updateReadinessSummary(currentReadinessData);
                
                const card = document.getElementById('morningReadinessCard');
                card.classList.add('collapsed');
                document.getElementById('readinessSummary').style.display = 'flex';
                
                loadReadinessHistory();
            } else {
                showToast(result.error || 'Failed to save', 'error');
            }
        } catch (err) {
            showToast('Error saving readiness', 'error');
        }
    });
}

// ============== Delete Records ==============
window.closeConfirmModal = function() {
    document.getElementById('confirmModal').classList.remove('active');
    deleteType = null;
    deleteId = null;
};

function showConfirmModal(type, id) {
    deleteType = type;
    deleteId = id;
    
    const titles = {
        'workout': 'Delete Workout?',
        'readiness': 'Delete Readiness Entry?',
        'sleep': 'Delete Sleep Summary?'
    };
    document.getElementById('confirmModalTitle').textContent = titles[type] || 'Delete?';
    document.getElementById('confirmModal').classList.add('active');
}

function initDeleteHandlers() {
    document.getElementById('confirmDeleteBtn').addEventListener('click', async function() {
        if (!deleteId || !deleteType) return;

        let endpoint = '';
        let successMessage = '';
        
        switch(deleteType) {
            case 'workout':
                endpoint = `/cycling-readiness/api/cycling/${deleteId}`;
                successMessage = 'Workout deleted';
                break;
            case 'readiness':
                endpoint = `/cycling-readiness/api/readiness/${deleteId}`;
                successMessage = 'Readiness entry deleted';
                break;
            case 'sleep':
                endpoint = `/cycling-readiness/api/sleep/${deleteId}`;
                successMessage = 'Sleep summary deleted';
                break;
            default:
                closeConfirmModal();
                return;
        }

        try {
            const response = await fetch(endpoint, { method: 'DELETE' });
            const data = await response.json();
            closeConfirmModal();

            if (data.success) {
                showToast(successMessage, 'success');
                
                if (deleteType === 'readiness') {
                    loadReadinessHistory();
                    const currentDate = document.getElementById('readinessDate').value;
                    loadFullReadinessData(currentDate);
                } else {
                    setTimeout(() => location.reload(), 500);
                }
            } else {
                showToast(data.error || 'Failed to delete', 'error');
            }
        } catch (err) {
            closeConfirmModal();
            showToast('Error deleting record', 'error');
        }
    });

    document.querySelectorAll('.btn-delete-workout').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            showConfirmModal('workout', this.dataset.id);
        });
    });

    document.getElementById('readinessHistoryBody').addEventListener('click', function(e) {
        const deleteBtn = e.target.closest('.btn-delete-readiness');
        if (deleteBtn) {
            e.stopPropagation();
            showConfirmModal('readiness', deleteBtn.dataset.id);
        }
    });

    document.getElementById('confirmModal').addEventListener('click', function(e) {
        if (e.target === this) closeConfirmModal();
    });
}

// ============== Edit Workout Functions ==============
function initEditWorkout() {
    document.querySelectorAll('.btn-edit-workout').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.stopPropagation();
            const workoutId = this.dataset.id;
            await openEditModal(workoutId);
        });
    });

    document.getElementById('editWorkoutModal').addEventListener('click', function(e) {
        if (e.target === this) closeEditModal();
    });
}

async function openEditModal(workoutId) {
    try {
        const response = await fetch(`/cycling-readiness/api/cycling/${workoutId}`);
        const data = await response.json();
        
        if (data.success && data.workout) {
            const w = data.workout;
            document.getElementById('editWorkoutId').value = w.id;
            document.getElementById('editDate').value = w.date || '';
            
            if (w.duration_sec) {
                const mins = Math.floor(w.duration_sec / 60);
                const secs = w.duration_sec % 60;
                document.getElementById('editDuration').value = `${mins}:${secs.toString().padStart(2, '0')}`;
            } else {
                document.getElementById('editDuration').value = '';
            }
            
            document.getElementById('editAvgPower').value = w.avg_power_w || '';
            document.getElementById('editMaxPower').value = w.max_power_w || '';
            document.getElementById('editNormalizedPower').value = w.normalized_power_w || '';
            document.getElementById('editIF').value = w.intensity_factor || '';
            document.getElementById('editTSS').value = w.tss || '';
            document.getElementById('editAvgHR').value = w.avg_heart_rate || '';
            document.getElementById('editMaxHR').value = w.max_heart_rate || '';
            document.getElementById('editCadence').value = w.avg_cadence || '';
            document.getElementById('editDistance').value = w.distance_km || '';
            document.getElementById('editKcalActive').value = w.kcal_active || '';
            document.getElementById('editKcalTotal').value = w.kcal_total || '';
            document.getElementById('editNotes').value = w.notes || '';
            
            document.getElementById('editWorkoutModal').classList.add('active');
        } else {
            showToast('Failed to load workout', 'error');
        }
    } catch (err) {
        showToast('Error loading workout', 'error');
    }
}

window.closeEditModal = function() {
    document.getElementById('editWorkoutModal').classList.remove('active');
};

window.saveEditedWorkout = async function() {
    const workoutId = document.getElementById('editWorkoutId').value;
    
    let durationSec = null;
    const durationVal = document.getElementById('editDuration').value;
    if (durationVal) {
        const parts = durationVal.split(':');
        if (parts.length === 2) {
            durationSec = parseInt(parts[0]) * 60 + parseInt(parts[1]);
        }
    }
    
    const data = {
        date: document.getElementById('editDate').value || null,
        duration_sec: durationSec,
        avg_power_w: parseFloat(document.getElementById('editAvgPower').value) || null,
        max_power_w: parseFloat(document.getElementById('editMaxPower').value) || null,
        normalized_power_w: parseFloat(document.getElementById('editNormalizedPower').value) || null,
        intensity_factor: parseFloat(document.getElementById('editIF').value) || null,
        tss: parseFloat(document.getElementById('editTSS').value) || null,
        avg_heart_rate: parseInt(document.getElementById('editAvgHR').value) || null,
        max_heart_rate: parseInt(document.getElementById('editMaxHR').value) || null,
        avg_cadence: parseInt(document.getElementById('editCadence').value) || null,
        distance_km: parseFloat(document.getElementById('editDistance').value) || null,
        kcal_active: parseInt(document.getElementById('editKcalActive').value) || null,
        kcal_total: parseInt(document.getElementById('editKcalTotal').value) || null,
        notes: document.getElementById('editNotes').value || null
    };
    
    try {
        const response = await fetch(`/cycling-readiness/api/cycling/${workoutId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (result.success) {
            closeEditModal();
            showToast('Workout updated!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(result.error || 'Failed to update', 'error');
        }
    } catch (err) {
        showToast('Error saving workout', 'error');
    }
};

// ============== Edit Readiness Functions ==============
function initEditReadiness() {
    document.querySelectorAll('.btn-edit-readiness').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.stopPropagation();
            const entryId = this.dataset.id;
            await openEditReadinessModal(entryId);
        });
    });

    document.getElementById('editReadinessModal').addEventListener('click', function(e) {
        if (e.target === this) closeEditReadinessModal();
    });
}

async function openEditReadinessModal(entryId) {
    try {
        const response = await fetch(`/cycling-readiness/api/readiness/${entryId}`);
        const data = await response.json();
        
        if (data.success && data.entry) {
            const e = data.entry;
            document.getElementById('editReadinessId').value = e.id;
            document.getElementById('editReadinessDate').value = e.date;
            document.getElementById('editReadinessEnergy').value = e.energy || '';
            document.getElementById('editReadinessMood').value = e.mood || '';
            document.getElementById('editReadinessFatigue').value = e.muscle_fatigue || '';
            document.getElementById('editReadinessHRV').value = e.hrv_status !== null ? e.hrv_status : '';
            document.getElementById('editReadinessRHR').value = e.rhr_status !== null ? e.rhr_status : '';
            document.getElementById('editReadinessMinHR').value = e.min_hr_status !== null ? e.min_hr_status : '';
            document.getElementById('editReadinessSymptoms').checked = e.symptoms_flag || false;
            document.getElementById('editReadinessNotes').value = e.evening_note || '';
            
            const cardioDisplay = document.getElementById('editCardioDisplay');
            const hrvAutoLabel = document.getElementById('editHrvAutoLabel');
            const rhrAutoLabel = document.getElementById('editRhrAutoLabel');
            
            cardioDisplay.style.display = 'none';
            hrvAutoLabel.style.display = 'none';
            rhrAutoLabel.style.display = 'none';
            
            try {
                const cardioRes = await fetch(`/cycling-readiness/api/cardio-status?date=${e.date}`);
                const cardioData = await cardioRes.json();
                
                if (cardioData.success && cardioData.has_cardio) {
                    cardioDisplay.style.display = 'block';
                    
                    const rhrDisplay = document.getElementById('editDisplayRhr');
                    if (cardioData.cardio.rhr_bpm) {
                        rhrDisplay.textContent = `${cardioData.cardio.rhr_bpm} bpm`;
                    } else {
                        rhrDisplay.textContent = '--';
                    }
                    
                    const hrvDisplay = document.getElementById('editDisplayHrv');
                    if (cardioData.cardio.hrv_low_ms && cardioData.cardio.hrv_high_ms) {
                        if (cardioData.cardio.hrv_low_ms === cardioData.cardio.hrv_high_ms) {
                            hrvDisplay.textContent = `${cardioData.cardio.hrv_low_ms} ms`;
                        } else {
                            hrvDisplay.textContent = `${cardioData.cardio.hrv_low_ms}–${cardioData.cardio.hrv_high_ms} ms`;
                        }
                    } else {
                        hrvDisplay.textContent = '--';
                    }
                    
                    if (cardioData.calculated_status.hrv_status !== null) {
                        hrvAutoLabel.style.display = 'inline';
                    }
                    if (cardioData.calculated_status.rhr_status !== null) {
                        rhrAutoLabel.style.display = 'inline';
                    }
                }
            } catch (cardioErr) {
                console.error('Error loading cardio status:', cardioErr);
            }
            
            document.getElementById('editReadinessModal').classList.add('active');
        } else {
            showToast('Failed to load entry', 'error');
        }
    } catch (err) {
        showToast('Error loading entry', 'error');
    }
}

window.closeEditReadinessModal = function() {
    document.getElementById('editReadinessModal').classList.remove('active');
};

window.saveEditedReadiness = async function() {
    const entryId = document.getElementById('editReadinessId').value;
    
    const data = {
        energy: parseInt(document.getElementById('editReadinessEnergy').value) || null,
        mood: parseInt(document.getElementById('editReadinessMood').value) || null,
        muscle_fatigue: parseInt(document.getElementById('editReadinessFatigue').value) || null,
        hrv_status: document.getElementById('editReadinessHRV').value !== '' ? 
            parseInt(document.getElementById('editReadinessHRV').value) : null,
        rhr_status: document.getElementById('editReadinessRHR').value !== '' ? 
            parseInt(document.getElementById('editReadinessRHR').value) : null,
        min_hr_status: document.getElementById('editReadinessMinHR').value !== '' ? 
            parseInt(document.getElementById('editReadinessMinHR').value) : null,
        symptoms_flag: document.getElementById('editReadinessSymptoms').checked,
        evening_note: document.getElementById('editReadinessNotes').value || null
    };
    
    try {
        const response = await fetch(`/cycling-readiness/api/readiness/${entryId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (result.success) {
            closeEditReadinessModal();
            showToast('Entry updated!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(result.error || 'Failed to update', 'error');
        }
    } catch (err) {
        showToast('Error saving entry', 'error');
    }
};

// ============== Score Tooltip ==============
window.toggleScoreTooltip = function() {
    const tooltip = document.getElementById('scoreTooltip');
    tooltip.classList.toggle('active');
};

function initScoreTooltip() {
    document.addEventListener('click', function(e) {
        const tooltip = document.getElementById('scoreTooltip');
        const infoBtn = document.querySelector('.score-info-icon');
        if (tooltip && infoBtn && !tooltip.contains(e.target) && !infoBtn.contains(e.target)) {
            tooltip.classList.remove('active');
        }
    });
}

// ============== Day View Functions ==============
function initDayView() {
    document.querySelectorAll('.btn-view-day').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.stopPropagation();
            const date = this.dataset.date;
            if (date) {
                await openDayViewModal(date);
            }
        });
    });

    document.getElementById('dayViewModal').addEventListener('click', function(e) {
        if (e.target === this) closeDayViewModal();
    });
}

async function openDayViewModal(date) {
    document.getElementById('dayViewDate').textContent = date;
    document.getElementById('dayViewModal').classList.add('active');
    document.getElementById('dayViewContent').innerHTML = `
        <div class="text-center" style="padding: 2rem; color: var(--color-muted);">
            <i class="fas fa-spinner fa-spin"></i> Loading...
        </div>
    `;
    
    try {
        const response = await fetch(`/cycling-readiness/api/day-summary?date=${date}`);
        const data = await response.json();
        
        if (data.success) {
            renderDayView(data);
        } else {
            document.getElementById('dayViewContent').innerHTML = `
                <div class="text-center" style="padding: 2rem; color: var(--color-red);">
                    <i class="fas fa-exclamation-triangle"></i> Failed to load data
                </div>
            `;
        }
    } catch (err) {
        document.getElementById('dayViewContent').innerHTML = `
            <div class="text-center" style="padding: 2rem; color: var(--color-red);">
                <i class="fas fa-exclamation-triangle"></i> Error loading data
            </div>
        `;
    }
}

function renderDayView(data) {
    const container = document.getElementById('dayViewContent');
    let html = '';
    
    // Cycling Workout Panel
    html += `<div class="day-panel">
        <div class="day-panel-header">
            <div class="day-panel-title cycling"><i class="fas fa-bicycle me-2"></i>Cycling Workout</div>
            ${data.cycling_workout ? `<button class="btn-edit" onclick="openEditModal(${data.cycling_workout.id})" title="Edit"><i class="fas fa-pencil-alt"></i></button>` : ''}
        </div>`;
    
    if (data.cycling_workout) {
        const w = data.cycling_workout;
        const missingCycling = data.missing?.cycling || [];
        html += `<div class="day-data-grid">
            ${renderDayDataItem('Duration', formatDuration(w.duration_sec), missingCycling.includes('duration_sec'))}
            ${renderDayDataItem('Avg Power', w.avg_power_w ? w.avg_power_w + 'W' : null, missingCycling.includes('avg_power_w'), 'good')}
            ${renderDayDataItem('Max Power', w.max_power_w ? w.max_power_w + 'W' : null, missingCycling.includes('max_power_w'), 'good')}
            ${renderDayDataItem('NP', w.normalized_power_w ? w.normalized_power_w + 'W' : null, missingCycling.includes('normalized_power_w'), 'good')}
            ${renderDayDataItem('Avg HR', w.avg_heart_rate ? w.avg_heart_rate + ' bpm' : null, missingCycling.includes('avg_heart_rate'), 'hr')}
            ${renderDayDataItem('Max HR', w.max_heart_rate ? w.max_heart_rate + ' bpm' : null, missingCycling.includes('max_heart_rate'), 'hr')}
            ${renderDayDataItem('TSS', w.tss, missingCycling.includes('tss'))}
            ${renderDayDataItem('IF', w.intensity_factor, missingCycling.includes('intensity_factor'))}
            ${renderDayDataItem('Cadence', w.avg_cadence ? w.avg_cadence + ' rpm' : null, missingCycling.includes('avg_cadence'))}
            ${renderDayDataItem('Distance', w.distance_km ? w.distance_km + ' km' : null, missingCycling.includes('distance_km'))}
            ${renderDayDataItem('Active kcal', w.kcal_active, missingCycling.includes('kcal_active'))}
            ${renderDayDataItem('Total kcal', w.kcal_total, missingCycling.includes('kcal_total'))}
        </div>`;
    } else {
        html += `<p class="empty-note">No cycling workout recorded for this date.</p>`;
    }
    html += `</div>`;
    
    // Readiness Entry Panel
    html += `<div class="day-panel">
        <div class="day-panel-header">
            <div class="day-panel-title readiness"><i class="fas fa-sun me-2"></i>Readiness Entry</div>
        </div>`;
    
    if (data.readiness_entry) {
        const r = data.readiness_entry;
        const missingReadiness = data.missing?.readiness || [];
        const score = r.morning_score;
        const scoreClass = score >= 70 ? 'good' : score >= 40 ? '' : 'missing';
        html += `<div class="day-data-grid">
            ${renderDayDataItem('Score', score, false, scoreClass)}
            ${renderDayDataItem('Energy', r.energy ? r.energy + '/5' : null, missingReadiness.includes('energy'))}
            ${renderDayDataItem('Mood', r.mood ? r.mood + '/3' : null, missingReadiness.includes('mood'))}
            ${renderDayDataItem('Fatigue', r.muscle_fatigue ? r.muscle_fatigue + '/3' : null, missingReadiness.includes('muscle_fatigue'))}
            ${renderDayDataItem('Sleep', r.sleep_minutes ? (r.sleep_minutes / 60).toFixed(1) + 'h' : null, missingReadiness.includes('sleep_minutes'), 'sleep')}
            ${renderDayDataItem('Deep Sleep', r.deep_sleep_minutes ? r.deep_sleep_minutes + 'min' : null, missingReadiness.includes('deep_sleep_minutes'), 'sleep')}
            ${renderDayDataItem('Awake', r.awake_minutes ? r.awake_minutes + 'min' : null, false)}
            ${renderDayDataItem('Symptoms', r.symptoms_flag ? 'Yes' : 'No', false)}
        </div>`;
    } else {
        html += `<p class="empty-note">No readiness entry for this date.</p>`;
    }
    html += `</div>`;
    
    // Sleep Summary Panel
    html += `<div class="day-panel">
        <div class="day-panel-header">
            <div class="day-panel-title sleep"><i class="fas fa-moon me-2"></i>Sleep Summary</div>
        </div>`;
    
    if (data.sleep_summary) {
        const s = data.sleep_summary;
        const missingSleep = data.missing?.sleep || [];
        html += `<div class="day-data-grid">
            ${renderDayDataItem('Total Sleep', s.total_sleep_minutes ? (s.total_sleep_minutes / 60).toFixed(1) + 'h' : null, missingSleep.includes('total_sleep_minutes'), 'sleep')}
            ${renderDayDataItem('Deep Sleep', s.deep_sleep_minutes ? s.deep_sleep_minutes + 'min' : null, missingSleep.includes('deep_sleep_minutes'), 'sleep')}
            ${renderDayDataItem('Awake', s.awake_minutes ? s.awake_minutes + 'min' : null, missingSleep.includes('awake_minutes'))}
            ${renderDayDataItem('Start', formatTime(s.sleep_start_time), false)}
            ${renderDayDataItem('End', formatTime(s.sleep_end_time), false)}
            ${renderDayDataItem('Min HR', s.min_heart_rate ? s.min_heart_rate + ' bpm' : null, missingSleep.includes('min_heart_rate'), 'hr')}
            ${renderDayDataItem('Avg HR', s.avg_heart_rate ? s.avg_heart_rate + ' bpm' : null, missingSleep.includes('avg_heart_rate'), 'hr')}
            ${renderDayDataItem('Max HR', s.max_heart_rate ? s.max_heart_rate + ' bpm' : null, missingSleep.includes('max_heart_rate'), 'hr')}
        </div>`;
    } else {
        html += `<p class="empty-note">No sleep data for this date.</p>`;
    }
    html += `</div>`;
    
    // Cardio Metrics Panel
    html += `<div class="day-panel">
        <div class="day-panel-header">
            <div class="day-panel-title" style="color: var(--color-red);"><i class="fas fa-heartbeat me-2"></i>Cardio Metrics</div>
        </div>`;
    
    if (data.cardio_metrics) {
        const c = data.cardio_metrics;
        const missingCardio = data.missing?.cardio || [];
        
        let rhrDisplay = null;
        if (c.rhr_bpm !== null && c.rhr_bpm !== undefined) {
            rhrDisplay = `${c.rhr_bpm} bpm`;
        }
        
        let hrvDisplay = null;
        if (c.hrv_low_ms !== null && c.hrv_high_ms !== null) {
            if (c.hrv_low_ms === c.hrv_high_ms) {
                hrvDisplay = `${c.hrv_low_ms} ms`;
            } else {
                hrvDisplay = `${c.hrv_low_ms}–${c.hrv_high_ms} ms`;
            }
        }
        
        html += `<div class="day-data-grid">
            ${renderDayDataItem('Resting HR', rhrDisplay, missingCardio.includes('rhr_bpm'), 'hr')}
            ${renderDayDataItem('HRV', hrvDisplay, missingCardio.includes('hrv_low_ms') || missingCardio.includes('hrv_high_ms'))}
        </div>`;
    } else {
        html += `<p class="empty-note">No cardio metrics for this date.</p>`;
    }
    html += `</div>`;
    
    // Training Recommendation Panel
    html += `<div class="day-panel">
        <div class="day-panel-header">
            <div class="day-panel-title" style="color: var(--color-yellow);"><i class="fas fa-brain me-2"></i>AI Coach</div>
            <button class="btn-coach" onclick="openCoachForDate('${data.date}')" title="Open in AI Coach">
                <i class="fas fa-external-link-alt"></i>
            </button>
        </div>`;
    
    if (data.training_recommendation) {
        const rec = data.training_recommendation;
        const dayTypeLabel = DAY_TYPE_LABELS[rec.day_type] || rec.day_type;
        const dayTypeClass = DAY_TYPE_CLASSES[rec.day_type] || '';
        
        html += `
            <div class="training-rec-mini">
                <div class="rec-mini-header">
                    <span class="day-type-badge ${dayTypeClass}">${dayTypeLabel}</span>
                    ${rec.session_plan ? `
                        <span class="rec-mini-details">
                            <i class="fas fa-clock"></i> ${rec.session_plan.duration_minutes}min
                            <i class="fas fa-heartbeat ms-2"></i> ${rec.session_plan.primary_zone}
                        </span>
                    ` : ''}
                </div>
                <p class="rec-mini-reason">${rec.reason_short}</p>
                ${rec.session_plan && rec.session_plan.intervals ? `
                    <div class="rec-mini-intervals">
                        ${rec.session_plan.intervals.map(interval => {
                            let desc = interval.repeats 
                                ? `${interval.repeats}× ${interval.work_minutes || interval.duration_minutes}min`
                                : `${interval.duration_minutes}min`;
                            return `<span class="interval-chip">${interval.kind} ${desc} ${interval.target_zone}</span>`;
                        }).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    } else {
        html += `
            <p class="empty-note mb-2">No recommendation saved for this date.</p>
            <button class="btn btn-outline-zyra btn-sm" onclick="openCoachForDate('${data.date}')">
                <i class="fas fa-magic me-1"></i>Get AI Recommendation
            </button>
        `;
    }
    html += `</div>`;
    
    container.innerHTML = html;
}

function renderDayDataItem(label, value, isMissing, valueClass = '') {
    const displayValue = value !== null && value !== undefined ? value : '--';
    const missingClass = isMissing ? 'missing' : valueClass;
    return `
        <div class="day-data-item">
            <div class="label">${label}</div>
            <div class="value ${missingClass}">${displayValue}</div>
        </div>
    `;
}

function formatDuration(seconds) {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatTime(timeValue) {
    if (!timeValue) return null;
    if (typeof timeValue === 'string' && timeValue.includes(':')) {
        return timeValue.substring(0, 5);
    }
    if (typeof timeValue === 'number') {
        const hours = Math.floor(timeValue / 3600) % 24;
        const mins = Math.floor((timeValue % 3600) / 60);
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    }
    return timeValue;
}

window.closeDayViewModal = function() {
    document.getElementById('dayViewModal').classList.remove('active');
};

// ============== Review Modal Functions ==============
function showReviewModal(data) {
    reviewData = data;
    const container = document.getElementById('reviewContent');
    let html = '';
    
    if (data.canonical_workout && data.canonical_workout.date) {
        const cw = data.canonical_workout;
        const missingWorkout = data.missing_fields?.workout || [];
        
        html += `<div class="review-card">
            <div class="review-card-header">
                <span class="review-card-type cycling"><i class="fas fa-bicycle me-1"></i>Cycling Workout</span>
                ${missingWorkout.length > 0 ? `<span class="review-missing-badge">${missingWorkout.length} missing</span>` : '<span style="color: var(--color-green); font-size: 0.8rem;"><i class="fas fa-check"></i> Complete</span>'}
            </div>
            <div class="modal-form-grid">
                ${renderReviewField('duration_sec', 'Duration (sec)', cw.duration_minutes ? Math.round(cw.duration_minutes * 60) : null, missingWorkout)}
                ${renderReviewField('avg_power_w', 'Avg Power (W)', cw.avg_power, missingWorkout)}
                ${renderReviewField('max_power_w', 'Max Power (W)', cw.max_power, missingWorkout)}
                ${renderReviewField('normalized_power_w', 'NP (W)', cw.normalized_power, missingWorkout)}
                ${renderReviewField('avg_heart_rate', 'Avg HR (bpm)', cw.avg_hr, missingWorkout)}
                ${renderReviewField('max_heart_rate', 'Max HR (bpm)', cw.max_hr, missingWorkout)}
                ${renderReviewField('tss', 'TSS', cw.tss, missingWorkout)}
                ${renderReviewField('intensity_factor', 'IF', cw.intensity_factor, missingWorkout)}
                ${renderReviewField('avg_cadence', 'Cadence (rpm)', cw.cadence_avg, missingWorkout)}
                ${renderReviewField('distance_km', 'Distance (km)', cw.distance_km, missingWorkout)}
                ${renderReviewField('kcal_active', 'Active kcal', cw.calories_active, missingWorkout)}
                ${renderReviewField('kcal_total', 'Total kcal', cw.calories_total, missingWorkout)}
            </div>
        </div>`;
    }
    
    if (data.canonical_sleep && data.canonical_sleep.date) {
        const cs = data.canonical_sleep;
        const missingSleep = data.missing_fields?.sleep || [];
        
        html += `<div class="review-card">
            <div class="review-card-header">
                <span class="review-card-type sleep"><i class="fas fa-moon me-1"></i>Sleep Summary</span>
                ${missingSleep.length > 0 ? `<span class="review-missing-badge">${missingSleep.length} missing</span>` : '<span style="color: var(--color-green); font-size: 0.8rem;"><i class="fas fa-check"></i> Complete</span>'}
            </div>
            <div class="modal-form-grid">
                ${renderReviewField('total_sleep_minutes', 'Total Sleep (min)', cs.total_sleep_minutes, missingSleep, 'sleep_')}
                ${renderReviewField('deep_sleep_minutes', 'Deep Sleep (min)', cs.deep_sleep_minutes, missingSleep, 'sleep_')}
                ${renderReviewField('wakeups_count', 'Wakeups', cs.wakeups, missingSleep, 'sleep_')}
                ${renderReviewField('min_heart_rate', 'Min HR (bpm)', cs.min_hr, missingSleep, 'sleep_')}
                ${renderReviewField('avg_heart_rate', 'Avg HR (bpm)', cs.avg_hr, missingSleep, 'sleep_')}
                ${renderReviewField('max_heart_rate', 'Max HR (bpm)', cs.max_hr, missingSleep, 'sleep_')}
            </div>
        </div>`;
    }
    
    if (!html) {
        html = '<p style="color: var(--color-muted);">No data to review.</p>';
    }
    
    container.innerHTML = html;
    document.getElementById('reviewModal').classList.add('active');
}

function renderReviewField(fieldName, label, value, missingFields, prefix = '') {
    const isMissing = missingFields.includes(fieldName);
    const inputId = prefix + fieldName;
    return `
        <div class="modal-field">
            <label>${label}</label>
            <input type="number" id="review_${inputId}" class="${isMissing ? 'missing' : ''}" 
                   value="${value !== null && value !== undefined ? value : ''}" 
                   step="any" placeholder="${isMissing ? 'Missing - enter value' : ''}">
        </div>
    `;
}

window.closeReviewModal = function() {
    document.getElementById('reviewModal').classList.remove('active');
    reviewData = null;
    setTimeout(() => location.reload(), 500);
};

window.skipReviewAndSave = function() {
    closeReviewModal();
};

window.saveReviewedData = async function() {
    if (!reviewData) return;
    
    const workoutId = reviewData.workout_id;
    
    if (workoutId) {
        const workoutUpdates = {
            duration_sec: parseInt(document.getElementById('review_duration_sec')?.value) || null,
            avg_power_w: parseFloat(document.getElementById('review_avg_power_w')?.value) || null,
            max_power_w: parseFloat(document.getElementById('review_max_power_w')?.value) || null,
            normalized_power_w: parseFloat(document.getElementById('review_normalized_power_w')?.value) || null,
            avg_heart_rate: parseInt(document.getElementById('review_avg_heart_rate')?.value) || null,
            max_heart_rate: parseInt(document.getElementById('review_max_heart_rate')?.value) || null,
            tss: parseFloat(document.getElementById('review_tss')?.value) || null,
            intensity_factor: parseFloat(document.getElementById('review_intensity_factor')?.value) || null,
            avg_cadence: parseInt(document.getElementById('review_avg_cadence')?.value) || null,
            distance_km: parseFloat(document.getElementById('review_distance_km')?.value) || null,
            kcal_active: parseInt(document.getElementById('review_kcal_active')?.value) || null,
            kcal_total: parseInt(document.getElementById('review_kcal_total')?.value) || null
        };
        
        try {
            const response = await fetch(`/cycling-readiness/api/cycling/${workoutId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(workoutUpdates)
            });
            
            const result = await response.json();
            if (!result.success) {
                showToast('Failed to update workout', 'error');
                return;
            }
        } catch (err) {
            showToast('Error updating workout', 'error');
            return;
        }
    }
    
    showToast('Data updated successfully!', 'success');
    closeReviewModal();
};

function initReviewModal() {
    document.getElementById('reviewModal').addEventListener('click', function(e) {
        if (e.target === this) closeReviewModal();
    });
}

// ============== Charts ==============
function initCharts(cyclingChartData, readinessChartData) {
    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: {
                labels: { color: 'rgba(255,255,255,0.6)', boxWidth: 10, font: { size: 10 } }
            }
        },
        scales: {
            x: {
                ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 }, maxRotation: 0 },
                grid: { color: 'rgba(255,255,255,0.04)' }
            },
            y: {
                ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } },
                grid: { color: 'rgba(255,255,255,0.04)' }
            }
        }
    };

    // Cycling Chart
    if (cyclingChartData.dates && cyclingChartData.dates.length > 0) {
        const cyclingChartEl = document.getElementById('cyclingChart');
        if (cyclingChartEl) {
            new Chart(cyclingChartEl, {
                type: 'line',
                data: {
                    labels: cyclingChartData.dates,
                    datasets: [
                        {
                            label: 'Power (W)',
                            data: cyclingChartData.avg_power,
                            borderColor: '#00E676',
                            backgroundColor: 'rgba(0, 230, 118, 0.1)',
                            tension: 0.4,
                            fill: true,
                            pointRadius: 2
                        },
                        {
                            label: 'Avg HR',
                            data: cyclingChartData.avg_heart_rate,
                            borderColor: '#FF5252',
                            backgroundColor: 'rgba(255, 82, 82, 0.1)',
                            tension: 0.4,
                            fill: false,
                            pointRadius: 2,
                            yAxisID: 'y2'
                        },
                        {
                            label: 'TSS',
                            data: cyclingChartData.tss,
                            borderColor: '#FFC107',
                            tension: 0.4,
                            yAxisID: 'y1',
                            pointRadius: 2
                        }
                    ]
                },
                options: {
                    ...chartDefaults,
                    scales: {
                        ...chartDefaults.scales,
                        y1: {
                            position: 'right',
                            ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } },
                            grid: { display: false }
                        },
                        y2: {
                            position: 'right',
                            ticks: { 
                                color: 'rgba(255, 82, 82, 0.6)', 
                                font: { size: 9 },
                                callback: function(value) { return value + ' bpm'; }
                            },
                            grid: { display: false },
                            min: 60,
                            suggestedMax: 200
                        }
                    }
                }
            });
        }
    }

    // Readiness Chart
    if (readinessChartData.dates && readinessChartData.dates.length > 0) {
        const readinessChartEl = document.getElementById('readinessChart');
        if (readinessChartEl) {
            new Chart(readinessChartEl, {
                type: 'line',
                data: {
                    labels: readinessChartData.dates,
                    datasets: [{
                        label: 'Score',
                        data: readinessChartData.morning_score,
                        borderColor: '#0077FF',
                        backgroundColor: 'rgba(0, 119, 255, 0.15)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 2
                    }]
                },
                options: {
                    ...chartDefaults,
                    plugins: { legend: { display: false } },
                    scales: {
                        ...chartDefaults.scales,
                        y: { ...chartDefaults.scales.y, min: 0, max: 100 }
                    }
                }
            });
        }
    }
}

// ============== Analytics Tab ==============
let analyticsKpisLoaded = false;
let analyticsChartsLoaded = false;
let efficiencyChart = null;
let vo2Chart = null;

function initAnalyticsTab() {
    // Load analytics data when Analytics tab is shown
    const analyticsTab = document.querySelector('[data-tab="analytics"]');
    if (analyticsTab) {
        analyticsTab.addEventListener('click', function() {
            if (!analyticsKpisLoaded) {
                loadAnalyticsKpis();
            }
            if (!analyticsChartsLoaded) {
                loadEfficiencyVo2Charts();
                loadBodyWeights();
            }
        });
    }
    
    // Set up body weight save button
    const saveWeightBtn = document.getElementById('saveWeightBtn');
    if (saveWeightBtn) {
        saveWeightBtn.addEventListener('click', saveBodyWeight);
    }
    
    // Set today's date as default for weight input
    const weightDateInput = document.getElementById('weightDate');
    if (weightDateInput && !weightDateInput.value) {
        const today = new Date().toISOString().split('T')[0];
        weightDateInput.value = today;
    }
}

async function loadAnalyticsKpis() {
    try {
        const response = await fetch('/cycling-readiness/api/analytics/kpis');
        const data = await response.json();
        
        if (data.success && data.kpis) {
            renderAnalyticsKpis(data.kpis);
            analyticsKpisLoaded = true;
        }
    } catch (err) {
        console.error('Error loading analytics KPIs:', err);
    }
}

async function loadEfficiencyVo2Charts() {
    try {
        const response = await fetch('/cycling-readiness/api/analytics/efficiency-vo2');
        const data = await response.json();
        
        if (data.success) {
            renderEfficiencyChart(data.efficiency_timeseries, data.efficiency_rolling_7d);
            renderVo2Chart(data.vo2_weekly);
            renderFatigueChart(data.fatigue_ratio);
            renderAerobicEfficiencyChart(data.aerobic_efficiency);
            analyticsChartsLoaded = true;
        }
    } catch (err) {
        console.error('Error loading efficiency/VO2 data:', err);
    }
}

// ============== Body Weight Chart Reference ==============
let weightSparklineChart = null;
let fatigueChart = null;
let aerobicChart = null;

// ============== Body Weight Functions ==============
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
    
    const dates = weights.map(w => w.date);
    const values = weights.map(w => w.weight_kg);
    
    if (weightSparklineChart) {
        weightSparklineChart.destroy();
    }
    
    weightSparklineChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                data: values,
                borderColor: '#26A69A',
                backgroundColor: 'rgba(38, 166, 154, 0.15)',
                pointRadius: 3,
                pointBackgroundColor: '#26A69A',
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
                    backgroundColor: 'rgba(0,0,0,0.85)',
                    titleColor: '#26A69A',
                    bodyColor: 'rgba(255,255,255,0.9)',
                    padding: 10,
                    callbacks: {
                        label: (context) => `${context.parsed.y} kg`
                    }
                }
            },
            scales: {
                x: {
                    display: false
                },
                y: {
                    display: true,
                    ticks: {
                        color: 'rgba(255,255,255,0.4)',
                        font: { size: 9 },
                        maxTicksLimit: 4
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
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
            loadBodyWeights(); // Refresh chart
            loadEfficiencyVo2Charts(); // Refresh VO2 chart with new weight
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

// ============== Fatigue Ratio (HR Drift) Chart ==============
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
    
    const dates = fatigueData.map(d => d.date);
    const values = fatigueData.map(d => d.fatigue_ratio);
    
    if (fatigueChart) {
        fatigueChart.destroy();
    }
    
    fatigueChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'HR Drift %',
                data: values,
                borderColor: '#FF7043',
                backgroundColor: 'rgba(255, 112, 67, 0.15)',
                pointRadius: 4,
                pointBackgroundColor: '#FF7043',
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
                    backgroundColor: 'rgba(0,0,0,0.85)',
                    titleColor: '#FF7043',
                    bodyColor: 'rgba(255,255,255,0.9)',
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            const entry = fatigueData[idx];
                            return [
                                `HR Drift: ${entry.fatigue_ratio}%`,
                                `Avg HR: ${entry.avg_hr} bpm`,
                                `Max HR: ${entry.max_hr} bpm`,
                                `Duration: ${entry.duration_min} min`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: 'rgba(255,255,255,0.4)',
                        font: { size: 9 },
                        maxRotation: 45
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    title: {
                        display: true,
                        text: 'HR Drift %',
                        color: 'rgba(255,255,255,0.6)',
                        font: { size: 10 }
                    },
                    ticks: {
                        color: 'rgba(255,255,255,0.4)',
                        font: { size: 9 }
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

// ============== Aerobic Efficiency Chart ==============
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
    
    const dates = aerobicData.map(d => d.date);
    const values = aerobicData.map(d => d.aerobic_efficiency);
    
    if (aerobicChart) {
        aerobicChart.destroy();
    }
    
    aerobicChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Aerobic Efficiency',
                data: values,
                borderColor: '#7C4DFF',
                backgroundColor: 'rgba(124, 77, 255, 0.15)',
                pointRadius: 4,
                pointBackgroundColor: '#7C4DFF',
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
                    backgroundColor: 'rgba(0,0,0,0.85)',
                    titleColor: '#7C4DFF',
                    bodyColor: 'rgba(255,255,255,0.9)',
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            const entry = aerobicData[idx];
                            return [
                                `Efficiency: ${entry.aerobic_efficiency} W/ms`,
                                `Power: ${entry.avg_power_w}W`,
                                `HRV: ${entry.hrv_avg} ms`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: 'rgba(255,255,255,0.4)',
                        font: { size: 9 },
                        maxRotation: 45
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    title: {
                        display: true,
                        text: 'W per ms HRV',
                        color: 'rgba(255,255,255,0.6)',
                        font: { size: 10 }
                    },
                    ticks: {
                        color: 'rgba(255,255,255,0.4)',
                        font: { size: 9 }
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

function renderEfficiencyChart(timeseries, rolling) {
    const chartContainer = document.getElementById('efficiencyChartContainer');
    const emptyState = document.getElementById('efficiencyChartEmpty');
    const canvas = document.getElementById('efficiencyChart');
    
    if (!timeseries || timeseries.length < 3) {
        chartContainer.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    chartContainer.style.display = 'block';
    emptyState.style.display = 'none';
    
    // Prepare data
    const dates = timeseries.map(d => d.date);
    const eiValues = timeseries.map(d => d.efficiency_index);
    const rollingDates = rolling.map(d => d.date);
    const rollingEi = rolling.map(d => d.rolling_ei);
    
    // Destroy existing chart if any
    if (efficiencyChart) {
        efficiencyChart.destroy();
    }
    
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
                    pointBackgroundColor: 'rgba(0, 255, 198, 0.8)',
                    pointBorderColor: 'rgba(0, 255, 198, 1)',
                    tension: 0,
                    fill: false,
                    order: 2
                },
                {
                    label: '7-Day Rolling Avg',
                    data: rollingDates.map(d => {
                        const idx = dates.indexOf(d);
                        if (idx >= 0) {
                            return rolling.find(r => r.date === d)?.rolling_ei || null;
                        }
                        return null;
                    }),
                    borderColor: '#00FFC6',
                    backgroundColor: 'rgba(0, 255, 198, 0.15)',
                    pointRadius: 0,
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    order: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: 'rgba(255,255,255,0.7)',
                        font: { size: 10 },
                        boxWidth: 12
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.85)',
                    titleColor: '#00FFC6',
                    bodyColor: 'rgba(255,255,255,0.9)',
                    padding: 12,
                    callbacks: {
                        afterBody: function(context) {
                            const dataIndex = context[0].dataIndex;
                            const entry = timeseries[dataIndex];
                            if (entry) {
                                return [
                                    `Power: ${entry.avg_power_w}W`,
                                    `HR: ${entry.avg_hr} bpm`,
                                    `Type: ${entry.workout_type || 'unknown'}`
                                ];
                            }
                            return [];
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: 'rgba(255,255,255,0.4)',
                        font: { size: 9 },
                        maxRotation: 45
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    title: {
                        display: true,
                        text: 'W per bpm',
                        color: 'rgba(255,255,255,0.6)',
                        font: { size: 10 }
                    },
                    ticks: {
                        color: 'rgba(255,255,255,0.4)',
                        font: { size: 9 }
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

function renderVo2Chart(weeklyData) {
    const chartContainer = document.getElementById('vo2ChartContainer');
    const emptyState = document.getElementById('vo2ChartEmpty');
    const canvas = document.getElementById('vo2Chart');
    const title = document.getElementById('vo2ChartTitle');
    
    if (!weeklyData || weeklyData.length < 2) {
        chartContainer.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    chartContainer.style.display = 'block';
    emptyState.style.display = 'none';
    
    // Check if we have VO2 index or just peak power
    const hasVo2Index = weeklyData.some(d => d.vo2_index !== null);
    
    // Update title based on data
    if (!hasVo2Index) {
        title.innerHTML = '<i class="fas fa-bolt"></i>Weekly Peak Power (proxy for VO₂ capacity)';
    }
    
    // Prepare data
    const labels = weeklyData.map(d => d.week_label);
    const values = hasVo2Index 
        ? weeklyData.map(d => d.vo2_index)
        : weeklyData.map(d => d.peak_power_w);
    
    // Destroy existing chart if any
    if (vo2Chart) {
        vo2Chart.destroy();
    }
    
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
                pointBackgroundColor: '#FF7043',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                borderWidth: 3,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.85)',
                    titleColor: '#FF7043',
                    bodyColor: 'rgba(255,255,255,0.9)',
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const idx = context.dataIndex;
                            const entry = weeklyData[idx];
                            const lines = [];
                            if (entry.vo2_index !== null) {
                                lines.push(`VO₂ Index: ${entry.vo2_index} W/kg`);
                            }
                            lines.push(`Peak Power: ${entry.peak_power_w}W`);
                            if (entry.weight_kg) {
                                lines.push(`Weight: ${entry.weight_kg} kg`);
                            }
                            lines.push(`Workouts: ${entry.workout_count}`);
                            return lines;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: 'rgba(255,255,255,0.4)',
                        font: { size: 9 }
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                y: {
                    title: {
                        display: true,
                        text: hasVo2Index ? 'W/kg' : 'Watts',
                        color: 'rgba(255,255,255,0.6)',
                        font: { size: 10 }
                    },
                    ticks: {
                        color: 'rgba(255,255,255,0.4)',
                        font: { size: 9 }
                    },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
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
        
        // Color card based on direction (HRV up = good)
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
        
        // For RHR, down is good, up is bad (opposite of HRV)
        const trendClass = rhrTrend.direction === 'up' ? 'down' : rhrTrend.direction === 'down' ? 'up' : 'flat';
        rhrTrendArrow.className = `kpi-trend ${trendClass}`;
        
        // Color card if elevated
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
        
        // Color card if improving
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

// ============== Initialize ==============
function initCyclingReadiness(cyclingChartData, readinessChartData) {
    initTabs();
    initRatingSelectors();
    initFileUpload();
    initReadinessForm();
    initDeleteHandlers();
    initEditWorkout();
    initEditReadiness();
    initScoreTooltip();
    initDayView();
    initReviewModal();
    initCoachTab();
    initAnalyticsTab();
    handleUrlParams();
    initCharts(cyclingChartData, readinessChartData);

    // Initial load
    const today = document.getElementById('readinessDate')?.value;
    if (today) {
        updateDateLabel(today);
        loadFullReadinessData(today);
    }
    loadReadinessHistory();

    console.log('🚴 Zyra Cycle v3.1 initialized');
}

// Export for use in HTML
window.initCyclingReadiness = initCyclingReadiness;

