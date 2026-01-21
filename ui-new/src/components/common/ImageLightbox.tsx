import { motion } from 'framer-motion'
import { Download, X } from 'lucide-react'
import { Button } from '@/components/ui'

interface ImageLightboxProps {
    src: string
    onClose: () => void
}

export function ImageLightbox({ src, onClose }: ImageLightboxProps) {
    const handleDownload = async () => {
        try {
            const response = await fetch(src)
            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `generated-${Date.now()}.png`
            a.click()
            window.URL.revokeObjectURL(url)
        } catch (error) {
            console.error('Download failed:', error)
            window.open(src, '_blank')
        }
    }

    return (
        <>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={onClose}
                className="fixed inset-0 bg-black/90 z-(--z-max) backdrop-blur-sm"
            />

            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="fixed inset-4 md:inset-12 z-(--z-max) flex flex-col items-center justify-center pointer-events-none"
            >
                <div className="relative max-w-full max-h-[calc(100%-60px)] pointer-events-auto group">
                    <img
                        src={src}
                        alt="Full size"
                        className="max-w-full max-h-[calc(100vh-140px)] object-contain rounded-lg shadow-2xl"
                    />

                    {/* Close button - Desktop (top-right of image) */}
                    <button
                        onClick={onClose}
                        className="absolute -top-4 -right-4 p-2 bg-black/50 hover:bg-black/70 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hidden md:block"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Controls */}
                <div className="flex gap-2 mt-6 pointer-events-auto">
                    <Button
                        variant="secondary"
                        onClick={handleDownload}
                        leftIcon={<Download className="h-4 w-4" />}
                    >
                        İndir
                    </Button>
                    <Button
                        variant="ghost"
                        onClick={onClose}
                        className="text-white hover:bg-white/10 hover:text-white"
                    >
                        Kapat
                    </Button>
                </div>
            </motion.div>
        </>
    )
}
