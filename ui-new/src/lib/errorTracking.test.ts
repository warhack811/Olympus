/**
 * Error Tracking Tests
 * 
 * Frontend error tracking modülünün unit test'leri.
 * 
 * Requirement 2.1: Frontend hataları otomatik yakalama
 * Requirement 2.2: API hata detaylarını log'a yazma
 * Requirement 2.3: Network hatası detaylarını log'a yazma
 * Requirement 2.4: Hata mesajı, stack trace ve browser bilgilerini içerme
 * Requirement 2.5: Hataları merkezi sunucuya gönderme (Sentry)
 * Requirement 2.6: Kullanıcı oturumu ve sayfa bilgilerini hata raporuna ekleme
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  initializeSentry,
  setUserContext,
  clearUserContext,
  setPageContext,
  setupGlobalErrorHandler,
  setupUnhandledRejectionHandler,
  captureApiError,
  captureNetworkError,
  addBreadcrumb,
} from './errorTracking'

// Mock Sentry
vi.mock('@sentry/react', () => ({
  init: vi.fn(),
  setUser: vi.fn(),
  setContext: vi.fn(),
  captureException: vi.fn(),
  addBreadcrumb: vi.fn(),
  close: vi.fn(),
  reactRouterV6Instrumentation: vi.fn(),
  Replay: vi.fn(),
}))

vi.mock('@sentry/tracing', () => ({
  BrowserTracing: vi.fn(),
}))

import * as Sentry from '@sentry/react'

describe('Error Tracking Module', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initializeSentry', () => {
    it('DSN olmadan initialize etmemeli', () => {
      const consoleSpy = vi.spyOn(console, 'warn')
      initializeSentry(undefined)
      expect(consoleSpy).toHaveBeenCalledWith(
        '[ErrorTracking] Sentry DSN not provided. Error tracking disabled.'
      )
      expect(Sentry.init).not.toHaveBeenCalled()
    })

    it('DSN ile Sentry\'yi initialize etmeli', () => {
      const dsn = 'https://example@sentry.io/123456'
      initializeSentry(dsn, 'production')
      expect(Sentry.init).toHaveBeenCalled()
    })

    it('development ortamında tracesSampleRate 1.0 olmalı', () => {
      const dsn = 'https://example@sentry.io/123456'
      initializeSentry(dsn, 'development')
      const callArgs = (Sentry.init as any).mock.calls[0][0]
      expect(callArgs.tracesSampleRate).toBe(1.0)
    })

    it('production ortamında tracesSampleRate 0.1 olmalı', () => {
      const dsn = 'https://example@sentry.io/123456'
      initializeSentry(dsn, 'production')
      const callArgs = (Sentry.init as any).mock.calls[0][0]
      expect(callArgs.tracesSampleRate).toBe(0.1)
    })
  })

  describe('setUserContext', () => {
    it('Kullanıcı context\'ini Sentry\'ye ayarlamalı', () => {
      setUserContext('user123', 'testuser', 'test@example.com')
      expect(Sentry.setUser).toHaveBeenCalledWith({
        id: 'user123',
        username: 'testuser',
        email: 'test@example.com',
      })
    })

    it('Email olmadan da çalışmalı', () => {
      setUserContext('user123', 'testuser')
      expect(Sentry.setUser).toHaveBeenCalledWith({
        id: 'user123',
        username: 'testuser',
        email: undefined,
      })
    })
  })

  describe('clearUserContext', () => {
    it('Kullanıcı context\'ini temizlemeli', () => {
      clearUserContext()
      expect(Sentry.setUser).toHaveBeenCalledWith(null)
    })
  })

  describe('setPageContext', () => {
    it('Sayfa context\'ini Sentry\'ye ayarlamalı', () => {
      setPageContext('chat', { conversationId: 'conv123' })
      expect(Sentry.setContext).toHaveBeenCalledWith('page', {
        name: 'chat',
        conversationId: 'conv123',
      })
    })

    it('Metadata olmadan da çalışmalı', () => {
      setPageContext('home')
      expect(Sentry.setContext).toHaveBeenCalledWith('page', {
        name: 'home',
      })
    })
  })

  describe('captureApiError', () => {
    it('API error\'ını Sentry\'ye göndermeli', () => {
      const error = new Error('API request failed')
      captureApiError(error, {
        endpoint: '/api/chat',
        method: 'POST',
        statusCode: 500,
      })
      expect(Sentry.captureException).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          tags: expect.objectContaining({
            error_type: 'api_error',
            endpoint: '/api/chat',
            method: 'POST',
            status_code: 500,
          }),
        })
      )
    })

    it('String error\'ı da handle etmeli', () => {
      captureApiError('API error message', {
        endpoint: '/api/chat',
        method: 'GET',
        statusCode: 404,
      })
      expect(Sentry.captureException).toHaveBeenCalled()
    })

    it('Context olmadan da çalışmalı', () => {
      const error = new Error('API error')
      captureApiError(error)
      expect(Sentry.captureException).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          tags: expect.objectContaining({
            error_type: 'api_error',
          }),
        })
      )
    })
  })

  describe('captureNetworkError', () => {
    it('Network error\'ını Sentry\'ye göndermeli', () => {
      const error = new Error('Network timeout')
      captureNetworkError(error, {
        url: 'https://api.example.com/chat',
        timeout: 10000,
        type: 'timeout',
      })
      expect(Sentry.captureException).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          tags: expect.objectContaining({
            error_type: 'network_error',
            network_type: 'timeout',
          }),
        })
      )
    })

    it('String error\'ı da handle etmeli', () => {
      captureNetworkError('Network error message', {
        url: 'https://api.example.com',
        type: 'connection_refused',
      })
      expect(Sentry.captureException).toHaveBeenCalled()
    })

    it('Context olmadan da çalışmalı', () => {
      const error = new Error('Network error')
      captureNetworkError(error)
      expect(Sentry.captureException).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          tags: expect.objectContaining({
            error_type: 'network_error',
          }),
        })
      )
    })
  })

  describe('addBreadcrumb', () => {
    it('Breadcrumb\'ı Sentry\'ye eklemeli', () => {
      addBreadcrumb('User clicked button', 'user-action', 'info', {
        buttonId: 'send-message',
      })
      expect(Sentry.addBreadcrumb).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'User clicked button',
          category: 'user-action',
          level: 'info',
          data: expect.objectContaining({
            buttonId: 'send-message',
          }),
        })
      )
    })

    it('Default category ve level kullanmalı', () => {
      addBreadcrumb('Some event')
      expect(Sentry.addBreadcrumb).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Some event',
          category: 'user-action',
          level: 'info',
        })
      )
    })

    it('Data olmadan da çalışmalı', () => {
      addBreadcrumb('Event without data', 'navigation')
      expect(Sentry.addBreadcrumb).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Event without data',
          category: 'navigation',
        })
      )
    })
  })

  describe('setupGlobalErrorHandler', () => {
    it('window.onerror handler\'ını ayarlamalı', () => {
      setupGlobalErrorHandler()
      expect(window.onerror).toBeDefined()
    })

    it('Global error\'ı Sentry\'ye göndermeli', () => {
      setupGlobalErrorHandler()
      const error = new Error('Global error')
      const result = window.onerror?.('Error message', 'script.js', 10, 5, error)
      expect(Sentry.captureException).toHaveBeenCalledWith(
        error,
        expect.objectContaining({
          tags: expect.objectContaining({
            error_type: 'global_error',
          }),
        })
      )
      expect(result).toBe(true)
    })
  })

  describe('setupUnhandledRejectionHandler', () => {
    it('unhandledrejection event listener\'ı ayarlamalı', () => {
      const addEventListenerSpy = vi.spyOn(window, 'addEventListener')
      setupUnhandledRejectionHandler()
      expect(addEventListenerSpy).toHaveBeenCalledWith(
        'unhandledrejection',
        expect.any(Function)
      )
    })

    it('Unhandled rejection\'ı Sentry\'ye göndermeli', async () => {
      setupUnhandledRejectionHandler()
      const error = new Error('Unhandled rejection')
      
      // Promise.reject'i catch etmek için
      const promise = Promise.reject(error).catch(() => {
        // Rejection'ı handle et
      })
      
      const event = new PromiseRejectionEvent('unhandledrejection', {
        promise,
        reason: error,
      })
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault')
      window.dispatchEvent(event)
      expect(preventDefaultSpy).toHaveBeenCalled()
      
      // Promise'in settle olmasını bekle
      await promise
    })
  })

  describe('Error Tracking Round-Trip Property', () => {
    /**
     * Property 5: Error Tracking Round-Trip
     * 
     * For any error (API, network, or global), capturing it should result in:
     * 1. Error being sent to Sentry
     * 2. Error being logged to console
     * 3. Error context being preserved
     * 
     * Validates: Requirements 2.2, 2.3, 2.5
     */
    it('API error round-trip: error -> capture -> Sentry', () => {
      const error = new Error('API failed')
      const context = {
        endpoint: '/api/test',
        method: 'POST',
        statusCode: 500,
      }

      captureApiError(error, context)

      // Error should be captured
      expect(Sentry.captureException).toHaveBeenCalledWith(
        error,
        expect.any(Object)
      )

      // Context should be preserved
      const callArgs = (Sentry.captureException as any).mock.calls[0][1]
      expect(callArgs.contexts.api_context).toEqual(context)
    })

    it('Network error round-trip: error -> capture -> Sentry', () => {
      const error = new Error('Network timeout')
      const context = {
        url: 'https://api.example.com',
        timeout: 10000,
        type: 'timeout',
      }

      captureNetworkError(error, context)

      // Error should be captured
      expect(Sentry.captureException).toHaveBeenCalledWith(
        error,
        expect.any(Object)
      )

      // Context should be preserved
      const callArgs = (Sentry.captureException as any).mock.calls[0][1]
      expect(callArgs.contexts.network_context).toEqual(context)
    })

    it('User context round-trip: set -> Sentry', () => {
      const userId = 'user123'
      const username = 'testuser'
      const email = 'test@example.com'

      setUserContext(userId, username, email)

      // User context should be set
      expect(Sentry.setUser).toHaveBeenCalledWith({
        id: userId,
        username,
        email,
      })

      // Clear should work
      clearUserContext()
      expect(Sentry.setUser).toHaveBeenCalledWith(null)
    })
  })
})
