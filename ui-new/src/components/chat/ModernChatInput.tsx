import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Image as ImageIcon, Globe, Sparkles, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModernChatInputProps {
    theme?: any; // Theme object from DesignLab
    onSendMessage?: (message: string) => void;
    isLoading?: boolean;
}

export function ModernChatInput({ theme, onSendMessage, isLoading }: ModernChatInputProps) {
    const [isFocused, setIsFocused] = useState(false);
    const [inputValue, setInputValue] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Otomatik yükseklik ayarı (Auto-resize)
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
        }
    }, [inputValue]);

    return (
        <div className="w-full max-w-3xl mx-auto p-4 transition-all duration-500">
            {/* ANA KAPSAYICI (THE COCKPIT) */}
            <div
                className={cn(
                    "relative flex flex-col gap-1 p-2.5 rounded-[26px] border transition-all duration-500 ease-out",
                    "bg-[var(--bg-glass)]/40 backdrop-blur-2xl",
                    isFocused
                        ? "border-[var(--accent)]/50 ring-4 ring-[var(--accent)]/10 shadow-[0_0_40px_-15px_var(--accent-glow)] bg-[var(--bg-glass)]/60"
                        : "border-[var(--border)] shadow-sm hover:border-[var(--border)]/80"
                )}
            >

                {/* TEXT AREA ALANI */}
                <textarea
                    ref={textareaRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    placeholder="Yapay zekaya bir şeyler sor..."
                    className="w-full bg-transparent text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] placeholder:opacity-40 text-[16px] px-3 resize-none !outline-none !ring-0 focus:!outline-none focus:!ring-0 focus-visible:!outline-none focus-visible:!ring-0 border-none shadow-none focus:shadow-none max-h-48 min-h-[44px] scrollbar-hide pt-2 pb-1"
                    rows={1}
                />

                {/* ALT ARAÇ ÇUBUĞU (TOOLBAR) */}
                <div className="flex items-center justify-between mt-1 px-1 bg-white/[0.02] rounded-xl py-1">

                    <div className="flex items-center gap-1">

                        {/* Model Badge */}
                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-transparent hover:border-white/5 hover:bg-white/5 transition-all text-[11px] font-bold uppercase tracking-wider text-[var(--text-secondary)] opacity-60 hover:opacity-100">
                            <Sparkles className="w-3 h-3" style={{ color: theme?.accent }} />
                            <span>Gemini 3 Pro</span>
                            <ChevronDown className="w-3 h-3 opacity-30" />
                        </button>

                        <div className="h-3 w-px bg-white/5 mx-1" />

                        <ToolButton icon={<Globe className="w-3.5 h-3.5" />} active label="Web" />
                        <ToolButton icon={<ImageIcon className="w-3.5 h-3.5" />} label="Görsel" />
                        <ToolButton icon={<Paperclip className="w-3.5 h-3.5" />} label="Dosya" />
                    </div>

                    <button
                        disabled={!inputValue.trim() || isLoading}
                        onClick={() => {
                            if (inputValue.trim() && onSendMessage) {
                                onSendMessage(inputValue);
                                setInputValue("");
                            }
                        }}
                        className={cn(
                            "w-8 h-8 rounded-lg transition-all duration-300 flex items-center justify-center",
                            inputValue.trim()
                                ? "shadow-lg opacity-100 scale-100 hover:scale-105"
                                : "bg-white/5 text-[var(--text-secondary)] cursor-not-allowed opacity-20 scale-95"
                        )}
                        style={{
                            backgroundColor: inputValue.trim() ? theme?.accent : undefined,
                            color: inputValue.trim() ? '#fff' : undefined
                        }}
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>

            <p className="text-center text-[10px] text-[var(--text-secondary)] mt-4 font-bold uppercase tracking-[0.2em] opacity-30">
                Professional AI Workspace
            </p>
        </div>
    );
}

// Yardımcı Ufak Bileşen
function ToolButton({ icon, active, label }: { icon: React.ReactNode, active?: boolean, label: string }) {
    return (
        <button
            className={cn(
                "p-2 rounded-lg transition-all group relative",
                active
                    ? "text-[var(--text-primary)] bg-white/5"
                    : "text-[var(--text-secondary)] opacity-40 hover:opacity-100 hover:bg-white/5"
            )}
            title={label}
        >
            {icon}
            {active && (
                <div className="absolute top-1 right-1 w-1 h-1 bg-[var(--accent)] rounded-full" />
            )}
        </button>
    );
}
