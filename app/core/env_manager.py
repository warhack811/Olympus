"""
Mami AI - Environment Variable Manager (.env)
=============================================

Bu modül, .env dosyasını güvenli bir şekilde okumak ve düzenlemek için kullanılır.
Dosyadaki yorum satırlarını ve boşlukları korumayı hedefler.

Kullanım:
    from app.core.env_manager import EnvManager

    manager = EnvManager()
    manager.set_key("GROQ_API_KEY_5", "gsk_...")
    manager.delete_key("OLD_KEY")
"""

import logging
import os
import shutil

logger = logging.getLogger(__name__)


class EnvManager:
    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path
        # Eğer dosya yoksa .env.example'dan veya boş oluştur
        if not os.path.exists(self.env_path):
            self._ensure_env_exists()

    def _ensure_env_exists(self):
        """Dosya yoksa oluşturur."""
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", self.env_path)
            logger.info("[ENV] .env dosyası .env.example'dan oluşturuldu.")
        else:
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("# Mami AI Configuration\n")
            logger.info("[ENV] Yeni .env dosyası oluşturuldu.")

    def _read_lines(self) -> list[str]:
        """Dosyayı satır satır okur."""
        try:
            with open(self.env_path, encoding="utf-8") as f:
                return f.readlines()
        except Exception as e:
            logger.error(f"[ENV] Okuma hatası: {e}")
            return []

    def _write_lines(self, lines: list[str]):
        """Dosyayı günceller."""
        try:
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            logger.error(f"[ENV] Yazma hatası: {e}")

    def get_all(self) -> dict[str, str]:
        """Tüm anahtar-değer çiftlerini döndürür (yorumlar hariç)."""
        data = {}
        for line in self._read_lines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                data[key.strip()] = val.strip().strip('"').strip("'")
        return data

    def get_key(self, key: str) -> str | None:
        """Belirli bir anahtarın değerini döndürür."""
        return self.get_all().get(key)

    def set_key(self, key: str, value: str):
        """Anahtarı günceller veya ekler."""
        lines = self._read_lines()
        updated = False
        new_lines = []

        # Değerde boşluk varsa tırnak içine al
        if " " in value and not (value.startswith('"') or value.startswith("'")):
            value_str = f'"{value}"'
        else:
            value_str = value

        for line in lines:
            stripped = line.strip()
            # Yorum satırı veya boş satır değilse ve key ile başlıyorsa
            if stripped and not stripped.startswith("#") and "=" in stripped:
                line_key = stripped.split("=", 1)[0].strip()
                if line_key == key:
                    new_lines.append(f"{key}={value_str}\n")
                    updated = True
                    continue
            new_lines.append(line)

        if not updated:
            # Dosya sonuna ekle
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(f"{key}={value_str}\n")

        self._write_lines(new_lines)
        logger.info(f"[ENV] Anahtar güncellendi: {key}")

    def delete_key(self, key: str):
        """Anahtarı siler."""
        lines = self._read_lines()
        new_lines = []
        found = False

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                line_key = stripped.split("=", 1)[0].strip()
                if line_key == key:
                    found = True
                    continue  # Satırı atla (sil)
            new_lines.append(line)

        if found:
            self._write_lines(new_lines)
            logger.info(f"[ENV] Anahtar silindi: {key}")
        else:
            logger.warning(f"[ENV] Silinecek anahtar bulunamadı: {key}")

    def get_groq_keys(self) -> list[dict[str, str]]:
        """Sadece GROQ_API_KEY ile başlayanları bulur."""
        all_vars = self.get_all()
        groq_keys = []
        for k, v in all_vars.items():
            if k.startswith("GROQ_API_KEY"):
                groq_keys.append({"key": k, "value": v})

        # Sıralama: GROQ_API_KEY, GROQ_API_KEY_BACKUP, GROQ_API_KEY_3...
        # Custom logic gerekebilir, şimdilik alfabetik
        return sorted(groq_keys, key=lambda x: x["key"])


# Singleton instance
env_manager = EnvManager()
