// Apply the saved theme before Angular boots to avoid a flash of the wrong colors.
// A file and not an inline script, so the Content-Security-Policy can forbid inline scripts.
try {
  var theme = localStorage.getItem('theme');
  if (theme === 'light' || theme === 'dark') {
    document.documentElement.style.colorScheme = theme;
  }
} catch (e) {}
