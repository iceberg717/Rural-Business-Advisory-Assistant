/**
 * RuralBiz Advisor — Frontend Chat Controller
 * Connects the interactive chat UI with the FastAPI /api/chat backend.
 */

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const messageList = document.getElementById('message-list');
    const chatStatus = document.getElementById('chat-status');
    const emptyPlaceholder = document.getElementById('empty-chat-placeholder');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    const sendButton = document.getElementById('btn-chat-send');

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
     * Scroll message list to bottom
     */
    function scrollToBottom() {
        if (messageList) {
            messageList.scrollTop = messageList.scrollHeight;
        }
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
    async function handleSendMessage(messageText) {
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

        try {
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ message: text })
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
            const reply = data.reply || data.response || "No response received from advisory assistant.";
            appendMessage('assistant', reply);

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

    // Form submit listener
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = chatInput ? chatInput.value : '';
            handleSendMessage(message);
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

// CSS animation keyframes for spinner injection
const styleEl = document.createElement('style');
styleEl.textContent = `
@keyframes spin {
    to { transform: rotate(360deg); }
}
.suggestion-chip {
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--ink);
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
.md-p { margin: 6px 0; line-height: 1.5; }
.md-list { margin: 6px 0; padding-left: 20px; }
.md-list li { margin-bottom: 4px; line-height: 1.45; }
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