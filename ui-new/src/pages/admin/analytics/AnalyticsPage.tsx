
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend, AreaChart, Area } from 'recharts'
import { LineChart as IconLineChart, TrendingUp, Users, MessageSquare, Image as ImageIcon } from 'lucide-react'

const DATA_GROWTH = [
    { name: 'Pzt', active: 4000, new: 2400 },
    { name: 'Sal', active: 3000, new: 1398 },
    { name: 'Çar', active: 2000, new: 9800 },
    { name: 'Per', active: 2780, new: 3908 },
    { name: 'Cum', active: 1890, new: 4800 },
    { name: 'Cmt', active: 2390, new: 3800 },
    { name: 'Paz', active: 3490, new: 4300 },
]

const DATA_MODELS = [
    { name: 'Llama 3', value: 400 },
    { name: 'Gemma 2', value: 300 },
    { name: 'Groq', value: 300 },
    { name: 'Flux', value: 200 },
]

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042']

export function AnalyticsPage() {
    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <IconLineChart className="text-blue-500" />
                        İstatistikler & Analiz
                    </h2>
                    <p className="text-gray-400">Kullanıcı büyümesi, model kullanımı ve token tüketimi</p>
                </div>
            </header>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <KPICard title="Toplam Kullanıcı" value="12,453" change="+12%" icon={Users} color="text-blue-500" />
                <KPICard title="Günlük Mesaj" value="45.2K" change="+5%" icon={MessageSquare} color="text-green-500" />
                <KPICard title="Üretilen Görsel" value="1,204" change="-2%" icon={ImageIcon} color="text-pink-500" />
                <KPICard title="Token Tüketimi" value="8.4M" change="+24%" icon={TrendingUp} color="text-yellow-500" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Growth Chart */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-6">Kullanıcı Büyümesi</h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={DATA_GROWTH}>
                                <defs>
                                    <linearGradient id="colorActive" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="colorNew" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#82ca9d" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <XAxis dataKey="name" stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#111', border: '1px solid #333' }}
                                    itemStyle={{ color: '#fff' }}
                                />
                                <Area type="monotone" dataKey="active" stroke="#8884d8" fillOpacity={1} fill="url(#colorActive)" />
                                <Area type="monotone" dataKey="new" stroke="#82ca9d" fillOpacity={1} fill="url(#colorNew)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Model Usage */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-6">Model Kullanım Dağılımı</h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={DATA_MODELS}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {DATA_MODELS.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#111', border: '1px solid #333' }}
                                    itemStyle={{ color: '#fff' }}
                                />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    )
}

function KPICard({ title, value, change, icon: Icon, color }: any) {
    const isPositive = change.startsWith('+')
    return (
        <div className="bg-white/5 border border-white/10 p-6 rounded-2xl">
            <div className="flex justify-between items-start mb-2">
                <div className={`p-2 rounded-lg bg-white/5 ${color}`}>
                    <Icon className="w-5 h-5" />
                </div>
                <span className={`text-xs font-medium px-2 py-1 rounded-full border ${isPositive ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                    {change}
                </span>
            </div>
            <p className="text-sm text-gray-400">{title}</p>
            <p className="text-2xl font-bold text-white mb-0">{value}</p>
        </div>
    )
}
