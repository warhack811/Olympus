
import React, { useEffect, useState } from 'react';
import { API_DOMAIN } from '@/api/client';

import { Card } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import { Badge } from '@/components/ui/Badge';
import { AlertCircle, CheckCircle, RefreshCw, Timer, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';


interface ApiKeyStats {
    key_name: string;
    masked_value: string;
    stats?: {
        limit_requests: number;
        limit_tokens: number;
        remaining_requests: number;
        remaining_tokens: number;
        percent_requests: number;
        percent_tokens: number;
        reset_time_str: string; // Ham string (2s)
        reset_timestamp: number; // Mutlak timestamp
        status?: string;
        daily_usage?: {
            date: string;
            requests_today: number;
            tokens_today: number;
            models: Record<string, { requests: number; tokens: number }>;
        };
    };
}

export function ApiUsageStats() {
    const [keys, setKeys] = useState<ApiKeyStats[]>([]);
    const [loading, setLoading] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [feedback, setFeedback] = useState<{ msg: string, type: 'success' | 'error' } | null>(null);

    const fetchStats = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_DOMAIN}/api/v1/admin/api-keys`);
            if (!res.ok) throw new Error('API verisi alınamadı');
            const data = await res.json();
            setKeys(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGlobalRefresh = async () => {
        if (keys.length === 0) return;
        setRefreshing(true);
        setFeedback(null);

        let successCount = 0;
        let failCount = 0;

        try {
            // Paralel değil, sıralı yapalım ki sunucuyu boğmayalım (veya Promise.all)
            // Promise.all daha hızlı
            const promises = keys.map(async (k) => {
                try {
                    const res = await fetch(`${API_DOMAIN}/api/v1/admin/api-keys/${k.key_name}/refresh`, {
                        method: 'POST'
                    });
                    if (res.ok) successCount++;
                    else failCount++;
                } catch (e) {
                    failCount++;
                }
            });

            await Promise.all(promises);
            await fetchStats(); // Son durumu çek

            if (failCount === 0) {
                setFeedback({ msg: "Tüm anahtarlar güncellendi.", type: 'success' });
            } else if (successCount > 0) {
                setFeedback({ msg: `${successCount} başarılı, ${failCount} başarısız.`, type: 'error' });
            } else {
                setFeedback({ msg: "Güncelleme başarısız.", type: 'error' });
            }

        } catch (err: any) {
            console.error(err);
            setFeedback({ msg: "Sistem hatası.", type: 'error' });
        } finally {
            setRefreshing(false);
            setTimeout(() => setFeedback(null), 3000);
        }
    };

    const formatResetTime = (timestamp: number, rawStr: string) => {
        if (!timestamp) return rawStr || '-';

        // Mutlak zamanı formatla
        const resetDate = new Date(timestamp * 1000);
        const timeStr = resetDate.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        return timeStr;
    };

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 30000);
        return () => clearInterval(interval);
    }, []);

    return (
        <Card className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-foreground">API Token Kullanımı (Groq)</h3>
                <div className="flex items-center gap-4">
                    {feedback && (
                        <span className={`text-sm font-medium animate-in fade-in slide-in-from-right-5 ${feedback.type === 'success' ? 'text-green-500' : 'text-red-500'}`}>
                            {feedback.msg}
                        </span>
                    )}
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleGlobalRefresh}
                        disabled={refreshing || loading}
                        className="gap-2"
                    >
                        <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                        {refreshing ? 'Güncelleniyor...' : 'Tümünü Yenile'}
                    </Button>
                </div>
            </div>

            {error && (
                <div className="text-red-500 text-sm flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" /> {error}
                </div>
            )}

            <div className="space-y-6">
                {keys.map((k) => (
                    <div key={k.key_name} className="space-y-3 p-4 border rounded-lg bg-card/50">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <Badge variant="outline">{k.key_name}</Badge>
                                <span className="text-sm text-muted-foreground font-mono">{k.masked_value}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                {/* Durum Rozeti */}
                                {k.stats ? (
                                    k.stats.status === 'invalid' ? (
                                        <Badge variant="destructive" className="bg-red-500/10 text-red-500 hover:bg-red-500/20">
                                            <XCircle className="w-3 h-3 mr-1" /> Geçersiz
                                        </Badge>
                                    ) : (
                                        <Badge variant="secondary" className="bg-green-500/10 text-green-500 hover:bg-green-500/20">
                                            <CheckCircle className="w-3 h-3 mr-1" /> Aktif
                                        </Badge>
                                    )
                                ) : (
                                    <Badge variant="secondary" className="bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20">
                                        Beklemede
                                    </Badge>
                                )}
                            </div>
                        </div>

                        {k.stats ? (
                            k.stats.status === 'invalid' ? (
                                <div className="text-xs text-red-400 italic">
                                    Bu anahtar geçersiz (401 Unauthorized). Lütfen kontrol ediniz.
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {/* Requests Progress */}
                                    <div className="space-y-1">
                                        <div className="flex justify-between text-xs">
                                            <span>İstek Limiti</span>
                                            <span className={k.stats.percent_requests < 20 ? "text-red-500 font-bold" : "text-muted-foreground"}>
                                                {k.stats.remaining_requests} / {k.stats.limit_requests} (%{k.stats.percent_requests.toFixed(1)})
                                            </span>
                                        </div>
                                        <Progress value={k.stats.percent_requests} className="h-2" />
                                    </div>

                                    {/* Tokens Progress */}
                                    <div className="space-y-1">
                                        <div className="flex justify-between text-xs">
                                            <span>Token Limiti</span>
                                            <span className={k.stats.percent_tokens < 20 ? "text-red-500 font-bold" : "text-muted-foreground"}>
                                                {k.stats.remaining_tokens} / {k.stats.limit_tokens} (%{k.stats.percent_tokens.toFixed(1)})
                                            </span>
                                        </div>
                                        <Progress value={k.stats.percent_tokens} className="h-2" />
                                    </div>

                                    <div className="flex justify-end items-center gap-2 text-xs text-muted-foreground">
                                        <Timer className="w-3 h-3" />
                                        <div className="flex flex-col items-end">
                                            <span>
                                                Hız Limiti Sıfırlanma:
                                                <span className="text-foreground font-medium ml-1">
                                                    {formatResetTime(k.stats.reset_timestamp, k.stats.reset_time_str)}
                                                </span>
                                            </span>
                                        </div>
                                    </div>

                                    {/* Daily Usage Section */}
                                    {k.stats.daily_usage && (
                                        <div className="mt-4 pt-4 border-t border-border/50">
                                            <div className="flex items-center justify-between mb-3">
                                                <span className="text-xs font-medium text-muted-foreground">
                                                    📊 Bugünkü Kullanım ({k.stats.daily_usage.date})
                                                </span>
                                            </div>
                                            <div className="grid grid-cols-2 gap-4 text-sm">
                                                <div className="bg-background/50 p-3 rounded-lg">
                                                    <div className="text-2xl font-bold text-foreground">
                                                        {k.stats.daily_usage.requests_today.toLocaleString()}
                                                    </div>
                                                    <div className="text-xs text-muted-foreground">İstek</div>
                                                </div>
                                                <div className="bg-background/50 p-3 rounded-lg">
                                                    <div className="text-2xl font-bold text-foreground">
                                                        {k.stats.daily_usage.tokens_today.toLocaleString()}
                                                    </div>
                                                    <div className="text-xs text-muted-foreground">Token</div>
                                                </div>
                                            </div>

                                            {/* Per-Model Breakdown */}
                                            {k.stats.daily_usage.models && Object.keys(k.stats.daily_usage.models).length > 0 && (
                                                <div className="mt-3">
                                                    <div className="text-xs font-medium text-muted-foreground mb-2">Model Bazlı:</div>
                                                    <div className="space-y-1">
                                                        {Object.entries(k.stats.daily_usage.models).map(([model, usage]: [string, any]) => (
                                                            <div key={model} className="flex justify-between text-xs py-1 px-2 bg-background/30 rounded">
                                                                <span className="font-mono truncate max-w-[180px]">{model}</span>
                                                                <span className="text-muted-foreground">
                                                                    {usage.requests} req / {usage.tokens.toLocaleString()} tok
                                                                </span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )
                        ) : (
                            <div className="text-xs md:text-sm text-muted-foreground italic flex items-center justify-between">
                                <span>Veri henüz yok (Yenile butonunu kullanın)</span>
                            </div>
                        )}
                    </div>
                ))}

                {keys.length === 0 && !loading && (
                    <div className="text-center text-muted-foreground py-4">
                        Hiçbir API anahtarı bulunamadı.
                    </div>
                )}
            </div>
        </Card>
    );
}
