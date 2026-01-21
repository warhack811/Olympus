/**
 * Frontend Analytics Module
 * 
 * Kullanıcı davranışını ve etkileşimlerini takip eder.
 * Event'leri backend'e gönderir.
 * 
 * Gereksinimler:
 * - 5.1: Login event'i ekle
 * - 5.2: Chat message event'i ekle
 * - 5.3: Image generation event'i ekle
 * - 5.4: Event'leri backend'e gönder
 * 
 * Kullanım:
 *   import { trackLogin, trackChatMessage, trackImageGenerated } from '@/lib/analytics'
 *   
 *   trackLogin(userId)
 *   trackChatMessage(userId, conversationId, messageLength)
 *   trackImageGenerated(userId, conversationId, model, promptLength)
 */

import { API_BASE } from '@/api/client'
import { addBreadcrumb, captureApiError } from '@/lib/errorTracking'

/**
 * Analytics event'i temsil eden interface
 */
interface AnalyticsEvent {
  event_type: string
  user_id: string | number
  timestamp: string
  data?: Record<string, any>
}

/**
 * Analytics tracker sınıfı
 * 
 * Event'leri batch halinde toplar ve backend'e gönderir.
 */
class AnalyticsTracker {
  private events: AnalyticsEvent[] = []
  private batchSize: number = 10
  private batchTimeout: number = 5 * 60 * 1000 // 5 dakika
  private flushTimer: NodeJS.Timeout | null = null
  private isEnabled: boolean = true

  constructor(batchSize: number = 10, batchTimeout: number = 5 * 60 * 1000) {
    this.batchSize = batchSize
    this.batchTimeout = batchTimeout
    
    // Sayfa kapatılırken pending event'leri flush et
    window.addEventListener('beforeunload', () => {
      this.flush()
    })
  }

  /**
   * Event'i track et
   * 
   * @param eventType - Event türü (login, chat_message, image_generated)
   * @param userId - Kullanıcı ID'si
   * @param data - Event verisi (opsiyonel)
   */
  trackEvent(
    eventType: string,
    userId: string | number,
    data?: Record<string, any>
  ): void {
    if (!this.isEnabled) {
      return
    }

    const event: AnalyticsEvent = {
      event_type: eventType,
      user_id: userId,
      timestamp: new Date().toISOString(),
      data: data || {},
    }

    this.events.push(event)

    // Breadcrumb ekle
    addBreadcrumb(
      `Analytics: ${eventType}`,
      'analytics',
      'info',
      { user_id: userId }
    )

    // Batch size'a ulaştıysa flush et
    if (this.events.length >= this.batchSize) {
      this.flush()
    } else {
      // Timer'ı reset et
      this.resetFlushTimer()
    }
  }

  /**
   * Flush timer'ı reset et
   */
  private resetFlushTimer(): void {
    // Eski timer'ı iptal et
    if (this.flushTimer) {
      clearTimeout(this.flushTimer)
    }

    // Yeni timer oluştur
    this.flushTimer = setTimeout(() => {
      this.flush()
    }, this.batchTimeout)
  }

  /**
   * Batch'i flush et (backend'e gönder)
   */
  async flush(): Promise<void> {
    if (this.events.length === 0) {
      return
    }

    const eventsToFlush = [...this.events]
    this.events = []

    // Timer'ı iptal et
    if (this.flushTimer) {
      clearTimeout(this.flushTimer)
      this.flushTimer = null
    }

    try {
      // Event'leri backend'e gönder
      const response = await fetch(`${API_BASE}/user/analytics/events`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          events: eventsToFlush,
        }),
      })

      if (!response.ok) {
        const error = new Error(`Analytics flush failed: ${response.status}`)
        captureApiError(error, {
          endpoint: '/user/analytics/events',
          method: 'POST',
          statusCode: response.status,
        })
        
        // Event'leri geri ekle (retry için)
        this.events.unshift(...eventsToFlush)
        return
      }

      addBreadcrumb(
        `Analytics: ${eventsToFlush.length} events flushed`,
        'analytics',
        'info'
      )
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error))
      captureApiError(err, {
        endpoint: '/user/analytics/events',
        method: 'POST',
      })
      
      // Event'leri geri ekle (retry için)
      this.events.unshift(...eventsToFlush)
    }
  }

  /**
   * Pending event'lerin sayısını döndür
   */
  getPendingEventsCount(): number {
    return this.events.length
  }

  /**
   * Analytics'i disable et
   */
  disable(): void {
    this.isEnabled = false
    this.flush()
  }

  /**
   * Analytics'i enable et
   */
  enable(): void {
    this.isEnabled = true
  }
}

// Global tracker instance
let tracker: AnalyticsTracker | null = null

/**
 * Global analytics tracker'ı döndür (Singleton)
 */
function getTracker(): AnalyticsTracker {
  if (!tracker) {
    tracker = new AnalyticsTracker()
  }
  return tracker
}

/**
 * Tracker'ı reset et (test'ler için)
 */
export function resetTracker(): void {
  if (tracker) {
    tracker.flush()
  }
  tracker = null
}

/**
 * Login event'ini track et
 * 
 * Requirement 5.1: Login event'i ekle
 * 
 * @param userId - Kullanıcı ID'si
 */
export function trackLogin(userId: string | number): void {
  const tracker = getTracker()
  tracker.trackEvent('login', userId, {
    timestamp: new Date().toISOString(),
  })
}

/**
 * Chat message event'ini track et
 * 
 * Requirement 5.2: Chat message event'i ekle
 * 
 * @param userId - Kullanıcı ID'si
 * @param conversationId - Sohbet ID'si
 * @param messageLength - Mesaj uzunluğu
 * @param hasImage - Resim içeriyor mu
 */
export function trackChatMessage(
  userId: string | number,
  conversationId: string | number,
  messageLength: number,
  hasImage: boolean = false
): void {
  const tracker = getTracker()
  tracker.trackEvent('message_sent', userId, {
    conversation_id: conversationId,
    message_length: messageLength,
    has_image: hasImage,
  })
}

/**
 * Image generation event'ini track et
 * 
 * Requirement 5.3: Image generation event'i ekle
 * 
 * @param userId - Kullanıcı ID'si
 * @param conversationId - Sohbet ID'si
 * @param model - Resim modeli (flux, vb.)
 * @param promptLength - Prompt uzunluğu
 */
export function trackImageGenerated(
  userId: string | number,
  conversationId: string | number,
  model: string,
  promptLength: number
): void {
  const tracker = getTracker()
  tracker.trackEvent('image_generated', userId, {
    conversation_id: conversationId,
    model,
    prompt_length: promptLength,
  })
}

/**
 * Chat start event'ini track et
 * 
 * @param userId - Kullanıcı ID'si
 * @param conversationId - Sohbet ID'si
 */
export function trackChatStart(
  userId: string | number,
  conversationId: string | number
): void {
  const tracker = getTracker()
  tracker.trackEvent('chat_start', userId, {
    conversation_id: conversationId,
  })
}

/**
 * Batch'i manuel olarak flush et
 * 
 * Requirement 5.4: Event'leri backend'e gönder
 */
export async function flushAnalytics(): Promise<void> {
  const tracker = getTracker()
  await tracker.flush()
}

/**
 * Pending event'lerin sayısını döndür
 */
export function getPendingEventsCount(): number {
  const tracker = getTracker()
  return tracker.getPendingEventsCount()
}

/**
 * Analytics'i disable et
 */
export function disableAnalytics(): void {
  const tracker = getTracker()
  tracker.disable()
}

/**
 * Analytics'i enable et
 */
export function enableAnalytics(): void {
  const tracker = getTracker()
  tracker.enable()
}

