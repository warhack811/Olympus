
import React, { useState, useEffect, useCallback } from 'react';
import { API_DOMAIN } from '@/api/client';

import { useChatStore } from '@/stores';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, Bug, ChevronRight, ChevronDown, ShieldAlert, BarChart3, Settings2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function OrchDebugPanel() {
    const isStreaming = useChatStore((state) => state.isStreaming);
    const [snapshot, setSnapshot] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isExpanded, setIsExpanded] = useState(false);
    const [verbose, setVerbose] = useState(false);
    const [showJson, setShowJson] = useState(false);

    // URL parametresini kontrol et
    const isEnabled = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('orch_debug') === '1';

    const fetchSnapshot = useCallback(async (isVerbose: boolean) => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_DOMAIN}/api/v1/admin/orch/snapshot?verbose=${isVerbose}`);
            if (response.status === 401 || response.status === 403) {
                setError('Admin oturumu gerekli');
                return;
            }
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            setSnapshot(data);
        } catch (err: any) {
            console.error('[OrchDebug] Fetch error:', err);
            setError(err.message || 'Veri alınamadı');
        } finally {
            setLoading(false);
        }
    }, []);

    // Yayın bittiğinde otomatik yenile
    useEffect(() => {
        if (!isEnabled) return;

        // isStreaming true'dan false'a geçtiğinde tetiklenir
        if (!isStreaming && snapshot !== null) {
            fetchSnapshot(verbose);
        }

        // İlk yükleme
        if (snapshot === null) {
            fetchSnapshot(verbose);
        }
    }, [isStreaming, isEnabled, verbose, fetchSnapshot, snapshot]);

    if (!isEnabled) return null;

    const data = snapshot?.snapshot || {};
    const telemetry = snapshot?.telemetry || {};
    const summary = snapshot?.snapshot?.telemetry_summary || {};

    return (
        <div className="fixed top-20 right-4 z-[9999] flex flex-col items-end gap-2">
            {/* Toggle Button */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-full shadow-2xl transition-all duration-300",
                    "bg-zinc-900/90 backdrop-blur-md border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700",
                    isExpanded && "bg-purple-600/20 border-purple-500/50 text-purple-300"
                )}
            >
                <Bug className={cn("h-4 w-4", loading && "animate-spin")} />
                <span className="text-xs font-medium">Orchestrator Debug</span>
                {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>

            {/* Panel Content */}
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ opacity: 0, y: -10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -10, scale: 0.95 }}
                        className="w-80 rounded-2xl bg-zinc-900/95 backdrop-blur-xl border border-zinc-800 shadow-2xl overflow-hidden text-xs"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between p-3 border-b border-zinc-800 bg-white/5">
                            <div className="flex items-center gap-2">
                                <Settings2 className="h-3.5 w-3.5 text-zinc-500" />
                                <span className="font-semibold text-zinc-300">Sistem Durumu</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => fetchSnapshot(verbose)}
                                    className="p-1 hover:bg-white/10 rounded-md transition-colors"
                                    title="Yenile"
                                >
                                    <RefreshCw className={cn("h-3.5 w-3.5 text-zinc-500", loading && "animate-spin")} />
                                </button>
                            </div>
                        </div>

                        {/* Content */}
                        <div className="p-3 space-y-4 max-h-[70vh] overflow-y-auto">
                            {error ? (
                                <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2">
                                    <ShieldAlert className="h-4 w-4" />
                                    <span>{error}</span>
                                </div>
                            ) : !snapshot ? (
                                <div className="text-zinc-500 italic text-center py-4">Veri yükleniyor...</div>
                            ) : (
                                <>
                                    {/* Flags & Rollout */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-1">Rollout & Switch</div>
                                        <div className="grid grid-cols-2 gap-2">
                                            <Badge label="ORCH_ENABLED" active={data.flags?.production_enabled} />
                                            <Badge label="Streaming" active={data.flags?.streaming_enabled} />
                                            <div className="col-span-2 p-2 rounded-lg bg-white/5 border border-white/5">
                                                <div className="flex justify-between items-center text-zinc-400">
                                                    <span>Rollout Oranı:</span>
                                                    <span className="font-mono text-white">%{data.rollout?.rollout_percent || 0}</span>
                                                </div>
                                                <div className="flex justify-between items-center text-zinc-400 mt-1">
                                                    <span>Allowlist:</span>
                                                    <span className="font-mono text-white">{data.rollout?.allowlist_count || 0} kullanıcı</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Fallback Reasons */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-1">Son Fallback Nedenleri</div>
                                        <div className="space-y-1">
                                            {Object.keys(summary.fallback_reasons || {}).length > 0 ? (
                                                Object.entries(summary.fallback_reasons).map(([reason, count]: any) => (
                                                    <div key={reason} className="flex justify-between items-center p-1.5 rounded-md bg-zinc-800/50">
                                                        <span className="text-zinc-400">{reason}</span>
                                                        <span className="bg-zinc-700 text-zinc-200 px-1.5 rounded font-mono">{count}</span>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="text-zinc-600 italic">Fallback kaydı yok.</div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Evidence Counts */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-1">Evidence (Anlık)</div>
                                        <div className="grid grid-cols-3 gap-2 text-center">
                                            <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                                                <div className="text-blue-400 font-bold text-lg leading-none">?</div>
                                                <div className="text-[9px] text-blue-300/60 mt-1">Tools</div>
                                            </div>
                                            <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/20">
                                                <div className="text-green-400 font-bold text-lg leading-none">?</div>
                                                <div className="text-[9px] text-green-300/60 mt-1">Memory</div>
                                            </div>
                                            <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                                <div className="text-amber-400 font-bold text-lg leading-none">{summary.rag?.used || 0}</div>
                                                <div className="text-[9px] text-amber-300/60 mt-1">RAG</div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Telemetry Summary */}
                                    <div className="space-y-2">
                                        <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-1 flex items-center gap-1">
                                            <BarChart3 className="h-3 w-3" /> Telemetri
                                        </div>
                                        <div className="p-2 divide-y divide-zinc-800 rounded-lg bg-black/40 border border-zinc-800">
                                            <StatRow label="Orch Deneme" value={summary.requests?.try} />
                                            <StatRow label="Orch Başarı" value={summary.requests?.returned} />
                                            <StatRow label="Rollout IN" value={summary.requests?.rollout_in} color="text-green-400" />
                                            <StatRow label="Auto-Circuit" value={data.auto_circuit?.status} color={data.auto_circuit?.status === 'closed' ? 'text-green-400' : 'text-red-400'} />
                                        </div>
                                    </div>

                                    {/* Verbose JSON Toggle */}
                                    <div className="pt-2 border-t border-zinc-800 flex flex-col gap-2">
                                        <div className="flex items-center justify-between">
                                            <label className="flex items-center gap-2 cursor-pointer text-zinc-500 hover:text-zinc-300 transition-colors">
                                                <input
                                                    type="checkbox"
                                                    checked={verbose}
                                                    onChange={(e) => setVerbose(e.target.checked)}
                                                    className="rounded border-zinc-700 bg-zinc-800 text-purple-600 focus:ring-purple-600/50"
                                                />
                                                <span>Verbose Mod</span>
                                            </label>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => {
                                                        if (snapshot) {
                                                            navigator.clipboard.writeText(JSON.stringify(snapshot, null, 2));
                                                        }
                                                    }}
                                                    className="text-zinc-500 hover:text-blue-400 font-medium text-[10px]"
                                                    title="JSON Kopyala"
                                                >
                                                    Kopyala
                                                </button>
                                                <div className="w-px h-3 bg-zinc-800" />
                                                <button
                                                    onClick={() => setShowJson(!showJson)}
                                                    className="text-zinc-500 hover:text-purple-400 font-medium"
                                                >
                                                    {showJson ? 'Gizle' : 'JSON Göster'}
                                                </button>
                                            </div>
                                        </div>

                                        {showJson && (
                                            <pre className="p-3 rounded-lg bg-black/60 border border-zinc-800 overflow-x-auto text-[10px] font-mono text-zinc-400 max-h-64 thin-scrollbar">
                                                {JSON.stringify(snapshot, null, 2)}
                                            </pre>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="p-2 bg-black/40 border-t border-zinc-800 text-[9px] text-center text-zinc-600">
                            Trace ID: {data.last_trace_summary?.trace_id || 'N/A'}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function Badge({ label, active }: { label: string; active?: boolean }) {
    return (
        <div className={cn(
            "px-2 py-1 rounded-md border text-[10px] font-medium flex items-center justify-between",
            active
                ? "bg-green-500/5 border-green-500/20 text-green-400"
                : "bg-zinc-500/5 border-zinc-500/10 text-zinc-600"
        )}>
            <span>{label}</span>
            <div className={cn("h-1.5 w-1.5 rounded-full", active ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" : "bg-zinc-700")} />
        </div>
    );
}

function StatRow({ label, value, color }: { label: string; value: any; color?: string }) {
    return (
        <div className="flex justify-between items-center py-1.5">
            <span className="text-zinc-500">{label}</span>
            <span className={cn("font-mono font-medium", color || "text-zinc-300")}>{value ?? 0}</span>
        </div>
    );
}
