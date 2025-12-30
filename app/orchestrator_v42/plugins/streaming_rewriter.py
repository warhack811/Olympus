# app/orchestrator_v42/plugins/streaming_rewriter.py

import os
import asyncio
import re
from typing import List, Tuple, Dict, Any

class StreamingRewriter:
    """
    Akışkan Yeniden Yazım (Streaming Rewriter).
    
    Gelen metin parçalarını (chunks) işler ve 'Şeffaflık Modu' (Transparency Mode) 
    uygulayarak kod bloklarını korur, dış metindeki formatı düzenler.
    
    Ayrıca 'Backpressure' mekanizması ile sistem yükü yüksekse işlemi atlar (bypass).
    """
    
    # Sınıf seviyesinde aktif işlem sayacı (Backpressure için)
    _active_rewrites: int = 0
    _lock = asyncio.Lock()
    _test_queue_depth: int = -1 # Test için override
    
    def __init__(self):
        self.enabled = os.environ.get("ORCH_STREAM_REWRITE", "false").lower() == "true"
        
        # State Machine Durumu
        self.in_fence = False
        self.pending_backticks = 0
        self.buffer = []
        
        # Metrikler
        self.chunks_in = 0
        self.chunks_out = 0
        self.modified = False

    @classmethod
    def _set_queue_depth_for_test(cls, value: int):
        """Sadece test amaçlı kuyruk derinliğini zorlar."""
        cls._test_queue_depth = value

    async def rewrite_chunks(self, chunks: List[str]) -> Tuple[List[str], Dict[str, Any]]:
        """
        Verilen parçaları işler ve düzenlenmiş listeyi döndürür.
        """
        self.chunks_in = len(chunks)
        
        # 1. Backpressure Kontrolü
        queue_depth = self._test_queue_depth if self._test_queue_depth >= 0 else self._active_rewrites
        
        if queue_depth > 5:
            return chunks, {
                "enabled": self.enabled,
                "bypassed": True,
                "queue_depth": queue_depth,
                "reason": "Yüksek yük (Backpressure)",
                "chunks_in": self.chunks_in,
                "chunks_out": self.chunks_in,
                "modified": False
            }
            
        if not self.enabled:
             return chunks, {
                "enabled": False,
                "bypassed": True,
                "queue_depth": queue_depth,
                "reason": "Konfigürasyon kapalı (ORCH_STREAM_REWRITE)",
                "chunks_in": self.chunks_in,
                "chunks_out": self.chunks_in,
                "modified": False
            }

        # Aktif sayacı artır
        async with self._lock:
            StreamingRewriter._active_rewrites += 1
            
        output_chunks = []
        try:
            for chunk in chunks:
                processed = self._process_chunk(chunk)
                if processed:
                    output_chunks.extend(processed)
            
            # Kalan buffer'ı boşalt
            if self.buffer:
                flushed = self._flush_buffer()
                if flushed:
                    output_chunks.append(flushed)

        finally:
            async with self._lock:
                StreamingRewriter._active_rewrites -= 1
                
        self.chunks_out = len(output_chunks)
        # Basit değişiklik kontrolü (uzunluk/içerik değişti mi) - tam diff pahalı olur
        self.modified = "".join(chunks) != "".join(output_chunks)
        
        return output_chunks, {
            "enabled": True,
            "bypassed": False,
            "queue_depth": queue_depth,
            "reason": "Başarılı",
            "chunks_in": self.chunks_in,
            "chunks_out": self.chunks_out,
            "modified": self.modified
        }

    def _process_chunk(self, chunk: str) -> List[str]:
        """Bir parça içindeki karakterleri State Machine ile işler."""
        out = []
        
        for char in chunk:
            # Fence Algılama (```)
            if char == '`':
                self.pending_backticks += 1
                if self.pending_backticks == 3:
                    # Durum değiştir
                    if self.buffer:
                        out.append(self._flush_buffer())
                    
                    self.in_fence = not self.in_fence
                    self.pending_backticks = 0
                    out.append("```") # Fence'in kendisini yaz
            else:
                # Birikmiş backtick'leri (1 veya 2 tane) normal karakter olarak işle
                if self.pending_backticks > 0:
                    for _ in range(self.pending_backticks):
                        self._handle_char('`', out)
                    self.pending_backticks = 0
                
                self._handle_char(char, out)
                
        return out

    def _handle_char(self, char: str, out_list: List[str]):
        """Karaktere göre işlem yapar (Inside/Outside Fence)."""
        if self.in_fence:
            # Kod bloğu içi: Dokunma, buffer kullanma, direkt yaz
            out_list.append(char)
        else:
            # Dışarıda: Buffer'a ekle, gerekirse flush et
            self.buffer.append(char)
            # Semantik flush (Nokta veya satır sonu veya buffer doluluğu)
            if char in ['.', '\n'] or len(self.buffer) > 120:
                out_list.append(self._flush_buffer())

    def _flush_buffer(self) -> str:
        """Buffer'daki metne basit stil uygular ve döndürür."""
        if not self.buffer:
            return ""
            
        raw_text = "".join(self.buffer)
        self.buffer = []
        
        # Basit Stil Kuralları (Deterministik)
        # 1. Fazla boşlukları tek boşluğa indir (regex)
        text = re.sub(r' +', ' ', raw_text)
        
        # 2. 3+ boş satırı 2'ye indir
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Not: Orijinal chunk akışını çok bozmamak için safe replacement yapıyoruz.
        return text
