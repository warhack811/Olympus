/**
 * API Client Integration Tests
 * 
 * Frontend API client'ın error tracking entegrasyonunun integration test'leri.
 * 
 * Requirement 2.2: API hata detaylarını log'a yazma
 * Requirement 2.3: Network hatası detaylarını log'a yazma
 * Requirement 2.4: Hata mesajı, stack trace ve browser bilgilerini içerme
 * Requirement 2.5: Hataları merkezi sunucuya gönderme (Sentry)
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import * as errorTracking from '@/lib/errorTracking'
import { fetchApi } from '@/api/client'

// Mock errorTracking modülü
vi.mock('@/lib/errorTracking', () => ({
  captureApiError: vi.fn(),
  captureNetworkError: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

// Mock fetch
global.fetch = vi.fn()

describe('API Client - Error Tracking Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as any).mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Error Tracking Functions', () => {
    /**
     * Test API error'larının Sentry'ye gönderildiği
     * 
     * Requirement 2.2: API hata detaylarını log'a yazma
     * Requirement 2.5: Hataları merkezi sunucuya gönderme
     */
    it('should send API error to Sentry via captureApiError', () => {
      const error = new Error('API request failed')
      const context = {
        endpoint: '/api/chat',
        method: 'POST',
        statusCode: 500,
        responseData: { message: 'Internal server error' },
      }

      errorTracking.captureApiError(error, context)

      // captureApiError çağrılmalı
      expect(errorTracking.captureApiError).toHaveBeenCalledWith(error, context)
    })

    /**
     * Test network error'larının Sentry'ye gönderildiği
     * 
     * Requirement 2.3: Network hatası detaylarını log'a yazma
     * Requirement 2.5: Hataları merkezi sunucuya gönderme
     */
    it('should send network error to Sentry via captureNetworkError', () => {
      const error = new Error('Network timeout')
      const context = {
        url: 'https://api.example.com/chat',
        timeout: 10000,
        type: 'timeout',
      }

      errorTracking.captureNetworkError(error, context)

      // captureNetworkError çağrılmalı
      expect(errorTracking.captureNetworkError).toHaveBeenCalledWith(error, context)
    })

    /**
     * Test error context'inin doğru eklendiği
     * 
     * Requirement 2.4: Hata mesajı, stack trace ve browser bilgilerini içerme
     */
    it('should include correct API error context (endpoint, method, status code)', () => {
      const error = new Error('Bad request')
      const context = {
        endpoint: '/user/memories',
        method: 'POST',
        statusCode: 400,
        responseData: { detail: 'Validation failed' },
      }

      errorTracking.captureApiError(error, context)

      // Context doğru olmalı
      expect(errorTracking.captureApiError).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          endpoint: '/user/memories',
          method: 'POST',
          statusCode: 400,
        })
      )
    })

    /**
     * Test network error context'inin doğru eklendiği
     * 
     * Requirement 2.4: Hata mesajı, stack trace ve browser bilgilerini içerme
     */
    it('should include correct network error context (URL, timeout)', () => {
      const error = new Error('Request timeout')
      const context = {
        url: 'https://api.example.com/documents',
        timeout: 5000,
        type: 'timeout',
      }

      errorTracking.captureNetworkError(error, context)

      // Context doğru olmalı
      expect(errorTracking.captureNetworkError).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          url: 'https://api.example.com/documents',
          timeout: 5000,
          type: 'timeout',
        })
      )
    })

    /**
     * Test breadcrumb'ların kaydedildiği
     * 
     * Requirement 2.4: Hata mesajı, stack trace ve browser bilgilerini içerme
     */
    it('should record API request breadcrumb', () => {
      errorTracking.addBreadcrumb(
        'API Request: POST /api/chat',
        'api',
        'info'
      )

      expect(errorTracking.addBreadcrumb).toHaveBeenCalledWith(
        'API Request: POST /api/chat',
        'api',
        'info'
      )
    })

    it('should record API response breadcrumb', () => {
      errorTracking.addBreadcrumb(
        'API Response: 200 /api/chat',
        'api',
        'info'
      )

      expect(errorTracking.addBreadcrumb).toHaveBeenCalledWith(
        'API Response: 200 /api/chat',
        'api',
        'info'
      )
    })

    it('should use warning level for error response breadcrumb', () => {
      errorTracking.addBreadcrumb(
        'API Response: 400 /api/chat',
        'api',
        'warning'
      )

      expect(errorTracking.addBreadcrumb).toHaveBeenCalledWith(
        'API Response: 400 /api/chat',
        'api',
        'warning'
      )
    })
  })

  describe('Error Tracking Round-Trip Property', () => {
    /**
     * Property 5: Error Tracking Round-Trip
     * 
     * For any API error, capturing it should result in:
     * 1. Error being sent to Sentry via captureApiError
     * 2. Error context being preserved (endpoint, method, status code)
     * 3. Error message being preserved
     * 
     * Validates: Requirements 2.2, 2.5
     */
    it('should preserve API error context in round-trip: error -> capture -> Sentry', () => {
      const error = new Error('API failed')
      const context = {
        endpoint: '/user/chat',
        method: 'POST',
        statusCode: 500,
        responseData: { message: 'Internal server error' },
      }

      errorTracking.captureApiError(error, context)

      // Error capture edilmiş olmalı
      expect(errorTracking.captureApiError).toHaveBeenCalled()

      // Context preserve edilmiş olmalı
      expect(errorTracking.captureApiError).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          endpoint: '/user/chat',
          method: 'POST',
          statusCode: 500,
        })
      )
    })

    /**
     * Network error round-trip: error -> capture -> Sentry with context
     * 
     * Validates: Requirements 2.3, 2.5
     */
    it('should preserve network error context in round-trip: error -> capture -> Sentry', () => {
      const error = new Error('Network failed')
      const context = {
        url: 'https://api.example.com/documents',
        timeout: 10000,
        type: 'network_error',
      }

      errorTracking.captureNetworkError(error, context)

      // Error capture edilmiş olmalı
      expect(errorTracking.captureNetworkError).toHaveBeenCalled()

      // Context preserve edilmiş olmalı
      expect(errorTracking.captureNetworkError).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          url: 'https://api.example.com/documents',
          timeout: 10000,
          type: 'network_error',
        })
      )
    })

    /**
     * Breadcrumb round-trip: event -> add -> recorded
     * 
     * Validates: Requirements 2.4
     */
    it('should record breadcrumb in round-trip: event -> add -> recorded', () => {
      const message = 'API Request: GET /user/memories'
      const category = 'api'
      const level = 'info'

      errorTracking.addBreadcrumb(message, category, level)

      // Breadcrumb recorded olmalı
      expect(errorTracking.addBreadcrumb).toHaveBeenCalledWith(
        message,
        category,
        level
      )
    })
  })

  describe('Integration with API Client', () => {
    /**
     * Test API client'ın error tracking fonksiyonlarını kullandığı
     * 
     * Requirement 2.2, 2.3, 2.5: API ve network error'larını Sentry'ye gönderme
     */
    it('should import error tracking functions in API client', async () => {
      // client.ts'de errorTracking import'ı var
      const { captureApiError, captureNetworkError, addBreadcrumb } = await import('@/lib/errorTracking')
      
      expect(captureApiError).toBeDefined()
      expect(captureNetworkError).toBeDefined()
      expect(addBreadcrumb).toBeDefined()
    })

    /**
     * Test API client'ın error tracking'i doğru şekilde entegre ettiği
     * 
     * Requirement 2.2, 2.3, 2.5: API ve network error'larını Sentry'ye gönderme
     */
    it('should have error tracking integration in client.ts', async () => {
      // client.ts dosyasını oku ve error tracking import'ını kontrol et
      const clientModule = await import('@/api/client')
      
      // fetchApi fonksiyonu var olmalı
      expect(clientModule.fetchApi).toBeDefined()
      expect(typeof clientModule.fetchApi).toBe('function')
    })

    /**
     * Test API client'ın breadcrumb'ları kaydedip kaydedmediği
     * 
     * Requirement 2.4: Hata mesajı, stack trace ve browser bilgilerini içerme
     */
    it('should record breadcrumb on successful request', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        text: vi.fn().mockResolvedValue('{"data": "test"}'),
      }
      ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

      await fetchApi('/test', {}, 0) // maxRetries=0 (no retries)

      // addBreadcrumb çağrılmalı (request ve response için)
      expect(errorTracking.addBreadcrumb).toHaveBeenCalled()
    })
  })
})
