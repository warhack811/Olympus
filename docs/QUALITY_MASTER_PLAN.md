# 🏆 Mami AI - Kalite Maksimizasyonu Master Planı

**Tarih:** 19 Aralık 2025  
**Hedef:** Tüm sistemleri ChatGPT/Claude seviyesine çıkarmak  
**Versiyon:** 1.1 (Güncellendi)

---

## 📑 İÇİNDEKİLER

1. [Hafıza Sistemi](#1-hafiza-sistemi)
2. [Prompt Sistemi](#2-prompt-sistemi)
3. [Sohbet İşleme](#3-sohbet-isleme)
4. [Görsel Üretim](#4-gorsel-uretim)
5. [İnternet Arama](#5-internet-arama)
6. [Gelecek Hedefleri](#gelecek-hedefleri)

---

## 1. HAFIZA SİSTEMİ

### 🎯 Hedef: Kişisel asistan seviyesinde kullanıcı tanıma

### Mevcut Durum
- ✅ **Duplicate Detection:** Hibrit sistem (Semantic + Text + Entity) devreye alındı.
- ✅ **Memory Decider:** Gereksiz bilgilerin (genel kültür) kaydedilmesi engellendi.
- 🟡 **Structured Profile:** Henüz tam yapılandırılmış (JSON based) profil yapısı yok, free-text ve vector search kullanılıyor.

### Yapılacaklar
- [ ] Structured User Profile (JSON) tablosu oluşturmak.
- [ ] Memory Decay (Zamanla önem azalması) mekanizması.
- [ ] Çelişki yönetimi (Eski bilgiyi güncelleme).

---

## 2. PROMPT SİSTEMİ

### 🎯 Hedef: Tutarlı, doğal, kişiselleştirilmiş yanıtlar

### Mevcut Durum
- ✅ **5 Katmanlı Yapı:** Core, Persona, Preferences, Toggles, Safety katmanları aktif.
- ✅ **Dynamic Toggles:** Kullanıcı ayarına göre prompt parçacıkları eklenip çıkarılıyor.

### Yapılacaklar
- [ ] **Prompt Versioning:** Prompt değişikliklerinin versiyonlanması.
- [ ] **Context-Aware Prompting:** Sohbetin gidişatına göre dinamik talimat ekleme.

---

## 3. SOHBET İŞLEME

### 🎯 Hedef: Akıcı, bağlamsal, hatırlayan sohbetler

### Mevcut Durum
- ✅ **Streaming:** SSE ile akıcı yanıt gösterimi.
- 🟡 **Context Window:** Son N mesaj alınıyor ancak akıllı özetleme (sliding window + summary) henüz yok.

### Yapılacaklar
- [ ] **Sliding Window + Summary:** Token tasarrufu ve uzun bağlam koruma.
- [ ] **Regenerate:** Son mesajı farklı parametrelerle yeniden üretme.

---

## 4. GÖRSEL ÜRETİM

### 🎯 Hedef: Hızlı, kaliteli, kontrollü görsel üretim

### Mevcut Durum
- ✅ **Queue System:** UUID tabanlı, asenkron kuyruk sistemi.
- ✅ **Progress Tracking:** WebSocket ile anlık yüzdelik bildirim.
- ✅ **Error Handling:** `SafeCallback` ve `CircuitBreaker` ile hatalara karşı dirençli.

### Yapılacaklar
- [ ] **Batch Generation:** Tek seferde çoklu varyasyon.
- [ ] **Upscaling:** Çözünürlük artırma.

---

## 14. UYGULAMA ÖNCELİK SIRASI

### 🔴 ACİL (Güncel)
1. **Regenerate Endpoint:** Frontend butonu hazır, backend bekleniyor.
2. **Search Cache:** API maliyetlerini düşürmek ve hızı artırmak için.
3. **Structured User Profile:** Hafıza kalitesini artırmak için.

### 🟡 ÖNEMLİ
1. **ML Moderation:** Daha güvenli içerik kontrolü.
2. **Memory Decay:** Hafıza kirliliğini önleme.
3. **Routing Cache:** Tepki süresini iyileştirme.
