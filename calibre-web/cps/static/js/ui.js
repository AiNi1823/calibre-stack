/* Calibre-Web UI Phase-0: Alpine store + shell interactivity
 * 依赖 Alpine（alpine.min.js）与 theme.js（window.calibreTheme）。
 * P2 (App Shell) 将在此之上搭建 sidebar/header/drawer。
 * P11 (A11y)：移动端 Drawer 打开时移动焦点、关闭时回移焦点到触发器。
 */
document.addEventListener('alpine:init', function () {
  Alpine.store('ui', {
    dark: window.calibreTheme ? window.calibreTheme.get() === 'dark' : false,
    sidebarOpen: false,
    uploadModalOpen: false,
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
    openUploadModal() {
      this._lastFocus = document.activeElement;
      this.uploadModalOpen = true;
      setTimeout(() => {
        const input = document.getElementById('uploadInput');
        if (input) input.focus();
      }, 0);
    },
    closeUploadModal() {
      this.uploadModalOpen = false;
      if (this._lastFocus && typeof this._lastFocus.focus === 'function') {
        this._lastFocus.focus();
        this._lastFocus = null;
      }
    },
    handleUpload(event) {
      const files = event.target.files;
      if (!files || files.length === 0) return;
      const form = document.getElementById('uploadForm');
      if (form) form.submit();
      this.closeUploadModal();
    },
    bookDetailOpen: false,
    bookDetailBusy: false,
    bookDetailError: false,
    openBookDetail(href, ev) {
      if (ev) ev.preventDefault();
      this._lastHref = href;
      this._lastFocus = document.activeElement;
      this.bookDetailOpen = true;
      this.bookDetailBusy = true;
      this.bookDetailError = false;
      const body = document.getElementById('bookDetailBody');
      if (body) body.innerHTML = '';
      // Signal the server to render only the detail fragment (is_xhr => fragment.html)
      fetch(href, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin'
      })
        .then(function (r) { return r.text(); })
        .then(function (html) {
          if (body) { body.innerHTML = html; }
        })
        .catch(function () {
          this.bookDetailError = true;
        }.bind(this))
        .finally(function () {
          this.bookDetailBusy = false;
          this._initBookDetail();
        }.bind(this));
    },
    closeBookDetail() {
      this.bookDetailOpen = false;
      if (this._lastFocus && typeof this._lastFocus.focus === 'function') {
        this._lastFocus.focus();
        this._lastFocus = null;
      }
    },
    _initBookDetail() {
      // Re-wire the read-toggle that details.js normally binds on page load
      var cb = document.getElementById('have_read_cb');
      if (cb && !cb.dataset.bound) {
        cb.dataset.bound = '1';
        cb.addEventListener('change', function () {
          var form = document.getElementById('have_read_form');
          if (form) form.submit();
        });
      }
    },
  });
});
