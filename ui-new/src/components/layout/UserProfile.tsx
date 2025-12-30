
import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Settings, LogOut, Shield, ChevronUp, MoreHorizontal, Download, Search, Brain, Image } from 'lucide-react'
import { useUserStore, useSettingsStore } from '@/stores'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Avatar } from '@/components/ui'

interface UserProfileProps {
    onLogout?: () => void
    onExportOpen?: () => void
    onSettingsOpen?: () => void
    onItemSelect?: () => void
    onSearchOpen?: () => void
    onMemoryOpen?: () => void
    onGalleryOpen?: () => void
}

export function UserProfile({ onLogout, onExportOpen, onSettingsOpen, onItemSelect, onSearchOpen, onMemoryOpen, onGalleryOpen }: UserProfileProps) {
    const [isOpen, setIsOpen] = useState(false)
    const menuRef = useRef<HTMLDivElement>(null)
    const buttonRef = useRef<HTMLButtonElement>(null)
    const navigate = useNavigate()

    const user = useUserStore((state) => state.user)
    const openSettings = useSettingsStore((state) => state.openSettings)

    // Fallback: Check for 'admin' role OR specific username 'admin' OR id '1'
    const isAdmin = user?.role === 'admin' || user?.username === 'admin' || user?.id === '1'

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (
                menuRef.current &&
                !menuRef.current.contains(event.target as Node) &&
                buttonRef.current &&
                !buttonRef.current.contains(event.target as Node)
            ) {
                setIsOpen(false)
            }
        }

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside)
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [isOpen])

    const handleLogout = () => {
        setIsOpen(false)
        onItemSelect?.()
        if (onLogout) {
            onLogout()
        } else {
            window.location.href = '/ui/login.html'
        }
    }

    const handleSettings = () => {
        setIsOpen(false)
        onItemSelect?.()
        // Original Sidebar behavior: always use store's openSettings
        openSettings()
    }

    return (
        <div className="relative mt-auto pt-2 border-t border-(--color-border)">
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        ref={menuRef}
                        initial={{ opacity: 0, scale: 0.95, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 10 }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        className={cn(
                            "absolute bottom-[calc(100%+8px)] left-0 w-full",
                            "bg-(--color-bg-surface) border border-(--color-border)",
                            "rounded-xl shadow-lg backdrop-blur-xl overflow-hidden",
                            "z-50 p-1.5"
                        )}
                    >
                        <div className="px-3 py-2 mb-1 border-b border-(--color-border/50)">
                            <p className="text-sm font-medium text-(--color-text)">{user?.username || 'Kullanıcı'}</p>
                            <p className="text-xs text-(--color-text-muted) truncate">{user?.displayName || user?.role || 'Üye'}</p>
                        </div>

                        <div className="space-y-0.5">
                            {/* Quick Actions */}
                            <MenuItem
                                icon={<Search className="w-4 h-4" />}
                                label="Ara"
                                onClick={() => { setIsOpen(false); onSearchOpen?.(); }}
                            />
                            <MenuItem
                                icon={<Brain className="w-4 h-4" />}
                                label="Hafıza"
                                onClick={() => { setIsOpen(false); onMemoryOpen?.(); onItemSelect?.(); }}
                            />
                            <MenuItem
                                icon={<Image className="w-4 h-4" />}
                                label="Galeri"
                                onClick={() => { setIsOpen(false); onGalleryOpen?.(); onItemSelect?.(); }}
                            />

                            <div className="h-px bg-(--color-border/50) my-1" />

                            {/* Settings & Export */}
                            <MenuItem
                                icon={<Settings className="w-4 h-4" />}
                                label="Ayarlar"
                                onClick={handleSettings}
                            />

                            <MenuItem
                                icon={<Download className="w-4 h-4" />}
                                label="Dışa/İçe Aktar"
                                onClick={() => { setIsOpen(false); onExportOpen?.(); onItemSelect?.(); }}
                            />

                            {isAdmin && (
                                <MenuItem
                                    icon={<Shield className="w-4 h-4" />}
                                    label="Admin Paneli"
                                    onClick={() => { setIsOpen(false); navigate('/admin'); onItemSelect?.(); }}
                                />
                            )}

                            <div className="h-px bg-(--color-border/50) my-1" />

                            <MenuItem
                                icon={<LogOut className="w-4 h-4" />}
                                label="Çıkış Yap"
                                variant="danger"
                                onClick={handleLogout}
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            <button
                ref={buttonRef}
                onClick={() => setIsOpen(!isOpen)}
                className={cn(
                    "w-full flex items-center gap-3 p-2 rounded-xl transition-all duration-200",
                    "hover:bg-(--color-bg-surface-hover) group",
                    isOpen && "bg-(--color-bg-surface-hover)"
                )}
            >
                <Avatar
                    className="h-9 w-9 border border-(--color-border/50) shadow-sm"
                    src={user?.avatarUrl}
                    fallback={user?.username?.[0]?.toUpperCase() || 'U'}
                />

                <div className="flex-1 text-left min-w-0">
                    <p className="text-sm font-medium text-(--color-text) truncate group-hover:text-(--color-primary) transition-colors">
                        {user?.username || 'Hesap'}
                    </p>
                    <p className="text-[10px] text-(--color-text-muted) truncate">
                        {isAdmin ? 'Yönetici' : 'Standart Üye'}
                    </p>
                </div>

                <div className="text-(--color-text-muted) group-hover:text-(--color-text) transition-colors">
                    {isOpen ? <ChevronUp className="w-4 h-4" /> : <MoreHorizontal className="w-4 h-4" />}
                </div>
            </button>
        </div>
    )
}

interface MenuItemProps {
    icon: React.ReactNode
    label: string
    onClick: () => void
    variant?: 'default' | 'danger'
}

function MenuItem({ icon, label, onClick, variant = 'default' }: MenuItemProps) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-colors",
                variant === 'danger'
                    ? "text-(--color-error) hover:bg-(--color-error-soft)"
                    : "text-(--color-text-secondary) hover:text-(--color-text) hover:bg-(--color-bg-surface-hover)"
            )}
        >
            {icon}
            <span>{label}</span>
        </button>
    )
}
