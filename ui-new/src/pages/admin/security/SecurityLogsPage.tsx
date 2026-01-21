
import { useState, useEffect } from 'react'
import { ShieldAlert, Search, Filter, AlertTriangle, Lock, Globe } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

// Mock Security API
const securityApi = {
    getLogs: async () => [
        { id: 1, type: 'warning', message: 'Failed login attempt (admin)', ip: '192.168.1.15', user: 'unknown', time: '10:42:15' },
        { id: 2, type: 'info', message: 'User "ahmet" updated profile', ip: '192.168.1.4', user: 'ahmet', time: '10:40:00' },
        { id: 3, type: 'danger', message: 'SQL Injection detected in query', ip: '45.12.99.1', user: 'guest', time: '09:15:22' },
        { id: 4, type: 'info', message: 'System feature "chat" disabled', ip: 'localhost', user: 'admin', time: '08:00:00' },
        { id: 5, type: 'warning', message: 'Rate limit exceeded (Image Gen)', ip: '192.168.1.20', user: 'mehmet', time: 'Yesterday' },
    ]
}

export function SecurityLogsPage() {
    const [logs, setLogs] = useState<any[]>([])
    const [search, setSearch] = useState('')

    useEffect(() => {
        securityApi.getLogs().then(setLogs)
    }, [])

    const filteredLogs = logs.filter(log =>
        log.message.toLowerCase().includes(search.toLowerCase()) ||
        log.user.toLowerCase().includes(search.toLowerCase())
    )

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <ShieldAlert className="text-red-500" />
                        Güvenlik & Log Kayıtları
                    </h2>
                    <p className="text-gray-400">Sistem aktivitesi, hata kayıtları ve güvenlik olayları</p>
                </div>
                <div className="flex gap-3">
                    <Button variant="outline" className="text-red-400 border-red-500/20 hover:bg-red-500/10">
                        Logları Temizle
                    </Button>
                    <Button variant="outline" leftIcon={<Lock className="w-4 h-4" />}>
                        IP Ban Listesi
                    </Button>
                </div>
            </header>

            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-2xl">
                    <h3 className="text-red-400 font-medium text-sm uppercase">Kritik Tehditler</h3>
                    <p className="text-3xl font-bold text-white mt-1">0</p>
                </div>
                <div className="bg-yellow-500/10 border border-yellow-500/20 p-6 rounded-2xl">
                    <h3 className="text-yellow-400 font-medium text-sm uppercase">Uyarılar (Son 24s)</h3>
                    <p className="text-3xl font-bold text-white mt-1">12</p>
                </div>
                <div className="bg-blue-500/10 border border-blue-500/20 p-6 rounded-2xl">
                    <h3 className="text-blue-400 font-medium text-sm uppercase">Aktif Oturum</h3>
                    <p className="text-3xl font-bold text-white mt-1">4</p>
                </div>
            </div>

            {/* Log Table */}
            <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                <div className="p-4 border-b border-white/10 flex justify-between items-center bg-black/20">
                    <div className="flex items-center gap-2">
                        <Filter className="w-4 h-4 text-gray-500" />
                        <span className="text-sm font-medium text-gray-400">Tüm Kayıtlar</span>
                    </div>
                    <div className="w-64">
                        <Input
                            placeholder="Loglarda ara..."
                            className="bg-black/20 border-white/10 h-9"
                            onChange={(e) => setSearch(e.target.value)}
                            leftIcon={<Search className="w-3 h-3" />}
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left whitespace-nowrap">
                        <thead className="bg-white/5 text-gray-400 text-xs uppercase">
                            <tr>
                                <th className="p-4 font-medium w-16">Tip</th>
                                <th className="p-4 font-medium">Zaman</th>
                                <th className="p-4 font-medium">Kullanıcı</th>
                                <th className="p-4 font-medium">IP Adresi</th>
                                <th className="p-4 font-medium">Olay</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-sm font-mono">
                            {filteredLogs.map((log) => (
                                <tr key={log.id} className="hover:bg-white/5 transition-colors">
                                    <td className="p-4 text-center">
                                        {log.type === 'danger' && <AlertTriangle className="w-4 h-4 text-red-500 mx-auto" />}
                                        {log.type === 'warning' && <AlertTriangle className="w-4 h-4 text-yellow-500 mx-auto" />}
                                        {log.type === 'info' && <span className="w-2 h-2 rounded-full bg-blue-500 block mx-auto" />}
                                    </td>
                                    <td className="p-4 text-gray-500">{log.time}</td>
                                    <td className="p-4 text-gray-300">{log.user}</td>
                                    <td className="p-4 text-gray-500 flex items-center gap-2">
                                        <Globe className="w-3 h-3" /> {log.ip}
                                    </td>
                                    <td className="p-4 text-white">
                                        {log.message}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
