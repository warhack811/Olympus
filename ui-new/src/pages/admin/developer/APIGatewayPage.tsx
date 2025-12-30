
import { useState } from 'react'
import { Key, Copy, Plus, RefreshCw, Trash2, Shield } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

const MOCK_KEYS = [
    { id: '1', name: 'Mobil Uygulama', key: 'sk-mami...8f2a', usage: 1542, limit: 10000, created: '2023-10-01' },
    { id: '2', name: 'Web Sitesi Widget', key: 'sk-mami...9k2l', usage: 504, limit: 5000, created: '2023-10-15' },
]

export function APIGatewayPage() {
    const [keys, setKeys] = useState(MOCK_KEYS)

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Key className="text-yellow-500" />
                        API Gateway
                    </h2>
                    <p className="text-gray-400">Geliştirici anahtarları ve entegrasyon yönetimi</p>
                </div>
                <Button leftIcon={<Plus className="w-4 h-4" />}>
                    Yeni Anahtar Oluştur
                </Button>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Stats */}
                <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white/5 border border-white/10 p-6 rounded-2xl">
                        <h3 className="text-gray-400 text-sm">Toplam İstek (Aylık)</h3>
                        <p className="text-2xl font-bold text-white mt-1">2,046</p>
                    </div>
                    <div className="bg-white/5 border border-white/10 p-6 rounded-2xl">
                        <h3 className="text-gray-400 text-sm">Aktif Anahtarlar</h3>
                        <p className="text-2xl font-bold text-white mt-1">{keys.length}</p>
                    </div>
                    <div className="bg-white/5 border border-white/10 p-6 rounded-2xl">
                        <h3 className="text-gray-400 text-sm">Hatalı İstekler</h3>
                        <p className="text-2xl font-bold text-red-400 mt-1">0.4%</p>
                    </div>
                </div>

                {/* API Keys List */}
                <div className="lg:col-span-2 space-y-4">
                    {keys.map((k) => (
                        <div key={k.id} className="bg-white/5 border border-white/10 rounded-xl p-4 flex items-center justify-between group hover:border-yellow-500/30 transition-colors">
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                                    <Key className="w-5 h-5 text-yellow-500" />
                                </div>
                                <div>
                                    <h4 className="text-white font-medium">{k.name}</h4>
                                    <div className="flex items-center gap-2 mt-1">
                                        <code className="text-xs bg-black/40 px-2 py-1 rounded text-gray-400 font-mono">{k.key}</code>
                                        <button className="text-gray-500 hover:text-white"><Copy className="w-3 h-3" /></button>
                                    </div>
                                </div>
                            </div>

                            <div className="text-right flex items-center gap-6">
                                <div>
                                    <p className="text-xs text-gray-500 uppercase">Kullanım</p>
                                    <p className="text-sm text-white font-mono">{k.usage} / {k.limit}</p>
                                </div>
                                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Button size="icon-sm" variant="ghost"><RefreshCw className="w-4 h-4" /></Button>
                                    <Button size="icon-sm" variant="ghost" className="text-red-400 hover:text-red-300"><Trash2 className="w-4 h-4" /></Button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Documentation / Info */}
                <div className="bg-blue-500/5 border border-blue-500/20 rounded-2xl p-6 h-fit">
                    <h3 className="text-lg font-semibold text-blue-400 mb-4 flex items-center gap-2">
                        <Shield className="w-5 h-5" />
                        Entegrasyon Rehberi
                    </h3>
                    <p className="text-sm text-gray-300 mb-4">
                        Mami AI API'sini kullanmak için aşağıdaki base URL'i ve oluşturduğunuz API anahtarını kullanın.
                    </p>

                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-blue-300 uppercase font-bold">Base URL</label>
                            <div className="mt-1 p-2 bg-black/40 rounded border border-blue-500/20 text-xs font-mono text-gray-400">
                                https://api.mamiai.com/v1
                            </div>
                        </div>
                        <div>
                            <label className="text-xs text-blue-300 uppercase font-bold">Header</label>
                            <div className="mt-1 p-2 bg-black/40 rounded border border-blue-500/20 text-xs font-mono text-gray-400">
                                Authorization: Bearer sk-mami...
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
