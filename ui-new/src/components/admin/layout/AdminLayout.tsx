
import { Outlet } from 'react-router-dom'
import { AdminSidebar } from './AdminSidebar'

import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/Sheet'
import { Menu } from 'lucide-react'

export function AdminLayout() {
    return (
        <div className="h-screen w-full flex bg-[#0a0a0a] text-gray-100 overflow-hidden font-sans selection:bg-red-500/30">
            {/* Desktop Sidebar (Hidden on mobile) */}
            <div className="hidden md:flex h-full">
                <AdminSidebar />
            </div>

            {/* Main Content Area */}
            <main className="flex-1 flex flex-col h-full overflow-hidden relative">

                {/* Top Bar */}
                <header className="h-16 border-b border-white/10 flex items-center justify-between px-4 md:px-8 bg-black/20 backdrop-blur-sm z-10">
                    <div className="flex items-center gap-3">
                        {/* Mobile Sidebar Trigger */}
                        <Sheet>
                            <SheetTrigger className="md:hidden p-2 hover:bg-white/10 rounded-lg">
                                <Menu className="w-5 h-5 text-gray-300" />
                            </SheetTrigger>
                            <SheetContent side="left" className="p-0 w-72 bg-black/95 border-r border-white/10">
                                <AdminSidebar />
                            </SheetContent>
                        </Sheet>

                        <h1 className="font-semibold text-lg text-gray-200">Yönetim Paneli</h1>
                    </div>

                    <div className="flex items-center gap-6">
                        {/* Status Indicator */}
                        <div className="flex items-center gap-2">
                            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_10px_#22c55e]" />
                            <span className="text-xs font-mono text-green-500 hidden md:block">SYSTEM ONLINE</span>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-3 border-l border-white/10 pl-6 h-8">
                            <a
                                href="/"
                                className="text-sm text-gray-400 hover:text-white flex items-center gap-2 transition-colors"
                            >
                                <span>← <span className="hidden md:inline">Sohbete Dön</span></span>
                            </a>
                        </div>
                    </div>
                </header>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto p-4 md:p-8 relative">
                    <Outlet />
                </div>
            </main>
        </div>
    )
}
