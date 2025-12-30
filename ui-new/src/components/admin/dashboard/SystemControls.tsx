
import { useState, useEffect } from 'react'
import { Switch } from '@/components/ui/Switch'
import { fetchApi, API_DOMAIN } from '@/api/client' // Assuming we can expose fetchApi or create a new method


interface FeatureFlags {
    chat: boolean
    image_generation: boolean
    file_upload: boolean
    internet: boolean
    bela_mode: boolean
    groq_enabled: boolean
}

export function SystemControls() {
    const [features, setFeatures] = useState<FeatureFlags | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadFeatures()
    }, [])

    const loadFeatures = async () => {
        try {
            // Hardcoding fetch for now as systemApi isn't fully updated yet with this specific endpoint structure
            const res = await fetch(`${API_DOMAIN}/api/system/features`).then(r => r.json())
            setFeatures(res.features || {})
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
        }
    }

    const toggleFeature = async (key: string, enabled: boolean) => {
        // Optimistic update
        setFeatures(prev => prev ? ({ ...prev, [key]: enabled }) : null)

        try {
            const res = await fetch(`${API_DOMAIN}/api/system/features/toggle`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, enabled })
            })
            if (!res.ok) throw new Error('Failed to toggle')
        } catch (error) {
            console.error(error)
            // Revert on error
            loadFeatures()
        }
    }

    if (loading || !features) return <div className="p-4 bg-white/5 rounded-2xl animate-pulse h-48" />

    const FLAGS = [
        { key: 'chat', label: 'Sohbet Sistemi', desc: 'Genel sohbet erişimi' },
        { key: 'image_generation', label: 'Görsel Üretimi', desc: 'Stable Diffusion / Flux' },
        { key: 'internet', label: 'İnternet Erişimi', desc: 'Google Search entegrasyonu' },
        { key: 'file_upload', label: 'Dosya Yükleme', desc: 'RAG / PDF analizi' },
        { key: 'groq_enabled', label: 'Hızlı Mod (Groq)', desc: 'Düşük gecikmeli yanıtlar' },
        { key: 'bela_mode', label: 'Bela Modu', desc: 'Agresif kişilik (Eğlence)' },
    ]

    return (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
            <h3 className="text-lg font-semibold mb-4 text-white">Sistem Kontrolleri (Kill Switch)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {FLAGS.map((flag) => (
                    <div key={flag.key} className="flex items-center justify-between p-3 bg-black/20 rounded-xl border border-white/5">
                        <div>
                            <p className="font-medium text-sm text-gray-200">{flag.label}</p>
                            <p className="text-xs text-gray-500">{flag.desc}</p>
                        </div>
                        <Switch
                            checked={features[flag.key as keyof FeatureFlags]}
                            onCheckedChange={(c) => toggleFeature(flag.key, c)}
                        />
                    </div>
                ))}
            </div>
        </div>
    )
}
