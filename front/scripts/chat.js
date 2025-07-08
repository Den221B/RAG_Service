document.addEventListener('DOMContentLoaded', () => {
  // Load config from external config.js
  const config = window.APP_CONFIG || {
    API_URL: 'http://local_ip:8001/api/stream',
    STORAGE_KEY: 'chatHistory',
    MAX_HISTORY_ITEMS: 50,
    REQUEST_TIMEOUT: 15000,
    TYPING_DELAY: 500
  };

  const appState = {
    isProcessing: false,
    activeRequest: null,
    draftMessage: ''
  };

  const elements = {
    messageInput: document.getElementById('message'),
    sendButton: document.getElementById('send-button'),
    chatContainer: document.getElementById('chat-messages'),
    inputWrapper: document.querySelector('.input-wrapper') || document.createElement('div')
  };

  if (!elements.messageInput || !elements.sendButton || !elements.chatContainer) {
    console.error('Critical DOM elements missing!');
    return;
  }

  const templates = {
    welcome: `
      <div class="welcome-message">
        <div class="welcome-text">How can I help you?<br>I am your personal assistant.</div>
      </div>
    `,
    typingIndicator: `
      <div class="typing-indicator">
        <div class="typing-dots">
          <span class="dot" style="animation-delay: 0s"></span>
          <span class="dot" style="animation-delay: 0.2s"></span>
          <span class="dot" style="animation-delay: 0.4s"></span>
        </div>
        <div class="typing-text">thinking<span class="typing-cursor"></span></div>
      </div>
    `,
    messageContainer: (content, isUser, timestamp) => `
      <div class="message-container ${isUser ? 'user-message' : 'server-message'}">
        <div class="${isUser ? 'user-icon' : 'server-icon'}">
          ${isUser ? '' : '<img src="img/server.svg" alt="AI" width="24" height="24">'}
        </div>
        <div class="message-content ${isUser ? 'message-user' : 'message-server'}">
          <div class="message-text">${content}</div>
          <div class="message-timestamp">${timestamp}</div>
        </div>
      </div>
    `,
    tooltip: (text) => `
      <div class="input-tooltip">${text}</div>
    `
  };

  function initialize() {
    setupEventListeners();
    loadChatHistory();
    elements.messageInput.focus();
    updateUIState();
  }

  function setupEventListeners() {
    elements.messageInput.addEventListener('input', handleInput);
    elements.messageInput.addEventListener('keydown', handleKeyDown);
    elements.sendButton.addEventListener('click', handleSendMessage);
  }

  function handleInput() {
    adjustTextareaHeight(this);
    updateUIState();
    if (appState.isProcessing) {
      appState.draftMessage = this.value;
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey && !elements.sendButton.disabled) {
      e.preventDefault();
      handleSendMessage();
    }
  }

  async function handleSendMessage() {
    if (appState.isProcessing) {
      showTooltip("Please wait for the previous response.");
      return;
    }

    const messageText = elements.messageInput.value.trim();
    if (!messageText) return;

    const currentDraft = elements.messageInput.value;

    addUserMessage(messageText);
    resetInput();

    appState.draftMessage = '';
    await processAIRequest(messageText);

    if (appState.draftMessage === '' && currentDraft !== messageText) {
      elements.messageInput.value = currentDraft;
      adjustTextareaHeight(elements.messageInput);
    }

    updateUIState();
  }

  function showTooltip(text) {
    const oldTooltip = elements.inputWrapper.querySelector('.input-tooltip');
    if (oldTooltip) oldTooltip.remove();

    const tooltip = document.createElement('div');
    tooltip.className = 'input-tooltip';
    tooltip.innerHTML = text;
    elements.inputWrapper.appendChild(tooltip);

    setTimeout(() => {
      tooltip.classList.add('fade-out');
      setTimeout(() => tooltip.remove(), 300);
    }, 2000);
  }

  function updateUIState() {
    const hasText = elements.messageInput.value.trim() !== '';
    elements.sendButton.disabled = !hasText || appState.isProcessing;

    if (appState.isProcessing) {
      elements.inputWrapper.classList.add('processing');
      elements.messageInput.placeholder = "You can keep typing...";
    } else {
      elements.inputWrapper.classList.remove('processing');
      elements.messageInput.placeholder = "Type your message...";
    }
  }

  function addUserMessage(text) {
    addMessage({ content: text, isUser: true, timestamp: new Date() });
  }

  async function processAIRequest(message) {
    appState.isProcessing = true;
    updateUIState();

    const tempMessageId = createTempMessage();

    try {
      const controller = new AbortController();
      appState.activeRequest = controller;

      const timeout = setTimeout(() => controller.abort(), config.REQUEST_TIMEOUT);

      const response = await fetch(config.API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          client_timestamp: new Date().toISOString(),
          stream: true
        }),
        signal: controller.signal
      });

      clearTimeout(timeout);

      if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

      await processResponseStream(response, tempMessageId);
    } catch (error) {
      handleAPIError(error, tempMessageId);
    } finally {
      appState.isProcessing = false;
      appState.activeRequest = null;
      updateUIState();
    }
  }

  async function processResponseStream(response, tempId) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';
    const responseElement = document.querySelector(`#${tempId} .message-text`);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      fullResponse += chunk;
      if (responseElement) {
        responseElement.innerHTML = formatMessageContent(fullResponse);
        scrollToBottom();
      }
    }

    finalizeMessage(tempId, fullResponse);
  }

  function formatMessageContent(text) {
    return text
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>');
  }

  function createTempMessage() {
    const messageId = `temp-${Date.now()}`;
    const messageHTML = templates.messageContainer(
      templates.typingIndicator,
      false,
      new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    );

    const messageElement = document.createElement('div');
    messageElement.id = messageId;
    messageElement.innerHTML = messageHTML;
    elements.chatContainer.appendChild(messageElement);
    scrollToBottom();
    animateTypingCursor(messageElement);

    return messageId;
  }

  function animateTypingCursor(element) {
    const cursor = element.querySelector('.typing-cursor');
    if (!cursor) return;

    let isVisible = true;
    const intervalId = setInterval(() => {
      isVisible = !isVisible;
      cursor.style.opacity = isVisible ? '1' : '0';
    }, config.TYPING_DELAY);

    element.dataset.intervalId = intervalId;
  }

  function finalizeMessage(tempId, content) {
    const tempElement = document.getElementById(tempId);
    if (!tempElement) return;

    if (tempElement.dataset.intervalId) {
      clearInterval(parseInt(tempElement.dataset.intervalId));
    }

    tempElement.outerHTML = templates.messageContainer(
      formatMessageContent(content),
      false,
      new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    );

    scrollToBottom();
    saveToHistory(content, false);
  }

  function handleAPIError(error, tempId) {
    console.error('API request failed:', error);
    addMessage({
      content: `Error: ${error.message || 'Unable to get response'}`,
      isUser: false,
      timestamp: new Date()
    });
  }

  function addMessage({ content, isUser, timestamp }) {
    removeWelcomeMessage();

    const messageHTML = templates.messageContainer(
      isUser ? content : formatMessageContent(content),
      isUser,
      timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    );

    const messageElement = document.createElement('div');
    messageElement.innerHTML = messageHTML;
    elements.chatContainer.appendChild(messageElement);
    scrollToBottom();

    if (!isUser) {
      saveToHistory(content, isUser);
    }
  }

  function saveToHistory(content, isUser) {
    try {
      const history = loadHistory();
      history.push({
        content,
        isUser,
        timestamp: new Date().toISOString()
      });

      if (history.length > config.MAX_HISTORY_ITEMS) {
        history.shift();
      }

      localStorage.setItem(config.STORAGE_KEY, JSON.stringify(history));
    } catch (error) {
      console.error('Failed to save history:', error);
    }
  }

  function loadChatHistory() {
    elements.chatContainer.innerHTML = templates.welcome;
  }

  function loadHistory() {
    const data = localStorage.getItem(config.STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  }

  function clearChatHistory() {
    localStorage.removeItem(config.STORAGE_KEY);
    elements.chatContainer.innerHTML = templates.welcome;
  }

  function resetInput() {
    elements.messageInput.value = '';
    elements.messageInput.style.height = 'auto';
    updateUIState();
  }

  function adjustTextareaHeight(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = `${textarea.scrollHeight}px`;
  }

  function removeWelcomeMessage() {
    const welcome = elements.chatContainer.querySelector('.welcome-message');
    if (welcome) {
      welcome.style.opacity = '0';
      setTimeout(() => welcome.remove(), 300);
    }
  }

  function scrollToBottom() {
    setTimeout(() => {
      elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    }, 10);
  }

  // Start app
  initialize();
});
