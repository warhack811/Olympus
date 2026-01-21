/**
 * CodeBlock Component
 * 
 * Styled code block with syntax highlighting, copy button, and language badge
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Copy, Check } from 'lucide-react'
import { highlightCode, getLanguageDisplayName, copyCode } from '@/lib/codeHighlighter'
import { cn } from '@/lib/utils'

interface CodeBlockProps {
    code: string
    language?: string
    className?: string
}

export function CodeBlock({ code, language = 'plaintext', className }: CodeBlockProps) {
    const [copied, setCopied] = useState(false)

    const highlightedCode = highlightCode(code, language)
    const displayLang = getLanguageDisplayName(language)

    const handleCopy = async () => {
        const success = await copyCode(code)
        if (success) {
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        }
    }

    return (
        <div
            className={cn(
                "relative group rounded-xl overflow-hidden my-4",
                className
            )}
            style={{
                backgroundColor: 'var(--color-code-bg)',
                borderColor: 'var(--color-code-border)',
                borderWidth: '1px'
            }}
        >
            {/* Header */}
            <div
                className="flex items-center justify-between px-4 py-2 border-b"
                style={{
                    backgroundColor: 'var(--color-code-surface)',
                    borderBottomColor: 'var(--color-code-border)'
                }}
            >
                <span className="text-xs font-medium" style={{ color: 'var(--color-code-text)' }}>
                    {displayLang}
                </span>

                <motion.button
                    onClick={handleCopy}
                    className={cn(
                        "flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs",
                        "transition-all duration-200",
                        copied
                            ? "bg-green-500/20 text-green-400"
                            : ""
                    )}
                    style={copied ? {} : {
                        backgroundColor: 'var(--color-code-border)',
                        color: 'var(--color-code-comment)'
                    }}
                    whileTap={{ scale: 0.95 }}
                >
                    {copied ? (
                        <>
                            <Check className="h-3.5 w-3.5" />
                            <span>Kopyalandı</span>
                        </>
                    ) : (
                        <>
                            <Copy className="h-3.5 w-3.5" />
                            <span>Kopyala</span>
                        </>
                    )}
                </motion.button>
            </div>

            {/* Code */}
            <div className="overflow-x-auto">
                <pre className="p-4 text-sm leading-relaxed">
                    <code
                        className={`language-${language}`}
                        dangerouslySetInnerHTML={{ __html: highlightedCode }}
                    />
                </pre>
            </div>
        </div>
    )
}
