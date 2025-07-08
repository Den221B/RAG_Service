// Constants
const CHAT_HISTORY_KEY = 'chatHistory';
const welcomeHTML = `
  <div class="welcome-message">
    <div class="welcome-text">How can I help you?<br>I’m your personal assistant</div>
  </div>
`;

// Clear chat history
function clearChatHistory() {
  localStorage.removeItem(CHAT_HISTORY_KEY);

  const chatMessages = document.getElementById('chat-messages');
  if (chatMessages) {
    chatMessages.innerHTML = welcomeHTML;
  }

  const messageInput = document.getElementById('message');
  if (messageInput) {
    messageInput.value = '';
    messageInput.style.height = 'auto';
  }

  const sendButton = document.getElementById('send-button');
  if (sendButton) {
    sendButton.disabled = true;
  }

  showNotification("Chat history cleared successfully");
}

// Display notification
function showNotification(message) {
  const notification = document.createElement('div');
  notification.className = 'notification';
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => notification.classList.add('show'), 10);
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const clearHistoryBtn = document.getElementById('clear-history');
  const confirmationDialog = document.getElementById('clear-confirmation');
  const confirmClearBtn = document.getElementById('confirm-clear');
  const cancelClearBtn = document.getElementById('cancel-clear');

  // Safety check
  if (!clearHistoryBtn || !confirmationDialog || !confirmClearBtn || !cancelClearBtn) {
    console.error('Clear chat elements not found!');
    return;
  }

  // Show confirmation dialog
  clearHistoryBtn.addEventListener('click', () => {
    confirmationDialog.style.display = 'flex';
  });

  // Cancel button
  cancelClearBtn.addEventListener('click', () => {
    confirmationDialog.style.display = 'none';
  });

  // Confirm clear
  confirmClearBtn.addEventListener('click', () => {
    clearChatHistory();
    confirmationDialog.style.display = 'none';
  });

  // Show welcome message if empty
  const chatMessages = document.getElementById('chat-messages');
  if (chatMessages && chatMessages.children.length === 0) {
    chatMessages.innerHTML = welcomeHTML;
  }
});
