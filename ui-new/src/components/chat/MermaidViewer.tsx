/**
 * MermaidViewer Component
 * 
 * Full-screen modal for viewing and interacting with mermaid diagrams.
 * RESTORED INTERACTIONS + NEW UI LAYOUT:
 * - PDF: Uses svg2pdf for vector quality (Sanitized).
 * - SVG: Raw Vector Export.
 * - Layout: Split Toolbar (Left: Zoom, Right: Download), 50% Transparent.
 * - Interaction: Pan/Drag, Wheel Zoom, Pinch Zoom reinstated.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ZoomIn, ZoomOut, Maximize2, Download, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

interface MermaidViewerProps {
    svgElement: SVGSVGElement
    diagramCode: string
    onClose: () => void
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export function MermaidViewer({ svgElement, diagramCode, onClose }: MermaidViewerProps) {
    const [zoom, setZoom] = useState(1)
    const [position, setPosition] = useState({ x: 0, y: 0 })
    const [isDragging, setIsDragging] = useState(false)
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
    const [isDownloading, setIsDownloading] = useState(false)
    const [lastPinchDistance, setLastPinchDistance] = useState<number | null>(null)

    const containerRef = useRef<HTMLDivElement>(null)
    const svgContainerRef = useRef<HTMLDivElement>(null)

    // ──────────────────────────────────────────────────────────────────────
    // MOUNT & LAYOUT
    // ──────────────────────────────────────────────────────────────────────
    useEffect(() => {
        if (svgContainerRef.current) {
            svgContainerRef.current.innerHTML = '' // Clear previous
            const clone = svgElement.cloneNode(true) as SVGSVGElement

            // For proper centering and sizing in pan-zoom mode
            // We remove fixed sizes and let it scale naturally
            clone.style.width = '100%'
            clone.style.height = 'auto'
            clone.style.maxWidth = 'none'
            clone.style.display = 'block'

            svgContainerRef.current.appendChild(clone)
        }
    }, [svgElement])

    // ESC key
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose()
        }
        window.addEventListener('keydown', handleEsc)
        return () => window.removeEventListener('keydown', handleEsc)
    }, [onClose])

    // Body scroll lock
    useEffect(() => {
        document.body.style.overflow = 'hidden'
        return () => { document.body.style.overflow = '' }
    }, [])

    // ──────────────────────────────────────────────────────────────────────
    // CONTROLS
    // ──────────────────────────────────────────────────────────────────────
    const handleZoomIn = useCallback(() => setZoom(prev => Math.min(prev + 0.2, 5)), [])
    const handleZoomOut = useCallback(() => setZoom(prev => Math.max(prev - 0.2, 0.5)), [])
    const handleResetZoom = useCallback(() => { setZoom(1); setPosition({ x: 0, y: 0 }); }, [])

    // Wheel Zoom (Restored)
    const handleWheel = useCallback((e: React.WheelEvent) => {
        e.preventDefault()
        const delta = e.deltaY > 0 ? -0.1 : 0.1
        setZoom(prev => Math.min(Math.max(prev + delta, 0.5), 5))
    }, [])

    // ──────────────────────────────────────────────────────────────────────
    // HELPER: SANITIZE SVG FOR EXPORT (Anti-Black Box)
    // ──────────────────────────────────────────────────────────────────────
    const getCleanSvgForExport = useCallback(async (): Promise<SVGSVGElement | null> => {
        if (!svgContainerRef.current) return null
        const originalSvg = svgContainerRef.current.querySelector('svg')
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
                    // Correctly handle stroke-only elements
                    if (!el.getAttribute('stroke')) {
                        el.setAttribute('fill', 'none')
                    } else {
                        el.setAttribute('fill', 'none')
                    }
                }
            }
        })

        return clone
    }, [])

    // ──────────────────────────────────────────────────────────────────────
    // EXPORT DOWNLOADS
    // ──────────────────────────────────────────────────────────────────────



    const downloadSVG = useCallback(async () => {
        if (isDownloading) return
        setIsDownloading(true)
        try {
            const svg = await getCleanSvgForExport()
            if (!svg) throw new Error('SVG Prep Failed')

            const serializer = new XMLSerializer()
            const source = serializer.serializeToString(svg)
            const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" })
            const url = URL.createObjectURL(blob)

            const a = document.createElement('a')
            a.href = url
            a.download = `mermaid-${Date.now()}.svg`
            a.click()
            URL.revokeObjectURL(url)
        } catch (e: any) {
            alert('SVG İndirme Hatası: ' + e.message)
        } finally {
            setIsDownloading(false)
        }
    }, [isDownloading, getCleanSvgForExport])

    // ──────────────────────────────────────────────────────────────────────
    // PAN / DRAG LOGIC (Restored & Robust)
    // ──────────────────────────────────────────────────────────────────────
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        // Drag works anywhere inside the container (unless checking specific excluded targets if needed)
        setIsDragging(true)
        setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y })
    }, [position])

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (isDragging) {
            setPosition({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
        }
    }, [isDragging, dragStart])

    const handleMouseUp = useCallback(() => setIsDragging(false), [])

    // Touch Logic (Restored)
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
                className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-0 overflow-hidden" // Hidden overflow for Pan/Zoom
                onClick={(e) => {
                    // Close if clicking the backdrop (not controls) AND not dragging
                    // If dragged, we assume user was interacting, not trying to close
                    if (e.target === containerRef.current && !isDragging) {
                        onClose()
                    }
                }}
            >
                {/* TOOLBAR (Updated: Comapct & Transparent) */}
                <div className="absolute top-4 left-0 right-0 z-50 flex items-center justify-between px-4 pointer-events-none">

                    {/* LEFT: Zoom Controls */}
                    <div className="bg-black/30 backdrop-blur-md rounded-lg p-1 flex items-center gap-1 pointer-events-auto shadow-lg border border-white/5">
                        <ControlButton icon={<ZoomOut className="h-4 w-4" />} onClick={handleZoomOut} disabled={zoom <= 0.5} label="Uzaklaş" />
                        <span className="text-white text-[10px] font-mono min-w-[2rem] text-center">{Math.round(zoom * 100)}%</span>
                        <ControlButton icon={<ZoomIn className="h-4 w-4" />} onClick={handleZoomIn} disabled={zoom >= 3} label="Yakınlaş" />
                        <div className="w-px h-4 bg-white/10 mx-0.5" />
                        <ControlButton icon={<Maximize2 className="h-4 w-4" />} onClick={handleResetZoom} label="Sıfırla" />
                    </div>

                    {/* RIGHT: Download Actions */}
                    <div className="bg-black/30 backdrop-blur-md rounded-lg p-1 flex items-center gap-1 pointer-events-auto shadow-lg border border-white/5">
                        <ControlButton
                            icon={isDownloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4 text-white" />}
                            onClick={downloadSVG}
                            disabled={isDownloading}
                            label="İndir"
                        />
                        <div className="w-px h-4 bg-white/10 mx-0.5" />
                        <ControlButton icon={<X className="h-4 w-4" />} onClick={onClose} label="Kapat" />
                    </div>
                </div>

                {/* CONTENT AREA (Pan & Zoom) */}
                {/* We remove overflow-auto to allow transform-based panning */}
                <div
                    className={cn(
                        "w-full h-full flex items-center justify-center",
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
                    <div
                        ref={svgContainerRef}
                        className="transition-transform duration-75 ease-out origin-center will-change-transform" // Performance optimization
                        style={{
                            transform: `translate(${position.x}px, ${position.y}px) scale(${zoom})`
                        }}
                    />
                </div>

                {/* Footer Hint */}
                <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 bg-black/20 backdrop-blur-sm rounded-full px-3 py-1 pointer-events-none">
                    <p className="text-white/40 text-[10px] font-medium">
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
