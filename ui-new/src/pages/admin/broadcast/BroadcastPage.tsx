
import { useState } from 'react'
import { Radio, Send, Bell, Trash2, CheckCircle, AlertTriangle, Info } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

const MOCK_BROADCASTS = [
    { id: 1, message: 'Sistem 22:00\'da kısa süreli bakıma girecektir.', type: 'warning', active: true, created_at: '10:00' },
    { id: 2, message: 'Yeni Llama 3 modeli kullanıma açıldı! 🎉', type: 'info', active: true, created_at: '09:30' },
    { id: 3, message: 'Hoşgeldin mesajı güncellendi.', type: 'success', active: false, created_at: 'Dün' },
]

export function BroadcastPage() {
    const [broadcasts, setBroadcasts] = useState(MOCK_BROADCASTS)
    const [newMessage, setNewMessage] = useState('')
    const [type, setType] = useState<'info' | 'warning' | 'success' | 'danger'>('info')

    const handleSend = () => {
        if (!newMessage) return
        const newBroadcast = {
            id: Date.now(),
            message: newMessage,
            type,
            active: true,
            created_at: 'Şimdi'
        }
        setBroadcasts([newBroadcast, ...broadcasts])
        setNewMessage('')
    }

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Radio className="text-orange-500" />
                        Anons Kulesi
                    </h2>
                    <p className="text-gray-400">Tüm kullanıcılara anlık sistem duyurusu gönderin</p>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Compose */}
                <div className="lg:col-span-1 bg-white/5 border border-white/10 rounded-2xl p-6 h-fit">
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Send className="w-5 h-5 text-blue-400" />
                        Yeni Duyuru
                    </h3>

                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs text-gray-400 uppercase">Mesaj Türü</label>
                            <div className="grid grid-cols-3 gap-2">
                                <button
                                    onClick={() => setType('info')}
                                    className={`p-2 rounded-lg border text-xs font-medium transition-all ${type === 'info' ? 'bg-blue-500/20 border-blue-500 text-blue-400' : 'border-white/10 hover:bg-white/5'}`}
                                >Bilgi</button>
                                <button
                                    onClick={() => setType('warning')}
                                    className={`p-2 rounded-lg border text-xs font-medium transition-all ${type === 'warning' ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400' : 'border-white/10 hover:bg-white/5'}`}
                                >Uyarı</button>
                                <button
                                    onClick={() => setType('danger')}
                                    className={`p-2 rounded-lg border text-xs font-medium transition-all ${type === 'danger' ? 'bg-red-500/20 border-red-500 text-red-400' : 'border-white/10 hover:bg-white/5'}`}
                                >Kritik</button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs text-gray-400 uppercase">Mesaj İçeriği</label>
                            <textarea
                                value={newMessage}
                                onChange={(e) => setNewMessage(e.target.value)}
                                className="w-full h-32 bg-black/20 border border-white/10 rounded-xl p-3 text-sm text-white resize-none focus:border-blue-500/50 outline-none"
                                placeholder="Duyuru metnini buraya yazın..."
                            />
                        </div>

                        <Button className="w-full" onClick={handleSend} disabled={!newMessage}>
                            Yayınla
                        </Button>
                    </div>
                </div>

                {/* History */}
                <div className="lg:col-span-2 bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                    <div className="p-4 border-b border-white/10 bg-black/20 flex justify-between items-center">
                        <h3 className="font-semibold text-white">Yayın Geçmişi</h3>
                        <span className="text-xs text-gray-500">{broadcasts.filter(b => b.active).length} Aktif Duyuru</span>
                    </div>

                    <div className="divide-y divide-white/5">
                        {broadcasts.map((item) => (
                            <div key={item.id} className="p-4 flex items-start gap-4 hover:bg-white/5 transition-colors group">
                                <div className={`mt-1 w-8 h-8 rounded-full flex items-center justify-center shrink-0 
                                    ${item.type === 'info' ? 'bg-blue-500/20 text-blue-400' :
                                        item.type === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                                            item.type === 'danger' ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
                                    }`}>
                                    {item.type === 'info' && <Info className="w-4 h-4" />}
                                    {item.type === 'warning' && <AlertTriangle className="w-4 h-4" />}
                                    {item.type === 'danger' && <AlertTriangle className="w-4 h-4" />}
                                    {item.type === 'success' && <CheckCircle className="w-4 h-4" />}
                                </div>
                                <div className="flex-1">
                                    <div className="flex justify-between items-start">
                                        <p className="text-white font-medium text-sm">{item.message}</p>
                                        <span className="text-[10px] text-gray-500 font-mono ml-2 shrink-0">{item.created_at}</span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-1">
                                        {item.active ? (
                                            <span className="text-[10px] bg-green-500/10 text-green-400 px-1.5 py-0.5 rounded border border-green-500/20">Yayında</span>
                                        ) : (
                                            <span className="text-[10px] bg-gray-500/10 text-gray-500 px-1.5 py-0.5 rounded border border-gray-500/20">Arşivlendi</span>
                                        )}
                                    </div>
                                </div>
                                <button
                                    className="opacity-0 group-hover:opacity-100 p-2 text-gray-500 hover:text-red-400 transition-all"
                                    onClick={() => setBroadcasts(broadcasts.filter(b => b.id !== item.id))}
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
