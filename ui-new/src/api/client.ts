/**
 * API Client
 *
 * Backend API ile iletişim için merkezi client
 * Fetch tabanlı, type-safe
 */

import { decodeHtmlEntities } from '@/lib/utils'
import { captureApiError, captureNetworkError, addBreadcrumb } from '@/lib/errorTracking'
import type {
    ApiResponse,
    User,
    Conversation,
    Message,
    Memory,
    Document,
    BrandingConfig,
    Persona
} from '@/types'

// Use relative path for Proxy/Cookie support in development, or current origin in production
export const API_DOMAIN = ''
const API_BASE = `/api/v1`

/**
 * Normalizes image URLs for cross-domain usage.
 * If URL is relative (/images/...), prepends API_DOMAIN.
 */
export function normalizeImageUrl(url: string | null | undefined): string {
    if (!url) return ''
    if (url.startsWith('http')) return url
    if (url.startsWith('data:')) return url // Base64 support

    // Check if it's a user upload (usually contains username/images/...)
    // Or if it's already prefixed with /uploads/
    if (url.startsWith('uploads/')) return `${API_DOMAIN}/${url}`
    if (url.includes('/images/')) {
        // Handle paths like "admin/images/photo.png" -> "/uploads/admin/images/photo.png"
        return `${API_DOMAIN}/uploads/${url}`
    }

    if (url.startsWith('/')) return `${API_DOMAIN}${url}`
    return `${API_DOMAIN}/${url}`
}


/**
 * Fetch with retry logic, timeout, and rate limit handling
 * Implements exponential backoff for transient failures
 */
async function fetchWithRetry<T>(
    endpoint: string,
    options: RequestInit = {},
    maxRetries: number = 3,
    timeout: number = 10000
): Promise<T> {
    const url = `${API_BASE}${endpoint}`

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), timeout)

            // Breadcrumb ekle - API isteği başlangıcı
            addBreadcrumb(
                `API Request: ${options.method || 'GET'} ${endpoint}`,
                'api',
                'info'
            )

            const response = await fetch(url, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
                ...options,
                signal: controller.signal,
            })

            clearTimeout(timeoutId)

            // Breadcrumb ekle - API yanıtı
            addBreadcrumb(
                `API Response: ${response.status} ${endpoint}`,
                'api',
                response.ok ? 'info' : 'warning'
            )

            // Handle rate limiting (429)
            if (response.status === 429) {
                const waitTime = 1000 * Math.pow(2, attempt)
                if (attempt < maxRetries) {
                    console.warn(`[API] Rate limited. Retrying in ${waitTime}ms...`)
                    await new Promise(r => setTimeout(r, waitTime))
                    continue
                }
            }

            // Handle server errors (5xx) with retry
            if (response.status >= 500 && attempt < maxRetries) {
                const waitTime = 1000 * Math.pow(2, attempt)
                console.warn(`[API] Server error ${response.status}. Retrying in ${waitTime}ms...`)
                await new Promise(r => setTimeout(r, waitTime))
                continue
            }

            // Handle auth errors (no retry)
            if (response.status === 401) {
                const error = new Error('Unauthorized')
                captureApiError(error, {
                    endpoint,
                    method: options.method || 'GET',
                    statusCode: response.status,
                })
                throw error
            }

            // Handle other client errors (4xx, except 429)
            if (!response.ok) {
                const error = await response.json().catch(() => ({}))
                const errorMessage = error.message || error.detail || `Request failed: ${response.status}`
                const apiError = new Error(errorMessage)
                
                captureApiError(apiError, {
                    endpoint,
                    method: options.method || 'GET',
                    statusCode: response.status,
                    responseData: error,
                })
                
                throw apiError
            }

            // Handle empty responses
            const text = await response.text()
            if (!text) {
                throw new Error('Empty response from server')
            }

            return JSON.parse(text)
        } catch (error) {
            // Handle timeout
            if (error instanceof Error && error.name === 'AbortError') {
                const waitTime = 1000 * Math.pow(2, attempt)
                if (attempt < maxRetries) {
                    console.warn(`[API] Request timeout. Retrying in ${waitTime}ms...`)
                    await new Promise(r => setTimeout(r, waitTime))
                    continue
                }
                
                const timeoutError = new Error(`Request timeout after ${timeout}ms`)
                captureNetworkError(timeoutError, {
                    url,
                    timeout,
                    type: 'timeout',
                })
                throw timeoutError
            }

            // If this was the last attempt, throw the error
            if (attempt === maxRetries) {
                // Network error'ını Sentry'ye gönder
                if (error instanceof Error) {
                    captureNetworkError(error, {
                        url,
                        type: 'network_error',
                    })
                }
                throw error
            }

            // Otherwise, retry with exponential backoff
            const waitTime = 1000 * Math.pow(2, attempt)
            console.warn(`[API] Request failed (attempt ${attempt + 1}/${maxRetries + 1}). Retrying in ${waitTime}ms...`)
            await new Promise(r => setTimeout(r, waitTime))
        }
    }

    throw new Error('Max retries exceeded')
}

/**
 * Base fetch wrapper with error handling
 * Uses retry logic with exponential backoff
 */
export async function fetchApi<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    return fetchWithRetry<T>(endpoint, options)
}

// ═══════════════════════════════════════════════════════════════════════════
// AUTH API
// ═══════════════════════════════════════════════════════════════════════════

export const authApi = {
    /**
     * Get current user
     */
    async getCurrentUser(): Promise<User> {
        return fetchApi<User>('/auth/me')
    },

    /**
     * Login
     */
    async login(username: string, password: string): Promise<{ user: User }> {
        return fetchApi('/public/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        })
    },

    /**
     * Register with invite code
     */
    async register(payload: { username: string, password: string, invite_code: string }): Promise<{ ok: boolean, message: string }> {
        return fetchApi('/public/register_with_invite', {
            method: 'POST',
            body: JSON.stringify(payload),
        })
    },

    /**
     * Logout
     */
    async logout(): Promise<void> {
        await fetchApi('/public/logout', { method: 'POST' })
    },
}

// ═══════════════════════════════════════════════════════════════════════════
// CHAT API
// ═══════════════════════════════════════════════════════════════════════════

export const chatApi = {
    /**
     * Send chat message (streaming)
     */
    async sendMessage(params: {
        message: string
        conversationId?: string | null
        forceLocal?: boolean
        requestedModel?: string | null
        persona?: string | null
        stream?: boolean
        styleProfile?: {
            tone?: string
            length?: string
            emojiLevel?: string
            useMarkdown?: boolean
            useCodeBlocks?: boolean
        }
        images?: string[]
        imageSettings?: any
    }): Promise<Response> {
        const response = await fetch(`${API_BASE}/user/chat`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: params.message,
                conversation_id: params.conversationId,
                force_local: params.forceLocal || false,
                model: params.requestedModel,
                persona: params.persona || 'standard',
                stream: params.stream ?? true,
                style_profile: params.styleProfile ? {
                    tone: params.styleProfile.tone,
                    length: params.styleProfile.length,
                    emoji_level: params.styleProfile.emojiLevel,
                    use_markdown: params.styleProfile.useMarkdown ?? true,
                    use_code_blocks: params.styleProfile.useCodeBlocks ?? true
                } : null,
                images: params.images,
                image_settings: params.imageSettings
            }),
        })

        if (!response.ok) {
            throw new Error(`Chat request failed: ${response.status}`)
        }

        return response
    },

    /**
     * Get conversations list
     */
    async getConversations(): Promise<Conversation[]> {
        return fetchApi<Conversation[]>('/user/conversations')
    },

    /**
     * Get conversation messages
     * Backend returns array of {id, role, text, extra_metadata}, we map to frontend format
     */
    async getMessages(conversationId: string): Promise<Message[]> {
        interface BackendMessage {
            id: number  // ← Backend message ID
            role: 'user' | 'bot'
            text: string
            extra_metadata?: Record<string, unknown>
        }

        // Backend uses /conversations/{id} not /conversations/{id}/messages
        const messages = await fetchApi<BackendMessage[]>(`/user/conversations/${conversationId}`)

        // Map backend format to frontend format - USE BACKEND ID!
        return messages.map((m) => ({
            id: String(m.id),  // ← Backend ID kullanılıyor (string'e çevir)
            role: m.role === 'bot' ? 'assistant' as const : 'user' as const,
            content: m.text,
            timestamp: new Date().toISOString(),
            conversationId,
            extra_metadata: m.extra_metadata as Message['extra_metadata'],
            // Hydrate Glass Box data from metadata
            reasoning_log: m.extra_metadata?.reasoning_log as any,
            unified_sources: m.extra_metadata?.unified_sources as any,
        }))
    },

    /**
     * Delete conversation
     */
    async deleteConversation(conversationId: string): Promise<void> {
        await fetchApi(`/user/conversations/${conversationId}`, { method: 'DELETE' })
    },

    /**
     * Delete all conversations
     */
    async deleteAllConversations(): Promise<void> {
        await fetchApi('/user/conversations', { method: 'DELETE' })
    },

    /**
     * Submit feedback
     */
    async submitFeedback(messageId: string, feedback: 'like' | 'dislike'): Promise<void> {
        await fetchApi('/user/feedback', {
            method: 'POST',
            body: JSON.stringify({ message_id: messageId, feedback }),
        })
    },

    /**
     * Get job status for a specific job_id
     * Used when page refreshes to restore pending job status
     */
    async getJobStatus(jobId: string): Promise<{
        job_id: string
        status: 'queued' | 'processing' | 'complete' | 'error' | 'unknown'
        progress: number
        queue_position: number
        conversation_id?: string
        image_url?: string
        error?: string
    }> {
        return fetchApi(`/user/image/job/${jobId}/status`)
    },

    /**
     * Cancel a pending image job
     */
    async cancelJob(jobId: string): Promise<{ success: boolean; message: string }> {
        return fetchApi(`/user/image/job/${jobId}/cancel`, { method: 'POST' })
    },
}

// ═══════════════════════════════════════════════════════════════════════════
// MEMORY API
// ═══════════════════════════════════════════════════════════════════════════

export const memoryApi = {
    /**
     * Get user memories
     */
    async getMemories(): Promise<Memory[]> {
        return fetchApi<Memory[]>('/user/memories')
    },

    /**
     * Create memory
     */
    async createMemory(text: string, importance?: number): Promise<Memory> {
        return fetchApi<Memory>('/user/memories', {
            method: 'POST',
            body: JSON.stringify({ text, importance: importance ?? 0.5 }),
        })
    },

    /**
     * Update memory
     */
    async updateMemory(id: string, updates: Partial<Memory>): Promise<Memory> {
        return fetchApi<Memory>(`/user/memories/${id}`, {
            method: 'PUT',
            body: JSON.stringify(updates),
        })
    },

    /**
     * Delete memory
     */
    async deleteMemory(id: string): Promise<void> {
        await fetchApi(`/user/memories/${id}`, { method: 'DELETE' })
    },

    /**
     * Delete all memories
     */
    async deleteAllMemories(): Promise<void> {
        await fetchApi('/user/memories', { method: 'DELETE' })
    },
}

// ═══════════════════════════════════════════════════════════════════════════
// DOCUMENT API (RAG)
// ═══════════════════════════════════════════════════════════════════════════

export const documentApi = {
    /**
     * Get documents
     */
    async getDocuments(): Promise<Document[]> {
        return fetchApi<Document[]>('/user/documents')
    },

    /**
     * Upload document
     */
    async uploadDocument(file: File, conversationId?: string | null): Promise<Document> {
        const formData = new FormData()
        formData.append('file', file)
        if (conversationId) {
            formData.append('conversation_id', conversationId)
        }

        const response = await fetch(`${API_BASE}/user/upload`, {
            method: 'POST',
            credentials: 'include',
            body: formData,
        })

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.status}`)
        }

        return response.json()
    },

    /**
     * Delete document
     */
    async deleteDocument(id: string): Promise<void> {
        await fetchApi(`/user/documents/${id}`, { method: 'DELETE' })
    },
}

// ═══════════════════════════════════════════════════════════════════════════
// USER PREFERENCES API
// ═══════════════════════════════════════════════════════════════════════════

export const preferencesApi = {
    /**
     * Get user preferences
     */
    async getPreferences(category?: string): Promise<Record<string, string>> {
        const url = category ? `/user/preferences?category=${category}` : '/user/preferences'
        const result = await fetchApi<{ preferences: Record<string, string> }>(url)
        return result.preferences
    },

    /**
     * Set preference
     */
    async setPreference(key: string, value: string, category: string = 'system'): Promise<void> {
        await fetchApi('/user/preferences', {
            method: 'POST',
            body: JSON.stringify({ key, value, category }),
        })
    },

    /**
     * Set multiple preferences at once
     */
    async setPreferences(preferences: Record<string, string>, category: string = 'system'): Promise<void> {
        const promises = Object.entries(preferences).map(([key, value]) =>
            this.setPreference(key, value, category)
        )
        await Promise.all(promises)
    },

    /**
     * Get personas list (backend returns {personas: [], active_persona: string})
     */
    async getPersonas(): Promise<{ personas: Persona[], activePersona: string }> {
        const result = await fetchApi<{ personas: Persona[], active_persona: string }>('/user/personas')
        return {
            personas: result.personas,
            activePersona: result.active_persona
        }
    },

    /**
     * Get active persona
     */
    async getActivePersona(): Promise<{ activePersona: string, displayName: string }> {
        const result = await fetchApi<{ active_persona: string, display_name: string }>('/user/personas/active')
        return {
            activePersona: result.active_persona,
            displayName: result.display_name
        }
    },

    /**
     * Set active persona
     */
    async setActivePersona(persona: string): Promise<{ success: boolean, message: string }> {
        const result = await fetchApi<{ success: boolean, active_persona: string, message: string }>('/user/personas/select', {
            method: 'POST',
            body: JSON.stringify({ persona }),
        })
        return { success: result.success, message: result.message }
    },
}

// ═══════════════════════════════════════════════════════════════════════════
// SYSTEM API
// ═══════════════════════════════════════════════════════════════════════════

export const systemApi = {
    /**
     * Get branding info
     */
    async getBranding(): Promise<BrandingConfig> {
        // Use public endpoint or admin endpoint depending on availability
        try {
            return await fetchApi<BrandingConfig>('/admin/ai-identity')
        } catch {
            // Return default if not authorized
            return {
                displayName: 'AI Assistant',
                developerName: 'Developer',
                productFamily: 'AI Platform',
                shortIntro: 'Kişisel AI asistanınız',
                forbidProviderMention: false
            }
        }
    },

    /**
     * Get feature flags
     */
    async getFeatures(): Promise<Record<string, boolean>> {
        const result = await fetchApi<{ features: Record<string, boolean> }>('/system/features')
        return result.features
    },

    /**
     * Health check
     */
    async healthCheck(): Promise<{ status: string }> {
        return fetchApi<{ status: string }>('/health')
    },
}

// ═══════════════════════════════════════════════════════════════════════════
// IMAGE API
// ═══════════════════════════════════════════════════════════════════════════

interface UserImageOut {
    index: number
    image_url: string
    prompt: string
    created_at: string
    conversation_id?: string
}

export const imageApi = {
    /**
     * Get gallery images
     * Backend returns List[UserImageOut], we map to simple image URLs
     */
    async getGallery(): Promise<{ images: UserImageOut[] }> {
        const result = await fetchApi<UserImageOut[]>('/user/images')
        // Decode HTML entities in prompts and normalize URLs
        const decodedImages = result.map(img => ({
            ...img,
            image_url: normalizeImageUrl(img.image_url),
            prompt: img.prompt ? decodeHtmlEntities(img.prompt) : img.prompt
        }))
        return { images: decodedImages }
    },
}
