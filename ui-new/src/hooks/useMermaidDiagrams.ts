/**
 * Mermaid Diagram Hook
 * 
 * Handles mermaid diagram rendering and click-to-view functionality
 */

import { useEffect, useState } from 'react'
import mermaid from 'mermaid'
import { convertSvgToPng } from '@/lib/svgToPng'

// Initialize mermaid once
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'loose',
})

let isInitialized = false

export function useMermaidDiagrams(
    containerRef: React.RefObject<HTMLElement | null>,
    content: string,
    onOpenLightbox: (imageUrl: string) => void,
    onOpenMermaidViewer?: (svg: SVGSVGElement, code: string) => void
) {
    useEffect(() => {
        const container = containerRef.current
        if (!container) return

        const processMermaid = async () => {
            // Find all potential mermaid blocks
            // 1. Standard markdown: <pre><code class="language-mermaid">
            // 2. Direct blocks: <div class="mermaid">
            const mermaidBlocks = container.querySelectorAll('code.language-mermaid, .mermaid, .language-mermaid')

            if (mermaidBlocks.length === 0) return

            // Process each mermaid block
            for (const block of Array.from(mermaidBlocks)) {
                try {
                    // Skip if already processed by mermaid.run or ours
                    if (block.hasAttribute('data-processed') || block.querySelector('svg')) continue

                    const code = block.textContent || ''
                    const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`

                    // Create container for mermaid
                    const mermaidContainer = document.createElement('div')
                    mermaidContainer.className = 'mermaid-diagram'
                    mermaidContainer.id = id
                    mermaidContainer.textContent = code

                    // Handle replacement based on parent structure
                    const pre = block.closest('pre')
                    if (pre && pre.parentNode) {
                        pre.parentNode.replaceChild(mermaidContainer, pre)
                    } else if (block.parentNode) {
                        block.parentNode.replaceChild(mermaidContainer, block)
                    }

                    // Render mermaid
                    await mermaid.run({ nodes: [mermaidContainer] })

                    // Add click handler to convert to PNG and show in lightbox
                    mermaidContainer.style.cursor = 'pointer'
                    mermaidContainer.style.transition = 'all 0.2s ease'
                    mermaidContainer.title = 'Tıklayarak büyütün'

                    // Add hover effect
                    mermaidContainer.addEventListener('mouseenter', () => {
                        mermaidContainer.style.opacity = '0.85'
                        mermaidContainer.style.transform = 'scale(1.01)'
                    })
                    mermaidContainer.addEventListener('mouseleave', () => {
                        mermaidContainer.style.opacity = '1'
                        mermaidContainer.style.transform = 'scale(1)'
                    })

                    mermaidContainer.addEventListener('click', async (e) => {
                        e.preventDefault()
                        e.stopPropagation()

                        // Find SVG at click time to ensure we have the latest reference
                        const svgElement = mermaidContainer.querySelector('svg')
                        if (!svgElement) {
                            console.error('No SVG found in mermaid container at click time')
                            return
                        }

                        // Prefer the direct SVG viewer if available
                        if (onOpenMermaidViewer) {
                            console.log('Opening direct SVG viewer')
                            onOpenMermaidViewer(svgElement, code)
                            return
                        }

                        console.log('Mermaid diagram clicked, starting PNG conversion...')

                        // Add a temporary loading state visual
                        const originalOpacity = mermaidContainer.style.opacity
                        mermaidContainer.style.opacity = '0.5'

                        try {
                            const pngUrl = await convertSvgToPng(svgElement)
                            console.log('Conversion successful, opening lightbox')
                            onOpenLightbox(pngUrl)
                        } catch (error) {
                            console.error('Failed to convert diagram:', error)
                        } finally {
                            mermaidContainer.style.opacity = originalOpacity || '1'
                        }
                    })

                    // Mark as processed
                    mermaidContainer.setAttribute('data-processed', 'true')
                } catch (error) {
                    console.error('Mermaid rendering error:', error)
                }
            }
        }

        // Small delay to ensure DOM is ready after React render
        const timeoutId = setTimeout(processMermaid, 50)
        return () => clearTimeout(timeoutId)
    }, [containerRef, onOpenLightbox, content])
}
