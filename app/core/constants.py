"""
Mami AI - Sabitler ve Konfigürasyon (Constants)
-----------------------------------------------
Atlas Sovereign OS'un merkezi sabit değerleri ve model yönetişim kuralları.
"""

from typing import Dict, List, Set

# --- INTENT PATTERN'LERİ (Türkçe Niyet Sınıflandırma) ---
PERSONAL_TRIGGERS: List[str] = [
    "hatirliyor musun", "benim", "bana", "gecen", "daha once", "profilim",
    "tercih", "seviyorum", "sevmiyorum", "aliskanlik", "isim", "ismim", "yas",
    "yasim", "nerede yasiyorum", "arkadasim", "hobim", "hobi", "adim", "adimi",
    "kendim", "hakkinda", "arabam", "evim", "memleket", "kardes", "anne", "baba",
    "isyerim", "okulum", "hayatim", "planlarim", "hedefim", "ilgi", "alisveris",
    "oyun", "sirket", "esim", "borc", "borcum", "sifrem",
    "yanlis", "duzelt", "degil", "muydum", "hatirladin", "hangi", "takim", "tutuyorum", "ben"
]

PERSONAL_OVERRIDES: List[str] = [
    "ben", "bana", "benim", "hatirliyor musun", "duzeltme", "unut", "ayar", "tercih"
]

TASK_TRIGGERS: List[str] = [
    "hatirlat", "remind", "yarin", "bugun", "saat", "gun sonra",
    "pazartesi", "randevu", "todo", "gorev", "yapmam lazim", "planla", "listele"
]

FOLLOWUP_TRIGGERS: List[str] = [
    "az once", "onceki", "devam", "bunu ac", "neden", "ne demek",
    "detaylandir", "acikla", "baska", "peki ya"
]

GENERAL_TRIGGERS: List[str] = [
    "nedir", "nasil", "kim", "nerede", "hava", "iklim", "tarih",
    "bilim", "fizik", "ulke", "sehir", "cografya", "teknoloji",
    "programlama", "python", "java", "javascript", "okyanus", "deniz",
    "kac", "neler"
]

URGENCY_KEYWORDS: List[str] = [
    "acil", "hemen", "urgent", "asap", "deadline", "yarın", "bugün", "şimdi"
]

# --- SPECIALIST ROLLER (Orchestrator tarafından seçilebilir) ---
# Bu liste task_runner.py tarafından provider registration için kullanılır
SPECIALIST_ROLES: List[str] = ["logic", "coding", "creative", "analysis", "safety"]

# --- MODEL YÖNETİŞİM (GOVERNANCE) - TEK KAYNAK ---
# Tüm rol bazlı model tanımları burada. governance.py buradan okur.
# 
# SPECIALIST ROLLER (Orchestrator tarafından seçilebilir):
# - logic: Mantıksal akıl yürütme, problem çözme, analitik düşünme
# - coding: Yazılım geliştirme, kod yazma, teknik çözümler
# - creative: Yaratıcı içerik, hikaye, şiir, tasarım fikirleri
# - analysis: Veri analizi, istatistik, araştırma, derinlemesine inceleme
# - safety: Güvenlik kontrolü, zararlı içerik tespiti, uygunluk denetimi
# - search: Bilgi arama ve derleme (Orchestrator tarafından kullanılmaz, task_runner tarafından)
#
# SISTEM ROLLER (Orchestrator tarafından seçilmez, sistem tarafından kullanılır):
# - orchestrator: Planlama ve görev koordinasyonu (Orchestrator modülü tarafından)
# - synthesizer: Nihai yanıt üretimi (Brain Engine tarafından)
# - semantic: Mesaj analizi ve sınıflandırma (semantic_classifier tarafından)
# - fast: Hızlı işlemler (query_enhancer tarafından)
# - episodic_summary: Konuşma özeti (memory service tarafından)
#
MODEL_GOVERNANCE: Dict[str, List[str]] = {
    # === SISTEM ROLLERI ===
    # Orchestrator - Planlama ve koordinasyon
    # Kullanım: Orchestrator modülü tarafından görev planı oluşturmak için
    # Özellik: Hızlı, akıllı planlama yapabilmeli
    "orchestrator": [
        "gemini-2.5-flash-lite",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ],
    
    # Synthesizer - Nihai yanıt üretimi
    # Kullanım: Brain Engine tarafından kullanıcıya sunulacak son cevabı oluşturmak için
    # Özellik: Samimi, doğal, kullanıcı-odaklı cevaplar
    # Not: Kimi modelleri samimiyet ve üslup için tercih edilir
    "synthesizer": [
        "moonshotai/kimi-k2-instruct-0905", # 1. Samimiyet/Üslup (Primary)
        "moonshotai/kimi-k2-instruct",      # 2. Alternatif Kimi
        "llama-3.1-8b-instant",             # 3. Yüksek Kapasite Fallback (128k context)
        "llama-3.3-70b-versatile",          # 4. Zeka Fallback
    ],
    
    # Semantic - Mesaj analizi
    # Kullanım: semantic_classifier tarafından mesajın niyetini ve bağlamını anlamak için
    # Özellik: Hızlı, doğru sınıflandırma
    "semantic": [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
    ],
    
    # Fast - Hızlı işlemler
    # Kullanım: query_enhancer tarafından sorguları optimize etmek için
    # Özellik: Çok hızlı, düşük latency
    "fast": [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
    ],
    
    # === SPECIALIST ROLLER (Orchestrator tarafından seçilebilir) ===
    # Safety - Güvenlik kontrolü
    # Kullanım: Orchestrator tarafından zararlı içerik tespiti için
    # Özellik: Güvenlik odaklı, uygunluk denetimi
    # Görev Türü: Güvenlik taraması, zararlı içerik tespiti
    "safety": [
        "meta-llama/llama-prompt-guard-2-86m",
        "meta-llama/llama-guard-4-12b",
        "openai/gpt-oss-safeguard-20b",
    ],
    
    # Coding - Yazılım geliştirme
    # Kullanım: Orchestrator tarafından kod yazma, teknik çözüm gerektiren görevler için
    # Özellik: Teknik bilgi, kod kalitesi, best practices
    # Görev Türü: Kod yazma, debugging, teknik açıklama, algoritma tasarımı
    "coding": [
        "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile",
        "qwen/qwen3-32b",
    ],
    
    # Creative - Yaratıcı içerik
    # Kullanım: Orchestrator tarafından yaratıcı görevler için
    # Özellik: Yaratıcılık, hayal gücü, sanatsal ifade
    # Görev Türü: Hikaye yazma, şiir, tasarım fikirleri, yaratıcı çözümler
    "creative": [
        "moonshotai/kimi-k2-instruct",
        "moonshotai/kimi-k2-instruct-0905",
        "llama-3.3-70b-versatile",
    ],
    
    # Logic - Mantıksal akıl yürütme
    # Kullanım: Orchestrator tarafından mantıksal problem çözme için (DEFAULT)
    # Özellik: Analitik düşünme, problem çözme, mantıksal akıl yürütme
    # Görev Türü: Genel sorular, problem çözme, analiz, açıklama
    "logic": [
        "llama-3.3-70b-versatile",
        "moonshotai/kimi-k2-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
    ],
    
    # Analysis - Veri analizi
    # Kullanım: Orchestrator tarafından veri analizi, araştırma gerektiren görevler için
    # Özellik: Veri analizi, istatistik, derinlemesine inceleme
    # Görev Türü: Veri analizi, araştırma, karşılaştırma, değerlendirme
    "analysis": [
        "llama-3.3-70b-versatile",
        "qwen/qwen3-32b",
        "openai/gpt-oss-120b",
    ],
    
    # Search - Bilgi arama ve derleme
    # Kullanım: task_runner tarafından web araması sonuçlarını işlemek için
    # Özellik: Hızlı, yüksek TPM (30K), bilgi derleme
    # Görev Türü: Arama sonuçlarını işleme, bilgi derleme
    "search": [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ],
    
    # === MEMORY ROLLERI ===
    # Episodic Summary - Konuşma özeti
    # Kullanım: Memory service tarafından konuşma özetlemek için
    # Özellik: Özet yapma, önemli noktaları çıkarma
    "episodic_summary": [
        "gemini-2.5-flash-lite",
        "llama-3.3-70b-versatile",
    ],
}

# --- CONTEXT BUDGET (Bağlam Bütçesi) ---
# Kısa Vadeli Plan: 12000 char, transcript %50 → ~10-12 turn kapasitesi
CONTEXT_BUDGET: Dict = {
    "max_total_chars": 12000,  # 6000 → 12000 (Kimi güvenli sınırı)
    "weights": {
        "transcript": 0.50,   # 0.40 → 0.50 (daha fazla sohbet geçmişi)
        "episodic": 0.30,     # Konuşma özetleri
        "semantic": 0.20      # Hafıza (graph/vector)
    }
}

# --- HISTORY LIMITS (Geçmiş Limitleri) ---
# Tüm bileşenler için merkezi limit tanımları
HISTORY_LIMITS: Dict[str, int] = {
    "orchestrator": 10,   # Planlama için (son 10 mesaj)
    "synthesizer": 15,    # Final yanıt için (son 15 mesaj)
    "memory_gateway": 8,  # Episodic retrieval limit
    "redis_cache": 20,    # Hot memory (Redis'te tutulacak)
}

CONTEXT_BUDGET_PROFILES: Dict[str, Dict[str, float]] = {
    "GENERAL":   {"transcript": 0.80, "episodic": 0.20, "semantic": 0.00},
    "FOLLOWUP":  {"transcript": 0.60, "episodic": 0.25, "semantic": 0.15},
    "PERSONAL":  {"transcript": 0.30, "episodic": 0.20, "semantic": 0.50},
    "TASK":      {"transcript": 0.35, "episodic": 0.25, "semantic": 0.40},
    "MIXED":     {"transcript": 0.40, "episodic": 0.30, "semantic": 0.30},
}

# --- EMBEDDING AYARLARI ---
EMBEDDING_SETTINGS: Dict = {
    "PROVIDER": "gemini",
    "MODEL_NAME": "text-embedding-004",
    "DIMENSION": 768,
    "SCORING_WEIGHTS": {
        "overlap": 0.45,
        "semantic": 0.35,
        "recency": 0.20
    }
}

# --- MEMORY CONFIDENCE AYARLARI ---
MEMORY_CONFIDENCE_SETTINGS: Dict = {
    "DEFAULT_HARD_FACT_CONFIDENCE": 1.0,
    "DEFAULT_SOFT_SIGNAL_CONFIDENCE": 0.6,
    "UNCERTAINTY_THRESHOLD": 0.5,
    "DECAY_RATE_PER_DAY": 0.05,
    "CONFLICT_THRESHOLD": 0.7,
    "DROP_THRESHOLD": 0.4,
    "SOFT_SIGNAL_THRESHOLD": 0.7
}

# --- RETENTION AYARLARI ---
RETENTION_SETTINGS: Dict = {
    "TURN_RETENTION_DAYS": 30,
    "MAX_TURNS_PER_SESSION": 400,
    "EPISODE_RETENTION_DAYS": 180,
    "NOTIFICATION_RETENTION_DAYS": 30,
    "DONE_TASK_RETENTION_DAYS": 30
}

# --- TEMPERATURE AYARLARI ---
STYLE_TEMPERATURE_MAP: Dict[str, float] = {
    "professional": 0.3,
    "expert": 0.3,
    "friendly": 0.5,
    "standard": 0.5,
    "kanka": 0.8,
    "creative": 0.8,
    "teacher": 0.4,
    "girlfriend": 0.8,
    "sincere": 0.6,
    "default": 0.5
}

INTENT_TEMPERATURE: Dict[str, float] = {
    "coding": 0.3,
    "debug": 0.2,
    "refactor": 0.3,
    "math": 0.2,
    "calculation": 0.2,
    "analysis": 0.4,
    "creative": 0.8,
    "story": 0.85,
    "poem": 0.9,
    "roleplay": 0.8,
    "greeting": 0.6,
    "question": 0.5,
    "general": 0.5,
    "search": 0.5,
}

# --- API AYARLARI ---
API_CONFIG: Dict = {
    "groq_api_base": "https://api.groq.com/openai/v1",
    "gemini_api_base": "https://generativelanguage.googleapis.com/v1beta",
    "default_temperature": 0.7,
    "max_tokens": 2048,
    "frequency_penalty": 0.1,
    "presence_penalty": 0.1
}
