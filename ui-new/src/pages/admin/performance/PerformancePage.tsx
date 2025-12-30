
import { Zap, Server, Database, Trash, PlayCircle, PauseCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Switch } from '@/components/ui/Switch'

export function PerformancePage() {
    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Zap className="text-yellow-400" />
                        Performans & Cache
                    </h2>
                    <p className="text-gray-400">Akıllı önbellek yönetimi ve sistem optimizasyonu</p>
                </div>
                <Button variant="outline" className="text-red-400 border-red-500/20 hover:bg-red-500/10" leftIcon={<Trash className="w-4 h-4" />}>
                    Önbelleği Temizle (Purge)
                </Button>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Cache Stats */}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                                <Zap className="w-5 h-5 text-green-500" />
                            </div>
                            <h3 className="font-semibold text-white">Cache Hit Rate</h3>
                        </div>
                        <p className="text-3xl font-bold text-white mb-2">%84.2</p>
                        <p className="text-xs text-gray-400">Son 24 saatte 12,450 istek önbellekten döndü.</p>
                    </div>
                    <div className="w-full bg-white/10 h-2 rounded-full mt-4 overflow-hidden">
                        <div className="bg-green-500 h-full w-[84%]" />
                    </div>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                                <Database className="w-5 h-5 text-blue-500" />
                            </div>
                            <h3 className="font-semibold text-white">Redis Bellek</h3>
                        </div>
                        <p className="text-3xl font-bold text-white mb-2">142 MB</p>
                        <p className="text-xs text-gray-400">/ 512 MB Tahsis edilen limit</p>
                    </div>
                    <div className="w-full bg-white/10 h-2 rounded-full mt-4 overflow-hidden">
                        <div className="bg-blue-500 h-full w-[28%]" />
                    </div>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                                <Server className="w-5 h-5 text-purple-500" />
                            </div>
                            <h3 className="font-semibold text-white">Ort. Tepki Süresi</h3>
                        </div>
                        <p className="text-3xl font-bold text-white mb-2">124ms</p>
                        <p className="text-xs text-gray-400">Cache sayesinde %40 hızlanma sağlandı.</p>
                    </div>
                </div>
            </div>

            {/* Smart Rules */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-white mb-6">Akıllı Önbellek Kuralları</h3>

                <div className="space-y-4">
                    <RuleItem
                        name="Statik Varlıklar"
                        desc="CSS, JS ve Resim dosyalarını 1 hafta cachele"
                        active={true}
                    />
                    <RuleItem
                        name="Yapay Zeka Cevapları (Exact Match)"
                        desc="Aynı soru tekrar sorulursa birebir aynı cevabı döndür"
                        active={true}
                    />
                    <RuleItem
                        name="Üye Profilleri"
                        desc="Kullanıcı verilerini 5 dakika önbellekte tut"
                        active={false}
                    />
                </div>
            </div>
        </div>
    )
}

function RuleItem({ name, desc, active }: any) {
    return (
        <div className="flex items-center justify-between p-4 bg-black/20 rounded-xl border border-white/5">
            <div className="flex items-center gap-4">
                {active ? <PlayCircle className="w-5 h-5 text-green-500" /> : <PauseCircle className="w-5 h-5 text-gray-500" />}
                <div>
                    <h4 className="text-sm font-medium text-white">{name}</h4>
                    <p className="text-xs text-gray-400">{desc}</p>
                </div>
            </div>
            <Switch checked={active} onCheckedChange={() => { }} />
        </div>
    )
}
