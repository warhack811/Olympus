
import { useState } from 'react'
import { ThumbsDown, MessageSquare, Check, X, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'

const MOCK_FEEDBACK = [
    {
        id: 1,
        user: 'ahmet',
        query: 'Python ile merge sort kodu yaz',
        response: 'Tabii, işte Java kodu...',
        reason: 'Yanlış dil kullanıldı',
        status: 'pending'
    },
    {
        id: 2,
        user: 'admin',
        query: 'Sistem ne zaman kapanacak?',
        response: 'Bilmiyorum.',
        reason: 'Yetersiz cevap',
        status: 'pending'
    },
]

export function RLHFPage() {
    const [items, setItems] = useState(MOCK_FEEDBACK)

    const handleAction = (id: number, action: 'approve' | 'reject') => {
        setItems(items.map(i => i.id === id ? { ...i, status: action === 'approve' ? 'fixed' : 'ignored' } : i))
    }

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <ThumbsDown className="text-red-500" />
                        RLHF & Kalite Merkezi
                    </h2>
                    <p className="text-gray-400">Kullanıcı geri bildirimlerini inceleyin ve modeli eğitin</p>
                </div>
                <div className="flex gap-2 text-sm text-gray-500">
                    <span className="px-3 py-1 bg-white/5 rounded-lg border border-white/10">Bekleyen: {items.filter(i => i.status === 'pending').length}</span>
                    <span className="px-3 py-1 bg-white/5 rounded-lg border border-white/10">Düzeltilen: {items.filter(i => i.status === 'fixed').length}</span>
                </div>
            </header>

            <div className="grid grid-cols-1 gap-6">
                {items.filter(i => i.status === 'pending').length === 0 && (
                    <div className="text-center py-20 bg-white/5 rounded-2xl border border-white/10 border-dashed">
                        <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Check className="w-8 h-8 text-green-500" />
                        </div>
                        <h3 className="text-white font-medium text-lg">Harika İş!</h3>
                        <p className="text-gray-500">İncelenecek yeni geri bildirim yok.</p>
                    </div>
                )}

                {items.filter(i => i.status === 'pending').map((item) => (
                    <div key={item.id} className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                        <div className="p-4 bg-red-500/5 border-b border-white/10 flex justify-between items-center">
                            <div className="flex items-center gap-2">
                                <AlertCircle className="w-4 h-4 text-red-400" />
                                <span className="text-red-300 font-medium text-sm">Şikayet: {item.reason}</span>
                            </div>
                            <span className="text-xs text-gray-500">Kullanıcı: {item.user}</span>
                        </div>

                        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-xs text-gray-400 uppercase font-bold">Kullanıcı Sorusu</label>
                                <div className="p-4 bg-black/20 rounded-xl border border-white/5 text-white">
                                    {item.query}
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs text-gray-400 uppercase font-bold">Model Cevabı</label>
                                <div className="p-4 bg-black/20 rounded-xl border border-white/5 text-gray-300">
                                    {item.response}
                                </div>
                            </div>
                        </div>

                        <div className="px-6 pb-6 pt-0 flex justify-end gap-3">
                            <Button variant="ghost" className="text-gray-400 hover:text-white" onClick={() => handleAction(item.id, 'reject')}>
                                <X className="w-4 h-4 mr-2" /> Yoksay
                            </Button>
                            <Button className="bg-green-600 hover:bg-green-700 text-white" onClick={() => handleAction(item.id, 'approve')}>
                                <MessageSquare className="w-4 h-4 mr-2" /> Düzeltilmiş Cevap Yaz
                            </Button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
