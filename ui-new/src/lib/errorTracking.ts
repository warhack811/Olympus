/**
 * Frontend Error Tracking Module
 * 
 * Sentry SDK'sını initialize eder ve global error handlers'ı ayarlar.
 * Tüm frontend hataları, API hataları ve network hatalarını otomatik olarak yakalar.
 * 
 * Gereksinimler:
 * - 2.1: Frontend hataları otomatik yakalama
 * - 2.2: API hata detaylarını log'a yazma
 * - 2.3: Network hatası detaylarını log'a yazma
 * - 2.4: Hata mesajı, stack trace ve browser bilgilerini içerme
 * - 2.5: Hataları merkezi sunucuya gönderme (Sentry)
 * - 2.6: Kullanıcı oturumu ve sayfa bilgilerini hata raporuna ekleme
 */

import * as Sentry from '@sentry/react'

/**
 * Sentry'yi initialize et
 * 
 * @param dsn - Sentry DSN (environment variable'dan alınır)
 * @param environment - Ortam (development, production, vb.)
 */
export function initializeSentry(dsn: string | undefined, environment: string = 'development'): void {
  // Eğer DSN yoksa, Sentry'yi initialize etme
  if (!dsn) {
    console.warn('[ErrorTracking] Sentry DSN not provided. Error tracking disabled.')
    return
  }

  Sentry.init({
    dsn,
    environment,
    // Performans izleme için tracing'i etkinleştir
    integrations: [
      new Sentry.Replay({
        // Hata durumunda session replay'i kaydet
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    // Performans izleme için sample rate'i ayarla
    tracesSampleRate: environment === 'production' ? 0.1 : 1.0,
    // Session replay için sample rate'i ayarla
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    // Hata raporlarında PII verilerini maskelemek için
    beforeSend(event, hint) {
      // Hassas bilgileri filtrele
      if (event.request) {
        // URL'deki query parameters'ı temizle
        if (event.request.url) {
          event.request.url = sanitizeUrl(event.request.url)
        }
      }

      // Breadcrumb'ları temizle
      if (event.breadcrumbs) {
        event.breadcrumbs = event.breadcrumbs.map(breadcrumb => {
          if (breadcrumb.data) {
            breadcrumb.data = sanitizeData(breadcrumb.data)
          }
          return breadcrumb
        })
      }

      return event
    },
  })

  console.log('[ErrorTracking] Sentry initialized successfully')
}

/**
 * Kullanıcı context'ini Sentry'ye ayarla
 * 
 * @param userId - Kullanıcı ID'si
 * @param username - Kullanıcı adı
 * @param email - Kullanıcı email'i (opsiyonel)
 */
export function setUserContext(userId: string, username: string, email?: string): void {
  Sentry.setUser({
    id: userId,
    username,
    email,
  })
}

/**
 * Kullanıcı context'ini temizle (logout sırasında)
 */
export function clearUserContext(): void {
  Sentry.setUser(null)
}

/**
 * Sayfa context'ini Sentry'ye ayarla
 * 
 * @param page - Sayfa adı
 * @param metadata - Ek metadata
 */
export function setPageContext(page: string, metadata?: Record<string, any>): void {
  Sentry.setContext('page', {
    name: page,
    ...metadata,
  })
}

/**
 * Global error handler'ı ayarla (window.onerror)
 * 
 * Requirement 2.1: Frontend hataları otomatik yakalama
 */
export function setupGlobalErrorHandler(): void {
  window.onerror = (message, source, lineno, colno, error) => {
    // Hata detaylarını Sentry'ye gönder
    Sentry.captureException(error || new Error(String(message)), {
      tags: {
        error_type: 'global_error',
      },
      contexts: {
        error_context: {
          message: String(message),
          source,
          lineno,
          colno,
        },
      },
    })

    // Hata'yı console'a da yaz
    console.error('[ErrorTracking] Global error caught:', {
      message,
      source,
      lineno,
      colno,
      error,
    })

    // true döndürerek error'ın default handler'ı tarafından işlenmesini engelle
    return true
  }
}

/**
 * Unhandled promise rejection handler'ı ayarla
 * 
 * Requirement 2.1: Frontend hataları otomatik yakalama
 */
export function setupUnhandledRejectionHandler(): void {
  window.addEventListener('unhandledrejection', (event) => {
    // Hata detaylarını Sentry'ye gönder
    Sentry.captureException(event.reason, {
      tags: {
        error_type: 'unhandled_rejection',
      },
    })

    // Hata'yı console'a da yaz
    console.error('[ErrorTracking] Unhandled promise rejection:', event.reason)

    // Event'i handle ettiğimizi belirt
    event.preventDefault()
  })
}

/**
 * API error'ını Sentry'ye gönder
 * 
 * Requirement 2.2: API hata detaylarını log'a yazma
 * Requirement 2.5: Hataları merkezi sunucuya gönderme
 * 
 * @param error - Hata nesnesi
 * @param context - API context (endpoint, method, status code, vb.)
 */
export function captureApiError(
  error: Error | string,
  context?: {
    endpoint?: string
    method?: string
    statusCode?: number
    responseData?: any
  }
): void {
  const errorObj = typeof error === 'string' ? new Error(error) : error

  Sentry.captureException(errorObj, {
    tags: {
      error_type: 'api_error',
      endpoint: context?.endpoint,
      method: context?.method,
      status_code: context?.statusCode,
    },
    contexts: {
      api_context: {
        endpoint: context?.endpoint,
        method: context?.method,
        statusCode: context?.statusCode,
        responseData: context?.responseData,
      },
    },
  })

  console.error('[ErrorTracking] API error captured:', {
    error: errorObj.message,
    context,
  })
}

/**
 * Network error'ını Sentry'ye gönder
 * 
 * Requirement 2.3: Network hatası detaylarını log'a yazma
 * Requirement 2.5: Hataları merkezi sunucuya gönderme
 * 
 * @param error - Hata nesnesi
 * @param context - Network context (URL, timeout, vb.)
 */
export function captureNetworkError(
  error: Error | string,
  context?: {
    url?: string
    timeout?: number
    type?: string
  }
): void {
  const errorObj = typeof error === 'string' ? new Error(error) : error

  Sentry.captureException(errorObj, {
    tags: {
      error_type: 'network_error',
      network_type: context?.type,
    },
    contexts: {
      network_context: {
        url: context?.url,
        timeout: context?.timeout,
        type: context?.type,
      },
    },
  })

  console.error('[ErrorTracking] Network error captured:', {
    error: errorObj.message,
    context,
  })
}

/**
 * Breadcrumb ekle (hata öncesi olayları takip etmek için)
 * 
 * @param message - Breadcrumb mesajı
 * @param category - Kategori (user-action, navigation, vb.)
 * @param level - Log seviyesi (info, warning, error)
 * @param data - Ek veri
 */
export function addBreadcrumb(
  message: string,
  category: string = 'user-action',
  level: 'info' | 'warning' | 'error' = 'info',
  data?: Record<string, any>
): void {
  Sentry.addBreadcrumb({
    message,
    category,
    level,
    data: data ? sanitizeData(data) : undefined,
  })
}

/**
 * URL'deki hassas bilgileri maskelemek için yardımcı fonksiyon
 * 
 * @param url - URL
 * @returns Maskelenmiş URL
 */
function sanitizeUrl(url: string): string {
  try {
    const urlObj = new URL(url)
    // Query parameters'ı temizle
    urlObj.search = ''
    return urlObj.toString()
  } catch {
    return url
  }
}

/**
 * Veri'deki hassas bilgileri maskelemek için yardımcı fonksiyon
 * 
 * @param data - Veri nesnesi
 * @returns Maskelenmiş veri
 */
function sanitizeData(data: Record<string, any>): Record<string, any> {
  const sensitiveKeys = ['password', 'token', 'secret', 'api_key', 'apiKey', 'authorization']
  const sanitized = { ...data }

  for (const key of sensitiveKeys) {
    if (key in sanitized) {
      sanitized[key] = '[REDACTED]'
    }
  }

  return sanitized
}

/**
 * Sentry'yi manuel olarak flush et (graceful shutdown için)
 * 
 * @param timeout - Timeout (ms)
 */
export async function flushSentry(timeout: number = 2000): Promise<boolean> {
  return Sentry.close(timeout)
}
