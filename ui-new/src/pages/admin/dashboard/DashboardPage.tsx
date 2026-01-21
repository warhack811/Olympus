
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar
} from 'recharts'
import { Activity, Cpu, Server, Users as UsersIcon, Zap } from 'lucide-react'
import { SystemControls } from '@/components/admin/dashboard/SystemControls'
import { ApiUsageStats } from '@/components/admin/dashboard/ApiUsageStats'
import { ApiKeysManager } from '@/components/admin/dashboard/ApiKeysManager'

const MOCK_DATA = [
    { name: '00:00', cpu: 12, gpu: 5, ram: 40 },
    { name: '04:00', cpu: 18, gpu: 10, ram: 42 },
    { name: '08:00', cpu: 45, gpu: 30, ram: 55 },
    { name: '12:00', cpu: 65, gpu: 70, ram: 65 },
    { name: '16:00', cpu: 55, gpu: 50, ram: 60 },
    { name: '20:00', cpu: 30, gpu: 20, ram: 45 },
    { name: '23:59', cpu: 20, gpu: 12, ram: 42 },
]

export function DashboardPage() {
    return (
        <div className="space-y-6">
            {/* Top Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    title="Aktif Kullanıcı"
                    value="124"
                    sub="+12% (24s)"
                    icon={UsersIcon}
                    color="text-blue-500"
                    bg="bg-blue-500/10"
                />
                <StatCard
                    title="GPU Sıcaklığı"
                    value="64°C"
                    sub="RTX 4090 (Safe)"
                    icon={Zap}
                    color="text-green-500"
                    bg="bg-green-500/10"
                />
                <StatCard
                    title="VRAM Kullanımı"
                    value="18.2 GB"
                    sub="24 GB Total"
                    icon={Cpu}
                    color="text-purple-500"
                    bg="bg-purple-500/10"
                />
                <StatCard
                    title="Sistem Yükü"
                    value="42%"
                    sub="Normal Seviye"
                    icon={Activity}
                    color="text-orange-500"
                    bg="bg-orange-500/10"
                />
            </div>

            {/* Main Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 2/3 Width - Main Load Graph */}
                <div className="lg:col-span-2 bg-white/5 border border-white/10 rounded-2xl p-6">
                    <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                        <Server className="w-5 h-5 text-gray-400" />
                        Sunucu Yükü (24s)
                    </h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={MOCK_DATA}>
                                <defs>
                                    <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="colorGpu" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#82ca9d" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                                <XAxis dataKey="name" stroke="#666" fontSize={12} tickLine={false} />
                                <YAxis stroke="#666" fontSize={12} tickLine={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                                    itemStyle={{ color: '#ccc' }}
                                />
                                <Area type="monotone" dataKey="cpu" stroke="#8884d8" fillOpacity={1} fill="url(#colorCpu)" />
                                <Area type="monotone" dataKey="gpu" stroke="#82ca9d" fillOpacity={1} fill="url(#colorGpu)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* 1/3 Width - Quick Actions or Logs */}
                <div className="space-y-6">
                    {/* System Controls */}
                    <SystemControls />

                    {/* Live Logs */}
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                        <h3 className="text-lg font-semibold mb-4 text-white">Canlı Log (Matrix)</h3>
                        <div className="font-mono text-xs text-green-400 bg-black/50 p-4 rounded-lg h-[200px] overflow-hidden relative">
                            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/80 pointer-events-none" />
                            <p>[INFO] User 'ahmet' connected (192.168.1.4)</p>
                            <p>[INFO] Generating image 'cyberpunk cat'...</p>
                            <p className="text-yellow-400">[WARN] VRAM usage spike detected (19GB)</p>
                            <p>[INFO] RAG: Found 3 chunks in 'kurallar.pdf'</p>
                            <p>[INFO] Reply generated in 1.2s (Groq)</p>
                            <p>[INFO] New chat session started (ID: 9942)</p>
                            <p>[INFO] WebSocket handshake complete</p>
                            <br />
                            <p className="animate-pulse">_</p>
                        </div>
                    </div>
                </div>
            </div>
            {/* API Management Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ApiUsageStats />
                <ApiKeysManager />
            </div>
        </div>
    )
}

function StatCard({ title, value, sub, icon: Icon, color, bg }: any) {
    return (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-colors">
            <div className="flex justify-between items-start">
                <div>
                    <p className="text-sm text-gray-400">{title}</p>
                    <h4 className="text-2xl font-bold mt-2 text-white">{value}</h4>
                    <span className="text-xs text-green-400 flex items-center gap-1 mt-1">
                        {sub}
                    </span>
                </div>
                <div className={`p-3 rounded-xl ${bg}`}>
                    <Icon className={`w-6 h-6 ${color}`} />
                </div>
            </div>
        </div>
    )
}
