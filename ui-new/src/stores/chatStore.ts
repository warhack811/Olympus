/**
 * Chat Store - Zustand
 * 
 * Sohbet, mesajlar ve konuşmalar için merkezi state
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { Message, Conversation, ReasoningStep, UnifiedSource } from '@/types'
import { generateId } from '@/lib/utils'

interface ChatState {
    // Current state
    currentConversationId: string | null
    messages: Message[]
    conversations: Conversation[]

    // Input state
    inputValue: string
    isTyping: boolean
    isStreaming: boolean
    streamingMessageId: string | null

    // UI state
    isSidebarOpen: boolean
    isLoadingHistory: boolean
    isInitialLoad: boolean  // First-time app load (separate from conversation-specific loading)

    // Actions - Conversations
    setCurrentConversation: (id: string | null, keepMessages?: boolean) => void
    createConversation: () => string
    deleteConversation: (id: string) => void
    updateConversationTitle: (id: string, title: string) => void
    setConversations: (conversations: Conversation[]) => void

    // Actions - Messages
    // id, timestamp ve extra_metadata opsiyonel - backend'den gelirse kullan
    addMessage: (message: Omit<Message, 'id' | 'timestamp'> & Partial<Pick<Message, 'id' | 'timestamp' | 'extra_metadata'>>) => string
    updateMessage: (id: string, updates: Partial<Message>) => void
    updateMessageId: (oldId: string, newId: string) => void
    deleteMessage: (id: string) => void
    setMessages: (messages: Message[]) => void
    clearMessages: () => void

    // Actions - Streaming
    startStreaming: (messageId: string) => void
    appendToStreaming: (content: string) => void
    stopStreaming: () => void
    appendReasoning: (step: ReasoningStep) => void
    setUnifiedSources: (sources: UnifiedSource[]) => void

    // Actions - Input
    setInputValue: (value: string) => void
    setIsTyping: (isTyping: boolean) => void

    // Actions - UI
    toggleSidebar: () => void
    setSidebarOpen: (isOpen: boolean) => void
    setLoadingHistory: (isLoading: boolean) => void
    setInitialLoad: (isLoading: boolean) => void  // Set initial load state
}

/**
 * Helper to ensure a message has flattened metadata fields
 */
const hydrateMessage = (m: any): Message => {
    return {
        ...m,
        reasoning_log: m.reasoning_log || m.extra_metadata?.reasoning_log || [],
        unified_sources: m.unified_sources || m.extra_metadata?.unified_sources || [],
    }
}

export const useChatStore = create<ChatState>()(
    persist(
        (set, get) => ({
            // Initial state
            currentConversationId: null,
            messages: [],
            conversations: [],
            inputValue: '',
            isTyping: false,
            isStreaming: false,
            streamingMessageId: null,
            isSidebarOpen: true,
            isLoadingHistory: false,
            isInitialLoad: true,  // Start with true, set to false after first load

            // Conversation actions
            setCurrentConversation: (id, keepMessages = false) => {
                if (keepMessages) {
                    // Just update the ID, keep existing messages (for new conversations)
                    set({ currentConversationId: id })
                } else {
                    // Change conversation, clear messages (for switching conversations)
                    set({ currentConversationId: id, messages: [] })
                }
            },

            createConversation: () => {
                // ID üretmiyoruz, null yapıyoruz (Backend ilk mesajda üretecek)
                // Böylece 500 hatası ve çöp kayıt oluşumu engellenir.

                set((state) => ({
                    // Yeni sohbeti listeye eklemiyoruz, ilk mesaj atılınca eklenecek
                    // conversations: [newConversation, ...state.conversations], 

                    currentConversationId: null, // ÖNEMLİ: ID yok, backend bekleyecek
                    messages: [],
                    inputValue: '' // Varsa yazılanı da temizle
                }))

                // Geriye boş string dönüyoruz çünkü ID henüz yok
                return ''
            },

            deleteConversation: (id) => {
                set((state) => ({
                    conversations: state.conversations.filter((c) => c.id !== id),
                    currentConversationId: state.currentConversationId === id
                        ? null
                        : state.currentConversationId,
                    messages: state.currentConversationId === id ? [] : state.messages
                }))
            },

            updateConversationTitle: (id, title) => {
                set((state) => ({
                    conversations: state.conversations.map((c) =>
                        c.id === id ? { ...c, title, updatedAt: new Date().toISOString() } : c
                    )
                }))
            },

            setConversations: (conversations) => {
                set({ conversations })
            },

            // Message actions
            // id ve extra_metadata opsiyonel - backend'den gelirse kullan, gelmezse üret
            addMessage: (message) => {
                // Backend'den id geldiyse kullan, yoksa local üret
                const id = message.id || generateId('msg')
                const timestamp = message.timestamp || new Date().toISOString()

                const newMessage = hydrateMessage({
                    ...message,
                    id,
                    timestamp,
                    conversationId: message.conversationId || get().currentConversationId || '',
                    extra_metadata: message.extra_metadata,
                })

                set((state) => ({
                    messages: [...state.messages, newMessage]
                }))

                // Update conversation
                const convId = get().currentConversationId
                if (convId) {
                    set((state) => ({
                        conversations: state.conversations.map((c) =>
                            c.id === convId
                                ? {
                                    ...c,
                                    messageCount: c.messageCount + 1,
                                    preview: message.content.slice(0, 100),
                                    updatedAt: timestamp
                                }
                                : c
                        )
                    }))
                }

                return id
            },

            updateMessage: (id, updates) => {
                set((state) => ({
                    messages: state.messages.map((m) =>
                        m.id === id
                            ? hydrateMessage({
                                ...m,
                                ...updates,
                                extra_metadata: updates.extra_metadata
                                    ? { ...m.extra_metadata, ...updates.extra_metadata }
                                    : m.extra_metadata
                            })
                            : m
                    )
                }))
            },

            updateMessageId: (oldId: string, newId: string) => {
                set((state) => ({
                    messages: state.messages.map((m) =>
                        m.id === oldId ? { ...m, id: newId } : m
                    ),
                    streamingMessageId: state.streamingMessageId === oldId ? newId : state.streamingMessageId
                }))
            },

            deleteMessage: (id: string) => {
                set((state) => ({
                    messages: state.messages.filter((m) => m.id !== id)
                }))
            },

            setMessages: (messages) => {
                const hydratedMessages = messages.map(hydrateMessage)
                set({ messages: hydratedMessages })

                // Phase 5: Hydration robustness - link image jobs to store
                const imageMessages = messages.filter(m => m.extra_metadata?.job_id)
                if (imageMessages.length > 0) {
                    import('@/stores/imageJobsStore').then(({ useImageJobsStore }) => {
                        const jobStore = useImageJobsStore.getState()
                        imageMessages.forEach(m => {
                            const jobId = m.extra_metadata!.job_id as string
                            jobStore.linkMessageToJob(m.id, jobId)
                            // If message is pending/processing, also sync to job store as active
                            const status = m.extra_metadata!.status as string
                            if (status === 'queued' || status === 'processing') {
                                jobStore.updateJob({
                                    id: jobId,
                                    status: status as any,
                                    progress: (m.extra_metadata!.progress as number) || 0,
                                    conversationId: m.conversationId
                                })
                            }
                        })
                    }).catch(err => console.error('[Hydration] Job store sync failed:', err))
                }
            },

            clearMessages: () => {
                set({ messages: [] })
            },

            // Streaming actions
            startStreaming: (messageId) => {
                set({ isStreaming: true, streamingMessageId: messageId })
            },

            appendToStreaming: (content) => {
                const { streamingMessageId } = get()
                if (!streamingMessageId) return

                set((state) => ({
                    messages: state.messages.map((m) =>
                        m.id === streamingMessageId
                            ? { ...m, content: m.content + content }
                            : m
                    )
                }))
            },

            stopStreaming: () => {
                const { streamingMessageId } = get()
                if (streamingMessageId) {
                    set((state) => ({
                        messages: state.messages.map((m) =>
                            m.id === streamingMessageId
                                ? { ...m, isStreaming: false }
                                : m
                        ),
                        isStreaming: false,
                        streamingMessageId: null
                    }))
                }
            },

            appendReasoning: (step) => {
                const { streamingMessageId } = get()
                if (!streamingMessageId) return

                set((state) => ({
                    messages: state.messages.map((m) =>
                        m.id === streamingMessageId
                            ? { ...m, reasoning_log: [...(m.reasoning_log || []), step] }
                            : m
                    )
                }))
            },

            setUnifiedSources: (sources) => {
                const { streamingMessageId } = get()
                if (!streamingMessageId) return

                set((state) => ({
                    messages: state.messages.map((m) =>
                        m.id === streamingMessageId
                            ? { ...m, unified_sources: sources }
                            : m
                    )
                }))
            },

            // Input actions
            setInputValue: (value) => {
                set({ inputValue: value })
            },

            setIsTyping: (isTyping) => {
                set({ isTyping })
            },

            // UI actions
            toggleSidebar: () => {
                set((state) => ({ isSidebarOpen: !state.isSidebarOpen }))
            },

            setSidebarOpen: (isOpen) => {
                set({ isSidebarOpen: isOpen })
            },

            setLoadingHistory: (isLoading) => {
                set({ isLoadingHistory: isLoading })
            },

            setInitialLoad: (isLoading) => {
                set({ isInitialLoad: isLoading })
            }
        }
        ),
        {
            name: 'mami-chat-storage',
            storage: createJSONStorage(() => localStorage),
            partialize: (state) => ({
                currentConversationId: state.currentConversationId,
                isSidebarOpen: state.isSidebarOpen,
            }),
        }
    ))
