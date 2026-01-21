
import { NavLink } from 'react-router-dom'
import {
    LayoutDashboard,
    BrainCircuit,
    Users,
    Palette,
    LineChart,
    Settings,
    ShieldAlert,
    LogOut,
    Radio,
    Database,
    Bot,
    CreditCard,
    History,
    ThumbsDown,
    Key,
    Zap,
    Ticket // Added for Invites
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { authApi } from '@/api/client'

const ADMIN_LINKS = [
    { to: '/admin/dashboard', icon: LayoutDashboard, label: 'Mission Control' },
    { to: '/admin/ai-core', icon: BrainCircuit, label: 'AI Orkestrasyonu' },
    { to: '/admin/knowledge', icon: Database, label: 'Bilgi Bankası (RAG)' },
    { to: '/admin/users', icon: Users, label: 'Kullanıcılar & Ekip' },
    { to: '/admin/cms', icon: Palette, label: 'Marka & CMS' },
    { to: '/admin/analytics', icon: LineChart, label: 'İstatistikler' },
    { to: '/admin/security', icon: ShieldAlert, label: 'Güvenlik & Log' },
    { to: '/admin/invites', icon: Ticket, label: 'Davet Kodları' },
    { to: '/admin/broadcast', icon: Radio, label: 'Anons Kulesi' },
    { to: '/admin/settings', icon: Settings, label: 'Sistem Ayarları' },
    { to: '/admin/agents', icon: Bot, label: 'Ajan Fabrikası' },
    { to: '/admin/finops', icon: CreditCard, label: 'FinOps & Bütçe' },
    { to: '/admin/quality', icon: ThumbsDown, label: 'RLHF & Kalite' },
    { to: '/admin/developer', icon: Key, label: 'API Gateway' },
    { to: '/admin/performance', icon: Zap, label: 'Smart Cache' },
    { to: '/admin/backup', icon: History, label: 'Zaman Makinesi' },
]

export function AdminSidebar() {
    const handleLogout = async () => {
        try {
            await authApi.logout()
            window.location.href = '/login'
        } catch (error) {
            console.error('Logout failed', error)
        }
    }

    return (
        <aside className="w-64 h-full border-r border-white/10 bg-black/40 backdrop-blur-xl flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-white/10">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-red-600 flex items-center justify-center shadow-lg shadow-red-500/20">
                        <ShieldAlert className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h2 className="font-bold text-white text-lg tracking-tight">GOD MODE</h2>
                        <p className="text-xs text-gray-500 font-mono">v4.2.0-Enterprise</p>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                {ADMIN_LINKS.map((link) => (
                    <NavLink
                        key={link.to}
                        to={link.to}
                        className={({ isActive }) => cn(
                            "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group",
                            isActive
                                ? "bg-white/10 text-white shadow-lg shadow-white/5"
                                : "text-gray-400 hover:text-white hover:bg-white/5"
                        )}
                    >
                        <link.icon className="w-5 h-5 transition-colors" />
                        <span className="font-medium text-sm">{link.label}</span>
                    </NavLink>
                ))}
            </nav>

            {/* Footer / User */}
            <div className="p-4 border-t border-white/10 space-y-2">
                <div className="flex items-center justify-between px-4 py-2 rounded-lg bg-green-500/10 border border-green-500/20">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs font-medium text-green-400">System Healthy</span>
                    </div>
                    <span className="text-[10px] text-green-500/70 font-mono">100%</span>
                </div>

                <button
                    onClick={handleLogout}
                    className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
                >
                    <LogOut className="w-5 h-5" />
                    <span className="font-medium text-sm">Çıkış Yap</span>
                </button>
            </div>
        </aside>
    )
}
