# Chat Sistemi - 5 Ek Sorunun Sebep-Sonuç Açıklaması

**Tarih**: 21 Ocak 2026  
**Durum**: DETAYLI ANALIZ TAMAMLANDI  
**Amaç**: Her sorunun sebep-sonuç ilişkisini anlaşılır şekilde açıklamak

---

## SORUN 4: API Client'ta Hata Yönetimi Eksikliği

### Nerede Olduğu
`ui-new/src/api/client.ts` - `fetchApi()` fonksiyonu

### Sebep (Root Cause)

API client'ın `fetchApi()` fonksiyonu çok basit yazılmış:

```typescript
export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(url, { ... })
    
    if (!response.ok) {
        throw new Error(...)
    }
    
    return JSON.parse(text)
}
```

**Eksiklikler**:
1. **Ağ Hatası Yeniden Deneme Yok**: Eğer internet bağlantısı kesilirse, hata fırlatılır ve biter
2. **Timeout Yok**: Eğer sunucu çok yavaşsa, istek sonsuza kadar bekler
3. **Rate Limit Yönetimi Yok**: Sunucu 429 (çok fazla istek) döndürse bile, yeniden deneme yapılmaz
4. **Sessiz Başarısızlık**: Boş response gelirse `{}` döndürülür, kullanıcı bilmez

### Sonuç (Impact)

**Senaryo 1: Ağ Hatası**
```
1. Kullanıcı mesaj gönderir
2. İnternet kesilir
3. fetch() hata fırlatır
4. Uygulama çöker
5. Kullanıcı: "Ne oldu? Neden çöktü?"
```

**Senaryo 2: Yavaş Sunucu**
```
1. Kullanıcı mesaj gönderir
2. Sunucu yavaş cevap veriyor (30 saniye)
3. UI donuyor, hiçbir şey yapılamıyor
4. Kullanıcı: "Uygulama dondu mu?"
```

**Senaryo 3: Rate Limiting**
```
1. Kullanıcı hızlı hızlı mesaj gönderir
2. Sunucu: "429 - Çok fazla istek"
3. Client yeniden denemiyor
4. Mesajlar gönderilmiyor
5. Kullanıcı: "Neden mesajlar gönderilmiyor?"
```

**Senaryo 4: Boş Response**
```
1. Kullanıcı konuşma listesini yükler
2. Sunucu boş response döndürür
3. Client `{}` döndürür
4. Konuşma listesi boş görünür
5. Kullanıcı: "Konuşmalar nerede?"
```

### Önem Derecesi
🔴 **YÜKSEK** - Uygulamanın güvenilirliğini etkiler

---

## SORUN 5: ChatInput'ta Hata Yakalama Boş

### Nerede Olduğu
`ui-new/src/components/chat/ChatInput.tsx` - `handleSend()` fonksiyonu

### Sebep (Root Cause)

Mesaj gönderme fonksiyonunda try-catch var ama catch bloğu boş:

```typescript
const handleSend = useCallback(async () => {
    try {
        // Mesaj gönder, dosya yükle, vs.
        await chatApi.sendMessage(...)
    } catch (error) {
        // ← BOŞŞ! Hata yakalanıyor ama hiçbir şey yapılmıyor
    } finally {
        setIsSending(false)
    }
}, [...])
```

**Neden Boş?**
- Hata yakalanıyor ama görmezden geliniyordu
- Hiçbir log yazılmıyor
- Kullanıcıya bildirim yapılmıyor
- Hata debug edilemiyor

### Sonuç (Impact)

**Senaryo 1: Ağ Hatası**
```
1. Kullanıcı mesaj gönderir
2. İnternet kesilir
3. Hata oluşur
4. catch bloğu boş olduğu için hiçbir şey olmaz
5. UI: "Gönderiliyor..." durumundan çıkıyor
6. Kullanıcı: "Mesaj gönderildi mi? Bilmiyorum..."
```

**Senaryo 2: Sunucu Hatası**
```
1. Kullanıcı mesaj gönderir
2. Sunucu 500 hatası döndürür
3. catch bloğu boş
4. Hiçbir log yok
5. Developer: "Ne oldu? Neden başarısız oldu?"
```

**Senaryo 3: Dosya Yükleme Hatası**
```
1. Kullanıcı resim ekleyerek mesaj gönderir
2. Dosya yükleme başarısız olur
3. catch bloğu boş
4. Kullanıcı: "Resim yüklendi mi? Bilmiyorum..."
```

### Önem Derecesi
🔴 **YÜKSEK** - Kullanıcı hataları görmüyor

---

## SORUN 6: MessageBubble'da Polling Memory Leak

### Nerede Olduğu
`ui-new/src/components/chat/MessageBubble.tsx` - Resim işi polling'i

### Sebep (Root Cause)

Resim oluşturma işinin durumunu kontrol etmek için polling yapılıyor:

```typescript
const pollInterval = setInterval(async () => {
    try {
        const status = await chatApi.getJobStatus(jobId)
        // Durumu güncelle
    } catch (error) {
        // Hata yok sayılıyor
    }
}, 1000)  // Her 1 saniyede bir

// ← SORUN: Component unmount olduğunda interval temizlenmiyor!
```

**Neden Sorun?**
1. Component silinse bile interval çalışmaya devam ediyor
2. Her 1 saniyede bir API çağrısı yapılıyor
3. Bellek sızıntısı oluşuyor
4. Hata olsa bile yeniden deneme yapılmıyor

### Sonuç (Impact)

**Senaryo 1: Bellek Sızıntısı**
```
1. Kullanıcı 10 resim oluşturur
2. Her resim için polling interval başlatılır
3. Kullanıcı konuşmayı kapatır
4. Component silinir AMA intervallar çalışmaya devam ediyor
5. 10 interval × 1 saniye = 10 API çağrısı/saniye
6. Uygulama yavaşlaşıyor
7. Bellek kullanımı artıyor
```

**Senaryo 2: Performans Düşüşü**
```
1. Kullanıcı 50 resim oluşturur
2. 50 interval çalışıyor
3. Her saniye 50 API çağrısı
4. Sunucu yükü artıyor
5. Diğer kullanıcılar etkileniyor
6. Uygulama donuyor
```

**Senaryo 3: Hata Yönetimi Yok**
```
1. API başarısız olur
2. catch bloğu boş
3. Polling devam ediyor
4. Hiçbir log yok
5. Developer: "Neden polling durmuyor?"
```

### Önem Derecesi
🔴 **YÜKSEK** - Bellek sızıntısı + performans sorunu

---

## SORUN 7: Message Hydration'da Fallback Yok

### Nerede Olduğu
`ui-new/src/components/chat/ChatArea.tsx` - Hydration effect'i

### Sebep (Root Cause)

Sayfa yenilendiğinde mesajları yeniden yüklemek için hydration yapılıyor:

```typescript
useEffect(() => {
    if (currentConversationId && messages.length === 0 && !isLoadingHistory) {
        const hydrateMessages = async () => {
            try {
                const freshMessages = await chatApi.getMessages(currentConversationId)
                setMessages(freshMessages)
            } catch (error) {
                console.error('[ChatArea] Hydration failed:', error)
                // ← SORUN: Hata olsa bile hiçbir şey yapılmıyor
                // Kullanıcıya bildirim yok
                // Yeniden deneme yok
                // Fallback yok
            }
        }
        hydrateMessages()
    }
}, [...])
```

**Neden Sorun?**
1. Hydration başarısız olursa, mesajlar boş kalıyor
2. Kullanıcı bilmiyor ki hydration başarısız oldu
3. Yeniden deneme mekanizması yok
4. Sadece console'a log yazılıyor

### Sonuç (Impact)

**Senaryo 1: Ağ Hatası**
```
1. Kullanıcı mesaj gönderir
2. Sayfa yenilenir
3. Hydration başarısız olur (ağ hatası)
4. Mesajlar boş kalıyor
5. Kullanıcı: "Mesajlar nerede? Gönderdiğim mesaj kayboldu mu?"
6. Kullanıcı panik yaşıyor
```

**Senaryo 2: Sunucu Hatası**
```
1. Kullanıcı konuşmayı açıyor
2. Sayfa yenilenir
3. Sunucu 500 hatası döndürür
4. Hydration başarısız
5. Mesajlar boş
6. Kullanıcı: "Konuşma silindi mi?"
```

**Senaryo 3: Timeout**
```
1. Kullanıcı sayfa yenilenir
2. Hydration çok uzun sürüyor
3. Timeout oluyor
4. Mesajlar boş kalıyor
5. Kullanıcı: "Uygulama dondu mu?"
```

### Önem Derecesi
🟡 **ORTA** - UX sorunu, veri kaybı yok

---

## SORUN 8: Stream Error Handling Eksikliği

### Nerede Olduğu
`ui-new/src/components/chat/ChatInput.tsx` - Stream okuma döngüsü

### Sebep (Root Cause)

AI'dan cevap stream olarak geliyor. Stream okuma döngüsü:

```typescript
if (reader) {
    while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        // ... işle ...
    }
} else {
    console.error('[Chat] No response body reader')
}
```

**Neden Sorun?**
1. Stream sırasında ağ hatası olursa, hiçbir şey yapılmıyor
2. Stream timeout yok - sonsuza kadar bekleyebilir
3. Kısmi mesajlar kayboluyor
4. Hata yakalanmıyor

### Sonuç (Impact)

**Senaryo 1: Ağ Hatası Stream Sırasında**
```
1. Kullanıcı mesaj gönderir
2. AI cevap vermeye başlıyor
3. Stream sırasında ağ kesilir
4. reader.read() hata fırlatır
5. Hiçbir error handling yok
6. Kısmi cevap kayboluyor
7. Kullanıcı: "Cevap nerede?"
```

**Senaryo 2: Yavaş Stream**
```
1. Kullanıcı mesaj gönderir
2. AI cevap vermeye başlıyor
3. Stream çok yavaş (30 saniye)
4. UI donuyor
5. Timeout yok
6. Kullanıcı: "Uygulama dondu mu?"
```

**Senaryo 3: Kısmi Mesaj**
```
1. Kullanıcı mesaj gönderir
2. AI: "Merhaba, ben bir yapay zeka..."
3. Stream kesilir
4. Sadece "Merhaba, ben bir" kayboluyor
5. Kullanıcı: "Cevap eksik mi?"
```

### Önem Derecesi
🔴 **YÜKSEK** - Core chat işlevini etkiler

---

## SORUN 9: useConversations Hook'ta Error Handling Yok

### Nerede Olduğu
`ui-new/src/hooks/useConversations.ts`

### Sebep (Root Cause)

Konuşmaları yüklemek için hook kullanılıyor:

```typescript
export function useConversations() {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['conversations'],
        queryFn: async () => {
            const conversations = await chatApi.getConversations()
            return conversations
        },
    })

    useEffect(() => {
        if (data) {
            setConversations(data)
        }
    }, [data, setConversations])

    // ← SORUN: error var ama hiçbir şey yapılmıyor
    
    return {
        conversations: data || [],
        isLoading,
        error,  // ← Döndürülüyor ama kullanılmıyor
        refresh: refetch
    }
}
```

**Neden Sorun?**
1. `error` var ama hiçbir şey yapılmıyor
2. Kullanıcıya bildirim yok
3. Yeniden deneme mekanizması yok
4. Sidebar'da konuşma listesi boş kalıyor

### Sonuç (Impact)

**Senaryo 1: Ağ Hatası**
```
1. Uygulama başlatılıyor
2. Konuşmaları yüklemek için API çağrısı yapılıyor
3. İnternet kesilir
4. error oluşuyor
5. Hiçbir şey yapılmıyor
6. Sidebar boş kalıyor
7. Kullanıcı: "Konuşmalar nerede?"
```

**Senaryo 2: Sunucu Hatası**
```
1. Kullanıcı uygulamayı açıyor
2. Sunucu 500 hatası döndürüyor
3. error oluşuyor
4. Sidebar boş kalıyor
5. Kullanıcı: "Uygulama çalışmıyor mu?"
```

**Senaryo 3: Timeout**
```
1. Kullanıcı uygulamayı açıyor
2. API çağrısı çok uzun sürüyor
3. Timeout oluyor
4. error oluşuyor
5. Sidebar boş kalıyor
6. Kullanıcı: "Neden yüklemiyor?"
```

### Önem Derecesi
🟡 **ORTA** - UX sorunu

---

## Özet Tablosu

| Sorun | Konum | Önem | Tür | Etki |
|-------|-------|------|-----|------|
| 4 | API Client | 🔴 YÜKSEK | Hata Yönetimi | Güvenilirlik |
| 5 | ChatInput | 🔴 YÜKSEK | Hata Yönetimi | UX |
| 6 | MessageBubble | 🔴 YÜKSEK | Memory Leak | Performans |
| 7 | ChatArea | 🟡 ORTA | Hata Yönetimi | UX |
| 8 | ChatInput | 🔴 YÜKSEK | Hata Yönetimi | Güvenilirlik |
| 9 | useConversations | 🟡 ORTA | Hata Yönetimi | UX |

---

## Sebep-Sonuç Özeti

### Genel Patern

**Sebep** → **Sonuç** → **Kullanıcı Etkisi**

1. **Sorun 4**: Retry/Timeout yok → Ağ hatası → Uygulama çöker
2. **Sorun 5**: Boş catch bloğu → Hata gizleniyor → Kullanıcı bilmiyor
3. **Sorun 6**: Interval temizlenmiyor → Bellek sızıntısı → Uygulama yavaşlıyor
4. **Sorun 7**: Fallback yok → Hydration başarısız → Mesajlar kaybolmuş görünüyor
5. **Sorun 8**: Stream error handling yok → Kısmi mesaj → Cevap eksik
6. **Sorun 9**: Error handling yok → Konuşmalar yüklenmiyor → Sidebar boş

### Ortak Tema

Hepsi **hata yönetimi eksikliği** veya **resource cleanup eksikliği** nedeniyle oluşuyor.

---

## Sonraki Adımlar

1. **Sorun 4**: API client'a retry + timeout ekle
2. **Sorun 5**: ChatInput catch bloğuna error handling ekle
3. **Sorun 6**: MessageBubble polling'e cleanup ekle
4. **Sorun 7**: ChatArea hydration'a fallback + notification ekle
5. **Sorun 8**: Stream error handling + timeout ekle
6. **Sorun 9**: useConversations'a error handling ekle

**Tamamlanacak**: 6 sorun, 5 dosya, ~200 satır kod

