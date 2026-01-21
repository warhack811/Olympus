
import { useState } from 'react'
import { Bot, Sparkles, ChevronRight, Code, Wrench, MessageSquare, Plus, Search, Download, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

// Mock Data
const MOCK_AGENTS = [
    { id: 1, name: 'Kod Uzmanı', role: 'Developer', description: 'Python ve React konusunda uzmanlaşmış asistan.', active: true },
    { id: 2, name: 'Hukuk Danışmanı', role: 'Legal', description: 'Şirket sözleşmeleri ve KVKK konusunda yetkin.', active: false },
]

export function AgentFactoryPage() {
    const [view, setView] = useState<'list' | 'create'>('list')
    const [step, setStep] = useState(1)

    // Wizard State
    const [agentName, setAgentName] = useState('')
    const [agentRole, setAgentRole] = useState('')

    if (view === 'list') {
        return (
            <div className="space-y-6">
                <header className="flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                            <Bot className="text-purple-500" />
                            Ajan Fabrikası
                        </h2>
                        <p className="text-gray-400">Yeni özel yapay zeka ajanları oluşturun ve eğitin</p>
                    </div>
                    <Button onClick={() => setView('create')} leftIcon={<Plus className="w-4 h-4" />}>
                        Yeni Ajan Üret
                    </Button>
                </header>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {MOCK_AGENTS.map((agent) => (
                        <div key={agent.id} className="bg-white/5 border border-white/10 rounded-2xl p-6 hover:border-purple-500/50 transition-colors cursor-pointer group">
                            <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                <Bot className="w-6 h-6 text-purple-400" />
                            </div>
                            <h3 className="text-lg font-bold text-white">{agent.name}</h3>
                            <p className="text-xs text-purple-400 font-medium mb-2 uppercase tracking-wide">{agent.role}</p>
                            <p className="text-sm text-gray-400 mb-4">{agent.description}</p>
                            <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${agent.active ? 'bg-green-500' : 'bg-gray-500'}`} />
                                <span className="text-xs text-gray-500">{agent.active ? 'Aktif' : 'Pasif'}</span>
                            </div>
                        </div>
                    ))}

                    {/* Create New Card */}
                    <button
                        onClick={() => setView('create')}
                        className="border border-dashed border-white/10 rounded-2xl p-6 flex flex-col items-center justify-center text-center hover:bg-white/5 transition-colors"
                    >
                        <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4 text-gray-400">
                            <Plus className="w-6 h-6" />
                        </div>
                        <h3 className="text-lg font-medium text-white">Yeni Ekle</h3>
                        <p className="text-sm text-gray-500 mt-1">Sihirbazı başlat</p>
                    </button>
                </div>
            </div>
        )
    }

    // Wizard View
    return (
        <div className="max-w-2xl mx-auto py-10">
            <div className="mb-8 flex items-center gap-4 text-sm text-gray-500">
                <button onClick={() => setView('list')} className="hover:text-white">Ajanlar</button>
                <ChevronRight className="w-4 h-4" />
                <span className="text-white">Yeni Ajan Sihirbazı</span>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-3xl p-8 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-white/10">
                    <div className="h-full bg-purple-500 transition-all duration-300" style={{ width: `${(step / 3) * 100}%` }} />
                </div>

                {step === 1 && (
                    <div className="space-y-6">
                        <div className="w-16 h-16 rounded-2xl bg-purple-500/20 flex items-center justify-center mx-auto mb-6">
                            <Sparkles className="w-8 h-8 text-purple-400" />
                        </div>
                        <h2 className="text-2xl font-bold text-center text-white">Ajan Kimliği</h2>
                        <p className="text-center text-gray-400">Ajanınıza bir isim ve rol verin.</p>

                        <div className="space-y-4">
                            <div>
                                <label className="text-sm text-gray-400 mb-2 block">Ajan Adı</label>
                                <Input placeholder="Örn: Kod Ustası" value={agentName} onChange={(e) => setAgentName(e.target.value)} className="bg-black/20" />
                            </div>
                            <div>
                                <label className="text-sm text-gray-400 mb-2 block">Rol / Uzmanlık</label>
                                <Input placeholder="Örn: Senior React Developer" value={agentRole} onChange={(e) => setAgentRole(e.target.value)} className="bg-black/20" />
                            </div>
                        </div>

                        <Button className="w-full mt-4" onClick={() => setStep(2)} disabled={!agentName || !agentRole}>
                            Devam Et <ChevronRight className="w-4 h-4 ml-2" />
                        </Button>
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-6">
                        <div className="w-16 h-16 rounded-2xl bg-blue-500/20 flex items-center justify-center mx-auto mb-6">
                            <Wrench className="w-8 h-8 text-blue-400" />
                        </div>
                        <h2 className="text-2xl font-bold text-center text-white">Yetenekler</h2>
                        <p className="text-center text-gray-400">Ajanın hangi araçlara erişimi olsun?</p>

                        <div className="grid grid-cols-2 gap-4">
                            <SkillCard icon={Code} title="Kodlama" desc="Python/JS çalıştırabilir" active={true} />
                            <SkillCard icon={MessageSquare} title="Sohbet" desc="Doğal dil işleme" active={true} />
                            <SkillCard icon={Search} title="İnternet" desc="Web araması yapabilir" active={false} />
                            <SkillCard icon={Download} title="Dosya" desc="Dosya okuyup yazabilir" active={false} />
                        </div>

                        <div className="flex gap-4 mt-8">
                            <Button variant="ghost" onClick={() => setStep(1)} className="flex-1">Geri</Button>
                            <Button className="flex-1" onClick={() => setStep(3)}>Devam Et</Button>
                        </div>
                    </div>
                )}

                {step === 3 && (
                    <div className="space-y-6 text-center">
                        <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-6 animate-pulse">
                            <CheckCircle className="w-10 h-10 text-green-400" />
                        </div>
                        <h2 className="text-2xl font-bold text-white">Her Şey Hazır!</h2>
                        <p className="text-gray-400">
                            <strong>{agentName}</strong> adlı ajan <strong>{agentRole}</strong> rolüyle oluşturulmaya hazır.
                        </p>

                        <div className="p-4 bg-black/30 rounded-xl border border-white/5 text-left text-sm text-gray-400 font-mono">
                            Creating agent blueprint...<br />
                            Injecting system prompts...<br />
                            Configuring tools...<br />
                            <span className="text-green-400">Ready to deploy.</span>
                        </div>

                        <div className="flex gap-4 mt-8">
                            <Button variant="ghost" onClick={() => setStep(2)} className="flex-1">Geri</Button>
                            <Button className="flex-1 bg-green-600 hover:bg-green-700 text-white" onClick={() => setView('list')}>
                                Ajanı Başlat 🚀
                            </Button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

function SkillCard({ icon: Icon, title, desc, active }: any) {
    const [isActive, setIsActive] = useState(active)
    return (
        <div
            onClick={() => setIsActive(!isActive)}
            className={`cursor-pointer p-4 rounded-xl border transition-all ${isActive
                ? 'bg-purple-500/20 border-purple-500 text-white'
                : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'
                }`}
        >
            <Icon className={`w-6 h-6 mb-2 ${isActive ? 'text-purple-400' : 'text-gray-500'}`} />
            <h4 className="font-medium text-sm">{title}</h4>
            <p className="text-xs opacity-70">{desc}</p>
        </div>
    )
}
