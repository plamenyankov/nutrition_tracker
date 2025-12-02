/**
 * Zyra Cycle - Readiness Page JavaScript
 * Handles morning readiness form and history
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

// ============== Rating Selectors ==============
function initRatingSelectors() {
    document.querySelectorAll('.rating-selector, .status-selector').forEach(selector => {
        selector.querySelectorAll('.rating-option, .status-option').forEach(option => {
            option.addEventListener('click', function() {
                const parent = this.closest('.rating-selector, .status-selector');
                parent.querySelectorAll('.rating-option, .status-option').forEach(o => o.classList.remove('selected'));
                this.classList.add('selected');
            });
        });
    });
}

// ============== Readiness Form ==============
function initReadinessForm() {
    const form = document.getElementById('readinessForm');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
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
            symptoms_flag: document.getElementById('symptomsFlag')?.checked || false
        };

        // Add manual cardio values if present (using correct field names for backend)
        if (manualRhr) data.manual_rhr_bpm = parseInt(manualRhr);
        if (manualHrvLow) data.manual_hrv_low_ms = parseInt(manualHrvLow);
        if (manualHrvHigh) data.manual_hrv_high_ms = parseInt(manualHrvHigh);
        
        // Override values take precedence (also using manual_ prefix)
        if (overrideRhr) data.manual_rhr_bpm = parseInt(overrideRhr);
        if (overrideHrvLow) data.manual_hrv_low_ms = parseInt(overrideHrvLow);
        if (overrideHrvHigh) data.manual_hrv_high_ms = parseInt(overrideHrvHigh);

        try {
            const response = await fetch('/cycling-readiness/api/readiness', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                showToast('Readiness saved successfully');
                loadReadinessHistory();
                loadFullReadinessData(data.date);
            } else {
                showToast(result.error || 'Error saving readiness', 'error');
            }
        } catch (err) {
            showToast('Error saving readiness', 'error');
        }
    });
}

// ============== Collapsible Readiness Card ==============
function toggleReadinessForm() {
    const card = document.getElementById('morningReadinessCard');
    const formBody = document.getElementById('readinessFormBody');
    const summary = document.getElementById('readinessSummary');
    const indicator = document.getElementById('collapseIndicator');
    
    const isExpanded = formBody.style.display !== 'none';
    
    if (isExpanded && currentReadinessData) {
        // Collapse - show summary
        formBody.style.display = 'none';
        summary.style.display = 'flex';
        indicator.innerHTML = '<i class="fas fa-chevron-right"></i>';
        card.classList.add('collapsed');
    } else {
        // Expand - show form
        formBody.style.display = 'block';
        summary.style.display = 'none';
        indicator.innerHTML = '<i class="fas fa-chevron-down"></i>';
        card.classList.remove('collapsed');
    }
}

function updateReadinessSummary(data) {
    if (!data) return;
    
    const scoreEl = document.getElementById('summaryScore');
    const energyEl = document.getElementById('summaryEnergy');
    const moodEl = document.getElementById('summaryMood');
    const fatigueEl = document.getElementById('summaryFatigue');
    const hrvEl = document.getElementById('summaryHrv');
    const rhrEl = document.getElementById('summaryRhr');
    const symptomsEl = document.getElementById('summarySymptoms');
    
    if (scoreEl && data.morning_score !== null) {
        scoreEl.textContent = `${data.morning_score}%`;
        scoreEl.className = `summary-pill score ${data.morning_score >= 70 ? 'good' : data.morning_score >= 50 ? 'ok' : 'low'}`;
    }
    
    if (energyEl) energyEl.textContent = `⚡ ${data.energy || '--'}`;
    if (moodEl) moodEl.textContent = data.mood === 3 ? '😊' : data.mood === 2 ? '😐' : data.mood === 1 ? '😔' : '😐';
    if (fatigueEl) fatigueEl.textContent = `💪 ${data.muscle_fatigue || '--'}`;
    
    if (hrvEl) {
        const hrvStatus = data.hrv_status;
        hrvEl.textContent = `HRV ${hrvStatus == 1 ? '↑' : hrvStatus == -1 ? '↓' : '→'}`;
        hrvEl.className = `summary-pill hrv ${hrvStatus == 1 ? 'positive' : hrvStatus == -1 ? 'negative' : ''}`;
    }
    
    if (rhrEl) {
        const rhrStatus = data.rhr_status;
        rhrEl.textContent = `RHR ${rhrStatus == 1 ? '↑' : rhrStatus == -1 ? '↓' : '→'}`;
        rhrEl.className = `summary-pill rhr ${rhrStatus == -1 ? 'positive' : rhrStatus == 1 ? 'negative' : ''}`;
    }
    
    if (symptomsEl) {
        symptomsEl.style.display = data.symptoms_flag ? 'inline-flex' : 'none';
    }
}

// ============== Load Readiness Data ==============
async function loadFullReadinessData(date) {
    try {
        const response = await fetch(`/cycling-readiness/api/readiness/full?date=${date}`);
        const data = await response.json();
        
        if (data.success) {
            currentReadinessData = data.readiness;
            populateReadinessForm(data.readiness, data.cardio);
            updateReadinessSummary(data.readiness);
            
            // Auto-collapse if data exists
            if (data.readiness && data.readiness.energy) {
                toggleReadinessForm();
            }
        }
    } catch (err) {
        console.error('Error loading readiness data:', err);
    }
}

function populateReadinessForm(readiness, cardio) {
    // Store entry ID if exists
    if (readiness?.id) {
        document.getElementById('readinessEntryId').value = readiness.id;
    }
    
    // Populate ratings
    if (readiness?.energy) {
        const energyRadio = document.querySelector(`[name="energy"][value="${readiness.energy}"]`);
        if (energyRadio) {
            energyRadio.checked = true;
            energyRadio.closest('.rating-option').classList.add('selected');
        }
    }
    
    if (readiness?.mood) {
        const moodRadio = document.querySelector(`[name="mood"][value="${readiness.mood}"]`);
        if (moodRadio) {
            moodRadio.checked = true;
            moodRadio.closest('.rating-option').classList.add('selected');
        }
    }
    
    if (readiness?.muscle_fatigue) {
        const fatigueRadio = document.querySelector(`[name="muscle_fatigue"][value="${readiness.muscle_fatigue}"]`);
        if (fatigueRadio) {
            fatigueRadio.checked = true;
            fatigueRadio.closest('.rating-option').classList.add('selected');
        }
    }
    
    // Populate status selectors
    if (readiness?.hrv_status !== undefined) {
        const hrvRadio = document.querySelector(`[name="hrv_status"][value="${readiness.hrv_status}"]`);
        if (hrvRadio) {
            hrvRadio.checked = true;
            hrvRadio.closest('.status-option').classList.add('selected');
        }
    }
    
    if (readiness?.rhr_status !== undefined) {
        const rhrRadio = document.querySelector(`[name="rhr_status"][value="${readiness.rhr_status}"]`);
        if (rhrRadio) {
            rhrRadio.checked = true;
            rhrRadio.closest('.status-option').classList.add('selected');
        }
    }
    
    // Symptoms
    if (document.getElementById('symptomsFlag')) {
        document.getElementById('symptomsFlag').checked = readiness?.symptoms_flag || false;
    }
    
    // Handle cardio display
    const cardioDisplay = document.getElementById('cardioDataDisplay');
    const manualInput = document.getElementById('manualCardioInput');
    
    if (cardio && (cardio.rhr_bpm || cardio.hrv_low_ms)) {
        hasCardioData = true;
        if (cardioDisplay) cardioDisplay.style.display = 'block';
        if (manualInput) manualInput.style.display = 'none';
        
        // Display values
        if (document.getElementById('displayRhrBpm')) {
            document.getElementById('displayRhrBpm').textContent = cardio.rhr_bpm ? `${cardio.rhr_bpm} bpm` : '--';
        }
        if (document.getElementById('displayHrv')) {
            const hrvAvg = (cardio.hrv_low_ms && cardio.hrv_high_ms) 
                ? Math.round((cardio.hrv_low_ms + cardio.hrv_high_ms) / 2) 
                : null;
            document.getElementById('displayHrv').textContent = hrvAvg ? `${hrvAvg} ms` : '--';
        }
        
        // Store original values
        originalRhrBpm = cardio.rhr_bpm;
        originalHrvLow = cardio.hrv_low_ms;
        originalHrvHigh = cardio.hrv_high_ms;
    } else {
        hasCardioData = false;
        if (cardioDisplay) cardioDisplay.style.display = 'none';
        if (manualInput) manualInput.style.display = 'block';
    }
}

// ============== Cardio Override ==============
function toggleCardioOverride(type) {
    if (type === 'rhr') {
        const input = document.getElementById('rhrOverrideInput');
        const isShowing = input.style.display !== 'none';
        input.style.display = isShowing ? 'none' : 'block';
        rhrManualOverride = !isShowing;
        
        if (!isShowing && originalRhrBpm) {
            document.getElementById('overrideRhrBpm').value = originalRhrBpm;
        }
    } else if (type === 'hrv') {
        const input = document.getElementById('hrvOverrideInput');
        const isShowing = input.style.display !== 'none';
        input.style.display = isShowing ? 'none' : 'block';
        hrvManualOverride = !isShowing;
        
        if (!isShowing) {
            if (originalHrvLow) document.getElementById('overrideHrvLow').value = originalHrvLow;
            if (originalHrvHigh) document.getElementById('overrideHrvHigh').value = originalHrvHigh;
        }
    }
}

function resetCardioToAuto(type) {
    if (type === 'rhr') {
        document.getElementById('rhrOverrideInput').style.display = 'none';
        document.getElementById('overrideRhrBpm').value = '';
        rhrManualOverride = false;
    } else if (type === 'hrv') {
        document.getElementById('hrvOverrideInput').style.display = 'none';
        document.getElementById('overrideHrvLow').value = '';
        document.getElementById('overrideHrvHigh').value = '';
        hrvManualOverride = false;
    }
}

// ============== Readiness History ==============
async function loadReadinessHistory() {
    try {
        const response = await fetch('/cycling-readiness/api/readiness?limit=14');
        const data = await response.json();
        
        const tbody = document.getElementById('readinessHistoryBody');
        const emptyState = document.getElementById('readinessHistoryEmpty');
        
        if (!data.success || !data.entries || data.entries.length === 0) {
            if (tbody) tbody.innerHTML = '';
            if (emptyState) emptyState.style.display = 'block';
            return;
        }
        
        if (emptyState) emptyState.style.display = 'none';
        
        if (tbody) {
            tbody.innerHTML = data.entries.map(e => `
                <tr data-id="${e.id}" data-date="${e.date}">
                    <td>
                        <button class="btn-view-day" data-date="${e.date}" title="View Day Details">
                            ${formatDateShort(e.date)}
                        </button>
                    </td>
                    <td class="${getScoreClass(e.morning_score)}">${e.morning_score || '--'}%</td>
                    <td>${e.energy || '--'}</td>
                    <td>${getMoodEmoji(e.mood)}</td>
                    <td>${e.muscle_fatigue || '--'}</td>
                    <td>${e.sleep_hours ? e.sleep_hours.toFixed(1) + 'h' : '--'}</td>
                    <td>${e.rhr_bpm || '--'}</td>
                    <td>${e.hrv_avg ? Math.round(e.hrv_avg) : '--'}</td>
                    <td>${getStatusArrow(e.hrv_status)}</td>
                    <td>${getStatusArrow(e.rhr_status, true)}</td>
                    <td>${e.symptoms_flag ? '🤒' : ''}</td>
                    <td>
                        <button class="btn-edit btn-edit-readiness" data-id="${e.id}" data-date="${e.date}" title="Edit">
                            <i class="fas fa-pencil-alt"></i>
                        </button>
                        <button class="btn-delete btn-delete-readiness" data-id="${e.id}" title="Delete">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
            
            // Re-attach event listeners
            initHistoryHandlers();
        }
    } catch (err) {
        console.error('Error loading readiness history:', err);
    }
}

function initHistoryHandlers() {
    // Edit buttons
    document.querySelectorAll('.btn-edit-readiness').forEach(btn => {
        btn.addEventListener('click', function() {
            openEditReadinessModal(this.dataset.id, this.dataset.date);
        });
    });
    
    // Delete buttons
    document.querySelectorAll('.btn-delete-readiness').forEach(btn => {
        btn.addEventListener('click', function() {
            showConfirmModal('readiness', this.dataset.id, 'Delete this readiness entry?');
        });
    });
    
    // Day view buttons
    document.querySelectorAll('.btn-view-day').forEach(btn => {
        btn.addEventListener('click', function() {
            openDayViewModal(this.dataset.date);
        });
    });
}

// ============== Helper Functions ==============
function formatDateShort(dateStr) {
    if (!dateStr) return '--';
    const d = new Date(dateStr);
    return `${d.getMonth() + 1}/${d.getDate()}`;
}

function getScoreClass(score) {
    if (!score) return '';
    if (score >= 70) return 'score-good';
    if (score >= 50) return 'score-ok';
    return 'score-low';
}

function getMoodEmoji(mood) {
    if (mood === 3) return '😊';
    if (mood === 2) return '😐';
    if (mood === 1) return '😔';
    return '--';
}

function getStatusArrow(status, inverted = false) {
    if (status == 1) return inverted ? '<span class="status-negative">↑</span>' : '<span class="status-positive">↑</span>';
    if (status == -1) return inverted ? '<span class="status-positive">↓</span>' : '<span class="status-negative">↓</span>';
    return '<span class="status-neutral">→</span>';
}

function updateDateLabel(date) {
    const label = document.getElementById('readinessDateLabel');
    if (label) {
        label.textContent = date;
    }
}

// ============== Score Tooltip ==============
function toggleScoreTooltip() {
    const tooltip = document.getElementById('scoreTooltip');
    if (tooltip) {
        tooltip.classList.toggle('active');
    }
}

function initScoreTooltip() {
    // Close tooltip when clicking outside
    document.addEventListener('click', function(e) {
        const tooltip = document.getElementById('scoreTooltip');
        const btn = document.querySelector('.score-info-icon');
        if (tooltip && !tooltip.contains(e.target) && e.target !== btn && !btn?.contains(e.target)) {
            tooltip.classList.remove('active');
        }
    });
}

// ============== Edit Readiness for Today ==============
function editReadinessForDate() {
    const date = document.getElementById('readinessDate')?.value;
    const id = document.getElementById('readinessEntryId')?.value;
    if (id && date) {
        openEditReadinessModal(id, date);
    }
}

// ============== Initialize ==============
document.addEventListener('DOMContentLoaded', function() {
    initRatingSelectors();
    initReadinessForm();
    initScoreTooltip();
    
    // Initial load
    const today = document.getElementById('readinessDate')?.value;
    if (today) {
        updateDateLabel(today);
        loadFullReadinessData(today);
    }
    loadReadinessHistory();
    
    console.log('💤 Readiness page initialized');
});

// Export for global use
window.toggleReadinessForm = toggleReadinessForm;
window.toggleCardioOverride = toggleCardioOverride;
window.resetCardioToAuto = resetCardioToAuto;
window.editReadinessForDate = editReadinessForDate;
window.toggleScoreTooltip = toggleScoreTooltip;

