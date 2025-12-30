/**
 * Header Component
 * 
 * Top navigation bar - responsive design
 */

import { Menu, Sparkles, Search } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui'
import { cn } from '@/lib/utils'

interface HeaderProps {
    title: string
    onMenuClick?: () => void
    onSearchClick?: () => void
    showBrand?: boolean
}

export function Header({ title, onMenuClick, onSearchClick, showBrand = true }: HeaderProps) {
    const navigate = useNavigate()

    return (
        <header className={cn(
            "h-15 px-4 flex items-center justify-between",
            "border-b border-(--color-border)",
            "bg-(--color-bg)/80 backdrop-blur-xl",
            "sticky top-0 z-10 safe-area-top"
        )}>
            {/* Left */}
            <div className="flex items-center gap-3">
                {/* Menu Toggle */}
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onMenuClick}
                    aria-label="Menü"
                >
                    <Menu className="h-5 w-5" />
                </Button>

                {/* Title with icon */}
                {showBrand && (
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-(--gradient-brand) flex items-center justify-center">
                            <Sparkles className="h-4 w-4 text-white" />
                        </div>
                        <h1 className="font-display font-semibold hidden sm:block">{title}</h1>
                    </div>
                )}
            </div>

            {/* Center - Spacer for balance if needed, or just empty */}
            <div className="flex-1" />

            {/* Right */}
            <div className="flex items-center gap-2">
                {/* Search Button */}
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onSearchClick}
                    aria-label="Ara"
                    className="hidden sm:flex items-center gap-2 text-(--color-text-muted)"
                >
                    <Search className="h-4 w-4" />
                    <span className="text-xs">Ara</span>
                    <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-(--color-bg) border border-(--color-border)">
                        Ctrl+K
                    </kbd>
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onSearchClick}
                    aria-label="Ara"
                    className="sm:hidden"
                >
                    <Search className="h-5 w-5" />
                </Button>
            </div>
        </header>
    )
}
