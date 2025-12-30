
import { Settings as SettingsIcon, Database, Server, Terminal, Save, RefreshCcw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Switch } from '@/components/ui/Switch'

export function SettingsPage() {
    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <SettingsIcon className="text-gray-400" />
                        Sistem Ayarları
                    </h2>
                    <p className="text-gray-400">Veritabanı, loglama ve düşük seviye yapılandırma</p>
                </div>
                <div className="flex gap-3">
                    <Button variant="outline" leftIcon={<RefreshCcw className="w-4 h-4" />}>Varsayılanları Yükle</Button>
                    <Button leftIcon={<Save className="w-4 h-4" />}>Kaydet</Button>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* General/Environment */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Server className="w-5 h-5 text-blue-400" />
                            Sunucu & Ortam
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-xs text-gray-400 uppercase">Environment</label>
                                <select className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-white">
                                    <option>Production</option>
                                    <option>Development</option>
                                    <option>Staging</option>
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs text-gray-400 uppercase">Log Seviyesi</label>
                                <select className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-white">
                                    <option>INFO</option>
                                    <option>DEBUG</option>
                                    <option>WARNING</option>
                                    <option>ERROR</option>
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs text-gray-400 uppercase">API Port</label>
                                <Input defaultValue="8000" className="bg-black/20" />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs text-gray-400 uppercase">Frontend Port</label>
                                <Input defaultValue="5173" className="bg-black/20" />
                            </div>
                        </div>
                    </div>

                    <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Database className="w-5 h-5 text-green-400" />
                            Veritabanı Yapılandırması
                        </h3>
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs text-gray-400 uppercase">Ana DB Yolu (SQLite)</label>
                                <Input defaultValue="./data/mami_v4.db" className="bg-black/20" />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs text-gray-400 uppercase">Vektör DB Yolu (Chroma)</label>
                                <Input defaultValue="./data/chroma_db" className="bg-black/20" />
                            </div>
                            <div className="flex items-center gap-4 mt-4 pt-4 border-t border-white/5">
                                <Button variant="outline" size="sm" className="text-red-400 border-red-500/20">DB Sıfırla (Reset)</Button>
                                <Button variant="outline" size="sm">Yedekle (Backup)</Button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Toggles & Flags */}
                <div className="space-y-6">
                    <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Terminal className="w-5 h-5 text-purple-400" />
                            Gelişmiş Özellikler
                        </h3>

                        <div className="space-y-4">
                            <div className="flex justify-between items-center p-3 bg-black/20 rounded-xl border border-white/5">
                                <span className="text-sm font-medium text-white">Debug Modu</span>
                                <Switch checked={false} onCheckedChange={() => { }} />
                            </div>
                            <div className="flex justify-between items-center p-3 bg-black/20 rounded-xl border border-white/5">
                                <span className="text-sm font-medium text-white">Swagger UI (/docs)</span>
                                <Switch checked={true} onCheckedChange={() => { }} />
                            </div>
                            <div className="flex justify-between items-center p-3 bg-black/20 rounded-xl border border-white/5">
                                <span className="text-sm font-medium text-white">CORS Herkese Açık</span>
                                <Switch checked={false} onCheckedChange={() => { }} />
                            </div>
                            <div className="flex justify-between items-center p-3 bg-black/20 rounded-xl border border-white/5">
                                <span className="text-sm font-medium text-white">Otomatik Güncelleme</span>
                                <Switch checked={true} onCheckedChange={() => { }} />
                            </div>
                        </div>

                        <div className="mt-6 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-xl">
                            <h4 className="text-yellow-400 text-sm font-bold mb-1">⚠️ Bakım Modu</h4>
                            <p className="text-xs text-gray-400 mb-3">Sistemi kullanıcı erişimine kapatır.</p>
                            <Button variant="outline" className="w-full text-yellow-500 border-yellow-500/30 hover:bg-yellow-500/10">Bakım Modunu Aç</Button>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    )
}
