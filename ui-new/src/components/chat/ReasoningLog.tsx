
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronRight, Activity, Brain, Globe, Wrench, Sparkles, Terminal } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ReasoningStep } from '@/types'

interface ReasoningLogProps {
    steps: ReasoningStep[]
    isStreaming?: boolean
}

export function ReasoningLog({ steps, isStreaming }: ReasoningLogProps) {
    const [isOpen, setIsOpen] = useState(isStreaming ?? false)

    // Auto-expand on stream start, auto-collapse on finish
    useEffect(() => {
        if (isStreaming) {
            setIsOpen(true)
        } else {
            setIsOpen(false)
        }
    }, [isStreaming])

    if (!steps || steps.length === 0) return null

    return (
        <div className="mb-2 mt-1 overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex w-full items-center gap-2 px-1 py-1 text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
                {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                <span>Düşünce Süreci</span>
                <span className="ml-auto flex items-center gap-1.5 opacity-70">
                    {isStreaming && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-primary)]" />}
                    {steps.length} adım
                </span>
            </button>

            <AnimatePresence initial={false}>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="border-t border-[var(--color-border)] bg-[var(--color-bg-base)]/50"
                    >
                        <div className="flex flex-col gap-0.5 p-2 font-mono text-[11px]">
                            {steps.map((step, idx) => (
                                <ReasoningItem key={`${step.task_id}-${idx}`} step={step} index={idx} isLast={idx === steps.length - 1} />
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

function ReasoningItem({ step, index, isLast }: { step: ReasoningStep, index: number, isLast: boolean }) {
    const getIcon = () => {
        switch (step.category) {
            case 'ROUTER': return <Activity className="h-3 w-3 text-blue-400" />
            case 'MEMORY': return <Brain className="h-3 w-3 text-purple-400" />
            case 'TOOL': return <Wrench className="h-3 w-3 text-amber-400" />
            case 'SYNTHESIS': return <Sparkles className="h-3 w-3 text-green-400" />
            default: return <Globe className="h-3 w-3 text-gray-400" />
        }
    }

    return (
        <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.05 }}
            className="flex items-start gap-2.5 px-2 py-1 relative group"
        >
            {/* Connector Line */}
            {!isLast && (
                <div className="absolute left-[13px] top-4 bottom-[-4px] w-px bg-[var(--color-border)] opacity-40" />
            )}

            <div className="relative z-10 mt-0.5 shrink-0">
                {getIcon()}
            </div>

            <span className="text-[var(--color-text-muted)] leading-tight break-words">
                {step.content}
            </span>
        </motion.div>
    )
}
