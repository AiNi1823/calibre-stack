/* Calibre-Web UI Phase-0 chrome: theme (dark mode) + Lucide init
 * 与 tailwind.config.js 的 darkMode:'class' 配套。
 * 主题持久化到 localStorage('calibre-theme')；默认跟随系统 prefers-color-scheme。
 */

(function () {
  const STORE = 'calibre-theme';

  function resolveInitial() {
    try {
      const saved = window.localStorage.getItem(STORE);
      if (saved === 'dark' || saved === 'light') return saved;
    } catch (e) { /* ignore */ }
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }

  function apply(theme) {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }

  function setTheme(theme) {
    apply(theme);
    try {
      window.localStorage.setItem(STORE, theme);
    } catch (e) { /* ignore */ }
    // 通知 Alpine (ui app) 同步状态
    document.documentElement.dispatchEvent(new CustomEvent('theme-change', { detail: { theme } }));
  }

  function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    setTheme(isDark ? 'light' : 'dark');
  }

  /* 头部内联脚本已先行应用，避免 FOUC；此处兜底（例如 script 延迟执行） */
  apply(resolveInitial());

  /* 暴露到全局，供模板/Alpine 调用 */
  window.calibreTheme = { get: resolveInitial, set: setTheme, toggle: toggleTheme };

  /* Lucide：初始渲染 + 支撑 Alpine 动态内容 */
  document.addEventListener('alpine:init', function () {
    const initIcons = function () {
      if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
      }
    };
    initIcons();
    document.addEventListener('alpine:initialized', function () { setTimeout(initIcons, 0); });
  });

  document.addEventListener('DOMContentLoaded', function () {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  });
})();
