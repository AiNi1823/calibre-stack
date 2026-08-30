/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './cps/templates/**/*.html',
    './cps/templates/*.html',
    './async-upload/**/*.html',
    '../async-upload/**/*.html',
  ],
  darkMode: 'class',
  theme: {
    screens: {
      sm: '640px',
      md: '768px',
      lg: '1024px',
      // Desktop Density 分档：
      //   xl  >= 1280px  Desktop (Comfortable/Spacious)
      //   2xl >= 1600px  Wide Desktop (更宽 content，padding-x 40px)
      xl: '1280px',
      '2xl': '1600px',
    },
    extend: {
      colors: {
        // Design tokens (master-plan §六 / ui-rewrite P1)
        background: 'rgb(var(--background) / <alpha-value>)',
        surface: 'rgb(var(--surface) / <alpha-value>)',
        surfaceSecondary: 'rgb(var(--surface-secondary) / <alpha-value>)',
        border: 'rgb(var(--border) / <alpha-value>)',
        textPrimary: 'rgb(var(--text-primary) / <alpha-value>)',
        textSecondary: 'rgb(var(--text-secondary) / <alpha-value>)',
        textMuted: 'rgb(var(--text-muted) / <alpha-value>)',
        primary: 'rgb(var(--primary) / <alpha-value>)',
        danger: 'rgb(var(--danger) / <alpha-value>)',
        success: 'rgb(var(--success) / <alpha-value>)',
      },
      borderRadius: {
        // 封面/卡片圆角 4-6px；Modal 8px；禁止使用 rounded-4xl
        '4': '4px',
        '6': '6px',
        '8': '8px',
      },
      transitionDuration: {
        // 动画 100-200ms
        '100': '100ms',
        '200': '200ms',
      },
    },
  },
  plugins: [],
}
