
import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { initializeTheme } from '@/stores'
import { useWebSocket, usePreferences, useMobileKeyboard, useAuth } from '@/hooks'
import { SettingsSheet, FullPageLoader } from '@/components/common'
import { Suspense } from 'react'


export function RootLayout() {
    // Initialize theme on mount
    useEffect(() => {
        initializeTheme()
    }, [])

    // Global Hooks
    const { isAuthenticated, isLoading } = useAuth() // Hydrate user state
    useWebSocket()
    usePreferences()
    useMobileKeyboard()

    // Protected Route Logic
    useEffect(() => {
        const isPublicPage = window.location.pathname === '/login' || window.location.pathname === '/register'

        if (!isLoading && !isAuthenticated && !isPublicPage) {
            window.location.href = '/login'
        }
    }, [isLoading, isAuthenticated])

    return (
        <div className="antialiased text-(--color-text-primary)">
            <Suspense fallback={<FullPageLoader />}>
                <Outlet />
            </Suspense>

            {/* Global Components */}
            <SettingsSheet />
            {/* ToastProvider is wrapping App, so Toaster logic is inside common components probably */}
        </div>
    )
}
