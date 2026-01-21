"""
Mami AI - Identity Engine (Atlas Sovereign Edition)
---------------------------------------------------
Master User Anchor yönetimi ve zamir çözümleme.

Sorumluluklar:
1. User Anchor: Her kullanıcı için benzersiz anchor entity
2. Pronoun Detection: 1. ve 2. şahıs zamirlerini tespit
3. Text Normalization: Türkçe karakter normalizasyonu
"""

# Türkçe karakter normalizasyon haritası
TR_NORMALIZE_MAP = str.maketrans(
    "İĞŞÜÖÇığşüöç",
    "IGSUOCigsüoc"
)

# 1. tekil şahıs zamirleri
FIRST_PERSON_PRONOUNS = {
    "BEN", "BENIM", "BANA", "BENDE", "BENDEN",
    "KENDIM", "KENDIMI", "KENDIME", "KENDIMDEN", "KENDIMDE",
    "ADIM", "ISMIM", "MESLEGIM", "YASIM", "LAKABIM", "MEMLEKETIM",
    "KULLANICI"
}

# 2. tekil şahıs zamirleri
SECOND_PERSON_PRONOUNS = {
    "SEN", "SENIN", "SANA", "SENDE", "SENDEN"
}

# Diğer zamirler (drop edilecekler)
OTHER_PRONOUNS = {
    "O", "ONLAR", "BIZ", "SIZ",
    "HOCAM", "HOCA", "BU", "SU", "BUNLAR", "SUNLAR"
}


def get_user_anchor(user_id: str) -> str:
    """
    Kullanıcı için Master Anchor entity adını döner.
    
    Args:
        user_id: Kullanıcı kimliği
    
    Returns:
        Master anchor entity adı (örn: "__USER__::session_123")
    """
    return f"__USER__::{user_id}"


def normalize_text_for_match(text: str) -> str:
    """
    Metin karşılaştırma için normalize eder.
    
    1. Boşlukları temizle
    2. Büyük harfe çevir
    3. Türkçe karakterleri ASCII'ye çevir
    """
    if not text:
        return ""
    cleaned = text.strip()
    upper = cleaned.upper()
    normalized = upper.translate(TR_NORMALIZE_MAP)
    return normalized


def is_first_person(token: str) -> bool:
    """
    Verilen token 1. tekil şahıs zamiri mi kontrol eder.
    
    BEN, BENIM, BANA, KENDIM, ADIM, İSMİM vb.
    """
    normalized = normalize_text_for_match(token)
    return normalized in FIRST_PERSON_PRONOUNS


def is_second_person(token: str) -> bool:
    """
    Verilen token 2. tekil şahıs zamiri mi kontrol eder.
    
    SEN, SENİN, SANA vb.
    """
    normalized = normalize_text_for_match(token)
    return normalized in SECOND_PERSON_PRONOUNS


def is_other_pronoun(token: str) -> bool:
    """
    Verilen token diğer zamirlerden biri mi kontrol eder.
    
    O, ONLAR, BİZ, SİZ, HOCAM vb.
    """
    normalized = normalize_text_for_match(token)
    return normalized in OTHER_PRONOUNS


def resolve_subject(subject: str, user_id: str) -> tuple[str, str]:
    """
    Subject'i çözer ve gerekirse user anchor'a map eder.
    
    Returns:
        (resolved_subject, resolution_type)
        resolution_type: "FIRST_PERSON", "SECOND_PERSON", "OTHER_PRONOUN", "ENTITY"
    """
    if is_first_person(subject):
        return get_user_anchor(user_id), "FIRST_PERSON"
    elif is_second_person(subject):
        return subject, "SECOND_PERSON"  # Will be dropped
    elif is_other_pronoun(subject):
        return subject, "OTHER_PRONOUN"  # Will be dropped
    else:
        return subject, "ENTITY"
