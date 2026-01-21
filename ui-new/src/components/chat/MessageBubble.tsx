/**
 * MessageBubble Component
 * 
 * Premium message bubble with:
 * - Enhanced markdown rendering
 * - Syntax highlighted code blocks
 * - Message reactions
 * - Reply support
 * - Action bar
 * - Image generation support (progress & completed)
 */

import { useState, useMemo, useEffect, useRef, useCallback, memo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Copy, ThumbsUp, ThumbsDown, RefreshCw, Check, Sparkles, Reply } from 'lucide-react'
import type { Message, ImageJob } from '@/types'
import { Avatar } from '@/components/ui'
import { MessageReactions, ReactionPicker } from './MessageReactions'
import { ReplyPreview } from './ReplyPreview'
import { ContextPanel } from './ContextPanel'
import { ImageProgressCard } from './ImageProgressCard'
import { ImageCompletedCard } from './ImageCompletedCard'
import { ReasoningLog } from './ReasoningLog'
import { renderMarkdown, setupCodeCopyButtons } from '@/lib/markdownRenderer'
import { cn, formatTime, copyToClipboard, decodeHtmlEntities } from '@/lib/utils'
import { useChatStore, useUserStore, useSettingsStore } from '@/stores'
import { useImageProgress } from '@/hooks/useImageProgress'
import { useMermaidDiagrams } from '@/hooks/useMermaidDiagrams'
import { chatApi, normalizeImageUrl } from '@/api/client'
import mermaid from 'mermaid'
// @ts-ignore
import renderMathInElement from 'katex/dist/contrib/auto-render'
import { UniversalMediaViewer } from './UniversalMediaViewer'

// Initialize mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'strict',
})

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

interface MessageBubbleProps {
    message: Message
    onReply?: (message: Message) => void
    onOpenLightbox?: (url: string) => void
}

// ═══════════════════════════════════════════════════════════════════════════
// HELPERS - Message Content Detection
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Check if message is an image pending message
 * Backend sometimes strips [IMAGE_PENDING] tag, so we also check for the text
 */
function isImagePendingMessage(message: Message): boolean {
    const meta = message.extra_metadata
    if (meta?.type === 'image' && (meta.status === 'queued' || meta.status === 'processing')) {
        return true
    }
    // Fallback logic
    const content = message.content
    return content.includes('[IMAGE_PENDING]') ||
        content.includes('Görsel isteğiniz kuyruğa alındı')
}

/**
 * Check if message contains a completed image
 */
function isImageCompletedMessage(message: Message): boolean {
    const meta = message.extra_metadata
    if (meta?.type === 'image' && (meta.status === 'complete' || !!meta.image_url)) {
        return true
    }
    // Fallback logic
    return message.content.includes('IMAGE_PATH:')
}

/**
 * Extract image URL from message content
 */
function extractImageUrl(content: string): string | null {
    const match = content.match(/IMAGE_PATH:\s*(\S+)/)
    return match ? match[1] : null
}

/**
 * Extract prompt from image message
 */
function extractImagePrompt(content: string): string {
    // Try to get prompt from data attribute
    const promptMatch = content.match(/data-prompt="([^"]+)"/)
    if (promptMatch) {
        // Decode HTML entities (&#x27; -> ' etc.)
        return decodeHtmlEntities(promptMatch[1])
    }

    // Fallback: return cleaned content
    return content
        .replace(/\[IMAGE\].*$/m, '')
        .replace(/IMAGE_PATH:\s*\S+/, '')
        .replace(/<[^>]+>/g, '')
        .trim() || 'Görsel'
}

/**
 * Get clean text content (without image markers and system prefixes)
 */
function getCleanContent(content: string): string {
    return content
        // Remove system prefixes
        .replace(/^\[GROQ\]\s*/gm, '')
        .replace(/^\[BELA\]\s*/gm, '')
        // Remove image markers
        .replace(/\[IMAGE_PENDING\].*$/gm, '')
        .replace(/\[IMAGE\].*$/gm, '')
        .replace(/IMAGE_PATH:\s*\S+/g, '')
        .replace(/<span class="image-prompt"[^>]*><\/span>/g, '')
        .trim()
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export function MessageBubble({ message, onReply, onOpenLightbox }: MessageBubbleProps) {
    const isUser = message.role === 'user'
    const user = useUserStore((state) => state.user)
    const updateMessage = useChatStore((state) => state.updateMessage)
    const deleteMessage = useChatStore((state) => state.deleteMessage)
    const messages = useChatStore((state) => state.messages)
    const setInputValue = useChatStore((state) => state.setInputValue)
    const currentConversationId = useChatStore((state) => state.currentConversationId)


    const [copied, setCopied] = useState(false)
    const [isHovered, setIsHovered] = useState(false)
    const [viewerState, setViewerState] = useState<{
        isOpen: boolean;
        mode: 'mermaid' | 'image';
        svg?: SVGSVGElement;
        code?: string;
        src?: string;
        alt?: string;
    }>({ isOpen: false, mode: 'mermaid' })
    const userImages = useMemo(() => {
        if (!isUser || !message.images || message.images.length === 0) return []
        return message.images.map(img => normalizeImageUrl(img.url))
    }, [isUser, message.images])

    // Get feature flag for metadata-first rendering
    const isMetadataFirst = useSettingsStore((state: any) => state.featureFlags?.FE_METADATA_FIRST_IMAGE_RENDER ?? true)

    // Detect message type
    const isPending = useMemo(() => {
        // 1. Primary: Metadata-first check
        if (isMetadataFirst && message.extra_metadata?.type === 'image') {
            const status = message.extra_metadata.status
            return status === 'queued' || status === 'processing'
        }
        // 2. Secondary: Fallback to legacy marker parsing
        return isImagePendingMessage(message)
    }, [isMetadataFirst, message])

    const isCompleted = useMemo(() => {
        // 1. Primary: Metadata-first check
        if (isMetadataFirst && message.extra_metadata?.type === 'image') {
            return message.extra_metadata.status === 'complete' || !!message.extra_metadata.image_url
        }
        // 2. Secondary: Fallback to legacy marker parsing
        return isImageCompletedMessage(message)
    }, [isMetadataFirst, message])

    const isImageMessage = isPending || isCompleted

    // Get job_id from message metadata
    const jobId = message.extra_metadata?.job_id

    // Get progress from WebSocket cache (if available)
    const progressData = useImageProgress(jobId)

    // POLLING FALLBACK: If WebSocket fails, poll the status every 5 seconds
    useEffect(() => {
        if (!isPending || !jobId || isCompleted) return

        const pollInterval = setInterval(async () => {
            try {
                const status = await chatApi.getJobStatus(jobId)
                if (status.status !== 'unknown') {
                    const currentStatus = message.extra_metadata?.status
                    if (status.status !== currentStatus || status.progress > ((message.extra_metadata?.progress as number) || 0) + 5) {
                        updateMessage(message.id, {
                            extra_metadata: {
                                ...message.extra_metadata,
                                status: status.status as any,
                                progress: status.progress,
                                queue_position: status.queue_position,
                                image_url: status.image_url,
                                error: status.error
                            }
                        })
                        if (status.status === 'complete' || status.status === 'error') {
                            // Stop polling when job is complete or errored
                            clearInterval(pollInterval)
                        }
                    }
                }
            } catch (err) {
                // Log polling errors but continue polling
                console.warn('[MessageBubble] Polling error:', err)
            }
        }, 5000)

        // CRITICAL: Cleanup interval on unmount to prevent memory leak
        return () => {
            clearInterval(pollInterval)
        }
    }, [isPending, jobId, isCompleted, message.id, message.extra_metadata, updateMessage])

    // Get replied message if exists
    const repliedMessage = useMemo(() => {
        if (!message.replyToId) return null
        return messages.find(m => m.id === message.replyToId)
    }, [message.replyToId, messages])

    // Build current job from message extra_metadata (updated by WebSocket)
    const currentJob = useMemo((): ImageJob | null => {
        if (!isPending) return null

        const meta = message.extra_metadata
        return {
            id: jobId || `fallback-${message.id}`,
            conversationId: currentConversationId || undefined,
            prompt: (meta?.prompt as string) || extractImagePrompt(message.content) || 'Görsel oluşturuluyor...',
            status: (meta?.status as any) || 'queued',
            progress: (meta?.progress as number) ?? 0,
            queuePosition: (meta?.queue_position as number) || 1,
        }
    }, [isPending, jobId, message.id, message.extra_metadata, message.content, currentConversationId])

    // Extract image data for completed messages
    const imageData = useMemo(() => {
        if (!isCompleted) return null

        const meta = message.extra_metadata
        const rawUrl = meta?.image_url || extractImageUrl(message.content)
        const imageUrl = normalizeImageUrl(rawUrl as string)
        const prompt = (meta?.prompt as string) || extractImagePrompt(message.content)

        return { imageUrl, prompt }
    }, [isCompleted, message.content, message.extra_metadata])

    // Get clean content (for non-image or partial messages)
    const cleanContent = useMemo(() => {
        return getCleanContent(message.content)
    }, [message.content])

    // Parse markdown for assistant messages
    const htmlContent = useMemo(() => {
        // FIXED: Removed isImageMessage check - AI text should show WITH image card
        if (isUser || !cleanContent) return cleanContent
        return renderMarkdown(cleanContent)
    }, [cleanContent, isUser])

    // Setup code copy buttons after render


    // Handlers
    const handleCopy = async () => {
        const success = await copyToClipboard(message.content)
        if (success) {
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        }
    }

    const handleFeedback = async (type: 'like' | 'dislike') => {
        try {
            await chatApi.submitFeedback(message.id, type)
            updateMessage(message.id, { feedback: type })
        } catch (error) {
            console.error('Feedback error:', error)
        }
    }

    const handleReact = (emoji: string) => {
        const currentReactions = message.reactions || []
        const existing = currentReactions.find(r => r.emoji === emoji)

        let newReactions
        if (existing) {
            if (existing.reacted) {
                newReactions = currentReactions.map(r =>
                    r.emoji === emoji
                        ? { ...r, count: r.count - 1, reacted: false }
                        : r
                ).filter(r => r.count > 0)
            } else {
                newReactions = currentReactions.map(r =>
                    r.emoji === emoji
                        ? { ...r, count: r.count + 1, reacted: true }
                        : r
                )
            }
        } else {
            newReactions = [...currentReactions, { emoji, count: 1, reacted: true }]
        }

        updateMessage(message.id, { reactions: newReactions })
    }

    const handleCancelImage = useCallback(async (jobId: string) => {
        try {
            // Call cancel API
            const result = await chatApi.cancelJob(jobId)
            console.log('[Cancel] Result:', result)

            if (result.success) {
                // Wait for animation then delete message
                setTimeout(() => {
                    deleteMessage(message.id)
                }, 800)
            }
        } catch (error) {
            console.error('Cancel failed:', error)
        }
    }, [message.id, deleteMessage])

    const handleRegenerateImage = useCallback((prompt: string) => {
        // Set the input value with the regenerate prompt
        // User will need to press send
        setInputValue(`Görsel oluştur: ${prompt}`)
    }, [setInputValue])

    const handleOpenLightbox = useCallback((imageUrl: string) => {
        if (onOpenLightbox) {
            onOpenLightbox(imageUrl)
        } else {
            setViewerState({
                isOpen: true,
                mode: 'image',
                src: imageUrl,
                alt: 'Image'
            })
        }
    }, [onOpenLightbox])

    const handleOpenMermaidViewer = useCallback((svg: SVGSVGElement, code: string) => {
        setViewerState({
            isOpen: true,
            mode: 'mermaid',
            svg,
            code
        })
    }, [])



    // ─────────────────────────────────────────────────────────────────────────
    // RENDER: Image Pending (Progress)
    // ─────────────────────────────────────────────────────────────────────────
    // ─────────────────────────────────────────────────────────────────────────
    // RENDER: Standard Message (Text + Optional Image Cards)
    // ─────────────────────────────────────────────────────────────────────────
    // We no longer return early for isPending/isCompleted.
    // Instead, we render them as attachments inside the message bubble or below it.

    // ─────────────────────────────────────────────────────────────────────────
    // RENDER: Standard Message
    // ─────────────────────────────────────────────────────────────────────────
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
                "group flex gap-1.5 md:gap-3 px-2 md:px-4 py-3",
                isUser ? "flex-row-reverse" : "flex-row"
            )}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            {/* Avatar */}
            <Avatar
                size="md"
                src={isUser ? user?.avatarUrl : undefined}
                fallback={isUser ? (
                    user?.displayName?.[0] || user?.username?.[0] || 'U'
                ) : (
                    <Sparkles className="h-4 w-4" />
                )}
                className="shrink-0 mt-1 hidden md:flex"
            />

            {/* Content */}
            <div className={cn(
                "flex flex-col gap-1",
                isUser ? "items-end" : "items-start",
                "max-w-(--message-max-width)"
            )}>
                {/* Model Badge (for assistant) */}
                {!isUser && message.model && (
                    <div className="flex items-center gap-2 mb-0.5">
                        <span className={cn(
                            "px-2 py-0.5 rounded-full text-xs font-medium",
                            "bg-(--color-primary-soft) text-(--color-primary)"
                        )}>
                            {message.model.toUpperCase()}
                        </span>
                    </div>
                )}

                {/* Reply Preview */}
                {repliedMessage && (
                    <ReplyPreview replyTo={repliedMessage} />
                )}

                {/* Message Bubble */}
                <div className={cn(
                    "relative px-4 py-3 rounded-2xl",
                    isUser ? [
                        "rounded-tr-sm",
                        "bg-(--color-msg-user) border border-(--color-msg-user-border)",
                        "text-(--color-msg-user-text)"
                    ] : [
                        "rounded-tl-sm",
                        "text-(--color-text)"
                    ]
                )}>
                    {/* Reasoning Log (Glass Box) */}
                    {!isUser && message.reasoning_log && message.reasoning_log.length > 0 && (
                        <div className="mb-3 border-b border-[var(--color-border)]/50 pb-1">
                            <ReasoningLog steps={message.reasoning_log} isStreaming={message.isStreaming} />
                        </div>
                    )}

                    {/* Content */}
                    <div className="prose dark:prose-invert max-w-none break-words">
                        <MarkdownDisplay
                            content={htmlContent}
                            isStreaming={message.isStreaming ?? false}
                            onOpenLightbox={handleOpenLightbox}
                            onOpenMermaidViewer={handleOpenMermaidViewer}
                        />
                    </div>

                    {/* ATTACHMENT: Image Progress Card */}
                    {isPending && currentJob && (
                        <div className="mt-3">
                            <ImageProgressCard
                                job={currentJob}
                                onCancel={handleCancelImage}
                            />
                        </div>
                    )}

                    {/* ATTACHMENT: Image Completed Card */}
                    {isCompleted && imageData?.imageUrl && (
                        <div className="mt-3">
                            <ImageCompletedCard
                                imageUrl={imageData.imageUrl}
                                prompt={imageData.prompt}
                                onRegenerate={handleRegenerateImage}
                                onOpenLightbox={handleOpenLightbox}
                            />
                        </div>
                    )}
                    {/* Messaging Status - Typing Indicator */}
                    {!isUser && message.isStreaming && !cleanContent && (
                        /* Typing Indicator - when streaming but no content yet */
                        <div className="flex items-center gap-2">
                            <span className="text-sm text-(--color-text-muted)">
                                AI Assistant yazıyor
                            </span>
                            <div className="flex gap-1">
                                {[0, 1, 2].map((i) => (
                                    <motion.span
                                        key={i}
                                        className="w-1.5 h-1.5 rounded-full bg-(--color-primary)"
                                        animate={{
                                            y: [0, -4, 0],
                                            opacity: [0.4, 1, 0.4]
                                        }}
                                        transition={{
                                            duration: 0.6,
                                            repeat: Infinity,
                                            delay: i * 0.15,
                                            ease: "easeInOut"
                                        }}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Streaming Cursor */}
                    {message.isStreaming && (
                        <span className="inline-block w-0.75 h-[1.2em] bg-(--color-primary) rounded-sm ml-1 animate-pulse" />
                    )}

                    {/* User Images Display (Vision) */}
                    {isUser && userImages.length > 0 && (
                        <div className={cn(
                            "grid gap-2 mt-3",
                            userImages.length === 1 ? "grid-cols-1" : "grid-cols-2"
                        )}>
                            {userImages.map((url, idx) => (
                                <motion.div
                                    key={idx}
                                    layoutId={`user-img-${message.id}-${idx}`}
                                    className="relative group cursor-zoom-in overflow-hidden rounded-xl border border-white/10"
                                    onClick={() => onOpenLightbox?.(url)}
                                >
                                    <img
                                        src={url}
                                        alt={`Attached image ${idx + 1}`}
                                        className="w-full h-auto max-h-[300px] object-cover transition-transform duration-300 group-hover:scale-105"
                                    />
                                    <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                        <Sparkles className="w-6 h-6 text-white" />
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}


                    {/* Context Panel - Unified Sources (INSIDE BUBBLE) */}
                    {!isUser && message.unified_sources && message.unified_sources.length > 0 && (
                        <ContextPanel
                            sources={message.unified_sources}
                            className="mt-3 border-t border-[var(--color-border)] pt-2"
                        />
                    )}

                </div>

                {/* Context Panel - Unified Sources */}





                {/* Footer: Timestamp & Reactions & Actions */}
                <div className={cn(
                    "flex items-center gap-2 px-1 mt-1 select-none",
                    isUser ? "flex-row-reverse" : "flex-row"
                )}>
                    {/* Timestamp */}
                    <span className="text-xs text-(--color-text-muted)">
                        {formatTime(message.timestamp)}
                        {message.isEdited && (
                            <span className="ml-1 italic">(düzenlendi)</span>
                        )}
                    </span>

                    {/* Reactions */}
                    <MessageReactions
                        messageId={message.id}
                        reactions={message.reactions}
                        onReact={handleReact}
                    />

                    {/* Actions Group (Picker + Buttons) - Visible on Hover */}
                    <div className={cn(
                        "flex items-center gap-0.5 transition-opacity duration-200",
                        isHovered ? "opacity-100" : "opacity-0",
                        isUser ? "flex-row-reverse" : "flex-row"
                    )}>
                        <ReactionPicker onReact={handleReact} />
                        {onReply && (
                            <ActionButton
                                icon={<Reply className="h-3.5 w-3.5" />}
                                onClick={() => onReply(message)}
                                label="Yanıtla"
                                simple
                            />
                        )}
                        <ActionButton
                            icon={copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                            onClick={handleCopy}
                            label="Kopyala"
                            active={copied}
                            simple
                        />
                        {!isUser && (
                            <>
                                <ActionButton
                                    icon={<ThumbsUp className="h-3.5 w-3.5" />}
                                    onClick={() => handleFeedback('like')}
                                    label="Beğen"
                                    active={message.feedback === 'like'}
                                    simple
                                />
                                <ActionButton
                                    icon={<ThumbsDown className="h-3.5 w-3.5" />}
                                    onClick={() => handleFeedback('dislike')}
                                    label="Beğenme"
                                    active={message.feedback === 'dislike'}
                                    simple
                                />
                                <ActionButton
                                    icon={<RefreshCw className="h-3.5 w-3.5" />}
                                    onClick={() => {/* TODO: regenerate */ }}
                                    label="Yeniden oluştur"
                                    simple
                                />
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Universal Media Viewer (Handles both Mermaid & Images) */}
            {viewerState.isOpen && (
                <UniversalMediaViewer
                    mode={viewerState.mode}
                    svgElement={viewerState.svg}
                    diagramCode={viewerState.code || ''}
                    src={viewerState.src}
                    alt={viewerState.alt}
                    onClose={() => setViewerState({ ...viewerState, isOpen: false })}
                />
            )}
        </motion.div>
    )
}

// ═══════════════════════════════════════════════════════════════════════════
// MEMOIZED MARKDOWN COMPONENT (Prevents Re-render Loop)
// ═══════════════════════════════════════════════════════════════════════════

const MarkdownDisplay = memo(({
    content,
    isStreaming,
    onOpenLightbox,
    onOpenMermaidViewer
}: {
    content: string,
    isStreaming: boolean,
    onOpenLightbox: (url: string) => void,
    onOpenMermaidViewer: (svg: SVGSVGElement, code: string) => void
}) => {
    const ref = useRef<HTMLDivElement>(null)

    // Mermaid diagrams hook
    useMermaidDiagrams(ref, content, isStreaming, onOpenLightbox, onOpenMermaidViewer)

    useEffect(() => {
        const container = ref.current
        if (!container) return

        // 1. Setup Copy Buttons
        setupCodeCopyButtons(container)

        // 2. Render KaTeX
        try {
            const mathOptions = {
                delimiters: [
                    { left: '$$', right: '$$', display: true },
                    { left: '$', right: '$', display: false },
                    { left: '\\[', right: '\\]', display: true },
                    { left: '\\(', right: '\\)', display: false }
                ],
                throwOnError: false
            }

            // Prio imported function
            if (typeof renderMathInElement === 'function') {
                renderMathInElement(container, mathOptions)
            } else if (window && (window as any).renderMathInElement) {
                (window as any).renderMathInElement(container, mathOptions)
            }
        } catch (e) {
            console.error('KaTeX error:', e)
        }
    }, [content, isStreaming])

    return (
        <div
            ref={ref}
            className={cn(
                "prose prose-sm md:prose-base dark:prose-invert max-w-none",
                "prose-p:leading-relaxed prose-pre:p-0",
                "prose-headings:font-semibold prose-a:text-blue-500 hover:prose-a:underline",
                "break-words"
            )}
            dangerouslySetInnerHTML={{ __html: content }}
        />
    )
})

// ═══════════════════════════════════════════════════════════════════════════
// ACTION BUTTON
// ═══════════════════════════════════════════════════════════════════════════

interface ActionButtonProps {
    icon: React.ReactNode
    onClick: () => void
    label: string
    active?: boolean
    simple?: boolean
}

function ActionButton({ icon, onClick, label, active, simple }: ActionButtonProps) {
    return (
        <button
            onClick={onClick}
            aria-label={label}
            title={label}
            className={cn(
                "rounded-md transition-all duration-200 flex items-center justify-center",
                simple ? "p-1.5" : "p-2",
                active
                    ? "bg-(--color-primary-soft) text-(--color-primary)"
                    : cn(
                        "text-(--color-text-muted) hover:text-(--color-text)",
                        "hover:bg-(--color-bg-surface-hover)"
                    )
            )}
        >
            {icon}
        </button>
    )
}
