/**
 * ChatLayout Component
 * 
 * Main layout with responsive sidebar (desktop) and drawer (mobile)
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useChatStore, useBranding } from '@/stores'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { ChatArea } from '@/components/chat/ChatArea'
import {
    MobileDrawer,
    ThemePicker,
    MemoryManager,
    ImageGallery,
    ConversationSearch,
    ExportImport
} from '@/components/common'
import { OrchDebugPanel } from '@/components/chat/OrchDebugPanel'
import { useIsMobile, useAuth } from '@/hooks'
import { cn } from '@/lib/utils'

export function ChatLayout() {
    const isSidebarOpen = useChatStore((state) => state.isSidebarOpen)
    const branding = useBranding()
    const isMobile = useIsMobile()
    const { logout } = useAuth()
    const showHeaderBrand = isMobile || !isSidebarOpen

    // Mobile drawer state
    const [isDrawerOpen, setDrawerOpen] = useState(false)

    // Modal states - managed here to be accessible from Sidebar
    const [isThemePickerOpen, setThemePickerOpen] = useState(false)
    const [isMemoryManagerOpen, setMemoryManagerOpen] = useState(false)
    const [isGalleryOpen, setGalleryOpen] = useState(false)
    const [isSearchOpen, setSearchOpen] = useState(false)
    const [isExportOpen, setExportOpen] = useState(false)

    const handleMenuToggle = () => {
        if (isMobile) {
            setDrawerOpen(!isDrawerOpen)
        } else {
            useChatStore.getState().toggleSidebar()
        }
    }

    // Sidebar navigation handlers
    const handleMemoryOpen = () => setMemoryManagerOpen(true)
    const handleGalleryOpen = () => setGalleryOpen(true)
    const handleSettingsOpen = () => setThemePickerOpen(true)
    const handleSearchOpen = () => setSearchOpen(true)
    const handleExportOpen = () => setExportOpen(true)

    // Search navigation handler
    const handleSearchNavigate = (conversationId: string, messageId?: string) => {
        // Set conversation and close search
        useChatStore.getState().setCurrentConversation(conversationId)
        // TODO: Scroll to message if messageId provided
    }

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Ctrl+K or Cmd+K to open search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault()
                setSearchOpen(true)
            }
        }

        document.addEventListener('keydown', handleKeyDown)
        return () => document.removeEventListener('keydown', handleKeyDown)
    }, [])

    // Listen for custom events from BottomNav/CommandPalette
    useEffect(() => {
        const handleOpenMemory = () => setMemoryManagerOpen(true)
        const handleOpenGallery = () => setGalleryOpen(true)
        const handleOpenTheme = () => setThemePickerOpen(true)

        document.addEventListener('open-memory-manager', handleOpenMemory)
        document.addEventListener('open-gallery', handleOpenGallery)
        document.addEventListener('open-theme-picker', handleOpenTheme)

        return () => {
            document.removeEventListener('open-memory-manager', handleOpenMemory)
            document.removeEventListener('open-gallery', handleOpenGallery)
            document.removeEventListener('open-theme-picker', handleOpenTheme)
        }
    }, [])

    return (
        <div
            className="flex h-full w-full relative overflow-hidden transition-colors duration-500 bg-(--color-bg) text-(--color-text)"
        >
            {/* ALIVE BACKGROUND EFFECT - Dynamic Theme Colors */}
            <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden" style={{ perspective: '1000px', contain: 'strict' }}>
                <motion.div
                    animate={{
                        scale: [1, 1.25],
                        opacity: [0.08, 0.25] // Reduced for subtlety
                    }}
                    transition={{
                        duration: 10,
                        repeat: Infinity,
                        repeatType: "reverse",
                        ease: "easeInOut"
                    }}
                    className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full blur-[60px] md:blur-[140px] will-change-[transform,opacity]"
                    style={{
                        backgroundColor: 'var(--color-primary)',
                        transform: 'translateZ(0)'
                    }}
                />
                <motion.div
                    animate={{
                        scale: [1, 1.2],
                        opacity: [0.05, 0.18] // Reduced for subtlety
                    }}
                    transition={{
                        duration: 12,
                        repeat: Infinity,
                        repeatType: "reverse",
                        ease: "easeInOut",
                        delay: 2
                    }}
                    className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[70%] rounded-full blur-[50px] md:blur-[120px] will-change-[transform,opacity]"
                    style={{
                        backgroundColor: 'var(--color-secondary)',
                        transform: 'translateZ(0)'
                    }}
                />
            </div>

            {/* Desktop Sidebar - Glass Effect */}
            {!isMobile && (
                <AnimatePresence mode="wait">
                    {isSidebarOpen && (
                        <motion.aside
                            initial={{ width: 0, opacity: 0 }}
                            animate={{ width: 280, opacity: 1 }}
                            exit={{ width: 0, opacity: 0 }}
                            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                            className="h-full border-r border-(--color-border) backdrop-blur-lg md:backdrop-blur-3xl overflow-hidden flex-shrink-0 relative z-10"
                            style={{ backgroundColor: 'var(--glass-bg)' }}
                        >
                            <Sidebar
                                onMemoryOpen={handleMemoryOpen}
                                onGalleryOpen={handleGalleryOpen}
                                onSettingsOpen={handleSettingsOpen}
                                onSearchOpen={handleSearchOpen}
                                onExportOpen={handleExportOpen}
                                onLogout={logout}
                            />
                        </motion.aside>
                    )}
                </AnimatePresence>
            )}

            {/* Mobile Drawer */}
            {isMobile && (
                <MobileDrawer
                    isOpen={isDrawerOpen}
                    onClose={() => setDrawerOpen(false)}
                    side="left"
                >
                    <Sidebar
                        onItemSelect={() => setDrawerOpen(false)}
                        onMemoryOpen={handleMemoryOpen}
                        onGalleryOpen={handleGalleryOpen}
                        onSettingsOpen={handleSettingsOpen}
                        onSearchOpen={handleSearchOpen}
                        onExportOpen={handleExportOpen}
                        onLogout={logout}
                    />
                </MobileDrawer>
            )}

            {/* Main Content - Transparent to show background */}
            <main className={cn(
                "flex-1 flex flex-col h-full overflow-hidden relative z-10",
                "transition-all duration-200"
            )}>
                {/* Header */}
                <Header
                    title={branding.displayName}
                    onMenuClick={handleMenuToggle}
                    onSearchClick={handleSearchOpen}
                    showBrand={showHeaderBrand}
                />

                {/* Chat Area - Ensure it uses transparent backgrounds too */}
                <ChatArea />
            </main>

            {/* Modals - Rendered in ChatLayout for Sidebar access */}
            <ThemePicker
                isOpen={isThemePickerOpen}
                onClose={() => setThemePickerOpen(false)}
            />
            <MemoryManager
                isOpen={isMemoryManagerOpen}
                onClose={() => setMemoryManagerOpen(false)}
            />
            <ImageGallery
                isOpen={isGalleryOpen}
                onClose={() => setGalleryOpen(false)}
            />
            <ConversationSearch
                isOpen={isSearchOpen}
                onClose={() => setSearchOpen(false)}
                onNavigate={handleSearchNavigate}
            />
            <ExportImport
                isOpen={isExportOpen}
                onClose={() => setExportOpen(false)}
            />

            {/* DEV-ONLY ORCHESTRATOR DEBUG PANEL */}
            <OrchDebugPanel />
        </div>
    )
}
