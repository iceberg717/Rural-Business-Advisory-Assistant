/**
 * RuralBiz Advisor — Frontend Chat Controller
 * Connects the interactive chat UI with the FastAPI /api/chat backend.
 * Handles missing-information popovers and 1-click Taluka selection.
 */

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    if (!chatForm) return; // Exit cleanly on non-chat pages

    const chatInput = document.getElementById('chat-input');
    const messageList = document.getElementById('message-list');
    const chatStatus = document.getElementById('chat-status');
    const emptyPlaceholder = document.getElementById('empty-chat-placeholder');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    const sendButton = document.getElementById('btn-chat-send');
    
    // Popup & Location Picker Elements
    const promptPopup = document.getElementById('prompt-popup-container');
    const btnLocationPicker = document.getElementById('btn-location-picker');
    const btnClosePopup = document.getElementById('btn-close-popup');
    const popupBusinessName = document.getElementById('popup-business-name');
    const popupTalukaChips = document.querySelectorAll('.taluka-pill-btn');

    // Budget Popup Elements
    const btnBudgetPicker = document.getElementById('btn-budget-picker');
    const btnCloseBudgetPopup = document.getElementById('btn-close-budget-popup');
    const popupTalukaPanel = document.getElementById('popup-taluka-panel');
    const popupBudgetPanel = document.getElementById('popup-budget-panel');
    const popupBudgetChips = document.querySelectorAll('.budget-pill-btn');
    const customBudgetInput = document.getElementById('custom-budget-input');
    const btnSubmitCustomBudget = document.getElementById('btn-submit-custom-budget');
    const budgetBtnLabel = document.getElementById('budget-btn-label');

    // State tracking for partial inquiries
    let pendingBusinessIdea = "";
    let selectedTaluka = "";
    let selectedInvestment = "";  // e.g. "₹5 Lakhs" or "₹2,50,000"

    // Get API endpoint from data-send-url or fallback to /api/chat
    const apiEndpoint = (chatForm && chatForm.getAttribute('data-send-url')) || '/api/chat';

    /**
     * Converts basic markdown syntax to clean HTML
     */
    function formatMarkdown(text) {
        if (!text) return '';
        
        let html = text
            // Escape existing raw HTML tags to prevent XSS
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Headers
        html = html.replace(/^### (.*$)/gim, '<h4 class="md-h4">$1</h4>');
        html = html.replace(/^## (.*$)/gim, '<h3 class="md-h3">$1</h3>');
        html = html.replace(/^# (.*$)/gim, '<h2 class="md-h2">$1</h2>');

        // Bold & Italic
        html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
        html = html.replace(/`(.*?)`/gim, '<code>$1</code>');

        // Bullet lists
        const lines = html.split('\n');
        let inList = false;
        let formattedLines = [];

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();
            if (line.startsWith('- ') || line.startsWith('* ')) {
                if (!inList) {
                    formattedLines.push('<ul class="md-list">');
                    inList = true;
                }
                formattedLines.push(`<li>${line.substring(2)}</li>`);
            } else {
                if (inList) {
                    formattedLines.push('</ul>');
                    inList = false;
                }
                if (line.length > 0) {
                    // Check if it's already a header or block element
                    if (line.startsWith('<h') || line.startsWith('<ul') || line.startsWith('<li')) {
                        formattedLines.push(line);
                    } else {
                        formattedLines.push(`<p class="md-p">${line}</p>`);
                    }
                }
            }
        }
        if (inList) {
            formattedLines.push('</ul>');
        }

        return formattedLines.join('\n');
    }

    /**
     * Scroll message list to bottom smoothly
     */
    function scrollToBottom() {
        if (messageList) {
            messageList.scrollTo({
                top: messageList.scrollHeight,
                behavior: 'smooth'
            });
        }
    }

    /**
     * Shows the floating prompt popover for Taluka selection
     */
    function showLocationPopup(businessName = "") {
        if (!promptPopup) return;
        
        // Switch to taluka panel
        if (popupTalukaPanel) popupTalukaPanel.style.display = 'block';
        if (popupBudgetPanel) popupBudgetPanel.style.display = 'none';
        promptPopup.setAttribute('data-mode', 'taluka');
        
        const displayIdea = businessName || pendingBusinessIdea || (chatInput ? chatInput.value.trim() : "") || "Your Business Idea";
        if (popupBusinessName) {
            popupBusinessName.textContent = displayIdea;
        }
        
        promptPopup.style.display = 'block';
        promptPopup.classList.add('popup-animate-in');
        
        if (btnLocationPicker) btnLocationPicker.classList.add('active');
        if (btnBudgetPicker) btnBudgetPicker.classList.remove('active');
    }

    /**
     * Shows the floating prompt popover for Budget selection
     */
    function showBudgetPopup(businessName = "") {
        if (!promptPopup) return;
        
        // Switch to budget panel
        if (popupTalukaPanel) popupTalukaPanel.style.display = 'none';
        if (popupBudgetPanel) popupBudgetPanel.style.display = 'block';
        promptPopup.setAttribute('data-mode', 'budget');
        
        const displayIdea = businessName || pendingBusinessIdea || (chatInput ? chatInput.value.trim() : "") || "Your Venture";
        const budgetBusinessEl = document.getElementById('popup-budget-business-name');
        if (budgetBusinessEl) budgetBusinessEl.textContent = displayIdea;
        
        promptPopup.style.display = 'block';
        promptPopup.classList.add('popup-animate-in');
        
        if (btnBudgetPicker) btnBudgetPicker.classList.add('active');
        if (btnLocationPicker) btnLocationPicker.classList.remove('active');
    }

    /**
     * Hides the floating prompt popover
     */
    function hideLocationPopup() {
        if (!promptPopup) return;
        promptPopup.style.display = 'none';
        promptPopup.classList.remove('popup-animate-in');
        
        if (btnLocationPicker) btnLocationPicker.classList.remove('active');
        if (btnBudgetPicker) btnBudgetPicker.classList.remove('active');
    }

    /**
     * Append a message bubble to the chat panel
     */
    function appendMessage(role, content, isHtml = false) {
        if (emptyPlaceholder) {
            emptyPlaceholder.style.display = 'none';
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const label = document.createElement('span');
        label.className = 'message-label';
        label.textContent = role === 'user' ? 'You' : 'Advisor';
        messageDiv.appendChild(label);

        const body = document.createElement('div');
        body.className = 'message-body';

        if (isHtml) {
            body.innerHTML = content;
        } else {
            body.innerHTML = formatMarkdown(content);
        }

        messageDiv.appendChild(body);
        messageList.appendChild(messageDiv);
        scrollToBottom();
        return messageDiv;
    }

    /**
     * Renders an interactive prompt card when location or details are missing
     */
    function renderInteractiveChoiceMessage(data) {
        if (emptyPlaceholder) {
            emptyPlaceholder.style.display = 'none';
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant interactive-prompt-message';

        const label = document.createElement('span');
        label.className = 'message-label';
        label.textContent = 'Advisor';
        messageDiv.appendChild(label);

        const body = document.createElement('div');
        body.className = 'message-body';

        if (data.missing_field === 'taluka') {
            const ideaTitle = data.business_type || pendingBusinessIdea || "Your Business Idea";
            const talukas = data.available_talukas || [
                "Becharaji", "Kadi", "Kheralu", "Mahesana", "Satlasana", "Unjha", "Vadnagar", "Vijapur", "Visnagar"
            ];

            let chipsHtml = talukas.map(t => `
                <button type="button" class="interactive-taluka-btn" data-taluka="${t}">
                    <span class="btn-pin">📍</span>
                    <span class="btn-name">${t}</span>
                </button>
            `).join('');

            body.innerHTML = `
                <div class="interactive-card">
                    <div class="interactive-card-header">
                        <div class="pin-badge">📍</div>
                        <div>
                            <h4 class="card-title">Select Target Taluka</h4>
                            <p class="card-subtitle">For your <strong>${ideaTitle}</strong> venture in Mehsana district:</p>
                        </div>
                    </div>
                    <div class="interactive-buttons-grid">
                        ${chipsHtml}
                    </div>
                    <div class="interactive-card-footer">
                        <small>💡 <em>Tip: Click any taluka above or select via the 📍 button in the input bar to generate analysis.</em></small>
                    </div>
                </div>
            `;
        } else if (data.missing_field === 'business_type') {
            const talukaName = data.taluka || "Mehsana";
            const categories = data.suggested_categories || [
                "Dairy & Milk Processing", "Textile & Garments", "Spice Processing & Trading", "Retail & Kirana Store", "Engineering & Machinery"
            ];

            let catChipsHtml = categories.map(c => `
                <button type="button" class="interactive-category-btn" data-category="${c}" data-taluka="${talukaName}">
                    <span>💼</span>
                    <span>${c}</span>
                </button>
            `).join('');

            body.innerHTML = `
                <div class="interactive-card">
                    <div class="interactive-card-header">
                        <div class="pin-badge">🏢</div>
                        <div>
                            <h4 class="card-title">Business Idea Needed</h4>
                            <p class="card-subtitle">What type of business are you planning in <strong>${talukaName} Taluka</strong>?</p>
                        </div>
                    </div>
                    <div class="interactive-buttons-grid">
                        ${catChipsHtml}
                    </div>
                </div>
            `;
        } else if (data.missing_field === 'investment') {
            const ideaTitle = data.business_type || pendingBusinessIdea || "Your Business Idea";
            const talukaName = data.taluka || selectedTaluka || "Mehsana";

            let budgetChipsHtml = [
                { amount: 75000, formatted: '₹75,000', icon: '🌱', label: 'Micro', range: '< ₹1 Lakh' },
                { amount: 200000, formatted: '₹2 Lakhs', icon: '🏪', label: 'Small Unit', range: '₹1 – 3 Lakhs' },
                { amount: 400000, formatted: '₹4 Lakhs', icon: '📋', label: 'PMEGP Micro', range: '₹3 – 5 Lakhs' },
                { amount: 750000, formatted: '₹7.5 Lakhs', icon: '🏦', label: 'Mudra Tarun', range: '₹5 – 10 Lakhs' },
                { amount: 1500000, formatted: '₹15 Lakhs', icon: '🏭', label: 'Medium MSME', range: '₹10 – 25 Lakhs' },
                { amount: 3500000, formatted: '₹35 Lakhs', icon: '🏗️', label: 'Commercial', range: '₹25+ Lakhs' }
            ].map(p => `
                <button type="button" class="interactive-budget-btn"
                    data-amount="${p.amount}" data-formatted="${p.formatted}"
                    data-business="${ideaTitle}" data-taluka="${talukaName}">
                    <span class="budget-pill-icon">${p.icon}</span>
                    <span class="budget-pill-label">${p.label}</span>
                    <span class="budget-pill-range">${p.range}</span>
                </button>
            `).join('');

            body.innerHTML = `
                <div class="interactive-card budget-info-card">
                    <div class="interactive-card-header">
                        <div class="pin-badge" style="background: rgba(255,193,7,0.15); color: #f59e0b;">💰</div>
                        <div>
                            <h4 class="card-title">Investment Budget Required</h4>
                            <p class="card-subtitle">What is your planned investment for <strong>${ideaTitle}</strong> in <strong>${talukaName} Taluka</strong>?</p>
                        </div>
                    </div>
                    <div class="interactive-buttons-grid budget-interactive-grid">
                        ${budgetChipsHtml}
                    </div>
                    <div class="custom-budget-row in-chat-budget-row">
                        <span class="custom-budget-rupee">₹</span>
                        <input type="text" class="custom-budget-input in-chat-budget-input"
                            placeholder="Custom amount: e.g. 2.5 lakhs, 80k, 120000"
                            data-business="${ideaTitle}" data-taluka="${talukaName}" />
                        <button type="button" class="custom-budget-submit in-chat-budget-submit">Analyse →</button>
                    </div>
                    <div class="interactive-card-footer">
                        <small>💡 <em>Your budget determines PMEGP subsidy eligibility and which local alternatives are recommended.</em></small>
                    </div>
                </div>
            `;
        } else {
            body.innerHTML = formatMarkdown(data.reply || "Please provide your business idea and target location.");
        }

        messageDiv.appendChild(body);
        messageList.appendChild(messageDiv);

        // Attach listeners to interactive budget buttons
        messageDiv.querySelectorAll('.interactive-budget-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const formatted = btn.getAttribute('data-formatted');
                const idea = btn.getAttribute('data-business') || pendingBusinessIdea || "Business";
                const taluka = btn.getAttribute('data-taluka') || selectedTaluka;
                selectedInvestment = formatted;
                updateBudgetButtonLabel(formatted);
                hideLocationPopup();
                handleSendMessage(`${idea} in ${taluka} with ${formatted} budget`, taluka, formatted);
            });
        });

        // In-chat custom budget submit
        const inChatCustomInput = messageDiv.querySelector('.in-chat-budget-input');
        const inChatCustomSubmit = messageDiv.querySelector('.in-chat-budget-submit');
        if (inChatCustomSubmit && inChatCustomInput) {
            inChatCustomSubmit.addEventListener('click', () => {
                const customVal = inChatCustomInput.value.trim();
                if (!customVal) return;
                const idea = inChatCustomInput.getAttribute('data-business') || pendingBusinessIdea || "Business";
                const taluka = inChatCustomInput.getAttribute('data-taluka') || selectedTaluka;
                selectedInvestment = customVal;
                updateBudgetButtonLabel(customVal);
                hideLocationPopup();
                handleSendMessage(`${idea} in ${taluka} with ${customVal} budget`, taluka, customVal);
            });
            inChatCustomInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') inChatCustomSubmit.click();
            });
        }

        // Attach listeners to taluka buttons
        messageDiv.querySelectorAll('.interactive-taluka-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const chosenTaluka = btn.getAttribute('data-taluka');
                const idea = data.business_type || pendingBusinessIdea || "Business";
                hideLocationPopup();
                handleSendMessage(`${idea} in ${chosenTaluka}`, chosenTaluka);
            });
        });

        messageDiv.querySelectorAll('.interactive-category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const chosenCategory = btn.getAttribute('data-category');
                const chosenTaluka = btn.getAttribute('data-taluka');
                hideLocationPopup();
                handleSendMessage(`${chosenCategory} in ${chosenTaluka}`, chosenTaluka);
            });
        });

        scrollToBottom();
        return messageDiv;
    }

    /**
     * Append temporary typing / thinking indicator
     */
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant typing-indicator-bubble';
        typingDiv.id = 'typing-indicator';

        const label = document.createElement('span');
        label.className = 'message-label';
        label.textContent = 'Advisor';
        typingDiv.appendChild(label);

        const body = document.createElement('div');
        body.className = 'message-body';
        body.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; font-style: italic; color: var(--muted);">
                <span class="spinner" style="display: inline-block; width: 14px; height: 14px; border: 2px solid var(--green); border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></span>
                Analyzing MSME records, loan subsidies, and local market data...
            </div>
        `;
        typingDiv.appendChild(body);
        messageList.appendChild(typingDiv);
        scrollToBottom();
    }

    /**
     * Remove typing indicator
     */
    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Send user message to FastAPI backend
     */
    async function handleSendMessage(messageText, overrideTaluka = null, overrideInvestment = null) {
        const text = messageText.trim();
        if (!text) return;

        // Render user message immediately
        appendMessage('user', text);

        // Clear input and disable submit button
        if (chatInput) chatInput.value = '';
        if (sendButton) sendButton.disabled = true;

        // Show thinking indicator
        showTypingIndicator();
        if (chatStatus) {
            chatStatus.textContent = 'Contacting RuralBiz Advisory engine...';
            chatStatus.style.display = 'block';
        }

        // Determine final taluka and investment to send
        const talukaToSend = overrideTaluka || selectedTaluka || null;
        const investmentToSend = overrideInvestment || selectedInvestment || null;

        try {
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ 
                    message: text,
                    taluka: talukaToSend,
                    investment: investmentToSend
                })
            });

            hideTypingIndicator();
            if (chatStatus) chatStatus.style.display = 'none';

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const detailMsg = errorData.detail || `Server returned HTTP ${response.status}`;
                appendMessage('assistant', `⚠️ **Advisory Notice:** ${detailMsg}\n\nPlease verify your request and try again.`);
                return;
            }

            const data = await response.json();

            // Check if backend reports missing location / info
            if (data.status === 'needs_info') {
                if (data.missing_field === 'taluka') {
                    pendingBusinessIdea = data.business_type || text;
                    showLocationPopup(data.business_type);
                } else if (data.missing_field === 'business_type') {
                    selectedTaluka = data.taluka || "";
                } else if (data.missing_field === 'investment') {
                    pendingBusinessIdea = data.business_type || pendingBusinessIdea || text;
                    selectedTaluka = data.taluka || selectedTaluka || "";
                    showBudgetPopup(data.business_type || pendingBusinessIdea);
                }
                renderInteractiveChoiceMessage(data);
            } else {
                // Successful complete report received
                pendingBusinessIdea = "";
                hideLocationPopup();
                const reply = data.reply || data.response || "No response received from advisory assistant.";
                appendMessage('assistant', reply);
            }

        } catch (error) {
            console.error('Chat API Error:', error);
            hideTypingIndicator();
            if (chatStatus) chatStatus.style.display = 'none';
            appendMessage('assistant', '⚠️ **Connection Error:** Could not reach the advisory server. Please ensure the backend server is running and try again.');
        } finally {
            if (sendButton) sendButton.disabled = false;
            if (chatInput) chatInput.focus();
        }
    }

    /**
     * Updates the 💰 Budget button label to reflect the selected budget
     */
    function updateBudgetButtonLabel(budgetLabel) {
        if (budgetBtnLabel) {
            budgetBtnLabel.textContent = budgetLabel.length > 10 ? budgetLabel.substring(0, 10) + '…' : budgetLabel;
        }
        if (btnBudgetPicker) {
            btnBudgetPicker.classList.add('active');
        }
    }

    // Form submit listener
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = chatInput ? chatInput.value : '';
            handleSendMessage(message);
        });
    }

    // Prompt Bar Location Icon Toggle Listener
    if (btnLocationPicker) {
        btnLocationPicker.addEventListener('click', (e) => {
            e.preventDefault();
            const currentMode = promptPopup ? promptPopup.getAttribute('data-mode') : 'taluka';
            if (promptPopup && promptPopup.style.display === 'block' && currentMode === 'taluka') {
                hideLocationPopup();
            } else {
                const currentInput = chatInput ? chatInput.value.trim() : "";
                showLocationPopup(currentInput || pendingBusinessIdea);
            }
        });
    }

    // Prompt Bar Budget Icon Toggle Listener
    if (btnBudgetPicker) {
        btnBudgetPicker.addEventListener('click', (e) => {
            e.preventDefault();
            const currentMode = promptPopup ? promptPopup.getAttribute('data-mode') : 'taluka';
            if (promptPopup && promptPopup.style.display === 'block' && currentMode === 'budget') {
                hideLocationPopup();
            } else {
                const currentInput = chatInput ? chatInput.value.trim() : "";
                showBudgetPopup(currentInput || pendingBusinessIdea);
            }
        });
    }

    // Popup Close Button Listeners
    if (btnClosePopup) {
        btnClosePopup.addEventListener('click', () => hideLocationPopup());
    }
    if (btnCloseBudgetPopup) {
        btnCloseBudgetPopup.addEventListener('click', () => hideLocationPopup());
    }

    // Popup Taluka Chip Buttons Click Listener
    popupTalukaChips.forEach(btn => {
        btn.addEventListener('click', () => {
            const taluka = btn.getAttribute('data-taluka');
            const currentIdea = pendingBusinessIdea || (chatInput ? chatInput.value.trim() : "") || "Business opportunities";
            hideLocationPopup();
            handleSendMessage(`${currentIdea} in ${taluka}`, taluka);
        });
    });

    // Popup Budget Chip Buttons Click Listener
    popupBudgetChips.forEach(btn => {
        btn.addEventListener('click', () => {
            const formatted = btn.getAttribute('data-formatted');
            const currentIdea = pendingBusinessIdea || (chatInput ? chatInput.value.trim() : "") || "Business";
            const taluka = selectedTaluka || "";
            selectedInvestment = formatted;
            updateBudgetButtonLabel(formatted);
            hideLocationPopup();
            if (currentIdea && taluka) {
                handleSendMessage(`${currentIdea} in ${taluka} with ${formatted} budget`, taluka, formatted);
            } else if (chatInput) {
                chatInput.value = chatInput.value.trim() + (chatInput.value.trim() ? ` with ${formatted} budget` : `${formatted} budget`);
                chatInput.focus();
            }
        });
    });

    // Popup Custom Budget Submit
    if (btnSubmitCustomBudget && customBudgetInput) {
        btnSubmitCustomBudget.addEventListener('click', () => {
            const customVal = customBudgetInput.value.trim();
            if (!customVal) return;
            const currentIdea = pendingBusinessIdea || (chatInput ? chatInput.value.trim() : "") || "Business";
            const taluka = selectedTaluka || "";
            selectedInvestment = customVal;
            updateBudgetButtonLabel(customVal);
            hideLocationPopup();
            customBudgetInput.value = '';
            if (currentIdea && taluka) {
                handleSendMessage(`${currentIdea} in ${taluka} with ${customVal} budget`, taluka, customVal);
            } else if (chatInput) {
                chatInput.value = chatInput.value.trim() + (chatInput.value.trim() ? ` with ${customVal} budget` : `${customVal} budget`);
                chatInput.focus();
            }
        });
        customBudgetInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') btnSubmitCustomBudget.click();
        });
    }

    // Suggestion chip click listeners
    suggestionChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.getAttribute('data-query');
            if (query) {
                if (chatInput) chatInput.value = query;
                handleSendMessage(query);
            }
        });
    });

    // Check URL search params for preloaded prompt (e.g. ?prompt=...)
    const urlParams = new URLSearchParams(window.location.search);
    const initialPrompt = urlParams.get('prompt');
    if (initialPrompt) {
        if (chatInput) chatInput.value = initialPrompt;
        handleSendMessage(initialPrompt);
    }
});

// CSS styles for popup popovers, interactive cards, budget chips, and micro-animations
const styleEl = document.createElement('style');
styleEl.textContent = `
@keyframes spin {
    to { transform: rotate(360deg); }
}

@keyframes popupSlideUp {
    from {
        opacity: 0;
        transform: translateY(12px) scale(0.98);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

.popup-animate-in {
    animation: popupSlideUp 0.24s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* Floating Prompt Popover */
.prompt-popup-card {
    background: var(--popup-bg);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1.5px solid var(--green);
    border-radius: 14px;
    box-shadow: var(--shadow);
    padding: 16px 20px;
    margin: 0 16px 14px 16px;
    position: relative;
    z-index: 10;
    transition: background-color 0.25s ease, border-color 0.25s ease;
}

.popup-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.popup-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--ink);
}

.popup-icon {
    font-size: 1.1rem;
}

.highlight-text {
    color: var(--green);
    background: var(--mint);
    padding: 2px 8px;
    border-radius: 6px;
    display: inline-block;
}

.popup-close-btn {
    background: var(--mint);
    border: none;
    border-radius: 50%;
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    color: var(--muted);
    cursor: pointer;
    transition: all 0.2s ease;
}

.popup-close-btn:hover {
    background: rgba(241, 146, 119, 0.25);
    color: var(--coral);
}

.popup-subtext {
    font-size: 0.82rem;
    color: var(--muted);
    margin: 0 0 12px 0;
    line-height: 1.4;
}

.popup-chips-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
    gap: 8px;
}

/* Budget chips grid — wider to fit 3 columns of label+range stacked */
.budget-chips-grid {
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
}

.taluka-pill-btn {
    background: var(--chip-bg);
    border: 1px solid var(--chip-border);
    border-radius: 20px;
    padding: 8px 12px;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--chip-text);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    transition: all 0.2s ease;
}

.taluka-pill-btn:hover {
    background: var(--mint);
    border-color: var(--green);
    color: var(--green-dark);
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
}

/* Budget Pill Buttons (popup & in-chat) */
.budget-pill-btn, .interactive-budget-btn {
    background: var(--chip-bg);
    border: 1px solid var(--chip-border);
    border-radius: 10px;
    padding: 10px 10px 8px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--chip-text);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    text-align: center;
}

.budget-pill-btn:hover, .interactive-budget-btn:hover {
    background: rgba(255, 193, 7, 0.12);
    border-color: #f59e0b;
    color: #b45309;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2);
}

.budget-pill-icon { font-size: 1.2rem; }
.budget-pill-label { font-weight: 700; font-size: 0.80rem; color: var(--ink); }
.budget-pill-range { font-size: 0.72rem; color: var(--muted); }

/* Custom Budget Input Row */
.custom-budget-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    background: var(--chip-bg);
    border: 1px solid var(--chip-border);
    border-radius: 10px;
    padding: 6px 10px;
}

.in-chat-budget-row {
    margin-top: 10px;
}

.custom-budget-rupee {
    font-size: 1rem;
    font-weight: 700;
    color: #f59e0b;
    flex-shrink: 0;
}

.custom-budget-input {
    flex: 1;
    border: none;
    background: transparent;
    font-size: 0.84rem;
    color: var(--ink);
    outline: none;
    font-family: inherit;
}

.custom-budget-input::placeholder {
    color: var(--muted);
    font-style: italic;
}

.custom-budget-submit {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    border: none;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 0.80rem;
    font-weight: 700;
    color: #fff;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    flex-shrink: 0;
}

.custom-budget-submit:hover {
    background: linear-gradient(135deg, #d97706, #b45309);
    transform: scale(1.04);
}

/* Budget interactive grid — 3-col for in-chat cards */
.budget-interactive-grid {
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
}

/* Location Selector Pin Icon in Prompt Bar */
.location-pop-icon {
    background: var(--mint);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 10px 14px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--green-dark);
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
}

.location-pop-icon:hover, .location-pop-icon.active {
    background: var(--green);
    color: #ffffff;
    border-color: var(--green-dark);
    transform: scale(1.03);
    box-shadow: 0 4px 12px rgba(47, 165, 132, 0.25);
}

/* Budget Selector Button in Prompt Bar */
.budget-pop-icon {
    background: rgba(255, 193, 7, 0.10);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 8px;
    padding: 10px 14px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.82rem;
    font-weight: 700;
    color: #b45309;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
}

.budget-pop-icon:hover, .budget-pop-icon.active {
    background: #f59e0b;
    color: #ffffff;
    border-color: #d97706;
    transform: scale(1.03);
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

/* In-Chat Interactive Choice Card */
.interactive-card {
    background: var(--card-bg);
    border: 1.5px solid var(--mint);
    border-radius: 12px;
    padding: 16px;
    box-shadow: var(--shadow);
    margin-top: 4px;
}

.budget-info-card {
    border-color: rgba(245, 158, 11, 0.3);
}

.interactive-card-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
}

.pin-badge {
    background: var(--mint);
    color: var(--green);
    font-size: 1.1rem;
    width: 34px;
    height: 34px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.card-title {
    margin: 0 0 4px 0;
    font-size: 0.96rem;
    color: var(--ink);
    font-weight: 700;
}

.card-subtitle {
    margin: 0;
    font-size: 0.84rem;
    color: var(--muted);
    line-height: 1.4;
}

.interactive-buttons-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(115px, 1fr));
    gap: 8px;
    margin: 12px 0;
}

.interactive-taluka-btn, .interactive-category-btn {
    background: var(--chip-bg);
    border: 1px solid var(--chip-border);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--chip-text);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    justify-content: center;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.interactive-taluka-btn:hover, .interactive-category-btn:hover {
    background: var(--mint);
    border-color: var(--green);
    color: var(--green-dark);
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
}

.interactive-card-footer {
    border-top: 1px dashed var(--line);
    padding-top: 8px;
    margin-top: 8px;
    color: var(--muted);
}

/* General Chat & Markdown Styles */
.suggestion-chip {
    background: var(--chip-bg);
    border: 1px solid var(--chip-border);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--chip-text);
    cursor: pointer;
    transition: all 0.2s ease;
}
.suggestion-chip:hover {
    background: var(--mint);
    border-color: var(--green);
    color: var(--green);
    transform: translateY(-1px);
}
.md-h2, .md-h3, .md-h4 {
    margin: 12px 0 6px 0;
    color: var(--ink);
    font-weight: 700;
}
.md-h2 { font-size: 1.25rem; }
.md-h3 { font-size: 1.1rem; color: var(--green); }
.md-h4 { font-size: 0.98rem; }
.md-p { margin: 6px 0; line-height: 1.5; color: var(--ink); }
.md-list { margin: 6px 0; padding-left: 20px; color: var(--ink); }
.md-list li { margin-bottom: 4px; line-height: 1.45; }
code {
    background: var(--mint);
    color: var(--green);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.9em;
}
.user-badge {
    background: var(--mint);
    color: var(--green);
    font-size: 0.78rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 12px;
}
`;
document.head.appendChild(styleEl);