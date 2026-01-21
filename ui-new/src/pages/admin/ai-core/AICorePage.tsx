
import { useState, useEffect } from 'react'
import { Bot, Cpu, Sparkles, Zap, BrainCircuit, Save } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Switch } from '@/components/ui/Switch' // We made this recently


// Mock API for now - will replace with real endpoints
const aiApi = {
    getModels: async () => [
        { id: 'llama3-8b', name: 'Llama 3 (8B)', provider: 'ollama', active: true, type: 'chat' },
        { id: 'gemma-2b', name: 'Gemma (2B)', provider: 'ollama', active: false, type: 'chat' },
        { id: 'groq-mixed', name: 'Groq (Mixed)', provider: 'groq', active: true, type: 'chat' },
        { id: 'flux-schnell', name: 'Flux Schnell', provider: 'local', active: true, type: 'image' },
    ],
    getPersonas: async () => [
        { id: 'default', name: 'Mami (Default)', prompt: 'Sen yardımsever bir asistansın...' },
        { id: 'coder', name: 'Kıdemli Yazılımcı', prompt: 'Sen uzman bir yazılımcısın...' },
        { id: 'bela', name: 'Bela Modu', prompt: 'Sen agresif ve ters bir karaktersin...' },
    ]
}

export function AICorePage() {
    const [activeTab, setActiveTab] = useState<'models' | 'personas'>('models')

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <BrainCircuit className="text-purple-500" />
                        AI Orkestrasyonu
                    </h2>
                    <p className="text-gray-400">Model seçimi, API anahtarları ve Persona yönetimi</p>
                </div>
                <div className="flex bg-white/5 p-1 rounded-lg">
                    <button
                        onClick={() => setActiveTab('models')}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === 'models' ? 'bg-purple-500 text-white shadow-lg' : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Modeller & API
                    </button>
                    <button
                        onClick={() => setActiveTab('personas')}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === 'personas' ? 'bg-purple-500 text-white shadow-lg' : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Personalar (Prompts)
                    </button>
                </div>
            </header>

            {activeTab === 'models' ? <ModelsView /> : <PersonasView />}
        </div>
    )
}

function ModelsView() {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* LLM Configuration */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Bot className="w-5 h-5 text-blue-400" />
                    Dil Modelleri (LLM)
                </h3>

                <div className="space-y-4">
                    <div className="p-4 bg-black/20 rounded-xl border border-white/5 flex items-center justify-between">
                        <div>
                            <h4 className="font-medium text-white">Ollama (Yerel)</h4>
                            <p className="text-xs text-gray-500">http://localhost:11434</p>
                        </div>
                        <span className="text-xs bg-green-500/10 text-green-400 px-2 py-1 rounded">Connected</span>
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs text-gray-400 uppercase">Aktif Model</label>
                        <select className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-white">
                            <option>Llama 3 (8B) - Instruct</option>
                            <option>Gemma 2 (2B)</option>
                            <option>Mistral v0.3</option>
                        </select>
                    </div>

                    <div className="pt-4 border-t border-white/10">
                        <h4 className="font-medium text-white mb-2">Groq (Bulut / Hızlı)</h4>
                        <Input placeholder="gsk_..." type="password" className="bg-black/20" />
                        <p className="text-xs text-gray-500 mt-1">API Key girilmezse yerel model kullanılır.</p>
                    </div>
                </div>
            </div>

            {/* Image Generation Config */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-pink-400" />
                    Görsel Üretimi (Image Gen)
                </h3>

                <div className="space-y-4">
                    <div className="p-4 bg-black/20 rounded-xl border border-white/5">
                        <div className="flex justify-between items-center mb-2">
                            <h4 className="font-medium text-white">Flux Schnell (Local)</h4>
                            <Switch checked={true} onCheckedChange={() => { }} />
                        </div>
                        <p className="text-xs text-gray-500">
                            Yerel GPU üzerinden yüksek kaliteli görsel üretimi. VRAM: ~12GB gerektirir.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs text-gray-400 uppercase">Adım Sayısı (Steps)</label>
                        <div className="flex items-center gap-4">
                            <input type="range" min="1" max="50" defaultValue="4" className="flex-1 accent-pink-500" />
                            <span className="text-white font-mono w-8">4</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

function PersonasView() {
    const [personas, setPersonas] = useState([
        { id: 1, name: 'Mami (Default)', desc: 'Varsayılan yardımcı asistan.', active: true },
        { id: 2, name: 'Kod Uzmanı', desc: 'Yazılım ve teknik konularda uzman.', active: false },
        { id: 3, name: 'Bela Modu', desc: 'Eğlence amaçlı agresif mod.', active: false },
    ])

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Persona List */}
            <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                <div className="p-4 border-b border-white/10 bg-black/20">
                    <h3 className="font-semibold text-white">Kayıtlı Personalar</h3>
                </div>
                <div className="divide-y divide-white/5">
                    {personas.map(p => (
                        <div key={p.id} className="p-4 hover:bg-white/5 cursor-pointer transition-colors group">
                            <div className="flex justify-between items-start">
                                <div>
                                    <h4 className="text-white font-medium group-hover:text-purple-400 transition-colors">{p.name}</h4>
                                    <p className="text-xs text-gray-500">{p.desc}</p>
                                </div>
                                {p.active && <span className="w-2 h-2 rounded-full bg-green-500" />}
                            </div>
                        </div>
                    ))}
                    <div className="p-4 text-center">
                        <Button variant="outline" size="sm" className="w-full">+ Yeni Persona</Button>
                    </div>
                </div>
            </div>

            {/* Editor */}
            <div className="lg:col-span-2 bg-white/5 border border-white/10 rounded-2xl p-6">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h3 className="text-lg font-bold text-white">Mami (Default)</h3>
                        <span className="text-xs text-gray-500">ID: system_default_v1</span>
                    </div>
                    <Button leftIcon={<Save className="w-4 h-4" />}>Kaydet</Button>
                </div>

                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-xs text-gray-400 uppercase">Görünen Ad</label>
                            <Input defaultValue="Mami AI" className="bg-black/20" />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs text-gray-400 uppercase">Tetikeleyici (Command)</label>
                            <Input defaultValue="/mami" className="bg-black/20" />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs text-gray-400 uppercase">Sistem Mesajı (System Prompt)</label>
                        <textarea
                            className="w-full h-64 bg-black/20 border border-white/10 rounded-xl p-4 text-sm text-gray-300 font-mono focus:outline-none focus:border-purple-500/50 resize-none"
                            defaultValue={`Sen Mami AI adında, yardımsever ve zeki bir yapay zeka asistanısın.
Kullanıcının sorularına net, doğru ve Türkçe yanıtlar verirsin.
Yazılım, genel kültür ve yaratıcı yazarlık konularında yetkinsin.`}
                        />
                        <p className="text-xs text-gray-500">
                            Modelin temel davranışını belirleyen ana komuttur. Değişiklikler anında yansımaz, yeni sohbet gerektirir.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
