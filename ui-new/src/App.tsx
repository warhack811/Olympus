/**
 * Main App Component
 * 
 * Root component with providers and layout
 * Note: Auth is handled by backend - /new-ui redirects if not logged in
 */

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

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <BrowserRouter basename="/new-ui">
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
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
