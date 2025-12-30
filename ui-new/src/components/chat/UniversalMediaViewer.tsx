/**
 * UniversalMediaViewer Component
 * 
 * A generic full-screen viewer for both Mermaid diagrams and standard Images.
 * Features:
 * - Shared Pan/Zoom/Drag engine using CSS Transforms.
 * - Mode-specific rendering and downloads.
 * - Mobile-optimized, compact, transparent UI.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ZoomIn, ZoomOut, Maximize2, Download, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

interface UniversalMediaViewerProps {
    mode: 'mermaid' | 'image'
    // Mermaid specific
    svgElement?: SVGSVGElement
    diagramCode?: string
    // Image specific
    src?: string
    alt?: string
    onClose: () => void
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export function UniversalMediaViewer({
    mode,
    svgElement,
    diagramCode,
    src,
    alt,
    onClose
}: UniversalMediaViewerProps) {
    const [zoom, setZoom] = useState(1)
    const [position, setPosition] = useState({ x: 0, y: 0 })
    const [isDragging, setIsDragging] = useState(false)
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
    const [isDownloading, setIsDownloading] = useState(false)
    const [isLoading, setIsLoading] = useState(mode === 'image') // Image starts loading
    const [lastPinchDistance, setLastPinchDistance] = useState<number | null>(null)

    const containerRef = useRef<HTMLDivElement>(null)
    const mediaContainerRef = useRef<HTMLDivElement>(null)

    // ──────────────────────────────────────────────────────────────────────
    // MOUNT & LAYOUT (Mermaid Only)
    // ──────────────────────────────────────────────────────────────────────
    useEffect(() => {
        if (mode === 'mermaid' && svgElement && mediaContainerRef.current) {
            mediaContainerRef.current.innerHTML = ''
            const clone = svgElement.cloneNode(true) as SVGSVGElement
            clone.style.width = '100%'
            clone.style.height = 'auto'
            clone.style.maxWidth = 'none'
            clone.style.display = 'block'
            mediaContainerRef.current.appendChild(clone)
        }
    }, [mode, svgElement])

    // ESC key & Body scroll lock
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
        window.addEventListener('keydown', handleEsc)
        document.body.style.overflow = 'hidden'
        return () => {
            window.removeEventListener('keydown', handleEsc)
            document.body.style.overflow = ''
        }
    }, [onClose])

    // ──────────────────────────────────────────────────────────────────────
    // CONTROLS
    // ──────────────────────────────────────────────────────────────────────
    const handleZoomIn = useCallback(() => setZoom(prev => Math.min(prev + 0.2, 5)), [])
    const handleZoomOut = useCallback(() => setZoom(prev => Math.max(prev - 0.2, 0.5)), [])
    const handleResetZoom = useCallback(() => { setZoom(1); setPosition({ x: 0, y: 0 }); }, [])

    const handleWheel = useCallback((e: React.WheelEvent) => {
        e.preventDefault()
        const delta = e.deltaY > 0 ? -0.1 : 0.1
        setZoom(prev => Math.min(Math.max(prev + delta, 0.5), 5))
    }, [])

    // ──────────────────────────────────────────────────────────────────────
    // DOWNLOAD LOGIC
    // ──────────────────────────────────────────────────────────────────────

    // Mermaid SVG Sanitizer (Kept from MermaidViewer)
    const getCleanSvgForExport = useCallback(async (): Promise<SVGSVGElement | null> => {
        if (mode !== 'mermaid' || !mediaContainerRef.current) return null
        const originalSvg = mediaContainerRef.current.querySelector('svg')
        if (!originalSvg) return null

        let width = 800, height = 600, x = 0, y = 0
        try {
            const bbox = originalSvg.getBBox()
            width = bbox.width + 20
            height = bbox.height + 20
            x = bbox.x - 10
            y = bbox.y - 10
        } catch (e) {
            const rect = originalSvg.getBoundingClientRect()
            width = rect.width
            height = rect.height
        }

        const clone = originalSvg.cloneNode(true) as SVGSVGElement
        clone.setAttribute('width', width.toString())
        clone.setAttribute('height', height.toString())
        clone.setAttribute('viewBox', `${x} ${y} ${width} ${height}`)
        clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')

        const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
        bgRect.setAttribute('x', x.toString())
        bgRect.setAttribute('y', y.toString())
        bgRect.setAttribute('width', width.toString())
        bgRect.setAttribute('height', height.toString())
        bgRect.setAttribute('fill', '#ffffff')
        clone.insertBefore(bgRect, clone.firstChild)

        const allElements = clone.querySelectorAll('*')
        allElements.forEach(el => {
            if (el instanceof SVGElement) {
                const fill = el.getAttribute('fill')
                if (fill === 'transparent' || fill === 'none' || (fill && fill.startsWith('rgba(0,0,0,0)'))) {
                    el.setAttribute('fill', 'none')
                }
            }
        })
        return clone
    }, [mode])

    const handleDownload = useCallback(async () => {
        if (isDownloading) return
        setIsDownloading(true)

        try {
            if (mode === 'mermaid') {
                const svg = await getCleanSvgForExport()
                if (!svg) throw new Error('SVG Hazırlanamadı')
                const serializer = new XMLSerializer()
                const source = serializer.serializeToString(svg)
                const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `mermaid-${Date.now()}.svg`
                a.click()
                URL.revokeObjectURL(url)
            } else if (mode === 'image' && src) {
                const response = await fetch(src)
                const blob = await response.blob()
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `image-${Date.now()}.${blob.type.split('/')[1] || 'png'}`
                a.click()
                URL.revokeObjectURL(url)
            }
        } catch (e: any) {
            alert('İndirme Hatası: ' + e.message)
        } finally {
            setIsDownloading(false)
        }
    }, [isDownloading, mode, src, getCleanSvgForExport])

    // ──────────────────────────────────────────────────────────────────────
    // PAN / DRAG LOGIC (Universal)
    // ──────────────────────────────────────────────────────────────────────
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        setIsDragging(true)
        setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y })
    }, [position])

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (isDragging) {
            setPosition({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
        }
    }, [isDragging, dragStart])

    const handleMouseUp = useCallback(() => setIsDragging(false), [])

    const handleTouchStart = useCallback((e: React.TouchEvent) => {
        if (e.touches.length === 1) {
            setIsDragging(true)
            setDragStart({ x: e.touches[0].clientX - position.x, y: e.touches[0].clientY - position.y })
        } else if (e.touches.length === 2) {
            const dist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            )
            setLastPinchDistance(dist)
        }
    }, [position])

    const handleTouchMove = useCallback((e: React.TouchEvent) => {
        if (e.touches.length === 1 && isDragging) {
            setPosition({ x: e.touches[0].clientX - dragStart.x, y: e.touches[0].clientY - dragStart.y })
        } else if (e.touches.length === 2 && lastPinchDistance !== null) {
            const dist = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            )
            const delta = (dist - lastPinchDistance) / 200
            setZoom(prev => Math.min(Math.max(prev + delta, 0.5), 5))
            setLastPinchDistance(dist)
        }
    }, [isDragging, dragStart, lastPinchDistance])

    const handleTouchEnd = useCallback(() => {
        setIsDragging(false)
        setLastPinchDistance(null)
    }, [])

    // ──────────────────────────────────────────────────────────────────────
    // RENDER
    // ──────────────────────────────────────────────────────────────────────

    return createPortal(
        <AnimatePresence>
            <motion.div
                ref={containerRef}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-[9999] bg-black/90 backdrop-blur-sm flex items-center justify-center p-0 overflow-hidden"
                onClick={(e) => {
                    if (e.target === containerRef.current && !isDragging) onClose()
                }}
            >
                {/* TOOLBAR */}
                <div className="absolute top-4 left-0 right-0 z-50 flex items-center justify-between px-4 pointer-events-none">

                    {/* LEFT: Zoom */}
                    <div className="bg-black/30 backdrop-blur-md rounded-lg p-1 flex items-center gap-1 pointer-events-auto shadow-lg border border-white/5">
                        <ControlButton icon={<ZoomOut className="h-4 w-4" />} onClick={handleZoomOut} disabled={zoom <= 0.5} label="Uzaklaş" />
                        <span className="text-white text-[10px] font-mono min-w-[2.5rem] text-center">{Math.round(zoom * 100)}%</span>
                        <ControlButton icon={<ZoomIn className="h-4 w-4" />} onClick={handleZoomIn} disabled={zoom >= 5} label="Yakınlaş" />
                        <div className="w-px h-4 bg-white/10 mx-0.5" />
                        <ControlButton icon={<Maximize2 className="h-4 w-4" />} onClick={handleResetZoom} label="Sıfırla" />
                    </div>

                    {/* RIGHT: Actions */}
                    <div className="bg-black/30 backdrop-blur-md rounded-lg p-1 flex items-center gap-1 pointer-events-auto shadow-lg border border-white/5">
                        <ControlButton
                            icon={isDownloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4 text-white" />}
                            onClick={handleDownload}
                            disabled={isDownloading}
                            label="İndir"
                        />
                        <div className="w-px h-4 bg-white/10 mx-0.5" />
                        <ControlButton icon={<X className="h-4 w-4" />} onClick={onClose} label="Kapat" />
                    </div>
                </div>

                {/* CONTENT AREA */}
                <div
                    className={cn(
                        "w-full h-full flex items-center justify-center relative",
                        isDragging ? "cursor-grabbing" : "cursor-grab"
                    )}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                    onWheel={handleWheel}
                    onTouchStart={handleTouchStart}
                    onTouchMove={handleTouchMove}
                    onTouchEnd={handleTouchEnd}
                >
                    {/* Loading Spinner for high-res images */}
                    {isLoading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/20 z-10">
                            <Loader2 className="h-8 w-8 text-white/50 animate-spin" />
                        </div>
                    )}

                    <div
                        ref={mediaContainerRef}
                        className="transition-transform duration-75 ease-out origin-center will-change-transform flex items-center justify-center"
                        style={{
                            transform: `translate(${position.x}px, ${position.y}px) scale(${zoom})`
                        }}
                    >
                        {mode === 'image' && src && (
                            <img
                                src={src}
                                alt={alt || 'Image'}
                                className="max-w-[90vw] max-h-[85vh] object-contain select-none pointer-events-none"
                                onLoad={() => setIsLoading(false)}
                                onError={() => setIsLoading(false)}
                            />
                        )}
                        {/* Mermaid content is injected via useEffect into mediaContainerRef */}
                    </div>
                </div>

                {/* Footer Hint */}
                <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 bg-black/20 backdrop-blur-sm rounded-full px-3 py-1 pointer-events-none">
                    <p className="text-white/40 text-[10px] font-medium font-sans">
                        Sürükle & Yakınlaştır
                    </p>
                </div>
            </motion.div>
        </AnimatePresence>,
        document.body
    )
}

function ControlButton({ icon, onClick, disabled, label }: any) {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            title={label}
            className={cn(
                "p-2 rounded-md transition-colors hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed",
                "text-white/90"
            )}
        >
            {icon}
        </button>
    )
}
