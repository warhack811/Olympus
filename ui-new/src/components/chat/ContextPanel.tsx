/**
 * Context Panel Component
 * 
 * Collapsible panel showing sources, memory, and context used for AI response
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    ChevronDown,
    ChevronRight,
    ChevronUp,
    Link2,
    Brain,
    FileText,
    Clock,
    ExternalLink,
    BookOpen,
    Globe
} from 'lucide-react'
import type { UnifiedSource } from '@/types'
import { cn } from '@/lib/utils'

interface Memory {
    id: string
    text: string
    importance: number
    createdAt: string
}

interface ContextPanelProps {
    sources?: UnifiedSource[]
    memories?: Memory[]
    // documentChunks is legacy/redundant if we use unifiedSources for everything, but keeping for compatibility
    documentChunks?: { title: string; snippet: string }[]
    isOpen?: boolean
    onToggle?: () => void
    className?: string
}

// ─────────────────────────────────────────────────────────────────────────────
// CONTEXT PANEL
// ─────────────────────────────────────────────────────────────────────────────

export function ContextPanel({
    sources = [],
    memories = [],
    documentChunks = [],
    className
}: ContextPanelProps) {
    const [isOpen, setIsOpen] = useState(false)

    // Group sources (Permissive fallback)
    const webSources = sources.filter(s => s.type === 'web' || (!s.type && s.url))

    // Deduplicate Document sources by title
    const rawDocSources = sources.filter(s => s.type === 'document' || (!s.type && !s.url))
    const docMap = new Map<string, typeof rawDocSources[0] & { count: number }>()

    rawDocSources.forEach(s => {
        const key = s.title || 'Adsız Doküman'
        if (docMap.has(key)) {
            docMap.get(key)!.count++
        } else {
            docMap.set(key, { ...s, count: 1 })
        }
    })
    const docSources = Array.from(docMap.values())

    // Calculate totals
    const totalWeb = webSources.length
    const totalDocs = docSources.length + documentChunks.length
    const totalMemories = memories.length
    const totalItems = totalWeb + totalDocs + totalMemories

    if (totalItems === 0) return null

    return (
        <div className={cn("mt-2", className)}>
            <div className="overflow-hidden">
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="flex w-full items-center gap-2 px-1 py-1 text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                >
                    {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    <span>Kaynaklar</span>
                    <span className="ml-auto opacity-70">
                        {totalItems} kaynak
                    </span>
                </button>

                <AnimatePresence initial={false}>
                    {isOpen && (
                        <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className=""
                        >
                            <div className="pt-2 pb-1 px-1 flex flex-col gap-3">
                                {/* Web Sources - Compact Horizontal List */}
                                {totalWeb > 0 && (
                                    <div className="flex flex-wrap gap-2">
                                        <div className="w-full flex items-center text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-0.5">
                                            <Globe className="w-3 h-3 mr-1.5" />
                                            Web
                                        </div>
                                        {webSources.map((source, i) => (
                                            <SourcePill key={i} source={source} index={i} />
                                        ))}
                                    </div>
                                )}

                                {/* Documents & Memories */}
                                {(totalDocs > 0 || totalMemories > 0) && (
                                    <div className="flex flex-col gap-2">
                                        {/* Docs */}
                                        {totalDocs > 0 && (
                                            <div className="flex flex-col gap-1.5">
                                                <div className="flex items-center text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                                                    <FileText className="w-3 h-3 mr-1.5" />
                                                    Dokümanlar
                                                </div>
                                                <div className="grid grid-cols-1 gap-1.5">
                                                    {docSources.map((s, i) => (
                                                        <div key={i} className="text-xs bg-[var(--color-bg-surface)] border border-[var(--color-border)] px-2 py-1.5 rounded-md flex items-center gap-2 hover:border-[var(--color-primary)] transition-colors cursor-pointer group">
                                                            <FileText className="w-3 h-3 opacity-70" />
                                                            <span className="truncate flex-1">{s.title}</span>
                                                            {(s.count > 1) && (
                                                                <span className="text-[9px] bg-[var(--color-border)] text-[var(--color-text-muted)] px-1.5 py-0.5 rounded-full group-hover:bg-[var(--color-primary)] group-hover:text-white transition-colors">
                                                                    {s.count}
                                                                </span>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Memories */}
                                        {totalMemories > 0 && (
                                            <div className="flex flex-col gap-1.5">
                                                <div className="flex items-center text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                                                    <Brain className="w-3 h-3 mr-1.5" />
                                                    Hafıza
                                                </div>
                                                <div className="grid grid-cols-1 gap-1.5">
                                                    {memories.map((m, i) => (
                                                        <div key={i} className="text-xs bg-[var(--color-bg-surface)] border border-[var(--color-border)] px-2 py-1.5 rounded-md flex items-center gap-2">
                                                            <span className="truncate flex-1 opacity-80">{m.text}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    )
}

function SourcePill({ source, index }: { source: UnifiedSource, index: number }) {
    // Extract domain (e.g. "cnn.com")
    let domain = "Link"
    try {
        if (source.url) {
            domain = new URL(source.url).hostname.replace('www.', '')
        }
    } catch (e) { }

    return (
        <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5",
                "bg-[var(--color-bg-surface)] hover:bg-[var(--color-bg-surface-hover)]",
                "border border-[var(--color-border)] rounded-full",
                "text-xs font-medium text-[var(--color-text-primary)]",
                "transition-colors duration-200",
                "max-w-[200px] truncate"
            )}
            title={source.title} // Tooltip shows full title
        >
            {source.favicon ? (
                <img src={source.favicon} alt="" className="w-3.5 h-3.5 rounded-sm opacity-80" />
            ) : (
                <span className="text-[9px] bg-[var(--color-border)] px-1 rounded text-[var(--color-text-muted)]">{index + 1}</span>
            )}
            <span className="truncate">{domain}</span>
        </a>
    )
}

// Legacy components kept but unused for now
// Legacy components kept but unused for now
function MemoryCard({ memory }: { memory: Memory }) { return null }
function DocumentChunkCard({ chunk }: { chunk: { title: string; snippet: string } }) { return null }
function SourceCard({ source }: { source: UnifiedSource }) { return null }
