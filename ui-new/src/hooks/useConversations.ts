/**
 * useConversations Hook
 * 
 * Konuşma geçmişini API'den yükler ve yönetir
 */

import { useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { chatApi } from '@/api'
import { useChatStore } from '@/stores'

export function useConversations() {
    const setConversations = useChatStore((state) => state.setConversations)
    const setLoadingHistory = useChatStore((state) => state.setLoadingHistory)
    const setInitialLoad = useChatStore((state) => state.setInitialLoad)

    // API'den konuşmaları yükle
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['conversations'],
        queryFn: async () => {
            const conversations = await chatApi.getConversations()
            return conversations
        },
        staleTime: 1000 * 60 * 5, // 5 dakika
    })

    // Veri değiştiğinde store'u güncelle
    useEffect(() => {
        if (data) {
            setConversations(data)
        }
    }, [data, setConversations])

    // Yükleme durumunu takip et
    useEffect(() => {
        setLoadingHistory(isLoading)
    }, [isLoading, setLoadingHistory])

    // İlk yükleme tamamlandığında işaretle
    useEffect(() => {
        if (!isLoading && data) {
            setInitialLoad(false)
        }
    }, [isLoading, data, setInitialLoad])

    // Hata yönetimi: Hata oluşursa log yaz
    useEffect(() => {
        if (error) {
            console.error('[useConversations] Konuşmalar yüklenirken hata:', error)
        }
    }, [error])

    // Manuel yenileme
    const refreshConversations = useCallback(() => {
        refetch()
    }, [refetch])

    // Yeniden deneme mekanizması
    const retryLoad = useCallback(() => {
        console.log('[useConversations] Yeniden deneniyor...')
        refetch()
    }, [refetch])

    return {
        conversations: data || [],
        isLoading,
        error,
        refresh: refreshConversations,
        retry: retryLoad  // Yeniden deneme metodu
    }
}
