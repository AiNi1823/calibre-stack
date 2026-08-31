/* Calibre-Web UI Phase-0: Alpine store + shell interactivity
 * 依赖 Alpine（alpine.min.js）与 theme.js（window.calibreTheme）。
 * P2 (App Shell) 将在此之上搭建 sidebar/header/drawer。
 * P11 (A11y)：移动端 Drawer 打开时移动焦点、关闭时回移焦点到触发器。
 */
document.addEventListener('alpine:init', function () {
  Alpine.store('ui', {
    dark: window.calibreTheme ? window.calibreTheme.get() === 'dark' : false,
    sidebarOpen: false,
    _lastFocus: null,
    toggleDark() {
      if (!window.calibreTheme) return;
      const next = this.dark ? 'light' : 'dark';
      window.calibreTheme.set(next);
      this.dark = next === 'dark';
    },
    openSidebar() {
      this._lastFocus = document.activeElement;
      this.sidebarOpen = true;
      setTimeout(() => this._focusDrawer(), 0);
    },
    closeSidebar() {
      this.sidebarOpen = false;
      if (this._lastFocus && typeof this._lastFocus.focus === 'function') {
        this._lastFocus.focus();
        this._lastFocus = null;
      }
    },
    _focusDrawer() {
      const drawer = document.querySelector('.cw-sidebar--drawer');
      if (!drawer) return;
      const focusables = drawer.querySelectorAll('button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      const target = focusables[0] || drawer;
      target.focus();
    },
    focusSearch() {
      const input = document.getElementById('query');
      if (input) { input.focus(); input.select(); }
    },
  });
});
