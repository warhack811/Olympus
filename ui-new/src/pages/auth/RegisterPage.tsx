
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { User as UserIcon, Lock, Key, ArrowRight, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { authApi } from '@/api/client'
import { useToast } from '@/components/common'

export function RegisterPage() {
    const [formData, setFormData] = useState({
        username: '',
        password: '',
        confirmPassword: '',
        inviteCode: ''
    })
    const [isLoading, setIsLoading] = useState(false)
    const toast = useToast()
    const navigate = useNavigate()

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }))
    }

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!formData.username || !formData.password || !formData.inviteCode) {
            toast.error('Lütfen tüm zorunlu alanları doldurun.')
            return
        }

        if (formData.password !== formData.confirmPassword) {
            toast.error('Şifreler eşleşmiyor.')
            return
        }

        setIsLoading(true)
        try {
            await authApi.register({
                username: formData.username,
                password: formData.password,
                invite_code: formData.inviteCode
            })

            toast.success('Kayıt başarılı! Giriş sayfasına yönlendiriliyorsunuz.')
            setTimeout(() => navigate('/login'), 1500)

        } catch (error: any) {
            toast.error(error.message || 'Kayıt işlemi başarısız.')
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
                    <p className="text-gray-300">Yeni hesap oluşturun</p>
                </div>

                <form onSubmit={handleRegister} className="space-y-4">
                    <Input
                        name="inviteCode"
                        type="text"
                        placeholder="Davet Kodu (Zorunlu)"
                        value={formData.inviteCode}
                        onChange={handleChange}
                        leftIcon={<Key className="w-4 h-4 text-purple-400" />}
                        className="bg-black/20 border-purple-500/30 text-white placeholder:text-gray-400 focus:bg-black/40 hover:bg-black/30 transition-colors"
                    />

                    <div className="h-px bg-white/10 my-4" />

                    <Input
                        name="username"
                        type="text"
                        placeholder="Kullanıcı Adı"
                        value={formData.username}
                        onChange={handleChange}
                        leftIcon={<UserIcon className="w-4 h-4" />}
                        className="bg-black/20 border-white/10 text-white placeholder:text-gray-400 focus:bg-black/40 hover:bg-black/30 transition-colors"
                    />

                    <Input
                        name="password"
                        type="password"
                        placeholder="Şifre"
                        value={formData.password}
                        onChange={handleChange}
                        leftIcon={<Lock className="w-4 h-4" />}
                        className="bg-black/20 border-white/10 text-white placeholder:text-gray-400 focus:bg-black/40 hover:bg-black/30 transition-colors"
                    />

                    <Input
                        name="confirmPassword"
                        type="password"
                        placeholder="Şifre Tekrar"
                        value={formData.confirmPassword}
                        onChange={handleChange}
                        leftIcon={<CheckCircle className="w-4 h-4" />}
                        className="bg-black/20 border-white/10 text-white placeholder:text-gray-400 focus:bg-black/40 hover:bg-black/30 transition-colors"
                    />

                    <Button
                        type="submit"
                        variant="primary"
                        className="w-full h-12 text-lg font-semibold mt-4 shadow-purple-500/20"
                        isLoading={isLoading}
                        rightIcon={<ArrowRight className="w-4 h-4" />}
                    >
                        Kayıt Ol
                    </Button>
                </form>

                <div className="mt-6 text-center">
                    <p className="text-sm text-gray-400">
                        Zaten hesabınız var mı?{' '}
                        <Link to="/login" className="text-purple-400 hover:text-purple-300 font-medium hover:underline transition-all">
                            Giriş yapın
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
