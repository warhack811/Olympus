/**
 * Frontend Analytics Integration Tests
 * 
 * Frontend analytics modülünün integration test'leri.
 * 
 * Requirement 5.1: Login event'i ekle
 * Requirement 5.2: Chat message event'i ekle
 * Requirement 5.3: Image generation event'i ekle
 * Requirement 5.4: Event'leri backend'e gönder
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import {
  trackLogin,
  trackChatMessage,
  trackImageGenerated,
  trackChatStart,
  flushAnalytics,
  getPendingEventsCount,
  disableAnalytics,
  enableAnalytics,
  resetTracker,
} from '@/lib/analytics'
import * as errorTracking from '@/lib/errorTracking'

// Mock errorTracking modülü
vi.mock('@/lib/errorTracking', () => ({
  addBreadcrumb: vi.fn(),
  captureApiError: vi.fn(),
}))

// Mock fetch
global.fetch = vi.fn()

describe('Frontend Analytics Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as any).mockClear()
    resetTracker()
  })

  afterEach(() => {
    vi.clearAllMocks()
    resetTracker()
  })

  describe('Event Tracking Functions', () => {
    /**
     * Test login event'inin track edildiği
     * 
     * Requirement 5.1: Login event'i ekle
     */
    it('should track login event', () => {
      trackLogin(123)

      // Breadcrumb eklenmiş olmalı
      expect(errorTracking.addBreadcrumb).toHaveBeenCalledWith(
        'Analytics: login',
        'analytics',
        'info',
        expect.objectContaining({ user_id: 123 })
      )

      // Pending event sayısı 1 olmalı
      expect(getPendingEventsCount()).toBe(1)
    })

    /**
     * Test chat message event'inin track edildiği
     * 
     * Requirement 5.2: Chat message event'i ekle
     */
    it('should track chat message event', () => {
      trackChatMessage(123, 456, 100, false)

      // Breadcrumb eklenmiş olmalı
      expect(errorTracking.addBreadcrumb).toHaveBeenCalledWith(
        'Analytics: message_sent',
        'analytics',
        'info',
        expect.objectContaining({ user_id: 123 })
      )

      // Pending event sayısı 1 olmalı
      expect(getPendingEventsCount()).toBe(1)
    })

    /**
     * Test image generation event'inin track edildiği
     * 
     * Requirement 5.3: Image generation event'i ekle
     */
    it('should track image generation event', () => {
      trackImageGenerated(123, 456, 'flux', 50)

      // Breadcrumb eklenmiş olmalı
      expect(errorTracking.addBreadcrumb).toHaveBeenCalledWith(
        'Analytics: image_generated',
        'analytics',
        'info',
        expect.objectContaining({ user_id: 123 })
      )

      // Pending event sayısı 1 olmalı
      expect(getPendingEventsCount()).toBe(1)
    })

    /**
     * Test chat start event'inin track edildiği
     */
    it('should track chat start event', () => {
      trackChatStart(123, 456)

      // Breadcrumb eklenmiş olmalı
      expect(errorTracking.addBreadcrumb).toHaveBeenCalledWith(
        'Analytics: chat_start',
        'analytics',
        'info',
        expect.objectContaining({ user_id: 123 })
      )

      // Pending event sayısı 1 olmalı
      expect(getPendingEventsCount()).toBe(1)
    })
  })

  describe('Event Flushing', () => {
    /**
     * Test event'lerin backend'e gönderildiği
     * 
     * Requirement 5.4: Event'leri backend'e gönder
     */
    it('should send events to backend on flush', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      // Event'leri track et
      trackLogin(123)
      trackChatMessage(123, 456, 100, false)

      // Pending event sayısı 2 olmalı
      expect(getPendingEventsCount()).toBe(2)

      // Flush et
      await flushAnalytics()

      // Fetch çağrılmalı
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/user/analytics/events'),
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      )

      // Pending event sayısı 0 olmalı
      expect(getPendingEventsCount()).toBe(0)
    })

    /**
     * Test flush başarısız olduğunda event'lerin geri eklenmesi
     */
    it('should re-add events if flush fails', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      // Event'leri track et
      trackLogin(123)
      trackChatMessage(123, 456, 100, false)

      // Pending event sayısı 2 olmalı
      expect(getPendingEventsCount()).toBe(2)

      // Flush et
      await flushAnalytics()

      // Error capture edilmiş olmalı
      expect(errorTracking.captureApiError).toHaveBeenCalled()

      // Pending event sayısı 2 olmalı (geri eklendi)
      expect(getPendingEventsCount()).toBe(2)
    })

    /**
     * Test network error sırasında event'lerin geri eklenmesi
     */
    it('should re-add events if network error occurs', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('Network error'))

      // Event'leri track et
      trackLogin(123)

      // Pending event sayısı 1 olmalı
      expect(getPendingEventsCount()).toBe(1)

      // Flush et
      await flushAnalytics()

      // Error capture edilmiş olmalı
      expect(errorTracking.captureApiError).toHaveBeenCalled()

      // Pending event sayısı 1 olmalı (geri eklendi)
      expect(getPendingEventsCount()).toBe(1)
    })
  })

  describe('Event Completeness Property', () => {
    /**
     * Property 3: Event Completeness
     * 
     * Tüm event'ler user_id, timestamp ve event_type içermeli.
     * Farklı event türleri ve veri kombinasyonları için test et.
     * 
     * Validates: Requirements 5.1, 5.2, 5.3, 5.4
     * 
     * Feature: logging-monitoring-system, Property 3: Event Completeness
     */
    it('should track all event types with complete data', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      // Farklı event türleri track et
      trackLogin(123)
      trackChatStart(123, 456)
      trackChatMessage(123, 456, 100, false)
      trackImageGenerated(123, 456, 'flux', 50)

      // Pending event sayısı 4 olmalı
      expect(getPendingEventsCount()).toBe(4)

      // Flush et
      await flushAnalytics()

      // Fetch çağrılmalı
      expect(global.fetch).toHaveBeenCalled()

      // Fetch call'ının body'sini kontrol et
      const fetchCall = (global.fetch as any).mock.calls[0]
      const requestBody = JSON.parse(fetchCall[1].body)

      // Events array'i var olmalı
      expect(requestBody.events).toBeDefined()
      expect(Array.isArray(requestBody.events)).toBe(true)
      expect(requestBody.events.length).toBe(4)

      // Her event'in gerekli alanları olmalı
      for (const event of requestBody.events) {
        expect(event.event_type).toBeDefined()
        expect(event.user_id).toBeDefined()
        expect(event.timestamp).toBeDefined()
        expect(event.data).toBeDefined()
        expect(typeof event.data).toBe('object')

        // Timestamp ISO 8601 formatında olmalı
        expect(event.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/)
      }

      // Event türleri doğru olmalı
      const eventTypes = requestBody.events.map((e: any) => e.event_type)
      expect(eventTypes).toContain('login')
      expect(eventTypes).toContain('chat_start')
      expect(eventTypes).toContain('message_sent')
      expect(eventTypes).toContain('image_generated')

      // Pending event sayısı 0 olmalı
      expect(getPendingEventsCount()).toBe(0)
    })

    /**
     * Test event data'sının doğru şekilde kaydedildiği
     */
    it('should preserve event data correctly', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      // Event'leri track et
      trackChatMessage(123, 456, 150, true)
      trackImageGenerated(123, 456, 'flux', 75)

      // Flush et
      await flushAnalytics()

      // Fetch call'ının body'sini kontrol et
      const fetchCall = (global.fetch as any).mock.calls[0]
      const requestBody = JSON.parse(fetchCall[1].body)

      // Chat message event'i kontrol et
      const chatEvent = requestBody.events.find((e: any) => e.event_type === 'message_sent')
      expect(chatEvent).toBeDefined()
      expect(chatEvent.data.conversation_id).toBe(456)
      expect(chatEvent.data.message_length).toBe(150)
      expect(chatEvent.data.has_image).toBe(true)

      // Image event'i kontrol et
      const imageEvent = requestBody.events.find((e: any) => e.event_type === 'image_generated')
      expect(imageEvent).toBeDefined()
      expect(imageEvent.data.conversation_id).toBe(456)
      expect(imageEvent.data.model).toBe('flux')
      expect(imageEvent.data.prompt_length).toBe(75)
    })
  })

  describe('Analytics Control', () => {
    /**
     * Test analytics'in disable edilmesi
     */
    it('should not track events when disabled', () => {
      disableAnalytics()

      trackLogin(123)

      // Pending event sayısı 0 olmalı (track edilmedi)
      expect(getPendingEventsCount()).toBe(0)

      // Analytics'i tekrar enable et
      enableAnalytics()
    })

    /**
     * Test analytics'in enable edilmesi
     */
    it('should track events when enabled', () => {
      enableAnalytics()

      trackLogin(123)

      // Pending event sayısı 1 olmalı
      expect(getPendingEventsCount()).toBe(1)
    })
  })

  describe('Integration with API Client', () => {
    /**
     * Test analytics modülünün API client'ı kullandığı
     * 
     * Requirement 5.4: Event'leri backend'e gönder
     */
    it('should use correct API endpoint for analytics', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      trackLogin(123)
      await flushAnalytics()

      // Fetch çağrılmalı
      expect(global.fetch).toHaveBeenCalled()

      // Endpoint doğru olmalı
      const fetchCall = (global.fetch as any).mock.calls[0]
      const url = fetchCall[0]
      expect(url).toContain('/user/analytics/events')
    })

    /**
     * Test analytics'in error tracking'i entegre ettiği
     */
    it('should integrate with error tracking on API error', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      trackLogin(123)
      await flushAnalytics()

      // Error capture edilmiş olmalı
      expect(errorTracking.captureApiError).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          endpoint: '/user/analytics/events',
          method: 'POST',
          statusCode: 500,
        })
      )
    })

    /**
     * Test analytics'in breadcrumb'ları kaydedip kaydedmediği
     */
    it('should record breadcrumbs for analytics events', () => {
      trackLogin(123)
      trackChatMessage(123, 456, 100, false)

      // Breadcrumb'lar kaydedilmiş olmalı
      expect(errorTracking.addBreadcrumb).toHaveBeenCalledTimes(2)

      // İlk breadcrumb login event'i için
      expect(errorTracking.addBreadcrumb).toHaveBeenNthCalledWith(
        1,
        'Analytics: login',
        'analytics',
        'info',
        expect.any(Object)
      )

      // İkinci breadcrumb chat message event'i için
      expect(errorTracking.addBreadcrumb).toHaveBeenNthCalledWith(
        2,
        'Analytics: message_sent',
        'analytics',
        'info',
        expect.any(Object)
      )
    })
  })
})

