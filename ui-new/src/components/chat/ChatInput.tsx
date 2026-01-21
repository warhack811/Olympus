/**
 * ChatInput Component
 * 
 * Premium chat input with attachments, voice, commands, and slash command palette
 */

import { useState, useRef, useCallback, useMemo, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Paperclip, Mic, Send, Smile, X, Loader2, Slash, Image as ImageIcon, ChevronDown, ChevronUp } from 'lucide-react'
import { useChatStore, useSettingsStore } from '@/stores'
import { chatApi, documentApi } from '@/api'
import { Button, Textarea } from '@/components/ui'
import { useIsMobile, useSafeAreaInsets, useMobileKeyboard } from '@/hooks'
import { CommandPalette, MultiModalInput, useMultiModal } from '@/components/common'
import { QuickSettings } from './QuickSettings'
import { cn } from '@/lib/utils'
import type { Command, Message } from '@/types'

interface ChatInputProps {
    replyTo?: Message | null
    onClearReply?: () => void
}

const EMOJI_OPTIONS = [
    '😀', '😂', '😊', '😍', '🤔', '😎', '👍',
    '👏', '🙏', '🎉', '🚀', '✨', '💡', '🔥',
    '💯', '📌', '🧠', '📚', '✅', '💬', '🤖',
]

export function ChatInput({ replyTo, onClearReply }: ChatInputProps) {
    const inputValue = useChatStore((state) => state.inputValue)
    const setInputValue = useChatStore((state) => state.setInputValue)
    const isStreaming = useChatStore((state) => state.isStreaming)
    const currentConversationId = useChatStore((state) => state.currentConversationId)
    const addMessage = useChatStore((state) => state.addMessage)
    const createConversation = useChatStore((state) => state.createConversation)
    const startStreaming = useChatStore((state) => state.startStreaming)
    const appendToStreaming = useChatStore((state) => state.appendToStreaming)
    const appendReasoning = useChatStore((state) => state.appendReasoning)
    const setUnifiedSources = useChatStore((state) => state.setUnifiedSources)
    const stopStreaming = useChatStore((state) => state.stopStreaming)
    const isMobile = useIsMobile()
    const { bottom: safeAreaBottom } = useSafeAreaInsets()
    const { isVisible: isKeyboardVisible, height: keyboardHeight } = useMobileKeyboard()
    const responseStyle = useSettingsStore((state) => state.responseStyle)
    const activePersona = useSettingsStore((state) => state.activePersona)
    const imageSettings = useSettingsStore((state) => state.imageSettings)
    const [isFocused, setIsFocused] = useState(false)
    const [attachments, setAttachments] = useState<File[]>([])
    const [isSending, setIsSending] = useState(false)
    const [showToolbar, setShowToolbar] = useState(false)
    const [showEmojiPicker, setShowEmojiPicker] = useState(false)
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const inputWrapperRef = useRef<HTMLDivElement>(null)
    const emojiPickerRef = useRef<HTMLDivElement>(null)
    const emojiButtonRef = useRef<HTMLButtonElement>(null)
    // const BOTTOM_NAV_HEIGHT = 64 // Hidden as per request
    const GAP_BELOW_INPUT = 10
    const keyboardActive = isKeyboardVisible || keyboardHeight > 60
    const mobileBottomOffset = 0 // No bottom nav, so 0 offset logic is simplified

    // Multi-modal image support
    const multiModal = useMultiModal()

    const canSend = (inputValue.trim() || attachments.length > 0 || multiModal.hasImages) && !isSending && !isStreaming

    // Detect slash command
    const commandQuery = useMemo(() => {
        if (!inputValue.startsWith('/')) return null
        const query = inputValue.slice(1) // Remove leading /
        return query
    }, [inputValue])

    // Show palette when typing slash
    const shouldShowPalette = commandQuery !== null && isFocused

    const handleSend = useCallback(async () => {
        if (!canSend) return

        const message = inputValue.trim()
        if (!message && attachments.length === 0) return

        console.log('[Chat] handleSend triggered - isSending:', isSending, 'isStreaming:', isStreaming)
        setIsSending(true)
        setInputValue('')
        setShowToolbar(false)

        // Clear reply after sending
        onClearReply?.()

        // FIX 3: Capture conversation ID at send time to prevent race conditions
        // This ensures the message goes to the correct conversation even if user
        // quickly switches conversations while the message is being sent
        const sendConversationId = currentConversationId

        console.log('[Chat] Sending message:', { message, sendConversationId, replyTo: replyTo?.id, attachments: attachments.length })

        try {
            // 1. Upload Attachments (if any)
            let uploadedImagePaths: string[] = []

            if (attachments.length > 0) {
                console.log('[Chat] Uploading attachments...')
                try {
                    const uploadResults = await Promise.all(attachments.map(file =>
                        documentApi.uploadDocument(file, sendConversationId)
                    ))

                    // Collect image paths - Backend returns {type: 'image', path: '...'}
                    uploadResults.forEach(res => {
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        const r = res as any
                        if (r && r.type === 'image' && r.path) {
                            uploadedImagePaths.push(r.path)
                        }
                    })

                    // Clear attachments on success
                    setAttachments([])
                    console.log('[Chat] Attachments uploaded successfully', uploadedImagePaths)
                } catch (uploadError) {
                    console.error('[Chat] Upload failed:', uploadError)
                    addMessage({
                        role: 'assistant',
                        content: '⚠️ Dosya yüklenirken bir hata oluştu.',
                    })
                    setIsSending(false)
                    return // Stop if upload fails
                }
            }

            // If only attachment was sent without text, we might want to send a generic message
            // or just skip the chat call if it was just an upload (but usually we want LLM context)
            const textToSend = message || (attachments.length > 0 ? (uploadedImagePaths.length > 0 ? 'Bu görseli incele.' : 'Dosya yüklendi.') : '')
            if (!textToSend) {
                setIsSending(false)
                return
            }

            // Add user message to UI immediately
            addMessage({
                role: 'user',
                content: textToSend,
                replyToId: replyTo?.id,
                images: uploadedImagePaths.length > 0 ? uploadedImagePaths.map(path => ({
                    id: Math.random().toString(36).substring(7),
                    url: path,
                    status: 'complete'
                })) : undefined,
            })

            // Add placeholder for assistant message
            let assistantMsgId = addMessage({
                role: 'assistant',
                content: '',
                isStreaming: true,
            })

            startStreaming(assistantMsgId)

            // Send to API - pass null for new conversation, backend will create one
            console.log('[Chat] Calling API...')
            const response = await chatApi.sendMessage({
                message: textToSend,
                conversationId: sendConversationId, // Use captured ID
                persona: activePersona,
                stream: true,
                styleProfile: responseStyle,
                images: uploadedImagePaths.length > 0 ? uploadedImagePaths : undefined,
                imageSettings: imageSettings // Pass settings
            })

            console.log('[Chat] Response status:', response.status, response.headers.get('content-type'))

            // Get conversation ID from response header (backend creates it)
            const newConvId = response.headers.get('X-Conversation-ID')
            if (newConvId && !sendConversationId) {
                console.log('[Chat] Got new conversation ID:', newConvId)
                // Only update if we were creating new conversation

                // Create new conversation object and add to list
                const newConversation = {
                    id: newConvId,
                    title: textToSend.slice(0, 50) + (textToSend.length > 50 ? '...' : ''),
                    preview: textToSend.slice(0, 100),
                    messageCount: 1,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString(),
                }

                // Add to conversations list (at the top)
                useChatStore.setState((state) => ({
                    conversations: [newConversation, ...state.conversations],
                    currentConversationId: newConvId
                }))

                console.log('[Chat] New conversation added to sidebar:', newConvId)
            } else if (newConvId && sendConversationId && newConvId !== sendConversationId) {
                // FIX 3: Guard against conversation ID mismatch
                console.error('[Chat] Conversation ID mismatch!', {
                    sent: sendConversationId,
                    received: newConvId
                })
                // Don't update store, keep using sent ID
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                const errorMsg = errorData.message || errorData.detail || `Sunucu hatası: ${response.status}`
                throw new Error(errorMsg)
            }

            if (!response.body) {
                console.error('[Chat] No response body reader')
                throw new Error('Yanıt gövdesi okunamadı.')
            }

            // Handle streaming response - Structured NDJSON with timeout
            const streamTimeout = 60000 // 60 second timeout
            const streamController = new AbortController()
            const streamTimeoutId = setTimeout(() => streamController.abort(), streamTimeout)

            let fullResponse = ''
            let hasContent = false
            let hasImageJob = false

            try {
                const reader = response.body.getReader()
                const decoder = new TextDecoder()
                let buffer = ''

                if (reader) {
                    while (true) {
                        try {
                            const { done, value } = await reader.read()
                            if (done) break

                            buffer += decoder.decode(value, { stream: true })
                            const lines = buffer.split('\n')

                            // Keep the last part if it doesn't end with newline
                            buffer = lines.pop() || ''

                            for (const line of lines) {
                                if (!line.trim()) continue

                                try {
                                    const event = JSON.parse(line)

                                    switch (event.type) {
                                        case 'metadata':
                                            // [PHASE 5.1 persistence handshake]
                                            if (event.assistant_message_id) {
                                                const newId = String(event.assistant_message_id)
                                                console.log(`[Chat] Handshake: Replacing temp ID ${assistantMsgId} with persistent ID ${newId}`)

                                                // Update the message ID in the store
                                                useChatStore.getState().updateMessageId(assistantMsgId, newId)

                                                // Update our local reference for subsequent events
                                                assistantMsgId = newId
                                            }
                                            break

                                        case 'chunk':
                                            if (event.content) {
                                                hasContent = true
                                                fullResponse += event.content
                                                // Use current assistantMsgId (which might have been updated by handshake)
                                                useChatStore.getState().updateMessage(assistantMsgId, {
                                                    content: fullResponse
                                                })
                                            }
                                            break

                                        case 'thought':
                                            // Map backend thought to frontend model
                                            appendReasoning({
                                                task_id: event.task_id || 'unknown',
                                                category: event.cat || 'OTHER',
                                                content: event.content || event.thought,
                                                status: 'completed',
                                                timestamp: Date.now()
                                            })
                                            break

                                        case 'task_result':
                                            // Detect Flux Tool execution specifically
                                            // event structure: { type: 'task_result', result: { type: 'tool', tool_name: 'flux_tool', output: { job_id: '...' } } }
                                            const res = event.result || {}
                                            if (res.type === 'tool' && res.tool_name === 'flux_tool') {
                                                const output = res.output || {}
                                                // Backend TaskRunner returns: { prompt, result: { job_id, status }, thought }
                                                const jobId = output.result?.job_id || output.job_id

                                                console.log('[Chat] Task Result Payload:', {
                                                    tool: res.tool_name,
                                                    hasResult: !!output.result,
                                                    jobId
                                                })

                                                if (jobId) {
                                                    hasImageJob = true
                                                    console.log('[Chat] Task Result: Image Job Detected:', jobId)

                                                    // Dynamically import store to avoid circular deps if any
                                                    const { useImageJobsStore } = await import('@/stores/imageJobsStore')

                                                    // 1. Link Job
                                                    useImageJobsStore.getState().linkMessageToJob(assistantMsgId, jobId)
                                                    useImageJobsStore.getState().updateJob({
                                                        id: jobId,
                                                        conversationId: (sendConversationId || newConvId) || undefined,
                                                        status: 'queued',
                                                        progress: 0,
                                                        prompt: textToSend
                                                    })

                                                    // 2. Attach Image Pending Metadata (Do NOT overwrite content)
                                                    // We use updateMessage to add metadata to the existing text response
                                                    useChatStore.getState().updateMessage(assistantMsgId, {
                                                        isStreaming: false, // Stop streaming spinner for this message
                                                        extra_metadata: {
                                                            type: 'image',
                                                            job_id: jobId,
                                                            status: 'queued',
                                                            progress: 0,
                                                            queue_position: 1,
                                                        }
                                                    })
                                                }
                                            }
                                            break

                                        case 'sources':
                                            if (event.data) {
                                                setUnifiedSources(event.data)
                                            }
                                            break

                                        case 'error':
                                            console.error('[Stream Error]', event.content)
                                            appendToStreaming(`\n\n⚠️ Hata: ${event.content}`)
                                            break
                                    }
                                } catch (e) {
                                    // Verify if it's a legacy plain text chunk (fallback)
                                    console.warn('[Chat] Failed to parse JSON line, treating as text:', line)
                                    if (line.trim()) {
                                        hasContent = true
                                        fullResponse += line
                                        appendToStreaming(line)
                                    }
                                }
                            }
                        } catch (streamError) {
                            // Handle stream read errors
                            if (streamError instanceof Error && streamError.name === 'AbortError') {
                                throw new Error(`Stream timeout - response took longer than ${streamTimeout}ms`)
                            }
                            throw streamError
                        }
                    }
                } else {
                    console.error('[Chat] No response body reader')
                    throw new Error('Yanıt gövdesi okunamadı.')
                }
            } catch (streamError) {
                console.error('[Chat] Stream error:', streamError)
                const errorMsg = streamError instanceof Error
                    ? streamError.message
                    : 'Stream hatası'
                appendToStreaming(`\n\n⚠️ ${errorMsg}`)
            } finally {
                clearTimeout(streamTimeoutId)
            }

            // Check if this is an image queued response
            // New format: [IMAGE_QUEUED:job_id:message_id]
            const imageMatch = fullResponse.match(/\[IMAGE_QUEUED:([^:]+):(\d+)\]/)
            // Ensure we don't double-process if handled in stream loop
            const isImageRequest = !hasImageJob && (imageMatch !== null || !hasContent)

            if (isImageRequest) {
                // Delete the streaming placeholder
                useChatStore.getState().deleteMessage(assistantMsgId)

                if (imageMatch) {
                    const [, jobId, messageId] = imageMatch
                    console.log('[Chat] Image request with IDs:', { jobId: jobId.slice(0, 8), messageId })

                    const { useImageJobsStore } = await import('@/stores/imageJobsStore')
                    useImageJobsStore.getState().linkMessageToJob(messageId, jobId)
                    useImageJobsStore.getState().updateJob({
                        id: jobId,
                        conversationId: sendConversationId || newConvId || undefined,
                        status: 'queued',
                        progress: 0,
                        prompt: textToSend
                    })

                    useChatStore.getState().addMessage({
                        id: messageId,
                        role: 'assistant',
                        content: '[IMAGE_PENDING] Görsel isteğiniz kuyruğa alındı...',
                        conversationId: sendConversationId || newConvId || '',
                        extra_metadata: {
                            type: 'image',
                            job_id: jobId,
                            status: 'queued',
                            progress: 0,
                            queue_position: 1,
                        }
                    })
                } else {
                    console.log('[Chat] Image request without IDs - reloading from DB')
                    const finalConvId = sendConversationId || newConvId
                    if (finalConvId) {
                        try {
                            const freshMessages = await chatApi.getMessages(finalConvId)
                            useChatStore.getState().setMessages(freshMessages)
                        } catch (e) {
                            console.error('[Chat] Failed to reload messages:', e)
                        }
                    }
                }
            }
        } catch (error) {
            // Hata yönetimi: Kullanıcıya bildirim ver ve log yaz
            console.error('[Chat] Mesaj gönderme başarısız:', error)

            const errorMessage = error instanceof Error
                ? error.message
                : 'Mesaj gönderilemedi'

            // Kullanıcıya hata mesajı göster
            addMessage({
                role: 'assistant',
                content: `⚠️ Hata: ${errorMessage}`
            })
        } finally {
            setIsSending(false)
            stopStreaming()
        }
    }, [canSend, inputValue, attachments, currentConversationId, addMessage, createConversation, startStreaming, appendToStreaming, stopStreaming, setInputValue, imageSettings, activePersona, responseStyle, onClearReply, replyTo])

    const handleKeyDown = (e: React.KeyboardEvent) => {
        // Don't send if command palette is open - let it handle navigation
        if (shouldShowPalette && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
            return // Let palette handle
        }

        if (e.key === 'Enter' && !e.shiftKey) {
            if (!shouldShowPalette) {
                e.preventDefault()
                handleSend()
            }
        }

        if (e.key === 'Escape' && shouldShowPalette) {
            setInputValue('')
        }
    }

    const handleCommandSelect = useCallback((_command: Command) => {
        // Command already executed its action
        textareaRef.current?.focus()
    }, [])

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || [])
        setAttachments(prev => [...prev, ...files])
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    const removeAttachment = (index: number) => {
        setAttachments(prev => prev.filter((_, i) => i !== index))
    }

    const handleEmojiSelect = useCallback((emoji: string) => {
        const current = useChatStore.getState().inputValue
        setInputValue(current ? `${current}${emoji}` : emoji)
        setShowEmojiPicker(false)
        requestAnimationFrame(() => textareaRef.current?.focus())
    }, [setInputValue])

    // Close emoji picker on outside click
    useEffect(() => {
        if (!showEmojiPicker) return

        const handleClickOutside = (e: MouseEvent) => {
            const target = e.target as Node
            if (
                emojiPickerRef.current?.contains(target) ||
                emojiButtonRef.current?.contains(target)
            ) {
                return
            }
            setShowEmojiPicker(false)
        }

        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [showEmojiPicker])


    const handleInputMouseDownCapture = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        const textareaEl = textareaRef.current
        const target = e.target as HTMLElement
        const isTextarea = textareaEl ? target.closest('textarea') === textareaEl : false
        const isInteractive = !!target.closest('button, input, select, option, label, textarea')

        if (!isTextarea && !isInteractive) {
            // Boş alanda tıklamayı yut, caret açılmasın
            e.preventDefault()
            e.stopPropagation()
        }
    }, [])

    // Close advanced popup on outside click
    useEffect(() => {
        if (showToolbar) return

        const handleClickOutside = (e: MouseEvent) => {
            if (inputWrapperRef.current && !inputWrapperRef.current.contains(e.target as Node)) {
                setShowToolbar(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [showToolbar])

    return (
        <div className={cn(
            "px-3 md:px-8 py-4",
            "sticky bottom-0 z-50", // Always sticky, let interactive-widget handle the rest
            "bg-linear-to-t from-(--color-bg) via-(--color-bg)/95 to-transparent"
        )} style={{
            marginBottom: isMobile ? `${mobileBottomOffset}px` : 0,
            paddingBottom: isMobile && !keyboardActive ? '1rem' : undefined // Basic safe area
        }}>
            {/* Attachment Preview */}
            <AnimatePresence>
                {attachments.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 1, height: 'auto' }}
                        className="mb-3 flex gap-2 flex-wrap max-w-(--chat-max-width) mx-auto"
                    >
                        {attachments.map((file, i) => (
                            <AttachmentPreview
                                key={`${file.name}-${i}`}
                                file={file}
                                onRemove={() => removeAttachment(i)}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Input Container */}
            <div className="max-w-(--chat-max-width) mx-auto relative" ref={inputWrapperRef}>
                {/* Command Palette */}
                <AnimatePresence>
                    {shouldShowPalette && (
                        <CommandPalette
                            query={commandQuery || ''}
                            onSelect={handleCommandSelect}
                            onClose={() => setInputValue('')}
                        />
                    )}
                </AnimatePresence>

                {/* Image Attachments (Multi-Modal) */}
                <input
                    ref={multiModal.fileInputRef}
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={multiModal.handleFileChange}
                    className="hidden"
                />
                <MultiModalInput
                    images={multiModal.images}
                    onImagesChange={multiModal.setImages}
                    maxImages={4}
                />

                {/* Popup Toolbar (commands, uploads, quick settings) */}
                <AnimatePresence>
                    {showToolbar && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.98, y: 8 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.98, y: 8 }}
                            transition={{ duration: 0.15 }}
                            className="absolute bottom-full left-0 right-0 mb-3 px-1 z-50"
                        >
                            <div className="rounded-2xl border border-(--color-border) bg-(--color-bg-surface) shadow-xl p-3">
                                <QuickSettings>
                                    <Button
                                        variant="ghost"
                                        size="icon-sm"
                                        onClick={() => {
                                            setInputValue('/')
                                            textareaRef.current?.focus()
                                        }}
                                        title="Komut paleti"
                                        className="text-(--color-text-muted) hover:text-(--color-text)"
                                    >
                                        <Slash className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon-sm"
                                        onClick={() => {
                                            multiModal.openFilePicker()
                                        }}
                                        title="Görsel yükle"
                                        className="text-(--color-text-muted) hover:text-(--color-text)"
                                    >
                                        <ImageIcon className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon-sm"
                                        title="Sesle yaz"
                                        className="text-(--color-text-muted) hover:text-(--color-text)"
                                    >
                                        <Mic className="h-4 w-4" />
                                    </Button>
                                </QuickSettings>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                <div className={cn(
                    "relative flex items-end gap-3 p-3 rounded-2xl",
                    "bg-(--color-bg-surface) border transition-all duration-300",
                    isFocused
                        ? "border-(--color-primary)/50 shadow-lg shadow-(--color-primary)/10"
                        : "border-(--color-border)"
                )} onMouseDownCapture={handleInputMouseDownCapture}>
                    {/* Left Actions */}
                    <div className="flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => setShowToolbar(!showToolbar)}
                            className={cn(
                                "text-(--color-text-muted) hover:text-(--color-text)",
                                showToolbar && "text-(--color-primary)"
                            )}
                            aria-label="Araç menüsünü aç"
                        >
                            {showToolbar ? (
                                <ChevronDown className="h-5 w-5" />
                            ) : (
                                <ChevronUp className="h-5 w-5" />
                            )}
                        </Button>

                        {/* Attachment Button */}
                        <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            className="hidden"
                            onChange={handleFileSelect}
                            accept=".pdf,.txt,.doc,.docx,.md,.jpg,.jpeg,.png,.webp"
                        />
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => fileInputRef.current?.click()}
                            className="text-(--color-text-muted) hover:text-(--color-text)"
                            aria-label="Dosya ekle"
                        >
                            <Paperclip className="h-5 w-5" />
                        </Button>

                        <Button
                            variant="ghost"
                            size="icon-sm"
                            className="text-(--color-text-muted) hover:text-(--color-text)"
                            aria-label="Emoji ekle"
                            aria-expanded={showEmojiPicker}
                            ref={emojiButtonRef}
                            onClick={() => setShowEmojiPicker(prev => !prev)}
                        >
                            <Smile className="h-5 w-5" />
                        </Button>
                    </div>

                    {/* Text Area */}
                    <div className="flex-1 relative">
                        <Textarea
                            ref={textareaRef}
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onFocus={() => setIsFocused(true)}
                            onBlur={() => setIsFocused(false)}
                            onKeyDown={handleKeyDown}
                            placeholder={isMobile ? "Mesaj yazın..." : "Bir mesaj yazın veya / ile komut kullanın..."} rows={1}
                            maxHeight={200}
                            className={cn(
                                "w-full bg-transparent border-0 focus:ring-0 resize-none",
                                "text-(--color-text) text-left",
                                "placeholder-(--color-text-muted) placeholder:text-center placeholder:opacity-40",
                                "min-h-10 px-3 py-2",
                                "flex items-center"
                            )}
                        />
                    </div>

                    {/* Right Actions */}
                    <div className="flex items-center gap-1">
                        {/* Send Button */}
                        <Button
                            variant="ghost"
                            size="icon-sm"
                            disabled={!canSend}
                            onClick={handleSend}
                            className={cn(
                                "transition-all",
                                canSend
                                    ? "text-(--color-primary) hover:bg-(--color-primary-soft)"
                                    : "text-(--color-text-muted)"
                            )}
                            aria-label="Gönder"
                        >
                            {isSending || isStreaming ? (
                                <Loader2 className="h-5 w-5 animate-spin" />
                            ) : (
                                <Send className="h-5 w-5" />
                            )}
                        </Button>
                    </div>
                </div>

                {/* Emoji Picker */}
                <AnimatePresence>
                    {showEmojiPicker && (
                        <motion.div
                            ref={emojiPickerRef}
                            initial={{ opacity: 0, scale: 0.98, y: 8 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.98, y: 8 }}
                            transition={{ duration: 0.12 }}
                            className="absolute bottom-full left-0 mb-2 z-40 pointer-events-auto"
                        >
                            <div className="rounded-2xl border border-(--color-border) bg-(--color-bg-surface) shadow-xl p-2 w-56 sm:w-64">
                                <div className="grid grid-cols-7 gap-1.5">
                                    {EMOJI_OPTIONS.map((emoji) => (
                                        <button
                                            key={emoji}
                                            type="button"
                                            onClick={() => handleEmojiSelect(emoji)}
                                            className="text-lg sm:text-xl h-9 w-9 sm:h-10 sm:w-10 flex items-center justify-center rounded-lg hover:bg-(--color-bg) active:scale-95 transition"
                                            aria-label={`Emoji ${emoji}`}
                                        >
                                            {emoji}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Bottom Bar: Info */}
                <div className="flex items-center justify-end mt-2 px-1">
                    <div className="flex items-center gap-3 text-xs text-(--color-text-muted)">
                        {!isMobile && (
                            <span className={cn(
                                inputValue.length > 9000 ? "text-(--color-error)" :
                                    inputValue.length > 8000 ? "text-(--color-warning)" : ""
                            )}>
                                {inputValue.length > 0 && `${inputValue.length.toLocaleString('tr-TR')} / 10.000`}
                            </span>
                        )}
                        <span className="hidden md:inline">
                            Enter: Gönder • / : Komutlar
                        </span>
                    </div>
                </div>
            </div>
        </div>
    )
}

// ─────────────────────────────────────────────────────────────────────────────

interface AttachmentPreviewProps {
    file: File
    onRemove: () => void
}

function AttachmentPreview({ file, onRemove }: AttachmentPreviewProps) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-lg",
                "bg-(--color-bg-surface) border border-(--color-border)"
            )}
        >
            <Paperclip className="h-4 w-4 text-(--color-text-muted)" />
            <span className="text-sm truncate max-w-37.5">{file.name}</span>
            <button
                onClick={onRemove}
                className="p-0.5 rounded hover:bg-(--color-error-soft) text-(--color-text-muted) hover:text-(--color-error) transition-colors"
            >
                <X className="h-3.5 w-3.5" />
            </button>
        </motion.div>
    )
}
