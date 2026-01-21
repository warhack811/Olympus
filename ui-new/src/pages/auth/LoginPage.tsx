
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { User as UserIcon, Lock, ArrowRight, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { authApi } from '@/api/client'
import { useToast } from '@/components/common'

export function LoginPage() {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const toast = useToast()

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!username || !password) {
            toast.error('Lütfen tüm alanları doldurun.')
            return
        }

        setIsLoading(true)
        try {
            await authApi.login(username, password)
            toast.success('Giriş başarılı!')

            // Backend sets HttpOnly cookie, so we just reload/redirect
            // Reloading ensures all states (WebSocket, Preferences) are fresh
            window.location.href = '/new-ui/'
        } catch (error: any) {
            toast.error(error.message || 'Giriş yapılamadı.')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-gray-950">
            {/* Dark Overlay */}
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

            {/* Glass Card */}
            <div className="relative w-full max-w-md p-6 md:p-8 m-4 rounded-2xl bg-white/10 border border-white/20 backdrop-blur-xl shadow-2xl">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-white mb-2">Mami AI</h1>
                    <p className="text-gray-300">Hesabınıza giriş yapın</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-6">
                    <Input
                        type="text"
                        placeholder="Kullanıcı Adı"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        leftIcon={<UserIcon className="w-4 h-4" />}
                        className="bg-black/20 border-white/10 text-white placeholder:text-gray-400 focus:bg-black/40 hover:bg-black/30 transition-colors"
                    />

                    <Input
                        type="password"
                        placeholder="Şifre"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        leftIcon={<Lock className="w-4 h-4" />}
                        className="bg-black/20 border-white/10 text-white placeholder:text-gray-400 focus:bg-black/40 hover:bg-black/30 transition-colors"
                    />

                    <Button
                        type="submit"
                        variant="primary"
                        className="w-full h-12 text-lg font-semibold shadow-purple-500/20"
                        isLoading={isLoading}
                        rightIcon={<ArrowRight className="w-4 h-4" />}
                    >
                        Giriş Yap
                    </Button>
                </form>

                <div className="mt-6 text-center">
                    <p className="text-sm text-gray-400">
                        Hesabınız yok mu?{' '}
                        <Link to="/register" className="text-purple-400 hover:text-purple-300 font-medium hover:underline transition-all">
                            Davet kodu ile kayıt olun
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
