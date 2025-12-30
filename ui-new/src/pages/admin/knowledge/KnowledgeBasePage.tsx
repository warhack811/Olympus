
import { useState, useEffect } from 'react'
import { Database, Upload, FileText, Trash2, Search, RefreshCw, Layers } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

// Mock Data & API Wrapper
const ragApi = {
    getDocuments: async () => [
        { id: '1', name: 'sirket_politikasi.pdf', size: '2.4 MB', chunks: 142, status: 'indexed', uploaded_at: '2023-10-01' },
        { id: '2', name: 'urun_katalogu_v2.docx', size: '5.1 MB', chunks: 856, status: 'indexed', uploaded_at: '2023-10-05' },
        { id: '3', name: 'musteri_sikayetleri_2023.txt', size: '0.5 MB', chunks: 45, status: 'processing', uploaded_at: '2023-10-25' },
    ],
    uploadDocument: async (file: File) => {
        return { id: Math.random().toString(), name: file.name, size: '1.0 MB', chunks: 0, status: 'uploading' }
    },
    deleteDocument: async (id: string) => {
        // Mock deletion
        return true
    }
}

export function KnowledgeBasePage() {
    const [documents, setDocuments] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadData()
    }, [])

    const loadData = async () => {
        setLoading(true)
        const data = await ragApi.getDocuments()
        setDocuments(data)
        setLoading(false)
    }

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Database className="text-cyan-500" />
                        Bilgi Bankası (RAG)
                    </h2>
                    <p className="text-gray-400">Yapay zekanın eğitim verileri ve vektör veritabanı durumu</p>
                </div>
                <div className="flex gap-3">
                    <Button variant="outline" leftIcon={<RefreshCw className="w-4 h-4" />} onClick={loadData}>
                        Yenile
                    </Button>
                    <Button leftIcon={<Upload className="w-4 h-4" />}>
                        Yeni Doküman Yükle
                    </Button>
                </div>
            </header>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white/5 border border-white/10 p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-cyan-500/20 flex items-center justify-center">
                        <FileText className="w-6 h-6 text-cyan-500" />
                    </div>
                    <div>
                        <p className="text-sm text-gray-400">Toplam Doküman</p>
                        <p className="text-2xl font-bold text-white mb-0">{documents.length}</p>
                    </div>
                </div>
                <div className="bg-white/5 border border-white/10 p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                        <Layers className="w-6 h-6 text-purple-500" />
                    </div>
                    <div>
                        <p className="text-sm text-gray-400">Vektör Parçacığı (Chunks)</p>
                        <p className="text-2xl font-bold text-white mb-0">1,245</p>
                    </div>
                </div>
                <div className="bg-white/5 border border-white/10 p-6 rounded-2xl flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center">
                        <Database className="w-6 h-6 text-green-500" />
                    </div>
                    <div>
                        <p className="text-sm text-gray-400">DB Boyutu</p>
                        <p className="text-2xl font-bold text-white mb-0">45.2 MB</p>
                    </div>
                </div>
            </div>

            {/* File Manager */}
            <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                <div className="p-4 border-b border-white/10 flex justify-between items-center bg-black/20">
                    <h3 className="font-semibold text-white">Yüklü Dosyalar</h3>
                    <div className="w-64">
                        <Input
                            placeholder="Dosya ara..."
                            className="bg-black/20 border-white/10 h-9"
                            leftIcon={<Search className="w-3 h-3" />}
                        />
                    </div>
                </div>

                <table className="w-full text-left">
                    <thead className="bg-white/5 text-gray-400 text-xs uppercase">
                        <tr>
                            <th className="p-4 font-medium">Dosya Adı</th>
                            <th className="p-4 font-medium">Boyut</th>
                            <th className="p-4 font-medium">Chunks</th>
                            <th className="p-4 font-medium">Durum</th>
                            <th className="p-4 font-medium text-right">İşlem</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-sm">
                        {documents.map((doc) => (
                            <tr key={doc.id} className="hover:bg-white/5 transition-colors group">
                                <td className="p-4 flex items-center gap-3 text-white">
                                    <FileText className="w-4 h-4 text-gray-500" />
                                    {doc.name}
                                </td>
                                <td className="p-4 text-gray-400 font-mono text-xs">{doc.size}</td>
                                <td className="p-4 text-gray-400 font-mono text-xs">{doc.chunks}</td>
                                <td className="p-4">
                                    {doc.status === 'indexed' ? (
                                        <span className="bg-green-500/10 text-green-400 px-2 py-1 rounded text-xs font-medium border border-green-500/20">
                                            Hazır
                                        </span>
                                    ) : (
                                        <span className="bg-yellow-500/10 text-yellow-400 px-2 py-1 rounded text-xs font-medium border border-yellow-500/20 animate-pulse">
                                            İşleniyor
                                        </span>
                                    )}
                                </td>
                                <td className="p-4 text-right">
                                    <button className="text-gray-500 hover:text-red-400 transition-colors p-2 rounded-lg hover:bg-white/5">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
