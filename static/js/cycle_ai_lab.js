/**
 * AI Lab - Prompt Management UI
 * 
 * Handles CRUD operations for AI profiles (Coach and Analyzer).
 * Provides UI for editing prompts, settings, and switching active profiles.
 * Also provides Playground for testing prompts without persisting.
 */

// ============== State ==============

let currentEditingProfile = null;
let currentTab = 'coach';
let currentMainSection = 'profiles';
let workoutsLoaded = false;


// ============== Main Section Switching ==============

function switchMainSection(section) {
    currentMainSection = section;
    
    // Update main tab buttons
    document.querySelectorAll('.ai-lab-main-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.section === section);
    });
    
    // Update main sections
    document.querySelectorAll('.ai-lab-main-section').forEach(sec => {
        sec.classList.toggle('active', sec.id === `${section}-section`);
    });
    
    // Load workouts when switching to playground (lazy load)
    if (section === 'playground' && !workoutsLoaded) {
        loadWorkoutsForPlayground();
    }
}

// ============== Tab Switching ==============

function switchAiLabTab(tab) {
    currentTab = tab;
    
    // Update tab buttons
    document.querySelectorAll('.ai-lab-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.target === tab);
    });
    
    // Update sections
    document.querySelectorAll('.profile-section').forEach(section => {
        section.classList.toggle('active', section.id === `${tab}-section`);
    });
    
    // Close any open editor when switching tabs
    closeEditor('coach');
    closeEditor('analyzer');
}

// ============== Profile Actions ==============

async function editProfile(profileId, profileType) {
    try {
        showLoading();
        
        const response = await fetch(`/cycling-readiness/api/ai-profiles/${profileId}`);
        const data = await response.json();
        
        hideLoading();
        
        if (!data.success) {
            showToast(data.error || 'Failed to load profile', 'error');
            return;
        }
        
        const profile = data.profile;
        populateEditor(profileType, profile);
        openEditor(profileType);
        
    } catch (error) {
        hideLoading();
        console.error('Error loading profile:', error);
        showToast('Failed to load profile', 'error');
    }
}

async function duplicateProfile(profileId, profileType) {
    try {
        showLoading();
        
        const response = await fetch(`/cycling-readiness/api/ai-profiles/${profileId}/duplicate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (!data.success) {
            showToast(data.error || 'Failed to duplicate profile', 'error');
            return;
        }
        
        showToast(data.message || 'Profile duplicated', 'success');
        
        // Reload the page to show new profile
        setTimeout(() => window.location.reload(), 500);
        
    } catch (error) {
        hideLoading();
        console.error('Error duplicating profile:', error);
        showToast('Failed to duplicate profile', 'error');
    }
}

async function setActiveProfile(profileId, profileType) {
    try {
        showLoading();
        
        const response = await fetch(`/cycling-readiness/api/ai-profiles/${profileId}/set-active`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (!data.success) {
            showToast(data.error || 'Failed to set active profile', 'error');
            return;
        }
        
        showToast(data.message || 'Profile activated', 'success');
        
        // Reload the page to update UI
        setTimeout(() => window.location.reload(), 500);
        
    } catch (error) {
        hideLoading();
        console.error('Error setting active profile:', error);
        showToast('Failed to set active profile', 'error');
    }
}

async function setActiveFromEditor(profileType) {
    const profileId = document.getElementById(`${profileType}-profile-id`).value;
    if (profileId) {
        await setActiveProfile(profileId, profileType);
    }
}

// ============== Editor Functions ==============

function populateEditor(profileType, profile) {
    document.getElementById(`${profileType}-profile-id`).value = profile.id;
    document.getElementById(`${profileType}-version`).value = profile.version || '';
    document.getElementById(`${profileType}-system-prompt`).value = profile.system_prompt || '';
    document.getElementById(`${profileType}-user-prompt-template`).value = profile.user_prompt_template || '';
    
    // Format settings JSON nicely
    let settingsJson = profile.settings_json || '{}';
    try {
        const parsed = typeof settingsJson === 'string' ? JSON.parse(settingsJson) : settingsJson;
        settingsJson = JSON.stringify(parsed, null, 2);
    } catch (e) {
        // Keep as is if can't parse
    }
    document.getElementById(`${profileType}-settings-json`).value = settingsJson;
    
    // Update character count
    updateCharCount(profileType);
    
    // Clear any errors
    clearErrors(profileType);
    
    // Update "Set Active" button visibility
    const setActiveBtn = document.getElementById(`${profileType}-set-active-btn`);
    if (setActiveBtn) {
        setActiveBtn.style.display = profile.is_active ? 'none' : 'flex';
    }
    
    currentEditingProfile = profile;
}

function openEditor(profileType) {
    document.getElementById(`${profileType}-editor`).classList.add('active');
    
    // Scroll to editor
    document.getElementById(`${profileType}-editor`).scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start' 
    });
}

function closeEditor(profileType) {
    document.getElementById(`${profileType}-editor`).classList.remove('active');
    currentEditingProfile = null;
}

function clearErrors(profileType) {
    document.querySelectorAll(`#${profileType}-editor .editor-field`).forEach(field => {
        field.classList.remove('has-error');
    });
}

function updateCharCount(profileType) {
    const textarea = document.getElementById(`${profileType}-system-prompt`);
    const countSpan = document.getElementById(`${profileType}-system-prompt-count`);
    if (textarea && countSpan) {
        countSpan.textContent = textarea.value.length.toLocaleString();
    }
}

// ============== Save Profile ==============

async function saveProfile(profileType) {
    const profileId = document.getElementById(`${profileType}-profile-id`).value;
    const version = document.getElementById(`${profileType}-version`).value.trim();
    const systemPrompt = document.getElementById(`${profileType}-system-prompt`).value;
    const userPromptTemplate = document.getElementById(`${profileType}-user-prompt-template`).value;
    const settingsJson = document.getElementById(`${profileType}-settings-json`).value;
    
    // Clear previous errors
    clearErrors(profileType);
    
    // Validate version
    if (!version) {
        document.getElementById(`${profileType}-version`).parentElement.classList.add('has-error');
        showToast('Version is required', 'error');
        return;
    }
    
    // Validate settings JSON
    try {
        JSON.parse(settingsJson);
    } catch (e) {
        document.getElementById(`${profileType}-settings-json`).parentElement.classList.add('has-error');
        document.getElementById(`${profileType}-settings-json-error`).textContent = `Invalid JSON: ${e.message}`;
        showToast('Invalid settings JSON format', 'error');
        return;
    }
    
    try {
        showLoading();
        
        const response = await fetch(`/cycling-readiness/api/ai-profiles/${profileId}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                version: version,
                system_prompt: systemPrompt,
                user_prompt_template: userPromptTemplate,
                settings_json: settingsJson
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (!data.success) {
            showToast(data.error || 'Failed to save profile', 'error');
            return;
        }
        
        showToast('Profile saved successfully', 'success');
        
        // Reload the page to show updated data
        setTimeout(() => window.location.reload(), 500);
        
    } catch (error) {
        hideLoading();
        console.error('Error saving profile:', error);
        showToast('Failed to save profile', 'error');
    }
}

// ============== UI Helpers ==============

function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.add('active');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.remove('active');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) {
        console.log(`Toast (${type}): ${message}`);
        return;
    }
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'error' ? 'exclamation-circle' : 
                 'info-circle';
    
    toast.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============== Playground Functions ==============

async function loadWorkoutsForPlayground() {
    try {
        const response = await fetch('/cycling-readiness/api/ai-lab/workouts?limit=30');
        const data = await response.json();
        
        if (!data.success) {
            console.error('Failed to load workouts:', data.error);
            return;
        }
        
        const select = document.getElementById('analyzer-playground-workout');
        if (!select) return;
        
        // Clear existing options (except first)
        select.innerHTML = '<option value="">Select a workout...</option>';
        
        // Add workout options
        data.workouts.forEach(w => {
            const option = document.createElement('option');
            option.value = w.id;
            
            let label = `${w.date}`;
            if (w.duration_min) label += ` • ${w.duration_min}min`;
            if (w.avg_power_w) label += ` • ${w.avg_power_w}W`;
            if (w.avg_hr_bpm) label += ` • ${w.avg_hr_bpm}bpm`;
            if (w.tss) label += ` • TSS ${w.tss}`;
            
            option.textContent = label;
            select.appendChild(option);
        });
        
        workoutsLoaded = true;
        
    } catch (error) {
        console.error('Error loading workouts:', error);
    }
}

// ---- Coach Playground ----

async function previewCoachPayload() {
    const dateInput = document.getElementById('coach-playground-date');
    const profileSelect = document.getElementById('coach-playground-profile');
    
    const date = dateInput?.value || new Date().toISOString().split('T')[0];
    const profileId = profileSelect?.value || '';
    
    let url = `/cycling-readiness/api/ai-lab/coach/payload?date=${date}`;
    if (profileId) url += `&profile_id=${profileId}`;
    
    showPlaygroundLoading('coach');
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        hidePlaygroundLoading('coach');
        
        if (!data.success) {
            renderPlaygroundError('coach', data.error);
            return;
        }
        
        renderCoachPayload(data);
        
    } catch (error) {
        hidePlaygroundLoading('coach');
        renderPlaygroundError('coach', error.message);
    }
}

async function runCoachDryRun() {
    const dateInput = document.getElementById('coach-playground-date');
    const profileSelect = document.getElementById('coach-playground-profile');
    
    const date = dateInput?.value || new Date().toISOString().split('T')[0];
    const profileId = profileSelect?.value || null;
    
    showPlaygroundLoading('coach');
    
    try {
        const response = await fetch('/cycling-readiness/api/ai-lab/coach/dry-run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: date,
                profile_id: profileId ? parseInt(profileId) : null
            })
        });
        
        const data = await response.json();
        
        hidePlaygroundLoading('coach');
        
        if (!data.success) {
            renderPlaygroundError('coach', data.error);
            return;
        }
        
        renderCoachDryRunResult(data);
        
    } catch (error) {
        hidePlaygroundLoading('coach');
        renderPlaygroundError('coach', error.message);
    }
}

function renderCoachPayload(data) {
    const output = document.getElementById('coach-playground-output');
    if (!output) return;
    
    const payload = data.payload;
    
    output.innerHTML = `
        <div class="playground-panel">
            <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                <div class="playground-panel-title">
                    <i class="fas fa-cog"></i> Request Details
                </div>
                <i class="fas fa-chevron-down playground-panel-toggle"></i>
            </div>
            <div class="playground-panel-content">
                <p style="font-size: 0.8rem; color: var(--color-muted); margin: 0 0 0.5rem 0;">
                    <strong>Model:</strong> ${payload.model} &nbsp;|&nbsp; 
                    <strong>Temp:</strong> ${payload.temperature} &nbsp;|&nbsp;
                    <strong>Profile:</strong> ${data.profile.version || 'default'}
                </p>
            </div>
        </div>
        
        <div class="playground-panel collapsed">
            <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                <div class="playground-panel-title">
                    <i class="fas fa-robot"></i> System Prompt
                </div>
                <i class="fas fa-chevron-down playground-panel-toggle"></i>
            </div>
            <div class="playground-panel-content">
                <pre class="playground-json">${escapeHtml(payload.system_prompt)}</pre>
            </div>
        </div>
        
        <div class="playground-panel collapsed">
            <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                <div class="playground-panel-title">
                    <i class="fas fa-user"></i> User Prompt
                </div>
                <i class="fas fa-chevron-down playground-panel-toggle"></i>
            </div>
            <div class="playground-panel-content">
                <pre class="playground-json">${escapeHtml(payload.user_prompt)}</pre>
            </div>
        </div>
        
        <div class="playground-panel">
            <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                <div class="playground-panel-title">
                    <i class="fas fa-database"></i> Input Data (Training Context)
                </div>
                <i class="fas fa-chevron-down playground-panel-toggle"></i>
            </div>
            <div class="playground-panel-content">
                <pre class="playground-json">${JSON.stringify(payload.input_data, null, 2)}</pre>
            </div>
        </div>
    `;
}

function renderCoachDryRunResult(data) {
    const output = document.getElementById('coach-playground-output');
    if (!output) return;
    
    const parsed = data.parsed_result;
    const hasError = !!data.error;
    
    let resultHtml = '';
    
    // Error display
    if (hasError) {
        resultHtml += `
            <div class="playground-error">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${escapeHtml(data.error)}</span>
            </div>
        `;
    }
    
    // Parsed result preview (if available)
    if (parsed) {
        const dayType = parsed.day_type || 'unknown';
        const dayTypeDisplay = dayType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        resultHtml += `
            <div class="playground-preview-card">
                <div class="playground-preview-badge">
                    <i class="fas fa-flask"></i> Preview - Not Saved
                </div>
                <div class="playground-preview-type">${dayTypeDisplay}</div>
                <div class="playground-preview-summary">${escapeHtml(parsed.reason_short || '')}</div>
                ${parsed.session_plan ? `
                    <div class="playground-preview-score">
                        <i class="fas fa-clock"></i> ${parsed.session_plan.duration_minutes || '?'}min
                    </div>
                    <div class="playground-preview-score">
                        <i class="fas fa-heartbeat"></i> ${parsed.session_plan.primary_zone || 'N/A'}
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    // Parsed result JSON
    if (parsed) {
        resultHtml += `
            <div class="playground-panel">
                <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                    <div class="playground-panel-title">
                        <i class="fas fa-check-circle" style="color: var(--color-green);"></i> Parsed Result
                    </div>
                    <i class="fas fa-chevron-down playground-panel-toggle"></i>
                </div>
                <div class="playground-panel-content">
                    <pre class="playground-json">${JSON.stringify(parsed, null, 2)}</pre>
                </div>
            </div>
        `;
    }
    
    // Raw response
    if (data.raw_response) {
        resultHtml += `
            <div class="playground-panel collapsed">
                <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                    <div class="playground-panel-title">
                        <i class="fas fa-code"></i> Raw OpenAI Response
                    </div>
                    <i class="fas fa-chevron-down playground-panel-toggle"></i>
                </div>
                <div class="playground-panel-content">
                    <pre class="playground-json">${escapeHtml(data.raw_response)}</pre>
                </div>
            </div>
        `;
    }
    
    // Payload
    if (data.payload) {
        resultHtml += `
            <div class="playground-panel collapsed">
                <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                    <div class="playground-panel-title">
                        <i class="fas fa-paper-plane"></i> Request Payload
                    </div>
                    <i class="fas fa-chevron-down playground-panel-toggle"></i>
                </div>
                <div class="playground-panel-content">
                    <pre class="playground-json">${JSON.stringify(data.payload, null, 2)}</pre>
                </div>
            </div>
        `;
    }
    
    output.innerHTML = resultHtml;
}

// ---- Analyzer Playground ----

async function previewAnalyzerPayload() {
    const workoutSelect = document.getElementById('analyzer-playground-workout');
    const profileSelect = document.getElementById('analyzer-playground-profile');
    
    const workoutId = workoutSelect?.value;
    if (!workoutId) {
        showToast('Please select a workout first', 'error');
        return;
    }
    
    const profileId = profileSelect?.value || '';
    
    let url = `/cycling-readiness/api/ai-lab/analyzer/payload?workout_id=${workoutId}`;
    if (profileId) url += `&profile_id=${profileId}`;
    
    showPlaygroundLoading('analyzer');
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        hidePlaygroundLoading('analyzer');
        
        if (!data.success) {
            renderPlaygroundError('analyzer', data.error);
            return;
        }
        
        renderAnalyzerPayload(data);
        
    } catch (error) {
        hidePlaygroundLoading('analyzer');
        renderPlaygroundError('analyzer', error.message);
    }
}

async function runAnalyzerDryRun() {
    const workoutSelect = document.getElementById('analyzer-playground-workout');
    const profileSelect = document.getElementById('analyzer-playground-profile');
    
    const workoutId = workoutSelect?.value;
    if (!workoutId) {
        showToast('Please select a workout first', 'error');
        return;
    }
    
    const profileId = profileSelect?.value || null;
    
    showPlaygroundLoading('analyzer');
    
    try {
        const response = await fetch('/cycling-readiness/api/ai-lab/analyzer/dry-run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                workout_id: parseInt(workoutId),
                profile_id: profileId ? parseInt(profileId) : null
            })
        });
        
        const data = await response.json();
        
        hidePlaygroundLoading('analyzer');
        
        if (!data.success) {
            renderPlaygroundError('analyzer', data.error);
            return;
        }
        
        renderAnalyzerDryRunResult(data);
        
    } catch (error) {
        hidePlaygroundLoading('analyzer');
        renderPlaygroundError('analyzer', error.message);
    }
}

function renderAnalyzerPayload(data) {
    const output = document.getElementById('analyzer-playground-output');
    if (!output) return;
    
    const payload = data.payload;
    
    output.innerHTML = `
        <div class="playground-panel">
            <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                <div class="playground-panel-title">
                    <i class="fas fa-cog"></i> Request Details
                </div>
                <i class="fas fa-chevron-down playground-panel-toggle"></i>
            </div>
            <div class="playground-panel-content">
                <p style="font-size: 0.8rem; color: var(--color-muted); margin: 0 0 0.5rem 0;">
                    <strong>Model:</strong> ${payload.model} &nbsp;|&nbsp; 
                    <strong>Temp:</strong> ${payload.temperature} &nbsp;|&nbsp;
                    <strong>Profile:</strong> ${data.profile.version || 'default'}
                </p>
                <p style="font-size: 0.8rem; color: var(--color-muted); margin: 0;">
                    <strong>Workout:</strong> ${payload.workout?.date || 'N/A'} &nbsp;|&nbsp;
                    <strong>Duration:</strong> ${payload.workout?.duration_min || '?'}min &nbsp;|&nbsp;
                    <strong>Power:</strong> ${payload.workout?.avg_power_w || '?'}W
                </p>
            </div>
        </div>
        
        <div class="playground-panel collapsed">
            <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                <div class="playground-panel-title">
                    <i class="fas fa-robot"></i> System Prompt
                </div>
                <i class="fas fa-chevron-down playground-panel-toggle"></i>
            </div>
            <div class="playground-panel-content">
                <pre class="playground-json">${escapeHtml(payload.system_prompt)}</pre>
            </div>
        </div>
        
        <div class="playground-panel collapsed">
            <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                <div class="playground-panel-title">
                    <i class="fas fa-user"></i> User Prompt
                </div>
                <i class="fas fa-chevron-down playground-panel-toggle"></i>
            </div>
            <div class="playground-panel-content">
                <pre class="playground-json">${escapeHtml(payload.user_prompt)}</pre>
            </div>
        </div>
        
        <div class="playground-panel">
            <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                <div class="playground-panel-title">
                    <i class="fas fa-database"></i> Input Data (Analysis Context)
                </div>
                <i class="fas fa-chevron-down playground-panel-toggle"></i>
            </div>
            <div class="playground-panel-content">
                <pre class="playground-json">${JSON.stringify(payload.input_data, null, 2)}</pre>
            </div>
        </div>
    `;
}

function renderAnalyzerDryRunResult(data) {
    const output = document.getElementById('analyzer-playground-output');
    if (!output) return;
    
    const parsed = data.parsed_result;
    const hasError = !!data.error;
    
    let resultHtml = '';
    
    // Error display
    if (hasError) {
        resultHtml += `
            <div class="playground-error">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${escapeHtml(data.error)}</span>
            </div>
        `;
    }
    
    // Parsed result preview (if available)
    if (parsed) {
        const scores = parsed.scores || {};
        const overallScore = scores.overall_score || 0;
        const label = scores.label || 'unknown';
        const labelDisplay = label.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        let scoreClass = 'score-medium';
        if (overallScore >= 80) scoreClass = 'score-good';
        else if (overallScore < 60) scoreClass = 'score-poor';
        
        resultHtml += `
            <div class="playground-preview-card">
                <div class="playground-preview-badge">
                    <i class="fas fa-flask"></i> Preview - Not Saved
                </div>
                <div class="playground-preview-type">${labelDisplay}</div>
                <div class="playground-preview-summary">${escapeHtml(parsed.summary?.short_text || '')}</div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem;">
                    <div class="playground-preview-score ${scoreClass}">
                        <i class="fas fa-chart-line"></i> Score: ${overallScore}
                    </div>
                    <div class="playground-preview-score">
                        <i class="fas fa-fire"></i> Fatigue: ${scores.fatigue_risk || 'N/A'}
                    </div>
                    ${parsed.coach_comparison?.has_coach_plan ? `
                        <div class="playground-preview-score">
                            <i class="fas fa-check-double"></i> Compliance: ${parsed.coach_comparison.compliance_score || '?'}%
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    // Parsed result JSON
    if (parsed) {
        resultHtml += `
            <div class="playground-panel">
                <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                    <div class="playground-panel-title">
                        <i class="fas fa-check-circle" style="color: var(--color-green);"></i> Parsed Result
                    </div>
                    <i class="fas fa-chevron-down playground-panel-toggle"></i>
                </div>
                <div class="playground-panel-content">
                    <pre class="playground-json">${JSON.stringify(parsed, null, 2)}</pre>
                </div>
            </div>
        `;
    }
    
    // Raw response
    if (data.raw_response) {
        resultHtml += `
            <div class="playground-panel collapsed">
                <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                    <div class="playground-panel-title">
                        <i class="fas fa-code"></i> Raw OpenAI Response
                    </div>
                    <i class="fas fa-chevron-down playground-panel-toggle"></i>
                </div>
                <div class="playground-panel-content">
                    <pre class="playground-json">${escapeHtml(data.raw_response)}</pre>
                </div>
            </div>
        `;
    }
    
    // Payload
    if (data.payload) {
        resultHtml += `
            <div class="playground-panel collapsed">
                <div class="playground-panel-header" onclick="togglePlaygroundPanel(this)">
                    <div class="playground-panel-title">
                        <i class="fas fa-paper-plane"></i> Request Payload
                    </div>
                    <i class="fas fa-chevron-down playground-panel-toggle"></i>
                </div>
                <div class="playground-panel-content">
                    <pre class="playground-json">${JSON.stringify(data.payload, null, 2)}</pre>
                </div>
            </div>
        `;
    }
    
    output.innerHTML = resultHtml;
}

// ---- Playground UI Helpers ----

function showPlaygroundLoading(type) {
    const loading = document.getElementById(`${type}-playground-loading`);
    if (loading) loading.classList.add('active');
}

function hidePlaygroundLoading(type) {
    const loading = document.getElementById(`${type}-playground-loading`);
    if (loading) loading.classList.remove('active');
}

function renderPlaygroundError(type, message) {
    const output = document.getElementById(`${type}-playground-output`);
    if (!output) return;
    
    output.innerHTML = `
        <div class="playground-error">
            <i class="fas fa-exclamation-triangle"></i>
            <span>${escapeHtml(message)}</span>
        </div>
    `;
}

function togglePlaygroundPanel(header) {
    const panel = header.closest('.playground-panel');
    if (panel) {
        panel.classList.toggle('collapsed');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ============== Event Listeners ==============

document.addEventListener('DOMContentLoaded', function() {
    // Add character count listeners for system prompts
    ['coach', 'analyzer'].forEach(type => {
        const textarea = document.getElementById(`${type}-system-prompt`);
        if (textarea) {
            textarea.addEventListener('input', () => updateCharCount(type));
        }
    });
    
    // Add real-time JSON validation for settings
    ['coach', 'analyzer'].forEach(type => {
        const textarea = document.getElementById(`${type}-settings-json`);
        if (textarea) {
            textarea.addEventListener('input', () => {
                const field = textarea.parentElement;
                try {
                    JSON.parse(textarea.value || '{}');
                    field.classList.remove('has-error');
                } catch (e) {
                    // Don't show error while typing, only clear it when valid
                }
            });
            
            textarea.addEventListener('blur', () => {
                const field = textarea.parentElement;
                const errorEl = document.getElementById(`${type}-settings-json-error`);
                try {
                    JSON.parse(textarea.value || '{}');
                    field.classList.remove('has-error');
                } catch (e) {
                    field.classList.add('has-error');
                    if (errorEl) errorEl.textContent = `Invalid JSON: ${e.message}`;
                }
            });
        }
    });
    
    // Set default date for coach playground to today if not set
    const coachDateInput = document.getElementById('coach-playground-date');
    if (coachDateInput && !coachDateInput.value) {
        coachDateInput.value = new Date().toISOString().split('T')[0];
    }
});

