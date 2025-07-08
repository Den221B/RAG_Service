document.addEventListener('DOMContentLoaded', () => {
  const helpBtn = document.querySelector('.help-btn');
  const helpPopup = document.getElementById('help-popup');
  const closeHelpBtn = document.getElementById('close-help');

  if (!helpBtn || !helpPopup || !closeHelpBtn) return;

  // Show the help popup
  helpBtn.addEventListener('click', () => {
    helpPopup.style.display = 'flex';
  });

  // Close the help popup
  closeHelpBtn.addEventListener('click', () => {
    helpPopup.style.display = 'none';
  });

  // Close popup if clicked outside the content area
  helpPopup.addEventListener('click', (e) => {
    if (e.target === helpPopup) {
      helpPopup.style.display = 'none';
    }
  });
});
