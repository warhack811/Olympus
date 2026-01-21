import { useState, useEffect } from 'react'
import { FileText, Trash2, Upload, AlertCircle, Loader2, Check } from 'lucide-react'
import { documentApi } from '@/api'
import { Button } from '@/components/ui'
import { cn } from '@/lib/utils'
import type { Document } from '@/types'

export function DocumentsTab() {
    const [documents, setDocuments] = useState<Document[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [uploading, setUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Fetch documents on mount
    useEffect(() => {
        loadDocuments()
    }, [])

    const loadDocuments = async () => {
        try {
            setIsLoading(true)
            const docs = await documentApi.getDocuments()
            setDocuments(docs)
            setError(null)
        } catch (err) {
            console.error('Failed to load documents:', err)
            setError('Dokümanlar yüklenirken bir hata oluştu.')
        } finally {
            setIsLoading(false)
        }
    }

    const handleDelete = async (filename: string) => {
        if (!window.confirm(`${filename} dosyasını silmek istediğinize emin misiniz?`)) return

        try {
            // Optimistic update
            setDocuments(prev => prev.filter(d => d.filename !== filename))

            await documentApi.deleteDocument(filename)
        } catch (err) {
            console.error('Delete failed:', err)
            // Rollback on error
            loadDocuments()
            alert('Silme işlemi başarısız oldu.')
        }
    }

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setUploading(true)
        try {
            await documentApi.uploadDocument(file) // No conversation ID needed for global/user upload
            await loadDocuments() // Refresh list
        } catch (err) {
            console.error('Upload failed:', err)
            alert('Yükleme başarısız oldu.')
        } finally {
            setUploading(false)
            // Reset input
            e.target.value = ''
        }
    }

    return (
        <div className="space-y-4">
            {/* Header / Actions */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-(--color-bg) border border-(--color-border)">
                <div>
                    <h3 className="font-medium flex items-center gap-2">
                        <FileText className="h-5 w-5 text-(--color-primary)" />
                        Dokümanlarınız
                    </h3>
                    <p className="text-sm text-(--color-text-muted)">
                        Yapay zekanın bildiği kişisel dokümanlarınız.
                    </p>
                </div>

                <div className="relative">
                    <input
                        type="file"
                        accept=".pdf,.txt"
                        onChange={handleUpload}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        disabled={uploading}
                    />
                    <Button variant="outline" size="sm" disabled={uploading} className="bg-(--color-bg-surface) hover:bg-(--color-bg-surface-hover) text-(--color-text)">
                        {uploading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Upload className="h-4 w-4 mr-2" />
                        )}
                        {uploading ? 'Yükleniyor...' : 'Yeni Yükle'}
                    </Button>
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="p-3 rounded-lg bg-(--color-error-soft) text-(--color-error) text-sm flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    {error}
                </div>
            )}

            {/* List */}
            <div className="space-y-2">
                {isLoading ? (
                    <div className="text-center py-8 text-(--color-text-muted)">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                        Yükleniyor...
                    </div>
                ) : documents.length === 0 ? (
                    <div className="text-center py-8 text-(--color-text-muted) border-2 border-dashed border-(--color-border) rounded-xl">
                        <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
                        <p>Henüz yüklenmiş belge yok.</p>
                        <p className="text-xs mt-1">PDF veya TXT yükleyerek başlayın.</p>
                    </div>
                ) : (
                    documents.map(doc => (
                        <div
                            key={doc.filename}
                            className="group flex items-center justify-between p-3 rounded-xl border border-(--color-border) bg-(--color-bg-surface) hover:border-(--color-primary)/50 transition-colors"
                        >
                            <div className="flex items-center gap-3 overflow-hidden">
                                <div className="p-2 rounded-lg bg-(--color-bg) text-(--color-primary)">
                                    <FileText className="h-5 w-5" />
                                </div>
                                <div className="min-w-0">
                                    <div className="font-medium truncate">{doc.filename}</div>
                                    <div className="text-xs text-(--color-text-muted) flex items-center gap-2">
                                        <span>{doc.chunk_count} parça</span>
                                        <span>•</span>
                                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={() => handleDelete(doc.filename)}
                                className="p-2 rounded-lg text-(--color-text-muted) hover:text-(--color-error) hover:bg-(--color-error-soft) transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                                title="Sil"
                            >
                                <Trash2 className="h-4 w-4" />
                            </button>
                        </div>
                    ))
                )}
            </div>

            <div className="text-xs text-(--color-text-muted) p-3 rounded-lg bg-(--color-info-soft)">
                💡 Belgeleri silip tekrar yükleyerek Mami AI'ın yeni "Büyüteç" özelliğini (Geniş Okuma) aktif edebilirsiniz.
            </div>
        </div>
    )
}
