
import { CreditCard, DollarSign, TrendingDown, PieChart as PieChartIcon, Zap } from 'lucide-react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts'
import { Button } from '@/components/ui/Button'

// Mock Data
const COST_DATA = [
    { name: 'Ocak', cost: 120 },
    { name: 'Şubat', cost: 150 },
    { name: 'Mart', cost: 180 },
    { name: 'Nisan', cost: 140 },
    { name: 'Mayıs', cost: 210 },
    { name: 'Haziran', cost: 250 },
]

const MODEL_COSTS = [
    { name: 'GPT-4', cost: 150.20, usage: '1.2M Tokens' },
    { name: 'Claude 3 Opus', cost: 89.50, usage: '0.8M Tokens' },
    { name: 'Groq (Llama3)', cost: 5.40, usage: '12M Tokens' },
    { name: 'DALL-E 3', cost: 42.00, usage: '450 Images' },
]

export function FinOpsPage() {
    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <CreditCard className="text-green-500" />
                        FinOps & Maliyet Yönetimi
                    </h2>
                    <p className="text-gray-400">Yapay zeka operasyon maliyetleri ve bütçe planlaması</p>
                </div>
                <div className="text-right">
                    <p className="text-xs text-gray-400 uppercase">Bu Ay Tahmini</p>
                    <p className="text-2xl font-bold text-green-400">$285.50</p>
                </div>
            </header>

            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white/5 border border-white/10 p-6 rounded-2xl flex items-center justify-between">
                    <div>
                        <h3 className="text-gray-400 text-sm font-medium">Kalan Bütçe</h3>
                        <p className="text-2xl font-bold text-white mt-1">$214.50</p>
                    </div>
                    <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center">
                        <DollarSign className="w-6 h-6 text-green-500" />
                    </div>
                </div>
                <div className="bg-white/5 border border-white/10 p-6 rounded-2xl flex items-center justify-between">
                    <div>
                        <h3 className="text-gray-400 text-sm font-medium">Ort. Günlük Maliyet</h3>
                        <p className="text-2xl font-bold text-white mt-1">$9.20</p>
                    </div>
                    <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <TrendingDown className="w-6 h-6 text-blue-500" />
                    </div>
                </div>
                <div className="bg-white/5 border border-white/10 p-6 rounded-2xl flex items-center justify-between">
                    <div>
                        <h3 className="text-gray-400 text-sm font-medium">Tasarruf Oranı (Local AI)</h3>
                        <p className="text-2xl font-bold text-yellow-500 mt-1">%40</p>
                    </div>
                    <div className="w-12 h-12 rounded-full bg-yellow-500/20 flex items-center justify-center">
                        <Zap className="w-6 h-6 text-yellow-500" />
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Cost Chart */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-6">Aylık Harcama ($)</h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={COST_DATA}>
                                <XAxis dataKey="name" stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#111', border: '1px solid #333' }}
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                />
                                <Bar dataKey="cost" fill="#22c55e" radius={[4, 4, 0, 0]}>
                                    {COST_DATA.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={index === COST_DATA.length - 1 ? '#4ade80' : '#166534'} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Breakdown */}
                <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                    <div className="p-6 border-b border-white/10 flex justify-between items-center">
                        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                            <PieChartIcon className="w-5 h-5 text-purple-400" />
                            Model Bazlı Kırılım
                        </h3>
                        <Button size="sm" variant="outline">CSV İndir</Button>
                    </div>
                    <div className="divide-y divide-white/5">
                        {MODEL_COSTS.map((item) => (
                            <div key={item.name} className="p-4 flex items-center justify-between hover:bg-white/5 transition-colors">
                                <div>
                                    <p className="text-white font-medium">{item.name}</p>
                                    <p className="text-xs text-gray-500">{item.usage}</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-white font-mono font-medium">${item.cost.toFixed(2)}</p>
                                    <div className="w-24 h-1.5 bg-white/10 rounded-full mt-2 overflow-hidden">
                                        <div
                                            className="h-full bg-purple-500 rounded-full"
                                            style={{ width: `${(item.cost / 200) * 100}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
