/**
 * Settings Store
 * 
 * Centralized state for:
 * - Persona/Mode selection
 * - Feature toggles (web, image)
 * - Response style preferences
 * - Image generation settings
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────

export type PersonaMode =
    | 'professional'
    | 'friendly'
    | 'kanka'
    | 'sincere'
    | 'creative'
    | 'expert'
    | 'teacher'
    | 'girlfriend'
    | 'standard'

export type ResponseTone = 'formal' | 'casual' | 'playful' | 'professional'
export type ResponseLength = 'short' | 'normal' | 'detailed'
export type EmojiLevel = 'none' | 'low' | 'medium' | 'high'

export interface Persona {
    name: PersonaMode
    displayName: string
    icon: string
    description: string
}

export interface ResponseStyle {
    tone: ResponseTone
    length: ResponseLength
    emojiLevel: EmojiLevel
    useMarkdown: boolean
    useCodeBlocks: boolean
}

export interface ImageSettings {
    // Basic Settings
    aspectRatio: '1:1' | '16:9' | '9:16' | '4:3' | '3:4' | 'custom'
    qualityMode: 'draft' | 'hd'
    defaultStyle: 'realistic' | 'artistic' | 'anime' | 'sketch' | 'pixel' | '3d'
    autoEnhance: boolean

    // Advanced Forge Settings (Power User)
    width: number
    height: number
    model: string
    steps: number
    sampler: string
    seed: number
    negativePrompt: string
}

export interface FuturePlan {
    id: string
    text: string
    date: string
    remindBefore?: number // days before
    isRecurring?: boolean
    createdAt: string
}

interface SettingsState {
    // Persona/Mode
    activePersona: PersonaMode
    personas: Persona[]

    // Feature Toggles
    webSearchEnabled: boolean
    imageGenEnabled: boolean

    // Response Style
    responseStyle: ResponseStyle

    // Image Settings
    imageSettings: ImageSettings

    // Future Plans (local, synced to backend on add)
    futurePlans: FuturePlan[]
    featureFlags: {
        FE_METADATA_FIRST_IMAGE_RENDER: boolean
    }

    // UI State
    settingsOpen: boolean
    activeSettingsTab: 'style' | 'appearance' | 'memory' | 'image' | 'plans' | 'files'

    // Actions
    setActivePersona: (persona: PersonaMode) => void
    setWebSearchEnabled: (enabled: boolean) => void
    setImageGenEnabled: (enabled: boolean) => void
    setResponseStyle: (style: Partial<ResponseStyle>) => void
    setImageSettings: (settings: Partial<ImageSettings>) => void
    addFuturePlan: (plan: Omit<FuturePlan, 'id' | 'createdAt'>) => void
    removeFuturePlan: (id: string) => void
    updateFuturePlan: (id: string, updates: Partial<FuturePlan>) => void
    openSettings: (tab?: 'style' | 'appearance' | 'memory' | 'image' | 'plans' | 'files') => void
    closeSettings: () => void
    setActiveSettingsTab: (tab: 'style' | 'appearance' | 'memory' | 'image' | 'plans' | 'files') => void
}

// ─────────────────────────────────────────────────────────────────────────────
// DEFAULT VALUES
// ─────────────────────────────────────────────────────────────────────────────

export const PERSONAS: Persona[] = [
    { name: 'standard', displayName: 'Standart', icon: '🤖', description: 'Dengeli ve zeki' },
    { name: 'professional', displayName: 'Profesyonel', icon: '👔', description: 'Kurumsal ve ciddi' },
    { name: 'friendly', displayName: 'Arkadaşça', icon: '🤝', description: 'Nazik ve yardımcı' },
    { name: 'kanka', displayName: 'Kanka', icon: '😊', description: 'Samimi ve eğlenceli' },
    { name: 'sincere', displayName: 'İçten', icon: '🤝', description: 'Duygusal ve dürüst' },
    { name: 'expert', displayName: 'Uzman', icon: '🔬', description: 'Teknik ve detaycı' },
    { name: 'teacher', displayName: 'Öğretmen', icon: '📚', description: 'Sabırlı ve açıklayıcı' },
    { name: 'creative', displayName: 'Yaratıcı', icon: '🎨', description: 'İlham verici ve sanatsal' },
    { name: 'girlfriend', displayName: 'Sevgili', icon: '💕', description: 'Sıcak ve sevecen' },
]

const DEFAULT_RESPONSE_STYLE: ResponseStyle = {
    tone: 'casual',
    length: 'normal',
    emojiLevel: 'medium',
    useMarkdown: true,
    useCodeBlocks: true,
}

const DEFAULT_IMAGE_SETTINGS: ImageSettings = {
    // Basic
    aspectRatio: '1:1',
    qualityMode: 'draft',
    defaultStyle: 'realistic',
    autoEnhance: true,

    // Advanced
    width: 1024,
    height: 1024,
    model: 'Generic (SDXL)',
    steps: 20,
    sampler: 'Euler a',
    seed: -1,
    negativePrompt: ''
}

// ─────────────────────────────────────────────────────────────────────────────
// STORE
// ─────────────────────────────────────────────────────────────────────────────

export const useSettingsStore = create<SettingsState>()(
    persist(
        (set) => ({
            // Initial State
            activePersona: 'standard',
            personas: PERSONAS,
            webSearchEnabled: true,
            imageGenEnabled: true,
            responseStyle: DEFAULT_RESPONSE_STYLE,
            imageSettings: DEFAULT_IMAGE_SETTINGS,
            futurePlans: [],
            settingsOpen: false,
            activeSettingsTab: 'style',
            featureFlags: {
                FE_METADATA_FIRST_IMAGE_RENDER: true // Default ON as requested
            },

            // Actions
            setActivePersona: (persona) => set({ activePersona: persona }),

            setWebSearchEnabled: (enabled) => set({ webSearchEnabled: enabled }),

            setImageGenEnabled: (enabled) => set({ imageGenEnabled: enabled }),

            setResponseStyle: (style) => set((state) => ({
                responseStyle: { ...state.responseStyle, ...style }
            })),

            setImageSettings: (settings) => set((state) => ({
                imageSettings: { ...state.imageSettings, ...settings }
            })),

            addFuturePlan: (plan) => set((state) => ({
                futurePlans: [
                    ...state.futurePlans,
                    {
                        ...plan,
                        id: `plan-${Date.now()}`,
                        createdAt: new Date().toISOString(),
                    }
                ]
            })),

            removeFuturePlan: (id) => set((state) => ({
                futurePlans: state.futurePlans.filter(p => p.id !== id)
            })),

            updateFuturePlan: (id, updates) => set((state) => ({
                futurePlans: state.futurePlans.map(p =>
                    p.id === id ? { ...p, ...updates } : p
                )
            })),

            openSettings: (tab = 'style') => set({
                settingsOpen: true,
                activeSettingsTab: tab
            }),

            closeSettings: () => set({ settingsOpen: false }),

            setActiveSettingsTab: (tab) => set({ activeSettingsTab: tab }),
        }),
        {
            name: 'mami-settings',
            version: 1,
            migrate: (persistedState: any, version: number) => {
                return persistedState as any
            },
            partialize: (state) => ({
                activePersona: state.activePersona,
                webSearchEnabled: state.webSearchEnabled,
                imageGenEnabled: state.imageGenEnabled,
                responseStyle: state.responseStyle,
                imageSettings: state.imageSettings,
                futurePlans: state.futurePlans,
            }),
        }
    )
)
