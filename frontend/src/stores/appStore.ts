import { create } from 'zustand';

export type AppTheme = 'classic' | 'neubrutalism' | 'editorial';

export const THEME_OPTIONS: Array<{ label: string; value: AppTheme }> = [
  { label: '经典', value: 'classic' },
  { label: '新粗野', value: 'neubrutalism' },
  { label: '杂志', value: 'editorial' },
];

const THEME_KEY = 'kb-theme';
const stored = localStorage.getItem(THEME_KEY);
const initialTheme: AppTheme =
  stored === 'neubrutalism' || stored === 'editorial' ? stored : 'classic';

// 模块加载即落到 <html> 上，避免首屏闪烁
document.documentElement.dataset.theme = initialTheme;

interface AppState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  theme: AppTheme;
  setTheme: (theme: AppTheme) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  theme: initialTheme,
  setTheme: (theme) => {
    localStorage.setItem(THEME_KEY, theme);
    document.documentElement.dataset.theme = theme;
    set({ theme });
  },
}));
