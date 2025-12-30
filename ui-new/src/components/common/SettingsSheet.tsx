/**
 * SettingsSheet Component
 * 
 * Main settings modal/bottom sheet with tabbed interface:
 * - Response Style (tone, emoji, length)
 * - Memory & Future Plans
 * - Image Settings
 * 
 * Works as modal on desktop, bottom sheet on mobile
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    X, Settings, MessageSquare, Brain, Image, Calendar,
    Check, ChevronRight, Plus, Trash2, Sparkles, Palette, Sun, Moon, Monitor, FileText
} from 'lucide-react'
import { useSettingsStore, PERSONAS, type PersonaMode } from '@/stores/settingsStore'
import { useThemeStore } from '@/stores/themeStore'
import { Button, Input } from '@/components/ui'
import { useIsMobile } from '@/hooks'
import { cn } from '@/lib/utils'
import { DocumentsTab } from './DocumentsTab'

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export function SettingsSheet() {
    const {
        settingsOpen,
        closeSettings,
        activeSettingsTab,
        setActiveSettingsTab,
    } = useSettingsStore()

    const isMobile = useIsMobile()

    if (!settingsOpen) return null

    const tabs = [
        { id: 'style' as const, label: 'Yanıt Stili', icon: MessageSquare },
        { id: 'appearance' as const, label: 'Görünüm', icon: Palette },
        { id: 'memory' as const, label: 'Hafıza', icon: Brain },
        { id: 'files' as const, label: 'Belgeler', icon: FileText },
        { id: 'image' as const, label: 'Görsel', icon: Image },
        { id: 'plans' as const, label: 'Planlar', icon: Calendar },
    ]

    return (
        <AnimatePresence>
            {settingsOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={closeSettings}
                        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
                    />

                    {/* Sheet */}
                    <motion.div
                        initial={isMobile ? { y: '100%' } : { opacity: 0, scale: 0.95 }}
                        animate={isMobile ? { y: 0 } : { opacity: 1, scale: 1 }}
                        exit={isMobile ? { y: '100%' } : { opacity: 0, scale: 0.95 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                        className={cn(
                            "fixed z-50 bg-(--color-bg-surface) border border-(--color-border)",
                            "flex flex-col overflow-hidden",
                            isMobile
                                ? "inset-x-0 bottom-0 rounded-t-3xl max-h-[85vh]"
                                : "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-2xl w-full max-w-2xl max-h-[80vh]"
                        )}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-5 py-4 border-b border-(--color-border)">
                            {isMobile && (
                                <div className="w-12 h-1 rounded-full bg-(--color-border) absolute top-2 left-1/2 -translate-x-1/2" />
                            )}
                            <div className="flex items-center gap-3">
                                <div className="p-2 rounded-xl bg-(--color-primary-soft)">
                                    <Settings className="h-5 w-5 text-(--color-primary)" />
                                </div>
                                <div>
                                    <h2 className="text-lg font-semibold">Ayarlar</h2>
                                    <p className="text-xs text-(--color-text-muted)">
                                        AI yanıtlarını kişiselleştir
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={closeSettings}
                                className="p-2 rounded-lg hover:bg-(--color-bg-surface-hover) text-(--color-text-muted)"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        {/* Tabs */}
                        <div className="flex border-b border-(--color-border) px-2 overflow-x-auto scrollbar-hide">
                            {tabs.map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveSettingsTab(tab.id)}
                                    className={cn(
                                        "flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap",
                                        "border-b-2 transition-colors -mb-[2px]",
                                        activeSettingsTab === tab.id
                                            ? "border-(--color-primary) text-(--color-primary)"
                                            : "border-transparent text-(--color-text-muted) hover:text-(--color-text)"
                                    )}
                                >
                                    <tab.icon className="h-4 w-4" />
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        <div className="flex-1 overflow-y-auto p-5">
                            {activeSettingsTab === 'style' && <ResponseStyleTab />}
                            {activeSettingsTab === 'appearance' && <AppearanceTab />}
                            {activeSettingsTab === 'memory' && <MemoryTab />}
                            {activeSettingsTab === 'files' && <DocumentsTab />}
                            {activeSettingsTab === 'image' && <ImageSettingsTab />}
                            {activeSettingsTab === 'plans' && <FuturePlansTab />}
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    )
}

// ─────────────────────────────────────────────────────────────────────────────
// RESPONSE STYLE TAB
// ─────────────────────────────────────────────────────────────────────────────

function ResponseStyleTab() {
    const {
        activePersona,
        setActivePersona,
        responseStyle,
        setResponseStyle
    } = useSettingsStore()

    return (
        <div className="space-y-6">
            {/* Persona/Mode Selection */}
            <section>
                <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-(--color-primary)" />
                    AI Modu
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {PERSONAS.map(persona => (
                        <button
                            key={persona.name}
                            onClick={() => setActivePersona(persona.name)}
                            className={cn(
                                "flex items-center gap-3 p-3 rounded-xl border transition-all text-left",
                                activePersona === persona.name
                                    ? "border-(--color-primary) bg-(--color-primary-soft)"
                                    : "border-(--color-border) hover:border-(--color-primary)/50"
                            )}
                        >
                            <span className="text-xl">{persona.icon}</span>
                            <div className="min-w-0">
                                <div className="text-sm font-medium truncate">{persona.displayName}</div>
                                <div className="text-xs text-(--color-text-muted) truncate">{persona.description}</div>
                            </div>
                            {activePersona === persona.name && (
                                <Check className="h-4 w-4 text-(--color-primary) ml-auto shrink-0" />
                            )}
                        </button>
                    ))}
                </div>
            </section>

            {/* Tone */}
            <section>
                <h3 className="text-sm font-medium mb-3">Ton</h3>
                <div className="flex flex-wrap gap-2">
                    {[
                        { value: 'casual', label: 'Samimi' },
                        { value: 'formal', label: 'Resmi' },
                        { value: 'playful', label: 'Eğlenceli' },
                        { value: 'professional', label: 'Profesyonel' },
                    ].map(opt => (
                        <button
                            key={opt.value}
                            onClick={() => setResponseStyle({ tone: opt.value as any })}
                            className={cn(
                                "px-4 py-2 rounded-full text-sm border transition-all",
                                responseStyle.tone === opt.value
                                    ? "border-(--color-primary) bg-(--color-primary-soft) text-(--color-primary)"
                                    : "border-(--color-border) hover:border-(--color-primary)/50"
                            )}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            </section>

            {/* Emoji Level */}
            <section>
                <h3 className="text-sm font-medium mb-3">Emoji Kullanımı</h3>
                <div className="flex gap-2">
                    {[
                        { value: 'none', label: 'Yok' },
                        { value: 'low', label: 'Az 😊' },
                        { value: 'medium', label: 'Orta 😊👍' },
                        { value: 'high', label: 'Çok 🎉😍✨' },
                    ].map(opt => (
                        <button
                            key={opt.value}
                            onClick={() => setResponseStyle({ emojiLevel: opt.value as any })}
                            className={cn(
                                "flex-1 px-3 py-2 rounded-lg text-sm border transition-all",
                                responseStyle.emojiLevel === opt.value
                                    ? "border-(--color-primary) bg-(--color-primary-soft)"
                                    : "border-(--color-border) hover:border-(--color-primary)/50"
                            )}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            </section>

            {/* Length */}
            <section>
                <h3 className="text-sm font-medium mb-3">Yanıt Uzunluğu</h3>
                <div className="flex gap-2">
                    {[
                        { value: 'short', label: 'Kısa', desc: 'Öz ve net' },
                        { value: 'normal', label: 'Normal', desc: 'Dengeli' },
                        { value: 'detailed', label: 'Detaylı', desc: 'Kapsamlı' },
                    ].map(opt => (
                        <button
                            key={opt.value}
                            onClick={() => setResponseStyle({ length: opt.value as any })}
                            className={cn(
                                "flex-1 p-3 rounded-xl border transition-all text-center",
                                responseStyle.length === opt.value
                                    ? "border-(--color-primary) bg-(--color-primary-soft)"
                                    : "border-(--color-border) hover:border-(--color-primary)/50"
                            )}
                        >
                            <div className="text-sm font-medium">{opt.label}</div>
                            <div className="text-xs text-(--color-text-muted)">{opt.desc}</div>
                        </button>
                    ))}
                </div>
            </section>
        </div>
    )
}

// ─────────────────────────────────────────────────────────────────────────────
// APPEARANCE TAB (Theme Selection - Inline)
// ─────────────────────────────────────────────────────────────────────────────

// Theme definitions (copied from ThemePicker for inline display)
const THEMES = {
    warmDark: { name: 'Sıcak Karanlık', icon: '🌙', bg: '#0a0a0a', surface: '#171717', primary: '#7c3aed' },
    oledBlack: { name: 'OLED Siyah', icon: '⬛', bg: '#000000', surface: '#0a0a0a', primary: '#7c3aed' },
    midnight: { name: 'Gece Mavisi', icon: '🌌', bg: '#0c1222', surface: '#1a2744', primary: '#3b82f6' },
    forest: { name: 'Orman Gecesi', icon: '🌲', bg: '#0a1210', surface: '#132418', primary: '#10b981' },
    roseGold: { name: 'Rose Gold', icon: '🌹', bg: '#1a1418', surface: '#2d2226', primary: '#f43f5e' },
    dracula: { name: 'Dracula', icon: '🧛', bg: '#282a36', surface: '#44475a', primary: '#bd93f9' },
    nord: { name: 'Nord', icon: '❄️', bg: '#2e3440', surface: '#3b4252', primary: '#88c0d0' },
    cleanLight: { name: 'Temiz Aydınlık', icon: '☀️', bg: '#ffffff', surface: '#f5f5f5', primary: '#7c3aed' },
    warmCream: { name: 'Sıcak Krem', icon: '📜', bg: '#fefcf3', surface: '#faf5e6', primary: '#b45309' },
    oceanBreeze: { name: 'Okyanus Esintisi', icon: '🌊', bg: '#f0fdfa', surface: '#ccfbf1', primary: '#0d9488' },
    lavender: { name: 'Lavanta Rüyası', icon: '💜', bg: '#faf5ff', surface: '#f3e8ff', primary: '#9333ea' },
    highContrast: { name: 'Yüksek Kontrast', icon: '👁️', bg: '#000000', surface: '#1a1a1a', primary: '#ffff00' },
    system: { name: 'Sistem Teması', icon: '💻', bg: '#0a0a0a', surface: '#171717', primary: '#7c3aed' },
} as const

function AppearanceTab() {
    const { theme, setTheme } = useThemeStore()

    return (
        <div className="space-y-4">
            {/* Theme Selection Header */}
            <div className="flex items-center gap-2 mb-2">
                <Palette className="h-4 w-4 text-(--color-primary)" />
                <h3 className="text-sm font-medium">Tema Seçin</h3>
            </div>

            {/* Theme Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {Object.entries(THEMES).map(([id, t]) => (
                    <button
                        key={id}
                        onClick={() => setTheme(id as any)}
                        className={cn(
                            "relative p-3 rounded-xl border-2 transition-all text-left",
                            theme === id
                                ? "border-(--color-primary) ring-2 ring-(--color-primary)/30"
                                : "border-(--color-border) hover:border-(--color-border-hover)"
                        )}
                        style={{ backgroundColor: t.surface }}
                    >
                        {/* Color Preview */}
                        <div className="flex gap-1 mb-2">
                            <div
                                className="w-4 h-4 rounded-full border border-white/20"
                                style={{ backgroundColor: t.primary }}
                            />
                            <div
                                className="w-4 h-4 rounded-full border border-white/20"
                                style={{ backgroundColor: t.bg }}
                            />
                        </div>

                        {/* Name */}
                        <div className="flex items-center gap-1.5">
                            <span className="text-sm">{t.icon}</span>
                            <span
                                className="text-xs font-medium truncate"
                                style={{ color: t.bg === '#ffffff' || t.bg.startsWith('#f') ? '#171717' : '#fafafa' }}
                            >
                                {t.name}
                            </span>
                        </div>

                        {/* Active Indicator */}
                        {theme === id && (
                            <div className="absolute top-1.5 right-1.5 p-0.5 rounded-full bg-(--color-primary)">
                                <Check className="h-2.5 w-2.5 text-white" />
                            </div>
                        )}
                    </button>
                ))}
            </div>

            {/* Info */}
            <div className="text-xs text-(--color-text-muted) p-3 rounded-lg bg-(--color-info-soft)">
                💡 Tema tercihiniz bu cihazda kaydedilir.
            </div>
        </div>
    )
}

// ─────────────────────────────────────────────────────────────────────────────
// MEMORY TAB
// ─────────────────────────────────────────────────────────────────────────────

function MemoryTab() {
    return (
        <div className="space-y-4">
            <div className="p-4 rounded-xl bg-(--color-bg) border border-(--color-border)">
                <div className="flex items-center gap-3 mb-2">
                    <Brain className="h-5 w-5 text-(--color-secondary)" />
                    <h3 className="font-medium">Hafıza Yönetimi</h3>
                </div>
                <p className="text-sm text-(--color-text-muted) mb-4">
                    AI'ın hatırladığı bilgileri görüntüle ve düzenle.
                </p>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                        // Open Memory Manager modal
                        document.dispatchEvent(new CustomEvent('open-memory-manager'))
                    }}
                >
                    Hafızayı Yönet
                    <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
            </div>

            <div className="text-xs text-(--color-text-muted) p-3 rounded-lg bg-(--color-info-soft)">
                💡 İpucu: Sohbet sırasında "bunu hatırla" diyerek otomatik hafıza ekleyebilirsiniz.
            </div>
        </div>
    )
}

// ─────────────────────────────────────────────────────────────────────────────
// IMAGE SETTINGS TAB
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// IMAGE SETTINGS TAB
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// IMAGE SETTINGS TAB
// ─────────────────────────────────────────────────────────────────────────────

function ImageSettingsTab() {
    const { imageSettings, setImageSettings } = useSettingsStore()
    const [mode, setMode] = useState<'basic' | 'advanced'>('basic')

    // FIX: Clamp legacy persisted values (e.g. 55) to safe range
    useEffect(() => {
        if (imageSettings.steps > 35) {
            setImageSettings({ steps: 20 })
        }
    }, [imageSettings.steps, setImageSettings])

    // Aspect Ratio presets with dimensions
    const ASPECT_RATIOS = [
        { id: '1:1', label: 'Kare', icon: 'square', w: 1024, h: 1024 },
        { id: '16:9', label: 'Yatay', icon: 'rectangle-horizontal', w: 1216, h: 832 },
        { id: '9:16', label: 'Dikey', icon: 'rectangle-vertical', w: 832, h: 1216 },
        { id: '4:3', label: 'Klasik', icon: 'monitor', w: 1152, h: 896 },
        { id: 'custom', label: 'Özel', icon: 'settings-2', w: 1024, h: 1024 }, // Placeholder dimensions
    ] as const

    const updateRatio = (id: string) => {
        const ratio = ASPECT_RATIOS.find(r => r.id === id)
        if (ratio) {
            if (id !== 'custom') {
                setImageSettings({
                    aspectRatio: id as any,
                    width: ratio.w,
                    height: ratio.h
                })
            } else {
                setImageSettings({ aspectRatio: 'custom' })
            }
        }
    }

    const STYLES = [
        { id: 'realistic', label: 'Gerçekçi', icon: '📷', bg: 'bg-zinc-800' },
        { id: 'anime', label: 'Anime', icon: '🎌', bg: 'bg-pink-900' },
        { id: 'artistic', label: 'Sanatsal', icon: '🎨', bg: 'bg-purple-900' },
        { id: '3d', label: '3D Render', icon: '🔮', bg: 'bg-blue-900' },
        { id: 'sketch', label: 'Çizim', icon: '✏️', bg: 'bg-neutral-600' },
        { id: 'pixel', label: 'Pixel Art', icon: '👾', bg: 'bg-indigo-900' },
    ]

    // Admin configuration placeholder (TODO: Fetch from systemApi)
    const canSeeModels = true

    return (
        <div className="space-y-6">
            {/* Mode Switcher */}
            <div className="flex p-1 bg-(--color-bg-input) rounded-xl">
                <button
                    onClick={() => setMode('basic')}
                    className={cn(
                        "flex-1 py-1.5 text-sm font-medium rounded-lg transition-all",
                        mode === 'basic' ? "bg-(--color-bg-surface) shadow-sm text-(--color-text)" : "text-(--color-text-muted)"
                    )}
                >
                    Basit
                </button>
                <button
                    onClick={() => setMode('advanced')}
                    className={cn(
                        "flex-1 py-1.5 text-sm font-medium rounded-lg transition-all",
                        mode === 'advanced' ? "bg-(--color-bg-surface) shadow-sm text-(--color-text)" : "text-(--color-text-muted)"
                    )}
                >
                    Gelişmiş
                </button>
            </div>

            {mode === 'basic' ? (
                /* BASIC MODE */
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-6"
                >
                    {/* Ratio Selection */}
                    <section>
                        <h3 className="text-sm font-medium mb-3">Resim Oranı</h3>
                        <div className="grid grid-cols-5 gap-2">
                            {ASPECT_RATIOS.map(ratio => (
                                <button
                                    key={ratio.id}
                                    onClick={() => updateRatio(ratio.id)}
                                    className={cn(
                                        "p-2 rounded-xl border transition-all flex flex-col items-center gap-1",
                                        imageSettings.aspectRatio === ratio.id
                                            ? "border-(--color-primary) bg-(--color-primary-soft)"
                                            : "border-(--color-border) hover:border-(--color-primary)/50"
                                    )}
                                >
                                    <div className={cn(
                                        "border-2 border-current opacity-60 rounded-sm mb-1",
                                        ratio.id === '1:1' ? "w-6 h-6" :
                                            ratio.id === '16:9' ? "w-8 h-4.5 mt-1.5" :
                                                ratio.id === '9:16' ? "w-4.5 h-8" :
                                                    ratio.id === 'custom' ? "w-6 h-6 border-dashed" : "w-7 h-5 mt-1"
                                    )} />
                                    <span className="text-[10px] font-medium truncate w-full text-center">{ratio.label}</span>
                                </button>
                            ))}
                        </div>

                        {/* Custom Resolution Inputs */}
                        {imageSettings.aspectRatio === 'custom' && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className="grid grid-cols-2 gap-3 mt-3 overflow-hidden"
                            >
                                <div className="space-y-1">
                                    <label className="text-xs text-(--color-text-muted)">Genişlik (px)</label>
                                    <input
                                        type="number"
                                        value={imageSettings.width}
                                        onChange={(e) => setImageSettings({ width: Number(e.target.value) })}
                                        className="w-full p-2 rounded-lg bg-(--color-bg-input) border border-(--color-border) text-sm"
                                        step={64}
                                        min={256}
                                        max={1536}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs text-(--color-text-muted)">Yükseklik (px)</label>
                                    <input
                                        type="number"
                                        value={imageSettings.height}
                                        onChange={(e) => setImageSettings({ height: Number(e.target.value) })}
                                        className="w-full p-2 rounded-lg bg-(--color-bg-input) border border-(--color-border) text-sm"
                                        step={64}
                                        min={256}
                                        max={1536}
                                    />
                                </div>
                            </motion.div>
                        )}
                    </section>

                    {/* Styles */}
                    <section>
                        <h3 className="text-sm font-medium mb-3">Görsel Stil</h3>
                        <div className="grid grid-cols-3 gap-2">
                            {STYLES.map(style => (
                                <button
                                    key={style.id}
                                    onClick={() => setImageSettings({ defaultStyle: style.id as any })}
                                    className={cn(
                                        "relative overflow-hidden group p-3 h-20 rounded-xl border transition-all text-left flex flex-col justify-end",
                                        imageSettings.defaultStyle === style.id
                                            ? "border-(--color-primary) ring-1 ring-(--color-primary)"
                                            : "border-(--color-border) hover:border-(--color-primary)/50"
                                    )}
                                >
                                    <div className={cn("absolute inset-0 opacity-20 transition-opacity group-hover:opacity-30", style.bg)} />
                                    <span className="relative z-10 text-xl mb-1 block">{style.icon}</span>
                                    <span className="relative z-10 text-xs font-medium leading-none">{style.label}</span>
                                </button>
                            ))}
                        </div>
                    </section>

                    {/* Quality Switch */}
                    <section className="p-3 bg-(--color-bg-surface) border border-(--color-border) rounded-xl flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className={cn(
                                "p-2 rounded-lg",
                                imageSettings.qualityMode === 'hd' ? "bg-amber-500/10 text-amber-500" : "bg-emerald-500/10 text-emerald-500"
                            )}>
                                {imageSettings.qualityMode === 'hd' ? <Sparkles className="h-5 w-5" /> : <Monitor className="h-5 w-5" />}
                            </div>
                            <div>
                                <div className="text-sm font-medium">
                                    {imageSettings.qualityMode === 'hd' ? 'Yüksek Kalite (HD)' : 'Hızlı Üretim (Draft)'}
                                </div>
                                <div className="text-xs text-(--color-text-muted)">
                                    {imageSettings.qualityMode === 'hd' ? 'Daha detaylı (35 adım)' : 'Daha hızlı (20 adım)'}
                                </div>
                            </div>
                        </div>
                        <button
                            onClick={() => {
                                const newMode = imageSettings.qualityMode === 'hd' ? 'draft' : 'hd'
                                setImageSettings({
                                    qualityMode: newMode,
                                    steps: newMode === 'hd' ? 35 : 20 // Auto adjust steps based on preference
                                })
                            }}
                            className={cn(
                                "relative w-12 h-6 rounded-full transition-colors",
                                imageSettings.qualityMode === 'hd' ? "bg-(--color-primary)" : "bg-(--color-border)"
                            )}
                        >
                            <span className={cn(
                                "absolute top-1 w-4 h-4 rounded-full bg-white transition-all shadow-sm",
                                imageSettings.qualityMode === 'hd' ? "left-7" : "left-1"
                            )} />
                        </button>
                    </section>
                </motion.div>
            ) : (
                /* ADVANCED MODE */
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-4"
                >
                    {/* Model Selection - Conditionally Visible */}
                    {canSeeModels && (
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-(--color-text-muted)">Model Checkpoint</label>
                            <select
                                value={imageSettings.model}
                                onChange={(e) => setImageSettings({ model: e.target.value })}
                                className="w-full p-2 rounded-lg bg-(--color-bg-input) border border-(--color-border) text-sm"
                            >
                                <option value="Generic (SDXL)">Generic (SDXL)</option>
                                <option value="Juggernaut XL">Juggernaut XL</option>
                                <option value="DreamShaper 8">DreamShaper 8</option>
                                <option value="RealVisXL">RealVisXL</option>
                                <option value="Animagine XL">Animagine XL</option>
                            </select>
                        </div>
                    )}

                    <div className="space-y-4">
                        <div>
                            <div className="flex justify-between mb-2">
                                <label className="text-xs font-medium text-(--color-text-muted)">Üretim Adımları (Steps)</label>
                                <span className="text-xs font-mono">{imageSettings.steps}</span>
                            </div>
                            <input
                                type="range"
                                min="0" // Changed directly here
                                max="35"
                                step="1"
                                value={imageSettings.steps}
                                onChange={(e) => setImageSettings({ steps: parseInt(e.target.value) })}
                                className="w-full accent-(--color-primary)"
                            />
                            <div className="flex justify-between text-[10px] text-(--color-text-muted) px-1">
                                <span>Hızlı</span>
                                <span>Kaliteli</span>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-(--color-text-muted)">Sampler</label>
                            <select
                                value={imageSettings.sampler}
                                onChange={(e) => setImageSettings({ sampler: e.target.value })}
                                className="w-full p-2 rounded-lg bg-(--color-bg-input) border border-(--color-border) text-sm"
                            >
                                <option value="Euler a">Euler a</option>
                                <option value="DPM++ 2M Karras">DPM++ 2M Karras</option>
                                <option value="DPM++ SDE Karras">DPM++ SDE Karras</option>
                                <option value="UniPC">UniPC</option>
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-(--color-text-muted)">Seed</label>
                            <input
                                type="number"
                                value={imageSettings.seed}
                                onChange={(e) => setImageSettings({ seed: parseInt(e.target.value) })}
                                placeholder="-1"
                                className="w-full p-2 rounded-lg bg-(--color-bg-input) border border-(--color-border) text-sm"
                            />
                            <p className="text-[10px] text-(--color-text-muted)">-1 = Rastgele</p>
                        </div>
                    </div>
                </motion.div>
            )}
        </div>
    )
}

// ─────────────────────────────────────────────────────────────────────────────
// FUTURE PLANS TAB
// ─────────────────────────────────────────────────────────────────────────────

function FuturePlansTab() {
    const { futurePlans, addFuturePlan, removeFuturePlan } = useSettingsStore()
    const [newPlanText, setNewPlanText] = useState('')
    const [newPlanDate, setNewPlanDate] = useState('')

    const handleAdd = () => {
        if (!newPlanText.trim() || !newPlanDate) return

        addFuturePlan({
            text: newPlanText.trim(),
            date: newPlanDate,
        })

        setNewPlanText('')
        setNewPlanDate('')
    }

    return (
        <div className="space-y-4">
            <div className="p-4 rounded-xl bg-(--color-bg) border border-(--color-border)">
                <h3 className="font-medium mb-2 flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-(--color-accent)" />
                    Gelecek Planları
                </h3>
                <p className="text-sm text-(--color-text-muted) mb-4">
                    AI bu planları hatırlayacak ve uygun zamanda hatırlatacak.
                </p>

                {/* Add New Plan */}
                <div className="space-y-2 mb-4">
                    <Input
                        placeholder="Plan açıklaması..."
                        value={newPlanText}
                        onChange={(e) => setNewPlanText(e.target.value)}
                    />
                    <div className="flex gap-2">
                        <input
                            type="date"
                            value={newPlanDate}
                            onChange={(e) => setNewPlanDate(e.target.value)}
                            className="flex-1 px-3 py-2 rounded-lg border border-(--color-border) bg-(--color-bg-input) text-sm"
                        />
                        <Button
                            variant="primary"
                            size="sm"
                            onClick={handleAdd}
                            disabled={!newPlanText.trim() || !newPlanDate}
                        >
                            <Plus className="h-4 w-4" />
                            Ekle
                        </Button>
                    </div>
                </div>

                {/* Plan List */}
                {futurePlans.length === 0 ? (
                    <div className="text-center py-6 text-(--color-text-muted)">
                        <Calendar className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Henüz plan eklenmemiş</p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {futurePlans.map(plan => (
                            <div
                                key={plan.id}
                                className="flex items-center gap-3 p-3 rounded-lg bg-(--color-bg-surface) border border-(--color-border)"
                            >
                                <Calendar className="h-4 w-4 text-(--color-text-muted) shrink-0" />
                                <div className="flex-1 min-w-0">
                                    <div className="text-sm truncate">{plan.text}</div>
                                    <div className="text-xs text-(--color-text-muted)">
                                        {new Date(plan.date).toLocaleDateString('tr-TR', {
                                            day: 'numeric',
                                            month: 'long',
                                            year: 'numeric'
                                        })}
                                    </div>
                                </div>
                                <button
                                    onClick={() => removeFuturePlan(plan.id)}
                                    className="p-1.5 rounded hover:bg-(--color-error-soft) text-(--color-text-muted) hover:text-(--color-error)"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="text-xs text-(--color-text-muted) p-3 rounded-lg bg-(--color-warning-soft)">
                ⚠️ Planlar cihazınızda saklanır. AI bunları sohbet sırasında kullanır.
            </div>
        </div>
    )
}
