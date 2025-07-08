// Theme toggle functionality
const themeToggle = document.getElementById('theme-toggle');
const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
const logo = document.getElementById('site-logo');

// Check stored theme preference or system setting
const currentTheme = localStorage.getItem('theme');

if (currentTheme === 'dark' || (!currentTheme && prefersDarkScheme.matches)) {
  document.documentElement.classList.add('dark-theme');
  if (logo) logo.src = 'img/logo-dark.svg'; // Use dark logo
}

// Toggle theme on button click
if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const htmlElement = document.documentElement;
    const isDark = htmlElement.classList.contains('dark-theme');

    htmlElement.classList.toggle('dark-theme');
    localStorage.setItem('theme', isDark ? 'light' : 'dark');

    if (logo) {
      logo.src = isDark ? 'img/logo.svg' : 'img/logo-dark.svg'; // Update logo based on theme
    }
  });
}
