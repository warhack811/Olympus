/**
 * FAZE 3: Queue Position Updates Hook
 * 
 * Handles dynamic queue position recalculation and real-time UI updates.
 * Listens for WebSocket position change events and updates store.
 */

import { useEffect, useCallback } from 'react'
import { useImageJobsStore } from '@/stores/imageJobsStore'
import type { ImageJob } from '@/types'

interface QueuePositionUpdate {
    jobId: string
    newPosition: number
    conversationId: string
}

export function useQueuePositionUpdates() {
    const updateJob = useImageJobsStore((state) => state.updateJob)
    const jobs = useImageJobsStore((state) => state.jobs)

    // Handle position update from WebSocket
    const handlePositionUpdate = useCallback((update: QueuePositionUpdate) => {
        const job = jobs[update.jobId]
        if (!job) return

        // Only update if position actually changed
        if (job.queuePosition !== update.newPosition) {
            console.log(
                '[QueuePositionUpdates] Position changed:',
                update.jobId.slice(0, 8),
                `${job.queuePosition} → ${update.newPosition}`
            )

            updateJob({
                id: update.jobId,
                queuePosition: update.newPosition,
            })
        }
    }, [jobs, updateJob])

    // Listen for position update events from WebSocket
    useEffect(() => {
        const handleWebSocketMessage = (event: Event) => {
            const customEvent = event as CustomEvent
            const data = customEvent.detail

            if (data?.type === 'queue_position_update') {
                handlePositionUpdate({
                    jobId: data.jobId,
                    newPosition: data.newPosition,
                    conversationId: data.conversationId,
                })
            }
        }

        window.addEventListener('queue-position-update', handleWebSocketMessage)

        return () => {
            window.removeEventListener('queue-position-update', handleWebSocketMessage)
        }
    }, [handlePositionUpdate])

    // Recalculate positions for conversation when job completes
    const recalculatePositions = useCallback((conversationId: string) => {
        const allJobs = Object.values(jobs)
        const conversationJobs = allJobs.filter(
            (job) => job.conversationId === conversationId && job.status === 'queued'
        )

        // Sort by creation time
        conversationJobs.sort(
            (a, b) =>
                new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
        )

        // Update positions
        conversationJobs.forEach((job, index) => {
            const newPosition = index + 1
            if (job.queuePosition !== newPosition) {
                console.log(
                    '[QueuePositionUpdates] Recalculated position:',
                    job.id.slice(0, 8),
                    `${job.queuePosition} → ${newPosition}`
                )

                updateJob({
                    id: job.id,
                    queuePosition: newPosition,
                })
            }
        })
    }, [jobs, updateJob])

    return {
        handlePositionUpdate,
        recalculatePositions,
    }
}
