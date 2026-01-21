
import { useState } from 'react'
import { Palette, Type, Layout, Image as ImageIcon, Save, Smartphone } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Switch } from '@/components/ui/Switch'

export function CMSPage() {
    const [activeTab, setActiveTab] = useState<'branding' | 'theme'>('branding')

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Palette className="text-pink-500" />
                        Marka & Görünüm (CMS)
                    </h2>
                    <p className="text-gray-400">Sistem kimliği, temalar ve PWA ayarları</p>
                </div>
                <div className="flex bg-white/5 p-1 rounded-lg">
                    <button
                        onClick={() => setActiveTab('branding')}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === 'branding' ? 'bg-pink-500 text-white shadow-lg' : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Sistem Kimliği
                    </button>
                    <button
                        onClick={() => setActiveTab('theme')}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === 'theme' ? 'bg-pink-500 text-white shadow-lg' : 'text-gray-400 hover:text-white'
                            }`}
                    >
                        Tema Editörü
                    </button>
                </div>
            </header>

            {activeTab === 'branding' ? <BrandingView /> : <ThemeEditorView />}
        </div>
    )
}

function BrandingView() {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* General Settings */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Layout className="w-5 h-5 text-blue-400" />
                    Genel Bilgiler
                </h3>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-xs text-gray-400 uppercase">Uygulama Adı</label>
                        <Input defaultValue="Mami AI" className="bg-black/20" />
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs text-gray-400 uppercase">Tarayıcı Başlığı (Title)</label>
                        <Input defaultValue="Mami AI - Kişisel Asistan" className="bg-black/20" />
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs text-gray-400 uppercase">Hoş Geldin Mesajı (Login)</label>
                        <Input defaultValue="Hesabınıza giriş yapın" className="bg-black/20" />
                    </div>
                </div>
            </div>

            {/* PWA & Icons */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Smartphone className="w-5 h-5 text-green-400" />
                    PWA & İkonlar
                </h3>

                <div className="flex items-start gap-6 mb-6">
                    <div className="w-24 h-24 bg-black/40 rounded-2xl border border-white/10 flex items-center justify-center relative group cursor-pointer overflow-hidden">
                        <span className="text-4xl">🤖</span>
                        <div className="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <ImageIcon className="w-6 h-6 text-white" />
                        </div>
                    </div>
                    <div className="flex-1 space-y-2">
                        <h4 className="font-medium text-white">Uygulama İkonu</h4>
                        <p className="text-xs text-gray-500">
                            Ana ekran ve tarayıcı sekmesi için ikon. (PNG, SVG)
                        </p>
                        <Button size="sm" variant="outline">Yükle</Button>
                    </div>
                </div>

                <div className="space-y-4 pt-4 border-t border-white/10">
                    <div className="flex justify-between items-center bg-black/20 p-3 rounded-xl border border-white/5">
                        <span className="text-sm font-medium text-white">Yüklenebilir Uygulama (PWA)</span>
                        <Switch checked={true} onCheckedChange={() => { }} />
                    </div>
                    <div className="flex justify-between items-center bg-black/20 p-3 rounded-xl border border-white/5">
                        <span className="text-sm font-medium text-white">Çevrimdışı Mod</span>
                        <Switch checked={false} onCheckedChange={() => { }} />
                    </div>
                </div>
            </div>
        </div>
    )
}

function ThemeEditorView() {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-white/5 border border-white/10 rounded-2xl p-6">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Palette className="w-5 h-5 text-purple-400" />
                        Renk Paleti (CSS Variables)
                    </h3>
                    <Button leftIcon={<Save className="w-4 h-4" />}>Kaydet</Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Ana Renkler</h4>
                        <ColorInput label="Primary" variable="--color-primary" defaultValue="#a855f7" />
                        <ColorInput label="Background" variable="--color-bg" defaultValue="#09090b" />
                        <ColorInput label="Surface" variable="--color-bg-surface" defaultValue="#18181b" />
                    </div>

                    <div className="space-y-4">
                        <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Mesaj Balonları</h4>
                        <ColorInput label="User Message" variable="--color-msg-user-bg" defaultValue="#27272a" />
                        <ColorInput label="Bot Message" variable="--color-msg-bot-bg" defaultValue="transparent" />
                        <ColorInput label="Accent" variable="--color-accent" defaultValue="#ec4899" />
                    </div>
                </div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Type className="w-5 h-5 text-yellow-400" />
                    Tipografi & Stil
                </h3>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-xs text-gray-400 uppercase">Font Ailesi</label>
                        <select className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-white">
                            <option>Inter (Modern)</option>
                            <option>Manrope (Technical)</option>
                            <option>Roboto (Classic)</option>
                        </select>
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs text-gray-400 uppercase">Kenar Yuvarlaklığı</label>
                        <div className="flex items-center gap-4">
                            <input type="range" min="0" max="24" defaultValue="12" className="flex-1 accent-white" />
                            <span className="text-white font-mono text-xs">12px</span>
                        </div>
                    </div>

                    <div className="p-4 bg-black/40 rounded-xl border border-white/10 mt-6">
                        <p className="text-sm font-medium text-white mb-2">Önizleme</p>
                        <Button size="sm" className="w-full mb-2">Primary Button</Button>
                        <div className="p-2 bg-[var(--color-bg-surface)] rounded-lg text-xs text-gray-400">
                            Surface Color Test
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

function ColorInput({ label, variable, defaultValue }: { label: string, variable: string, defaultValue: string }) {
    return (
        <div className="flex items-center justify-between p-3 bg-black/20 rounded-xl border border-white/5">
            <div>
                <p className="text-sm font-medium text-white">{label}</p>
                <p className="text-[10px] text-gray-500 font-mono">{variable}</p>
            </div>
            <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-gray-300">{defaultValue}</span>
                <input type="color" defaultValue={defaultValue} className="w-8 h-8 rounded cursor-pointer bg-transparent border-none" />
            </div>
        </div>
    )
}
