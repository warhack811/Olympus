import sys
import unittest
from pathlib import Path

# Proje kök dizinini path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))


class TestPluginLoad(unittest.TestCase):
    def setUp(self):
        # Cache'i temizle
        from app.core import feature_flags

        feature_flags._flags_cache = {}
        feature_flags._loaded = False

    def test_import(self):
        """Plugin modülü import edilebiliyor mu?"""
        try:
            from app.plugins.beautiful_response.plugin import BeautifulResponsePlugin

            plugin = BeautifulResponsePlugin()
            self.assertEqual(plugin.name, "beautiful_response")
        except ImportError as e:
            self.fail(f"Plugin import edilemedi: {e}")

    def test_registry(self):
        """Plugin sisteme kayıtlı mı?"""
        from app.plugins import get_plugin, load_plugins

        # Pluginleri yükle
        load_plugins()

        plugin = get_plugin("beautiful_response")
        self.assertIsNotNone(plugin, "Beautiful Response plugin registry'de bulunamadı")
        self.assertEqual(plugin.name, "beautiful_response")

    def test_feature_flag(self):
        """Feature flag doğru çalışıyor mu?"""
        from app.core.feature_flags import feature_enabled, set_feature_flag

        # Varsayılan olarak kapalı olmalı (json'a göre)
        # Ancak test ortamında json okuma garantisi olmadığı için set ile emin olalım

        # Açık yap
        set_feature_flag("beautiful_response_enabled", True)
        self.assertTrue(feature_enabled("beautiful_response_enabled"))

        # Kapalı yap
        set_feature_flag("beautiful_response_enabled", False)
        self.assertFalse(feature_enabled("beautiful_response_enabled"))

    def test_is_enabled(self):
        """Plugin.is_enabled() feature flag'i kullanıyor mu?"""
        from app.core.feature_flags import set_feature_flag
        from app.plugins.beautiful_response.plugin import BeautifulResponsePlugin

        plugin = BeautifulResponsePlugin()

        set_feature_flag("beautiful_response_enabled", True)
        self.assertTrue(plugin.is_enabled())

        set_feature_flag("beautiful_response_enabled", False)
        self.assertFalse(plugin.is_enabled())


if __name__ == "__main__":
    unittest.main()
