/**
 * WebSocket Hook
 * 
 * Real-time connection for progress updates and notifications.
 * Görsel progress güncellemelerini progress cache'e yazar.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useToast } from '@/components/common'
import { useUserStore } from '@/stores'
// progressCache artık kullanılmıyor - state doğrudan güncelleniyor
import { decodeHtmlEntities } from '@/lib/utils'
import type { WebSocketMessage, Message } from '@/types'

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

interface UseWebSocketReturn {
    isConnected: boolean
    lastMessage: WebSocketMessage | null
    sendMessage: (message: string) => void
    reconnect: () => void
}

// Singleton WebSocket instance
let globalWs: WebSocket | null = null
let connectionPromise: Promise<void> | null = null

// ═══════════════════════════════════════════════════════════════════════════
// MAIN HOOK
// ═══════════════════════════════════════════════════════════════════════════

export function useWebSocket(): UseWebSocketReturn {
    const [isConnected, setIsConnected] = useState(false)
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
    const reconnectTimeoutRef = useRef<number | null>(null)
    const reconnectAttempts = useRef(0)
    const { success, error: toastError } = useToast()

    // Handle incoming messages
    const handleMessage = useCallback((event: MessageEvent) => {
        try {
            const rawData = JSON.parse(event.data)

            // Normalize message
            const message: WebSocketMessage = {
                type: rawData.type as WebSocketMessage['type'],
                data: rawData,
                timestamp: new Date().toISOString(),
            }

            setLastMessage(message)

            // Handle image_progress type (covers all states)
            if (message.type === 'image_progress') {
                const status = String(rawData.status || 'processing')
                const jobId = String(rawData.job_id || 'unknown')
                const progress = Number(rawData.progress || 0)
                const queuePosition = Number(rawData.queue_position || 1)
                const conversationId = rawData.conversation_id as string | undefined

                console.log('[WebSocket] Image progress:', jobId.slice(0, 8), status, progress + '%', 'queuePos:', queuePosition)

                const updateStores = async () => {
                    const { useChatStore } = await import('@/stores/chatStore')
                    const { useImageJobsStore } = await import('@/stores/imageJobsStore')

                    const chatStore = useChatStore.getState()
                    const imageStore = useImageJobsStore.getState()

                    // Ordered status levels to prevent regressions
                    const statusLevels: Record<string, number> = {
                        'queued': 1,
                        'processing': 2,
                        'complete': 3,
                        'error': 4
                    }

                    // 1. Update Chat Store (Persistent UI) - Detreministic Match First
                    const targetMessage = chatStore.messages.find(m =>
                        (m.id === String(rawData.message_id) && rawData.message_id) ||
                        m.extra_metadata?.job_id === jobId
                    )

                    if (targetMessage) {
                        const currentStatus = (targetMessage.extra_metadata?.status as string) || 'queued'
                        const currentLevel = statusLevels[currentStatus] || 0
                        const nextLevel = statusLevels[status] || 0

                        // Terminal State Rule (Phase 5.1):
                        // 1. If current status is complete or error, ignore later events.
                        // 2. complete cannot be downgraded to error.
                        if (currentStatus === 'complete' || currentStatus === 'error') {
                            console.log('[WebSocket] Ignoring event for terminal state:', { jobId, currentStatus, nextStatus: status })
                            return
                        }

                        // Guard: Don't revert to previous state (e.g., processing -> queued)
                        if (nextLevel < currentLevel) {
                            console.warn('[WebSocket] Ignored out-of-order event:', { jobId, currentStatus, nextStatus: status })
                            return
                        }

                        chatStore.updateMessage(targetMessage.id, {
                            extra_metadata: {
                                ...targetMessage.extra_metadata,
                                type: 'image',
                                status: status as any,
                                progress,
                                queue_position: queuePosition,
                                image_url: rawData.image_url,
                                error: rawData.error
                            },
                            // If complete/error, also update content as fallback
                            ...(status === 'complete' && rawData.image_url ? {
                                content: `[IMAGE] Resminiz hazır.\nIMAGE_PATH: ${rawData.image_url}`
                            } : {}),
                            ...(status === 'error' ? {
                                content: `❌ Görsel oluşturulamadı: ${rawData.error || 'Bilinmeyen hata'}`
                            } : {}),
                        })
                        console.log('[WebSocket] Updated message:', targetMessage.id, status, progress + '%')
                    } else {
                        console.warn('[WebSocket] No message found for job_id/msg_id:', { jobId: jobId.slice(0, 8), msgId: rawData.message_id })
                    }

                    // 2. Update Image Jobs Store (Active tracking)
                    imageStore.updateJob({
                        id: jobId,
                        conversationId,
                        status: status as any,
                        progress,
                        queuePosition,
                        imageUrl: rawData.image_url,
                        error: rawData.error
                    })
                }

                updateStores().catch(err => console.error('[WebSocket] store update error:', err))

                // Show toast when complete/error
                if (status === 'complete') {
                    success('Görsel Hazır', 'Görseliniz başarıyla oluşturuldu')
                    window.dispatchEvent(new CustomEvent('image-complete', {
                        detail: { jobId, conversationId, imageUrl: rawData.image_url }
                    }))
                } else if (status === 'error') {
                    toastError('Görsel Hatası', String(rawData.error || 'Görsel oluşturulamadı'))
                }
            }

            // Handle notifications
            if (message.type === 'notification') {
                const data = message.data || {}
                const notifType = data.type as string

                if (notifType === 'success') {
                    success(String(data.title || 'Başarılı'), String(data.message || ''))
                } else if (notifType === 'error') {
                    toastError(String(data.title || 'Hata'), String(data.message || ''))
                }
            }
        } catch (e) {
            console.error('[WebSocket] Parse error', e)
        }
    }, [success, toastError])

    // Connect to WebSocket
    const connect = useCallback(() => {
        // Prevent duplicate connections
        if (globalWs?.readyState === WebSocket.OPEN) {
            setIsConnected(true)
            return
        }

        // Wait for pending connection
        if (connectionPromise) {
            return
        }

        connectionPromise = new Promise<void>((resolve) => {
            try {
                // Build WebSocket URL - Use relative path for Proxy/Cookie support
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
                const wsUrl = `${protocol}//${window.location.host}/ws`

                console.log('[WebSocket] Connecting to:', wsUrl)

                globalWs = new WebSocket(wsUrl)

                globalWs.onopen = () => {
                    console.log('[WebSocket] Connected')
                    setIsConnected(true)
                    reconnectAttempts.current = 0
                    connectionPromise = null
                    resolve()
                }

                globalWs.onmessage = handleMessage

                globalWs.onclose = (e) => {
                    console.log('[WebSocket] Disconnected:', e.code, e.reason)
                    setIsConnected(false)
                    globalWs = null
                    connectionPromise = null

                    // Auto-reconnect with exponential backoff
                    // STOP reconnecting if it was a policy violation (1008) - usually means unauthorized/logout
                    if (e.code !== 1008 && reconnectAttempts.current < 5) {
                        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
                        console.log(`[WebSocket] Reconnecting in ${delay}ms...`)
                        reconnectTimeoutRef.current = window.setTimeout(() => {
                            reconnectAttempts.current++
                            connect()
                        }, delay)
                    }
                }

                globalWs.onerror = (error) => {
                    console.error('[WebSocket] Error:', error)
                    connectionPromise = null
                }
            } catch (error) {
                console.error('[WebSocket] Connection error:', error)
                connectionPromise = null
                resolve()
            }
        })
    }, [handleMessage])

    // Reconnect function
    const reconnect = useCallback(() => {
        if (globalWs) {
            globalWs.close()
            globalWs = null
        }
        reconnectAttempts.current = 0
        connect()
    }, [connect])

    // Send message
    const sendMessage = useCallback((message: string) => {
        if (globalWs?.readyState === WebSocket.OPEN) {
            globalWs.send(message)
        } else {
            console.warn('[WebSocket] Not connected, cannot send message')
        }
    }, [])

    // Connect on mount
    useEffect(() => {
        connect()

        return () => {
            // Clear reconnect timeout
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current)
            }
        }
    }, [connect])

    return {
        isConnected,
        lastMessage,
        sendMessage,
        reconnect,
    }
}
