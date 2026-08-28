/* Calibre-Web UI Phase-0: Alpine store + shell interactivity
 * 依赖 Alpine（alpine.min.js）与 theme.js（window.calibreTheme）。
 * P2 (App Shell) 将在此之上搭建 sidebar/header/drawer。
 */
document.addEventListener('alpine:init', function () {
  Alpine.store('ui', {
    dark: window.calibreTheme ? window.calibreTheme.get() === 'dark' : false,
    sidebarOpen: false,
    toggleDark() {
      if (!window.calibreTheme) return;
      const next = this.dark ? 'light' : 'dark';
      window.calibreTheme.set(next);
      this.dark = next === 'dark';
    },
    openSidebar() { this.sidebarOpen = true; },
    closeSidebar() { this.sidebarOpen = false; },
  });
});
