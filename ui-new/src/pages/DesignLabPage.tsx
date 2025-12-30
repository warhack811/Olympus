import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ModernChatInput } from '@/components/chat/ModernChatInput';
import {
    Sparkles, Layout, Menu, Plus, MessageSquare,
    Settings, User, ChevronRight, Copy, RefreshCw,
    ThumbsUp, ThumbsDown, PanelRight, X, Code, Eye,
    Terminal, BarChart3, Info, Palette, LogOut, ChevronUp, CreditCard
} from 'lucide-react';
import { cn } from '@/lib/utils';

// 1. THEME DEFINITIONS
interface ThemeConfig {
    id: string;
    name: string;
    bg: string;
    glass: string;
    accent: string;
    accentGlow: string;
    textPrimary: string;
    textSecondary: string;
    border: string;
    isDark: boolean;
}

const THEMES: Record<string, ThemeConfig> = {
    cosmic: {
        id: 'cosmic',
        name: 'Cosmic',
        bg: '#09090b',
        glass: 'rgba(24, 24, 27, 0.4)',
        accent: '#a855f7',
        accentGlow: 'rgba(168, 85, 247, 0.25)',
        textPrimary: '#ffffff',
        textSecondary: '#71717a',
        border: 'rgba(255, 255, 255, 0.05)',
        isDark: true
    },
    polaris: {
        id: 'polaris',
        name: 'Polaris',
        bg: '#ffffff',
        glass: 'rgba(255, 255, 255, 0.7)',
        accent: '#3b82f6',
        accentGlow: 'rgba(59, 130, 246, 0.15)',
        textPrimary: '#0f172a',
        textSecondary: '#64748b',
        border: 'rgba(15, 23, 42, 0.08)',
        isDark: false
    },
    toxic: {
        id: 'toxic',
        name: 'Toxic',
        bg: '#000000',
        glass: 'rgba(0, 0, 0, 0.6)',
        accent: '#22c55e',
        accentGlow: 'rgba(34, 197, 94, 0.3)',
        textPrimary: '#4ade80',
        textSecondary: '#14532d',
        border: 'rgba(34, 197, 94, 0.2)',
        isDark: true
    },
    navy: {
        id: 'navy',
        name: 'Navy',
        bg: '#0f172a',
        glass: 'rgba(30, 41, 59, 0.5)',
        accent: '#f59e0b',
        accentGlow: 'rgba(245, 158, 11, 0.2)',
        textPrimary: '#f8fafc',
        textSecondary: '#94a3b8',
        border: 'rgba(245, 158, 11, 0.15)',
        isDark: true
    },
    sunset: {
        id: 'sunset',
        name: 'Sunset',
        bg: '#18181b',
        glass: 'rgba(24, 24, 27, 0.6)',
        accent: '#f43f5e',
        accentGlow: 'rgba(244, 63, 94, 0.25)',
        textPrimary: '#ffffff',
        textSecondary: '#a1a1aa',
        border: 'rgba(244, 63, 94, 0.1)',
        isDark: true
    },
    sakura: {
        id: 'sakura',
        name: 'Sakura',
        bg: '#fff1f2',
        glass: 'rgba(255, 255, 255, 0.8)',
        accent: '#f43f5e',
        accentGlow: 'rgba(244, 63, 94, 0.1)',
        textPrimary: '#881337',
        textSecondary: '#fb7185',
        border: 'rgba(244, 63, 94, 0.1)',
        isDark: false
    },
    cyber: {
        id: 'cyber',
        name: 'Cyber',
        bg: '#09090b',
        glass: 'rgba(9, 9, 11, 0.8)',
        accent: '#06b6d4',
        accentGlow: 'rgba(6, 182, 212, 0.4)',
        textPrimary: '#06b6d4',
        textSecondary: '#eab308',
        border: 'rgba(234, 179, 8, 0.3)',
        isDark: true
    },
    oled: {
        id: 'oled',
        name: 'OLED',
        bg: '#000000',
        glass: 'rgba(0, 0, 0, 0.9)',
        accent: '#ffffff',
        accentGlow: 'rgba(255, 255, 255, 0.2)',
        textPrimary: '#ffffff',
        textSecondary: '#525252',
        border: 'rgba(255, 255, 255, 0.2)',
        isDark: true
    }
};

export function DesignLabPage() {
    const [showArtifact, setShowArtifact] = useState(true);
    const [currentTheme, setCurrentTheme] = useState<ThemeConfig>(THEMES.cosmic);
    const [isThemeOpen, setIsThemeOpen] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

    const themeStyles = {
        '--bg-primary': currentTheme.bg,
        '--bg-glass': currentTheme.glass,
        '--accent': currentTheme.accent,
        '--accent-glow': currentTheme.accentGlow,
        '--text-primary': currentTheme.textPrimary,
        '--text-secondary': currentTheme.textSecondary,
        '--border': currentTheme.border,
    } as React.CSSProperties;

    // Sidebar Component to reuse
    const SidebarContent = ({ isMobile = false }: { isMobile?: boolean }) => (
        <>
            <div className="p-4 flex items-center justify-between">
                <button className="flex-1 h-9 flex items-center gap-2.5 px-3 rounded-xl bg-white/5 border border-[var(--border)] hover:bg-white/10 transition-all text-xs font-semibold text-[var(--text-primary)]">
                    <Plus className="w-3.5 h-3.5" />
                    <span>Yeni Sohbet</span>
                </button>
                {isMobile && (
                    <button onClick={() => setIsSidebarOpen(false)} className="ml-2 p-2 rounded-lg hover:bg-white/5 text-[var(--text-secondary)]">
                        <X className="w-5 h-5" />
                    </button>
                )}
            </div>

            <div className="flex-1 overflow-y-auto px-3 space-y-0.5 scrollbar-hide">
                <div className="px-3 py-4 text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-[0.2em] opacity-30">Sohbet Geçmişi</div>
                <HistoryItem title="Python Veri Analizi" active accent={currentTheme.accent} />
                <HistoryItem title="React Hooks" />
                <HistoryItem title="Mermaid Fix" />
                <HistoryItem title="Dinamik Temalar" />
                <HistoryItem title="Mobil Görünüm" />
            </div>

            <div className="p-3 border-t border-[var(--border)] relative">
                {/* USER POPUP MENU */}
                <AnimatePresence>
                    {isUserMenuOpen && (
                        <motion.div
                            initial={{ opacity: 0, y: 10, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 10, scale: 0.95 }}
                            className="absolute bottom-[calc(100%+10px)] left-3 right-3 p-1.5 rounded-2xl bg-[var(--bg-primary)] border border-[var(--border)] shadow-[0_20px_50px_rgba(0,0,0,0.4)] z-[60] space-y-0.5"
                            style={{ backgroundColor: currentTheme.bg }}
                        >
                            <UserMenuItem icon={<CreditCard className="w-3.5 h-3.5" />} label="Planım" />
                            <UserMenuItem icon={<Settings className="w-3.5 h-3.5" />} label="Ayarlar" />
                            <div className="h-px bg-[var(--border)] my-1.5 mx-2" />
                            <UserMenuItem icon={<LogOut className="w-3.5 h-3.5" />} label="Çıkış Yap" danger />
                        </motion.div>
                    )}
                </AnimatePresence>

                <button
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                    className={cn(
                        "w-full p-2.5 rounded-xl flex items-center gap-3 transition-all",
                        isUserMenuOpen ? "bg-white/5" : "hover:bg-white/5"
                    )}
                >
                    <div className="w-8 h-8 rounded-lg flex-shrink-0" style={{ background: currentTheme.accent }} />
                    <div className="flex-1 min-w-0 text-left">
                        <p className="text-[13px] font-bold truncate text-[var(--text-primary)]">Muhammet</p>
                        <p className="text-[10px] text-[var(--text-secondary)] font-bold uppercase tracking-wider opacity-40">Pro Plan</p>
                    </div>
                    <ChevronUp className={cn("w-3.5 h-3.5 text-[var(--text-secondary)] transition-transform", isUserMenuOpen && "rotate-180")} />
                </button>
            </div>
        </>
    );

    return (
        <div
            className={cn(
                "relative min-h-screen w-full overflow-hidden flex transition-colors duration-500 selection:bg-[var(--accent)] selection:text-white",
                "font-['Inter',_sans-serif]",
                currentTheme.isDark ? "dark" : "light"
            )}
            style={{
                ...themeStyles,
                backgroundColor: currentTheme.bg,
                color: currentTheme.textPrimary
            }}
        >

            {/* 1. RADIAL GRADIENT */}
            <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
                <motion.div
                    animate={{ backgroundColor: currentTheme.accent }}
                    transition={{ duration: 1 }}
                    className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full opacity-[0.05] blur-[120px]"
                />
            </div>

            {/* 2. MOBILE BACKDROP */}
            <AnimatePresence>
                {isSidebarOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setIsSidebarOpen(false)}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[90] lg:hidden"
                    />
                )}
            </AnimatePresence>

            {/* 3. MOBILE SIDEBAR */}
            <AnimatePresence>
                {isSidebarOpen && (
                    <motion.aside
                        initial={{ x: "-100%" }}
                        animate={{ x: 0 }}
                        exit={{ x: "-100%" }}
                        transition={{ type: "spring", damping: 25, stiffness: 200 }}
                        className="fixed inset-y-0 left-0 w-[280px] bg-[var(--bg-primary)] border-r border-[var(--border)] z-[100] flex flex-col lg:hidden"
                        style={{ backgroundColor: currentTheme.bg }}
                    >
                        <SidebarContent isMobile />
                    </motion.aside>
                )}
            </AnimatePresence>

            {/* 4. DESKTOP SIDEBAR */}
            <aside className="relative z-20 w-[240px] h-screen border-r border-[var(--border)] bg-[var(--bg-glass)] backdrop-blur-3xl flex flex-col hidden lg:flex transition-all duration-500">
                <SidebarContent />
            </aside>

            {/* 5. MAIN LAYOUT AREA */}
            <div className="relative z-10 flex-1 flex flex-col h-screen overflow-hidden">

                {/* MOCK HEADER */}
                <header className="w-full border-b border-[var(--border)] bg-[var(--bg-glass)]/20 backdrop-blur-md px-4 sm:px-6 py-3 flex items-center justify-between transition-all duration-500 relative z-50">
                    <div className="flex items-center gap-3 sm:gap-4">
                        <button
                            onClick={() => setIsSidebarOpen(true)}
                            className="p-2 rounded-lg hover:bg-white/5 lg:hidden text-[var(--text-primary)]"
                        >
                            <Menu className="w-5 h-5" />
                        </button>
                        <div className="flex items-center gap-2">
                            <div className="p-1.5 rounded-lg bg-[var(--accent)]/5 text-[var(--accent)]">
                                <Layout className="w-4 h-4" />
                            </div>
                            <h1 className="text-[10px] sm:text-xs font-bold tracking-tight text-[var(--text-primary)] uppercase">
                                Mami AI <span className="mx-1 sm:mx-2 opacity-20">/</span> <span className="opacity-60">Design Lab</span>
                            </h1>
                        </div>
                    </div>

                    <div className="flex items-center gap-1 sm:gap-2">
                        {/* THEME POPPER */}
                        <div className="relative">
                            <button
                                onClick={() => setIsThemeOpen(!isThemeOpen)}
                                className={cn(
                                    "p-2 rounded-lg transition-all border border-transparent hover:border-[var(--border)] hover:bg-white/5",
                                    isThemeOpen ? "text-[var(--accent)] bg-[var(--accent)]/5 border-[var(--border)]" : "text-[var(--text-secondary)]"
                                )}
                                title="Tema Değiştir"
                            >
                                <Palette className="w-4 h-4" />
                            </button>
                            <AnimatePresence>
                                {isThemeOpen && (
                                    <>
                                        <div className="fixed inset-0 z-[90]" onClick={() => setIsThemeOpen(false)} />
                                        <motion.div
                                            initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                            animate={{ opacity: 1, y: 0, scale: 1 }}
                                            exit={{ opacity: 0, y: 10, scale: 0.95 }}
                                            className="absolute right-0 mt-2 p-3 rounded-2xl bg-[var(--bg-primary)] border border-[var(--border)] shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[100] grid grid-cols-4 gap-2.5 min-w-[180px] sm:min-w-[200px]"
                                            style={{ backgroundColor: currentTheme.bg }}
                                        >
                                            {Object.values(THEMES).map((t) => (
                                                <button
                                                    key={t.id}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setCurrentTheme(t);
                                                        setIsThemeOpen(false);
                                                    }}
                                                    className={cn(
                                                        "w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center transition-all hover:scale-110 active:scale-95 border border-white/10",
                                                        currentTheme.id === t.id ? "ring-2 ring-[var(--accent)] ring-offset-4 ring-offset-[var(--bg-primary)]" : "opacity-60 hover:opacity-100"
                                                    )}
                                                    style={{ backgroundColor: t.accent }}
                                                    title={t.name}
                                                />
                                            ))}
                                        </motion.div>
                                    </>
                                )}
                            </AnimatePresence>
                        </div>

                        <div className="h-4 w-px bg-[var(--border)] mx-1" />

                        <button
                            onClick={() => setShowArtifact(!showArtifact)}
                            className={cn(
                                "p-2 rounded-lg transition-colors hidden sm:flex",
                                showArtifact ? "text-[var(--accent)]" : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                            )}
                        >
                            <PanelRight className="w-4 h-4" />
                        </button>
                        <div className="w-7 h-7 rounded-lg border border-[var(--border)] overflow-hidden">
                            <div className="w-full h-full bg-gradient-to-tr from-purple-500 to-blue-500" />
                        </div>
                    </div>
                </header>

                <div className="flex-1 flex overflow-hidden">
                    <main className="flex-1 flex flex-col relative min-w-0">

                        <div
                            className="flex-1 overflow-y-auto p-4 sm:p-6 scrollbar-hide"
                            onClick={() => {
                                setIsUserMenuOpen(false);
                                setIsThemeOpen(false);
                            }}
                        >
                            <div className="max-w-3xl mx-auto space-y-10 sm:space-y-12 pb-40">
                                {/* 1. KULLANICI MESAJI */}
                                <MockMessage
                                    role="user"
                                    content="Bana son çeyrek satış verilerini Python ile analiz edip, modelleri karşılaştıran bir tablo oluştur."
                                    timestamp="14:15"
                                    accent={currentTheme.accent}
                                />

                                {/* 2. AI YANITI (NO AVATAR FOR SPACE) */}
                                <div className="flex flex-col gap-8">
                                    <MockMessage
                                        role="assistant"
                                        content="Elbette, işte satış verileri için hazırladığım Pandas analizi ve model karşılaştırması:"
                                        timestamp="14:16"
                                        isWrapped={false}
                                    />

                                    {/* 3. MAC-STYLE CODE WINDOW */}
                                    <CodeWindow
                                        filename="analysis.py"
                                        code={`import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

# Veri setini yükle ve analiz et
df = pd.read_csv('sales_q4.csv')
analysis = df.groupby('category').agg({
    'revenue': ['sum', 'mean'],
    'units': 'sum'
})

# Modelleri eğit ve karşılaştır
rf = RandomForestRegressor(n_estimators=100)
xgb = XGBRegressor(learning_rate=0.05)`}
                                        theme={currentTheme}
                                    />

                                    {/* 4. DATA TABLE */}
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2 text-[var(--text-secondary)] text-[10px] font-bold uppercase tracking-widest opacity-60">
                                            <BarChart3 className="w-3 h-3 text-[var(--accent)]" />
                                            <span>Model Performans Karşılaştırması</span>
                                        </div>
                                        <div className="overflow-x-auto">
                                            <DataTable theme={currentTheme} />
                                        </div>
                                    </div>

                                    {/* 5. CALLOUT */}
                                    <Callout theme={currentTheme} text="Not: Bu veriler simülasyon amaçlıdır. Model doğruluk değerleri eğitim setine göre değişiklik gösterebilir." />

                                    {/* ACTIONS */}
                                    <div className="flex items-center gap-3 pt-4 opacity-40 hover:opacity-100 transition-opacity">
                                        <button className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-[var(--border)] text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/5 transition-all">
                                            <Copy className="w-3 h-3" />
                                            <span className="hidden sm:inline">Kopyala</span>
                                        </button>
                                        <button className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-[var(--border)] text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/5 transition-all">
                                            <RefreshCw className="w-3 h-3" />
                                            <span className="hidden sm:inline">Tekrarla</span>
                                        </button>
                                    </div>
                                </div>

                                {/* 6. KULLANICI GORSEL ISTEGI */}
                                <MockMessage
                                    role="user"
                                    content="Minimalist bir kedi cizimi uret."
                                    timestamp="14:18"
                                    accent={currentTheme.accent}
                                />

                                {/* 7. AI GORSEL YANIT AKISI */}
                                <div className="flex flex-col gap-3 sm:gap-4">
                                    <AssistantCard timestamp="14:18">
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex items-start gap-3">
                                                <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-[var(--accent)]/15 border border-[var(--border)]">
                                                    <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[var(--accent)] animate-spin" />
                                                </div>
                                                <div className="space-y-1">
                                                    <p className="text-[12px] sm:text-[13px] font-semibold text-[var(--text-primary)]">Gorsel uretiliyor</p>
                                                    <p className="text-[10px] sm:text-[11px] text-[var(--text-secondary)]">Minimalist cizgi tarzi, temiz negatif alan.</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2 text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                                                <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                                                <span>In progress</span>
                                            </div>
                                        </div>

                                        <div className="mt-3 text-[10px] sm:text-[11px] text-[var(--text-secondary)] flex flex-wrap items-center gap-2">
                                            <span className="font-semibold text-[var(--text-primary)]">Mami Art v3</span>
                                            <span className="opacity-40">•</span>
                                            <span>1024 x 1024</span>
                                            <span className="opacity-40">•</span>
                                            <span>ETA 6s</span>
                                        </div>

                                        <div className="mt-3 h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                            <div className="h-full w-[62%] bg-[var(--accent)]/70" />
                                        </div>

                                        <div className="mt-3 rounded-2xl border border-[var(--border)] overflow-hidden bg-[var(--bg-glass)]/30 relative aspect-[3/2] sm:aspect-[4/3]">
                                            <div
                                                className="absolute inset-0"
                                                style={{
                                                    backgroundImage: `radial-gradient(circle at 20% 20%, ${currentTheme.accent}55, transparent 50%), radial-gradient(circle at 80% 30%, rgba(255,255,255,0.2), transparent 55%), linear-gradient(160deg, rgba(0,0,0,0.2), rgba(0,0,0,0.65))`,
                                                }}
                                            />
                                            <div className="absolute inset-0 backdrop-blur-[6px]" />
                                            <div className="absolute inset-0 animate-pulse opacity-40" style={{ background: "linear-gradient(120deg, transparent 35%, rgba(255,255,255,0.15), transparent 65%)" }} />
                                            <div className="absolute top-3 left-3 text-[9px] sm:text-[10px] font-bold uppercase tracking-widest text-[var(--text-secondary)] opacity-70">
                                                Preview
                                            </div>
                                        </div>
                                    </AssistantCard>

                                    <AssistantCard timestamp="14:18">
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex items-start gap-3">
                                                <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-white/5 border border-[var(--border)]">
                                                    <ChevronRight className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[var(--text-secondary)]" />
                                                </div>
                                                <div className="space-y-1">
                                                    <p className="text-[12px] sm:text-[13px] font-semibold text-[var(--text-primary)]">Istek siraya alindi</p>
                                                    <p className="text-[10px] sm:text-[11px] text-[var(--text-secondary)]">Kuyrukta ilerliyor, islenince otomatik baslar.</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2 text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                                                <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]/60" />
                                                <span>Queued</span>
                                            </div>
                                        </div>

                                        <div className="mt-3 text-[10px] sm:text-[11px] text-[var(--text-secondary)] flex flex-wrap items-center gap-2">
                                            <span className="font-semibold text-[var(--text-primary)]">Queue 3/12</span>
                                            <span className="opacity-40">•</span>
                                            <span>Standard</span>
                                            <span className="opacity-40">•</span>
                                            <span>ETA 8-12s</span>
                                        </div>
                                        <div className="mt-3 h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                            <div className="h-full w-1/3 bg-[var(--accent)]/50" />
                                        </div>
                                    </AssistantCard>

                                    <AssistantCard timestamp="14:19">
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex items-start gap-3">
                                                <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center bg-[var(--accent)]/15 border border-[var(--border)]">
                                                    <Eye className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[var(--accent)]" />
                                                </div>
                                                <div className="space-y-1">
                                                    <p className="text-[12px] sm:text-[13px] font-semibold text-[var(--text-primary)]">Gorsel hazir</p>
                                                    <p className="text-[10px] sm:text-[11px] text-[var(--text-secondary)]">Minimalist kedi cizimi teslim edildi. Preview ve indirme hazir.</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2 text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                                                <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                                                <span>Ready</span>
                                            </div>
                                        </div>

                                        <div className="mt-4 aspect-[5/4] sm:aspect-[4/3] rounded-2xl border border-[var(--border)] overflow-hidden bg-[var(--bg-glass)]/30 relative">
                                            <div
                                                className="absolute inset-0"
                                                style={{
                                                    backgroundImage: `linear-gradient(135deg, rgba(255,255,255,0.08), transparent 40%), radial-gradient(circle at 20% 20%, ${currentTheme.accent}44, transparent 55%), radial-gradient(circle at 80% 30%, rgba(255,255,255,0.15), transparent 50%), linear-gradient(180deg, rgba(0,0,0,0.2), rgba(0,0,0,0.5))`,
                                                }}
                                            />
                                            <div
                                                className="absolute inset-0 opacity-50"
                                                style={{
                                                    backgroundImage:
                                                        "linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px)",
                                                    backgroundSize: "24px 24px",
                                                }}
                                            />
                                            <div className="absolute inset-0 flex items-center justify-center">
                                                <div className="w-[72%] h-[72%] rounded-full border border-[var(--border)] bg-white/5 flex items-center justify-center">
                                                    <Palette className="w-6 h-6 text-[var(--text-secondary)] opacity-60" />
                                                </div>
                                            </div>
                                            <div className="absolute bottom-3 left-3 right-3 sm:bottom-4 sm:left-4 sm:right-4 flex items-center justify-between text-[9px] sm:text-[10px] font-bold uppercase tracking-widest text-[var(--text-secondary)] opacity-70">
                                                <span>1024 x 1024</span>
                                                <span>SVG + PNG</span>
                                            </div>
                                        </div>
                                        <div className="mt-3 text-[10px] sm:text-[11px] text-[var(--text-secondary)] flex flex-wrap items-center gap-2">
                                            <span className="font-semibold text-[var(--text-primary)]">28 steps</span>
                                            <span className="opacity-40">•</span>
                                            <span>7.9s</span>
                                            <span className="opacity-40">•</span>
                                            <span>Studio clean</span>
                                        </div>

                                        <div className="mt-3 flex flex-wrap items-center gap-2">
                                            <button className="px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-lg border border-[var(--border)] text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/5 transition-all">
                                                Indir PNG
                                            </button>
                                            <button className="px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-lg border border-[var(--border)] text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/5 transition-all">
                                                Prompt kopyala
                                            </button>
                                        </div>
                                    </AssistantCard>
                                </div>
                            </div>
                        </div>

                        {/* INPUT AREA */}
                        <div className="w-full max-w-3xl mx-auto pb-4 sm:pb-8 px-4 relative z-30">
                            <div className="flex flex-wrap justify-center gap-1.5 sm:gap-2 mb-4 sm:mb-6 opacity-60 hover:opacity-100 transition-opacity">
                                <SuggestionChip icon="🎨" label="Özet" />
                                <SuggestionChip icon="📝" label="Grafik" />
                                <SuggestionChip icon="⚡" label="CSV" />
                            </div>

                            <div className="relative z-30">
                                <ModernChatInput
                                    onSendMessage={() => { }}
                                    isLoading={false}
                                    theme={isUserMenuOpen ? undefined : currentTheme}
                                />
                            </div>
                        </div>
                    </main>
                </div>
            </div>
        </div>
    );
}

// --------------------------------------------------------------------------------
// UTILS & SMALL COMPONENTS
// --------------------------------------------------------------------------------

function UserMenuItem({ icon, label, danger = false }: { icon: React.ReactNode, label: string, danger?: boolean }) {
    return (
        <button className={cn(
            "w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium transition-all group",
            danger
                ? "text-red-500 hover:bg-red-500/10"
                : "text-[var(--text-primary)] hover:bg-white/5"
        )}>
            <div className={cn("opacity-40 group-hover:opacity-100 transition-opacity", danger && "opacity-100")}>{icon}</div>
            <span>{label}</span>
        </button>
    );
}

function CodeWindow({ filename, code }: { filename: string, code: string, theme: ThemeConfig }) {
    return (
        <div className="rounded-xl overflow-hidden border border-[var(--border)] shadow-2xl transition-all duration-500">
            <div className="flex items-center justify-between px-4 py-2.5 bg-white/[0.03] border-b border-[var(--border)]">
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]" />
                        <div className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]" />
                        <div className="w-2.5 h-2.5 rounded-full bg-[#27c93f]" />
                    </div>
                    <div className="flex items-center gap-2 opacity-60">
                        <Terminal className="w-3 h-3" />
                        <span className="text-[10px] font-bold font-mono tracking-tight">{filename}</span>
                    </div>
                </div>
                <button className="p-1 px-2 hover:bg-white/5 rounded transition-colors text-[var(--text-secondary)]">
                    <Copy className="w-3 h-3" />
                </button>
            </div>
            <div className="p-4 sm:p-5 font-mono text-[10px] sm:text-[11px] leading-[1.6] overflow-x-auto bg-black/20 backdrop-blur-3xl">
                <pre className="text-[var(--text-primary)]">
                    {code.split('\n').map((line, i) => (
                        <div key={i} className="flex gap-4">
                            <span className="w-4 text-left opacity-15 select-none">{i + 1}</span>
                            <span className="opacity-90">{line}</span>
                        </div>
                    ))}
                </pre>
            </div>
        </div>
    )
}

function DataTable({ theme }: { theme: ThemeConfig }) {
    const data = [
        { model: 'Random Forest', accuracy: '98.2%', speed: '124ms', resource: 'Mid' },
        { model: 'XGBoost', accuracy: '97.5%', speed: '86ms', resource: 'High' },
        { model: 'LightGBM', accuracy: '96.8%', speed: '42ms', resource: 'Low' },
    ]

    return (
        <div className="rounded-xl border border-[var(--border)] overflow-hidden transition-all duration-500 bg-black/10 min-w-[500px] sm:min-w-0">
            <table className="w-full text-left text-[11px] border-collapse">
                <thead>
                    <tr className="border-b border-[var(--border)] bg-white/[0.02] text-[var(--text-secondary)] font-bold uppercase tracking-widest opacity-60">
                        <th className="px-5 py-3">Model</th>
                        <th className="px-5 py-3 text-center">Doğruluk (%)</th>
                        <th className="px-5 py-3 text-center">Hız (ms)</th>
                        <th className="px-5 py-3 text-right">Kaynak</th>
                    </tr>
                </thead>
                <tbody className="text-[var(--text-primary)]">
                    {data.map((row, i) => (
                        <tr
                            key={i}
                            className={cn(
                                "border-b last:border-0 border-[var(--border)] transition-colors",
                                "hover:bg-white/[0.02]"
                            )}
                        >
                            <td className="px-5 py-3 font-semibold flex items-center gap-3">
                                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: theme.accent }} />
                                {row.model}
                            </td>
                            <td className="px-5 py-3 text-center opacity-60">{row.accuracy}</td>
                            <td className="px-5 py-3 text-center opacity-60">{row.speed}</td>
                            <td className="px-5 py-3 text-right">
                                <span className="px-2 py-0.5 rounded-lg bg-white/5 text-[9px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                                    {row.resource}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function Callout({ text, theme }: { text: string, theme: ThemeConfig }) {
    return (
        <div
            className="flex gap-4 p-4 sm:p-5 rounded-2xl border border-[var(--border)] transition-all duration-500"
            style={{ borderLeftColor: theme.accent, borderLeftWidth: '3px', backgroundColor: `${theme.accent}03` }}
        >
            <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 opacity-60" style={{ color: theme.accent }} />
            <p className="text-[11px] sm:text-[12px] leading-[1.6] text-[var(--text-secondary)] italic opacity-80">
                {text}
            </p>
        </div>
    )
}

function HistoryItem({ title, active, accent }: { title: string, active?: boolean, accent?: string }) {
    return (
        <button
            className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] transition-all text-left",
                active
                    ? "bg-white/5 text-[var(--text-primary)] font-semibold shadow-sm"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/5 opacity-60 hover:opacity-100"
            )}
        >
            <MessageSquare className="w-3.5 h-3.5" style={{ color: active ? accent : undefined, opacity: active ? 0.8 : 0.4 }} />
            <span className="truncate flex-1">{title}</span>
            {active && <div className="w-1 h-1 rounded-full" style={{ background: accent }} />}
        </button>
    )
}

function MockMessage({ role, content, timestamp, accent, isWrapped = true }: { role: 'user' | 'assistant', content: string, timestamp: string, accent?: string, isWrapped?: boolean }) {
    if (!isWrapped) {
        return <p className="text-[14px] sm:text-[15px] leading-relaxed text-[var(--text-primary)] opacity-90">{content}</p>
    }

    return (
        <div className={cn(
            "group relative flex flex-col max-w-[90%] sm:max-w-[85%] transition-all",
            role === 'user' ? "ml-auto items-end" : "mr-auto items-start"
        )}>
            <div className={cn(
                "px-4 py-3 sm:px-5 sm:py-3.5 rounded-3xl relative transition-all duration-300 border border-[var(--border)]",
                role === 'user'
                    ? "bg-zinc-800/40 text-[var(--text-primary)] rounded-tr-lg"
                    : "bg-[var(--bg-glass)]/40 text-[var(--text-primary)] rounded-tl-lg"
            )}>
                <p className="text-[13px] sm:text-[14px] leading-relaxed opacity-90">{content}</p>

                <div className="absolute right-3 top-full mt-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10">
                    <button className="p-1 px-1.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] shadow-sm"><Copy className="w-3 h-3" /></button>
                </div>
            </div>
            <span className="text-[9px] text-[var(--text-secondary)] mt-2.5 px-2 font-bold uppercase tracking-widest opacity-25">{timestamp}</span>
        </div>
    )
}

function AssistantCard({ children, timestamp }: { children: React.ReactNode, timestamp: string }) {
    return (
        <div className="group relative flex flex-col max-w-[92%] sm:max-w-[85%] transition-all mr-auto items-start">
            <div className="px-3 py-2.5 sm:px-5 sm:py-3.5 rounded-3xl relative transition-all duration-300 border border-[var(--border)] bg-[var(--bg-glass)]/40 text-[var(--text-primary)] rounded-tl-lg">
                {children}
                <div className="absolute right-3 top-full mt-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10">
                    <button className="p-1 px-1.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] shadow-sm"><Copy className="w-3 h-3" /></button>
                </div>
            </div>
            <span className="text-[9px] text-[var(--text-secondary)] mt-2.5 px-2 font-bold uppercase tracking-widest opacity-25">{timestamp}</span>
        </div>
    )
}

function SuggestionChip({ icon, label }: { icon: string, label: string }) {
    return (
        <button className="flex items-center gap-2 px-3 sm:px-3.5 py-1.5 rounded-full bg-[var(--bg-glass)]/20 border border-[var(--border)] hover:border-[var(--accent)]/40 hover:bg-[var(--bg-glass)]/40 text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all backdrop-blur-md">
            <span className="opacity-70">{icon}</span>
            <span>{label}</span>
        </button>
    )
}
