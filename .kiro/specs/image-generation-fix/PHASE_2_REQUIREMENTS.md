# FAZE 2: Concurrent Job Handling & Queue Position Dynamics

## Genel Bakış

FAZE 2, birden fazla job'un aynı anda işlenmesini ve queue position'ın dinamik olarak güncellenmesini sağlar.

**Süre**: 4-5 saat
**Etki**: YÜKSEK - Kullanıcı deneyimi
**Risk**: DÜŞÜK - İzole değişiklikler
**Bağımlılık**: FAZE 1 (persistence)

---

## Gereksinimler

### Requirement 1: Concurrent Job Processing

**User Story**: Kullanıcı olarak, birden fazla resim oluşturma isteği gönderebilmek istiyorum, böylece paralel işleme yapılabilir.

#### Acceptance Criteria

1. WHEN birden fazla job kuyruğa eklendiğinde, THEN her job'a benzersiz bir queue_position atanmalı
2. WHEN bir job processing başladığında, THEN diğer job'lar kuyruğa kalmalı ve sırayla işlenmelidir
3. WHEN bir job tamamlandığında, THEN kalan job'lar sırayla işlenmeye devam etmeli
4. WHEN bir job hata verdiğinde, THEN sonraki job otomatik olarak işlenmeye başlamalı
5. WHEN aynı anda 5+ job gönderildiğinde, THEN tüm job'lar kuyruğa alınmalı ve sırayla işlenmelidir

---

### Requirement 2: GPU Lock Mechanism

**User Story**: Sistem yöneticisi olarak, GPU'nun aynı anda sadece bir job tarafından kullanılmasını sağlamak istiyorum.

#### Acceptance Criteria

1. WHEN bir job processing başladığında, THEN GPU lock alınmalı
2. WHEN job tamamlandığında, THEN GPU lock serbest bırakılmalı
3. WHEN job hata verdiğinde, THEN GPU lock serbest bırakılmalı
4. WHEN GPU lock tutuluyorken başka bir job processing başlamaya çalışırsa, THEN beklemelidir
5. WHEN GPU lock 30 saniyeden fazla tutulursa, THEN timeout uyarısı loglanmalı

---

### Requirement 3: Queue Position Persistence

**User Story**: Kullanıcı olarak, sayfa yenilendiğinde queue position'ımı görebilmek istiyorum.

#### Acceptance Criteria

1. WHEN job kuyruğa eklendiğinde, THEN queue_position database'e persist edilmeli
2. WHEN job processing başladığında, THEN queue_position 0'a güncellenmeli
3. WHEN job tamamlandığında, THEN queue_position 0'a set edilmeli
4. WHEN sayfa yenilendiğinde, THEN queue_position database'den yüklenmelidir
5. WHEN concurrent update'ler olduğunda, THEN veri kaybı olmamali (deep merge)

---

### Requirement 4: Dynamic Queue Position Calculation

**User Story**: Kullanıcı olarak, queue position'ımın gerçek zamanlı olarak güncellenmesini görmek istiyorum.

#### Acceptance Criteria

1. WHEN bir job tamamlandığında, THEN kalan job'ların position'ları otomatik güncellenmeli
2. WHEN yeni job kuyruğa eklendiğinde, THEN tüm job'ların position'ları yeniden hesaplanmalı
3. WHEN WebSocket mesajı alındığında, THEN UI position'ları güncellemeli
4. WHEN sayfa yenilendiğinde, THEN position'lar database'den hesaplanmalı
5. WHEN concurrent job'lar olduğunda, THEN position'lar tutarlı olmalı

---

### Requirement 5: Job State Transitions

**User Story**: Sistem yöneticisi olarak, job'ların tüm state geçişlerini takip etmek istiyorum.

#### Acceptance Criteria

1. WHEN job oluşturulduğunda, THEN status "pending" olmalı
2. WHEN job kuyruğa eklendiğinde, THEN status "queued" olmalı
3. WHEN job processing başladığında, THEN status "processing" olmalı
4. WHEN job tamamlandığında, THEN status "complete" olmalı
5. WHEN job hata verdiğinde, THEN status "error" olmalı
6. WHEN state geçişi olduğunda, THEN timestamp güncellenmeli

---

### Requirement 6: Error Recovery

**User Story**: Kullanıcı olarak, bir job hata verirse sonraki job'un otomatik olarak işlenmesini istiyorum.

#### Acceptance Criteria

1. WHEN bir job timeout'a uğrarsa, THEN error status set edilmeli
2. WHEN error status set edildiğinde, THEN sonraki job otomatik olarak işlenmeye başlamalı
3. WHEN error message persist edildiğinde, THEN kullanıcı görebilmeli
4. WHEN hata sonrası sayfa yenilendiğinde, THEN error message korunmalı
5. WHEN retry mekanizması aktifse, THEN job otomatik retry edilmeli

---

### Requirement 7: Concurrent Update Safety

**User Story**: Geliştirici olarak, concurrent update'lerde veri kaybı olmadığından emin olmak istiyorum.

#### Acceptance Criteria

1. WHEN aynı message'a concurrent update'ler yapılırsa, THEN deep merge kullanılmalı
2. WHEN metadata field'ları update edilirse, THEN mevcut field'lar korunmalı
3. WHEN new field'lar eklenir, THEN eski field'lar silinmemeli
4. WHEN timestamp update edilirse, THEN updated_at otomatik set edilmeli
5. WHEN transaction fail'erse, THEN rollback yapılmalı

---

### Requirement 8: WebSocket Queue Position Updates

**User Story**: Kullanıcı olarak, queue position değişikliklerini WebSocket üzerinden almak istiyorum.

#### Acceptance Criteria

1. WHEN job kuyruğa eklendiğinde, THEN WebSocket "queued" mesajı gönderilmeli
2. WHEN job processing başladığında, THEN WebSocket "processing" mesajı gönderilmeli
3. WHEN job tamamlandığında, THEN WebSocket "complete" mesajı gönderilmeli
4. WHEN job hata verdiğinde, THEN WebSocket "error" mesajı gönderilmeli
5. WHEN queue_position değişirse, THEN WebSocket mesajında güncellenmiş position olmalı

---

### Requirement 9: Performance & Scalability

**User Story**: Sistem yöneticisi olarak, sistem 100+ concurrent job'u handle edebilmeli.

#### Acceptance Criteria

1. WHEN 100 job kuyruğa eklenirse, THEN tüm job'lar persist edilmeli
2. WHEN queue position hesaplanırsa, THEN 100ms'den hızlı olmalı
3. WHEN concurrent update'ler olursa, THEN database lock timeout'u olmamali
4. WHEN job processing'de, THEN memory leak olmamali
5. WHEN 1000+ message'lar database'de olursa, THEN query performance etkilenmemeli

---

## Glossary

- **Job**: Resim oluşturma isteği
- **Queue Position**: Job'un kuyruktaki sırası (1-based)
- **GPU Lock**: GPU'nun sadece bir job tarafından kullanılmasını sağlayan mekanizma
- **Deep Merge**: Mevcut metadata'yı koruyarak yeni field'ları ekleyen merge işlemi
- **State Transition**: Job'un bir durumdan diğerine geçmesi
- **Concurrent Update**: Aynı message'a aynı anda yapılan birden fazla update
- **Persistence**: Veri tabanına kaydetme
- **WebSocket**: Real-time iletişim protokolü

---

## Implementation Notes

### Backend Changes Required

1. **app/image/job_queue.py**
   - GPU lock mekanizması
   - Concurrent job handling
   - Queue position persistence

2. **app/image/flux_stub.py**
   - State transition logging
   - Error recovery
   - Message persistence

3. **app/memory/conversation.py**
   - Deep merge (FAZE 1'den)
   - Concurrent update safety

### Frontend Changes Required

1. **ui-new/src/components/chat/ImageProgressCard.tsx**
   - Dynamic queue position calculation
   - Real-time position updates

2. **ui-new/src/stores/imageJobsStore.ts**
   - All jobs tracking
   - Queue position calculation

### Database Changes

- Message.extra_metadata'da queue_position field'ı
- Message.extra_metadata'da job_id field'ı
- Message.extra_metadata'da status field'ı

---

## Testing Strategy

### Unit Tests (Backend)
- Deep merge logic
- Queue position calculation
- State transitions
- Error handling

### Integration Tests (Backend)
- Concurrent job processing
- GPU lock mechanism
- Message persistence
- Error recovery

### Component Tests (Frontend)
- Queue position display
- Real-time updates
- Page reload recovery

### E2E Tests
- Full workflow: submit → queue → processing → complete
- Multiple concurrent jobs
- Error scenarios
- Page reload recovery

---

## Success Criteria

- ✅ Tüm 9 requirement'ın acceptance criteria'ları geçmeli
- ✅ 30+ test case'i geçmeli (unit + integration + component + E2E)
- ✅ Hiçbir data loss olmamali
- ✅ Concurrent job'lar doğru sırayla işlenmeli
- ✅ Queue position'lar dinamik olarak güncellenmelidir
- ✅ Page reload'dan sonra state korunmalı
- ✅ Production-ready kod olmalı
- ✅ Hiçbir regression olmamali

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Concurrent update data loss | HIGH | Deep merge + transaction |
| GPU lock deadlock | MEDIUM | Timeout + monitoring |
| Queue position inconsistency | MEDIUM | Database persistence |
| WebSocket message loss | LOW | Retry mechanism |
| Performance degradation | MEDIUM | Query optimization |

---

## Timeline

- **Task 1**: GPU Lock Mechanism (1 saat)
- **Task 2**: Concurrent Job Processing (1.5 saat)
- **Task 3**: Queue Position Persistence (1 saat)
- **Task 4**: Dynamic Position Calculation (1 saat)
- **Task 5**: Testing & Verification (1.5 saat)

**Total**: 5.5 saat

---

## Deliverables

1. ✅ Production-ready backend code
2. ✅ Production-ready frontend code
3. ✅ 30+ test case'i (tümü geçmiş)
4. ✅ Comprehensive documentation
5. ✅ No regressions
6. ✅ Performance verified
