
import { useIsMobile } from '@/hooks'
import { useSettingsStore } from '@/stores'
import { ChatLayout } from '@/components/layout/ChatLayout'
import { BottomNav } from '@/components/common'
import { cn } from '@/lib/utils'

export function ChatPage() {
    const isMobile = useIsMobile()
    const openSettings = useSettingsStore((state) => state.openSettings)

    return (
        <div className="h-[100dvh] w-screen overflow-hidden bg-(--color-bg)">
            {/* Main Layout */}
            <div className="h-full">
                <ChatLayout />
            </div>

            {/* Mobile Bottom Navigation - Hidden as per request */}
            {/* {isMobile && (
                <BottomNav
                    onNewChat={() => { }}
                    onMemory={() => document.dispatchEvent(new CustomEvent('open-memory-manager'))}
                    onGallery={() => document.dispatchEvent(new CustomEvent('open-gallery'))}
                    onSettings={() => openSettings()}
                />
            )} */}
        </div>
    )
}
