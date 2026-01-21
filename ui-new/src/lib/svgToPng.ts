/**
 * Mermaid SVG to PNG converter helper
 */

export async function convertSvgToPng(svg: SVGElement): Promise<string> {
    console.log('convertSvgToPng: Starting conversion for SVG', {
        width: svg.clientWidth,
        height: svg.clientHeight,
        viewBox: svg.getAttribute('viewBox')
    })

    return new Promise((resolve, reject) => {
        try {
            // Clone the SVG to avoid modifying the original and ensure it has necessary styles
            const clonedSvg = svg.cloneNode(true) as SVGElement

            // Ensure xmlns is present for standalone rendering
            if (!clonedSvg.getAttribute('xmlns')) {
                clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
            }

            const svgData = new XMLSerializer().serializeToString(clonedSvg)
            const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
            const url = URL.createObjectURL(svgBlob)

            const img = new Image()

            img.onload = () => {
                console.log('convertSvgToPng: SVG Image loaded successfully')
                const canvas = document.createElement('canvas')
                const scale = 2 // Higher quality

                // Get dimensions from computed style if clientWidth is 0
                const computed = window.getComputedStyle(svg)
                const width = svg.clientWidth || parseFloat(computed.width) || 800
                const height = svg.clientHeight || parseFloat(computed.height) || 600

                canvas.width = width * scale
                canvas.height = height * scale

                const ctx = canvas.getContext('2d')
                if (ctx) {
                    // White background (good for diagrams)
                    ctx.fillStyle = 'white'
                    ctx.fillRect(0, 0, canvas.width, canvas.height)
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

                    canvas.toBlob((blob) => {
                        if (blob) {
                            const pngUrl = URL.createObjectURL(blob)
                            console.log('convertSvgToPng: PNG Blob created successfully')
                            URL.revokeObjectURL(url)
                            resolve(pngUrl)
                        } else {
                            console.error('convertSvgToPng: Failed to create PNG blob')
                            reject(new Error('Failed to create blob'))
                        }
                    })
                } else {
                    console.error('convertSvgToPng: Failed to get canvas context')
                    reject(new Error('Failed to get canvas context'))
                }
            }

            img.onerror = (err) => {
                console.error('convertSvgToPng: Failed to load SVG image', err)
                URL.revokeObjectURL(url)
                reject(new Error('Failed to load SVG image'))
            }

            img.src = url
        } catch (error) {
            console.error('convertSvgToPng: Unexpected error', error)
            reject(error)
        }
    })
}
