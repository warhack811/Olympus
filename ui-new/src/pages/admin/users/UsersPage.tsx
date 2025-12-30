
import { useState, useEffect } from 'react'
import {
    Search,
    MoreVertical,
    Shield,
    Ban,
    CheckCircle,
    Clock,
    Filter
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { authApi, API_DOMAIN } from '@/api/client' // Need a proper admin user api


interface User {
    username: string
    role: string
    created_at: string
    is_banned: boolean
    permissions: {
        censorship_level: number
        can_use_internet: boolean
        can_use_image: boolean
    }
    limits: {
        daily_internet: number
        daily_image: number
    }
}

// Temporary Admin API wrapper (should be moved to api/admin.ts)
const adminApi = {
    getUsers: async () => {
        const res = await fetch(`${API_DOMAIN}/api/admin/users`).then(r => r.json())
        return res
    },
    updateUser: async (username: string, data: any) => {
        const res = await fetch(`${API_DOMAIN}/api/admin/users/${username}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        return res.json()
    }
}

export function UsersPage() {
    const [users, setUsers] = useState<User[]>([])
    const [search, setSearch] = useState('')
    const [loading, setLoading] = useState(true)
    const [selectedUser, setSelectedUser] = useState<User | null>(null)

    useEffect(() => {
        loadUsers()
    }, [])

    const loadUsers = async () => {
        try {
            const data = await adminApi.getUsers()
            setUsers(data)
        } catch (error) {
            console.error(error)
        } finally {
            setLoading(false)
        }
    }

    const filteredUsers = users.filter(u =>
        u.username.toLowerCase().includes(search.toLowerCase())
    )

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white">Kullanıcı Yönetimi</h2>
                    <p className="text-gray-400">Toplam {users.length} kullanıcı</p>
                </div>
                <div className="flex gap-3">
                    <Input
                        placeholder="Kullanıcı ara..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        leftIcon={<Search className="w-4 h-4" />}
                        className="bg-white/5 border-white/10 w-64"
                    />
                    <Button variant="outline" leftIcon={<Filter className="w-4 h-4" />}>
                        Filtrele
                    </Button>
                </div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-white/5 text-gray-400 text-sm">
                        <tr>
                            <th className="p-4 font-medium">Kullanıcı</th>
                            <th className="p-4 font-medium">Rol</th>
                            <th className="p-4 font-medium">Durum</th>
                            <th className="p-4 font-medium">Limitler (Int/Img)</th>
                            <th className="p-4 font-medium text-right">İşlemler</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-sm">
                        {loading ? (
                            <tr><td colSpan={5} className="p-8 text-center text-gray-500">Yükleniyor...</td></tr>
                        ) : filteredUsers.map(user => (
                            <tr key={user.username} className="hover:bg-white/5 transition-colors group">
                                <td className="p-4 text-white font-medium flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-xs">
                                        {user.username.substring(0, 2).toUpperCase()}
                                    </div>
                                    {user.username}
                                </td>
                                <td className="p-4">
                                    <span className={`px-2 py-1 rounded-md text-xs font-medium ${user.role === 'admin' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'
                                        }`}>
                                        {user.role}
                                    </span>
                                </td>
                                <td className="p-4">
                                    {user.is_banned ? (
                                        <span className="flex items-center gap-1 text-red-400">
                                            <Ban className="w-3 h-3" /> Yasaklı
                                        </span>
                                    ) : (
                                        <span className="flex items-center gap-1 text-green-400">
                                            <CheckCircle className="w-3 h-3" /> Aktif
                                        </span>
                                    )}
                                </td>
                                <td className="p-4 text-gray-300 font-mono">
                                    {user.limits?.daily_internet || 0} / {user.limits?.daily_image || 0}
                                </td>
                                <td className="p-4 text-right">
                                    <Button size="icon-sm" variant="ghost" onClick={() => setSelectedUser(user)}>
                                        <MoreVertical className="w-4 h-4" />
                                    </Button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Quick Edit Modal / Drawer (Simplified for now) */}
            {selectedUser && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setSelectedUser(null)}>
                    <div className="bg-[#111] border border-white/10 rounded-2xl w-full max-w-lg p-6 shadow-2xl" onClick={e => e.stopPropagation()}>
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold text-white">Düzenle: {selectedUser.username}</h3>
                            <button onClick={() => setSelectedUser(null)} className="text-gray-500 hover:text-white">✕</button>
                        </div>

                        <div className="space-y-6">
                            {/* Role & Status */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs text-gray-400 uppercase">Rol</label>
                                    <select
                                        className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-white"
                                        defaultValue={selectedUser.role}
                                        onChange={(e) => adminApi.updateUser(selectedUser.username, { role: e.target.value }).then(loadUsers)}
                                    >
                                        <option value="user">User</option>
                                        <option value="admin">Admin</option>
                                        <option value="moderator">Moderator</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs text-gray-400 uppercase">Durum</label>
                                    <Button
                                        variant={selectedUser.is_banned ? "primary" : "destructive"}
                                        className="w-full justify-center"
                                        onClick={() => adminApi.updateUser(selectedUser.username, { is_banned: !selectedUser.is_banned }).then(loadUsers)}
                                    >
                                        {selectedUser.is_banned ? "Yasağı Kaldır" : "Kullanıcıyı Yasakla"}
                                    </Button>
                                </div>
                            </div>

                            {/* Features */}
                            <div className="space-y-3">
                                <label className="text-xs text-gray-400 uppercase">Yetkiler</label>
                                <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                                    <span className="text-sm">İnternet Erişimi</span>
                                    <input
                                        type="checkbox"
                                        checked={selectedUser.permissions?.can_use_internet}
                                        onChange={(e) => adminApi.updateUser(selectedUser.username, { can_use_internet: e.target.checked }).then(loadUsers)}
                                    />
                                </div>
                                <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                                    <span className="text-sm">Görsel Üretimi</span>
                                    <input
                                        type="checkbox"
                                        checked={selectedUser.permissions?.can_use_image}
                                        onChange={(e) => adminApi.updateUser(selectedUser.username, { can_use_image: e.target.checked }).then(loadUsers)}
                                    />
                                </div>
                            </div>

                            {/* Limits */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs text-gray-400 uppercase">Günlük İnternet</label>
                                    <Input
                                        type="number"
                                        defaultValue={selectedUser.limits?.daily_internet}
                                        onBlur={(e) => adminApi.updateUser(selectedUser.username, { daily_internet_limit: parseInt(e.target.value) }).then(loadUsers)}
                                        className="bg-black/20"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs text-gray-400 uppercase">Günlük Görsel</label>
                                    <Input
                                        type="number"
                                        defaultValue={selectedUser.limits?.daily_image}
                                        onBlur={(e) => adminApi.updateUser(selectedUser.username, { daily_image_limit: parseInt(e.target.value) }).then(loadUsers)}
                                        className="bg-black/20"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="mt-8 flex justify-end">
                            <Button variant="ghost" onClick={() => setSelectedUser(null)}>Kapat</Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
