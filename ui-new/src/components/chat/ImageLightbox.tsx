/**
 * ImageLightbox Component
 * 
 * Simple fullscreen image viewer with zoom and download
 */

import { useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ZoomIn, ZoomOut, Maximize2, Download } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ImageLightboxProps {
    imageUrl: string
    imageName?: string
    onClose: () => void
}

export function ImageLightbox({ imageUrl, imageName = 'image', onClose }: ImageLightboxProps) {
    const [zoom, setZoom] = useState(1)

    const handleZoomIn = useCallback(() => {
        setZoom(prev => Math.min(prev + 0.2, 3))
    }, [])

    const handleZoomOut = useCallback(() => {
        setZoom(prev => Math.max(prev - 0.2, 0.5))
    }, [])

    const handleResetZoom = useCallback(() => {
        setZoom(1)
    }, [])

    const handleDownload = useCallback(() => {
        const link = document.createElement('a')
        link.href = imageUrl
        link.download = `${imageName}-${Date.now()}.png`
        link.click()
    }, [imageUrl, imageName])

    return createPortal(
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm flex items-center justify-center"
                onClick={onClose}
            >
                {/* Header - Controls */}
                <div className="absolute top-4 left-0 right-0 z-10 flex items-center justify-between px-6">
                    {/* Zoom Controls */}
                    <div className="flex items-center gap-2 bg-black/60 backdrop-blur-md rounded-lg p-2">
                        <ControlButton
                            icon={<ZoomOut className="h-4 w-4" />}
                            onClick={(e) => { e.stopPropagation(); handleZoomOut() }}
                            disabled={zoom <= 0.5}
                            label="Uzaklaştır"
                        />
                        <span className="text-white text-sm font-medium px-2 min-w-[4rem] text-center">
                            {Math.round(zoom * 100)}%
                        </span>
                        <ControlButton
                            icon={<ZoomIn className="h-4 w-4" />}
                            onClick={(e) => { e.stopPropagation(); handleZoomIn() }}
                            disabled={zoom >= 3}
                            label="Yakınlaştır"
                        />
                        <div className="w-px h-6 bg-white/20 mx-1" />
                        <ControlButton
                            icon={<Maximize2 className="h-4 w-4" />}
                            onClick={(e) => { e.stopPropagation(); handleResetZoom() }}
                            label="Sıfırla"
                        />
                    </div>

                    {/* Download and Close */}
                    <div className="flex items-center gap-2 bg-black/60 backdrop-blur-md rounded-lg p-2">
                        <ControlButton
                            icon={<Download className="h-4 w-4" />}
                            onClick={(e) => { e.stopPropagation(); handleDownload() }}
                            label="İndir"
                        />
                        <div className="w-px h-6 bg-white/20 mx-1" />
                        <ControlButton
                            icon={<X className="h-4 w-4" />}
                            onClick={(e) => { e.stopPropagation(); onClose() }}
                            label="Kapat"
                        />
                    </div>
                </div>

                {/* Image */}
                <img
                    src={imageUrl}
                    alt={imageName}
                    className="max-w-[90vw] max-h-[90vh] object-contain"
                    style={{
                        transform: `scale(${zoom})`,
                        transition: 'transform 0.2s ease-out'
                    }}
                    onClick={(e) => e.stopPropagation()}
                />

                {/* Instructions */}
                <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/60 backdrop-blur-md rounded-lg px-4 py-2">
                    <p className="text-white/70 text-sm">
                        <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-white text-xs">ESC</kbd>
                        {' '}tuşu ile kapatın • Tıklayarak kapat
                    </p>
                </div>
            </motion.div>
        </AnimatePresence>,
        document.body
    )
}

interface ControlButtonProps {
    icon: React.ReactNode
    onClick: (e: React.MouseEvent) => void
    disabled?: boolean
    label: string
}

function ControlButton({ icon, onClick, disabled, label }: ControlButtonProps) {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            aria-label={label}
            title={label}
            className={cn(
                "p-2 rounded-md transition-all duration-200",
                disabled
                    ? "opacity-40 cursor-not-allowed"
                    : "hover:bg-white/10 text-white active:scale-95"
            )}
        >
            {icon}
        </button>
    )
}
