# ATLAS Router Sandbox (MAMI v4)

ATLAS (Autonomous Thinking & Logical Analysis System) projesinin yüksek performanslı, gözlemlenebilir ve güvenli yönlendirme (routing) merkezi.

## 🚀 Öne Çıkan Özellikler

- **Multi-Model Orchestrator:** Gemini 2.0 Flash tabanlı akıllı görev dağıtımı.
- **DAG Executor:** Görevleri bağımlılıklarına göre paralel veya ardışık çalıştıran motor.
- **Kalkan (Safety Gate):** PII redaksiyonu, Prompt Injection engelleme ve içerik denetimi.
- **Gelişmiş Gözlenebilirlik:** Her yanıt için detaylı RDR (Routing Decision Record) raporu ve Cyberpunk UI.
- **Hafıza Katmanı:** Neo4j Graph DB entegrasyonu ile kullanıcı odaklı bilgi saklama.

## 🛠️ Kurulum

1. **Bağımlılıkları Yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Çevresel Değişkenleri Hazırlayın:**
   `.env` dosyasını ana dizinde oluşturun veya güncelleyin:
   ```env
   GROQ_API_KEY=your_key_here
   NEO4J_URI=neo4j+s://your_db_id.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```

3. **Sistemi Başlatın:**
   ```bash
   python -m uvicorn sandbox_router.api:app --reload --port 8080
   ```

4. **Arayüze Erişin:**
   Tarayıcınızdan `http://localhost:8080` adresini açarak Cyberpunk temasındaki "Deep Inspector" panelini kullanmaya başlayın.

## 🧪 Test ve Analiz

### Stress Test (Yük Altında Test)
Sistemin aynı anda 5 farklı kullanıcıya nasıl yanıt verdiğini görmek için:
```bash
python -m tests.stress_test
```

### Maliyet Analizi
Sistem her RDR kaydı üzerinden tahmini maliyet hesaplaması yapabilir. `sandbox_router/cost_estimator.py` içerisindeki fiyatlandırma tablosunu projenize göre güncelleyebilirsiniz.

## 📁 Dizin Yapısı
- `sandbox_router/api.py`: FastAPI giriş noktası.
- `sandbox_router/orchestrator.py`: Zeka ve planlama katmanı.
- `sandbox_router/dag_executor.py`: Görev icra motoru.
- `sandbox_router/safety.py`: Güvenlik bariyeri.
- `sandbox_router/ui/`: Developer Dashboard arayüzü.

---
**ATLAS Framework** - Advanced Agentic Coding Project.