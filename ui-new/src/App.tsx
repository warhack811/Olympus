/**
 * Main App Component
 * 
 * Root component with providers and layout
 * Note: Auth is handled by backend
 */

import { Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import {
  ToastProvider,
  ErrorBoundary,
} from '@/components/common'

// Layouts & Pages
import { RootLayout } from '@/components/layout/RootLayout'
import { ChatPage } from '@/pages/chat/ChatPage'
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'
import { AdminPage } from '@/pages/admin/AdminPage'
import { DesignLabPage } from '@/pages/DesignLabPage'

// Create Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Simple Loading Component
const LoadingScreen = () => (
  <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
    <div className="flex flex-col items-center gap-4">
      <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      <div>Sistem Yükleniyor...</div>
    </div>
  </div>
)

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          {/* FIX: Set basename to "/" to match Vercel root deployment */}
          <BrowserRouter
            basename="/"
            future={{
              v7_startTransition: true,
              v7_relativeSplatPath: true,
            }}
          >
            <Suspense fallback={<LoadingScreen />}>
              <Routes>
                <Route element={<RootLayout />}>
                  <Route path="/" element={<ChatPage />} />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route path="/admin/*" element={<AdminPage />} />
                  <Route path="/design-lab" element={<DesignLabPage />} />

                  {/* Catch all redirect to chat */}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </Suspense>
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
