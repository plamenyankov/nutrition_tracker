/**
 * AI Lab - Prompt Management UI
 * 
 * Handles CRUD operations for AI profiles (Coach and Analyzer).
 * Provides UI for editing prompts, settings, and switching active profiles.
 */

// ============== State ==============

let currentEditingProfile = null;
let currentTab = 'coach';

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
});

