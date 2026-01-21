"""
Grafana Entegrasyonu Test'leri

Bu test dosyası, Grafana dashboard'larının ve alert kurallarının
doğru şekilde konfigüre edilip edilmediğini test eder.

Test Kapsamı:
    - Dashboard'ların oluşturulduğu
    - Dashboard'ların veri gösterdiği
    - Alert'lerin konfigüre edildiği
    - Veri kaynaklarının bağlı olduğu
    - Dashboard panel'lerinin doğru sorguları kullandığı
"""

import json
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestGrafanaDashboards:
    """Grafana dashboard'ları test'leri."""

    @pytest.fixture
    def dashboard_dir(self):
        """Dashboard JSON dosyalarının dizini."""
        return Path("docker/grafana/provisioning/dashboards/json")

    @pytest.fixture
    def dashboards(self, dashboard_dir):
        """Tüm dashboard JSON dosyalarını yükle."""
        dashboards = {}
        for json_file in dashboard_dir.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                dashboards[json_file.stem] = json.load(f)
        return dashboards

    def test_dashboards_exist(self, dashboard_dir):
        """
        Dashboard JSON dosyalarının var olup olmadığını test et.
        
        For any Grafana setup, all required dashboard files should exist.
        """
        required_dashboards = [
            "api-performance",
            "error-rate",
            "system-metrics",
            "top-errors",
        ]
        
        for dashboard_name in required_dashboards:
            dashboard_file = dashboard_dir / f"{dashboard_name}.json"
            assert dashboard_file.exists(), f"Dashboard {dashboard_name} bulunamadı"

    def test_dashboard_structure(self, dashboards):
        """
        Dashboard JSON yapısının doğru olup olmadığını test et.
        
        For any dashboard JSON, it should have required fields like title, panels, and refresh.
        """
        required_fields = ["title", "panels", "refresh", "uid", "tags"]
        
        for dashboard_name, dashboard in dashboards.items():
            for field in required_fields:
                assert field in dashboard, f"{dashboard_name} dashboard'ında {field} alanı yok"

    def test_dashboard_has_panels(self, dashboards):
        """
        Dashboard'ların panel'leri olup olmadığını test et.
        
        For any dashboard, it should have at least one panel.
        """
        for dashboard_name, dashboard in dashboards.items():
            assert len(dashboard["panels"]) > 0, f"{dashboard_name} dashboard'ında panel yok"

    def test_dashboard_panels_have_targets(self, dashboards):
        """
        Dashboard panel'lerinin target'ları olup olmadığını test et.
        
        For any dashboard panel, it should have at least one target (query).
        """
        for dashboard_name, dashboard in dashboards.items():
            for idx, panel in enumerate(dashboard["panels"]):
                assert "targets" in panel, f"{dashboard_name} dashboard'ının {idx}. panel'inde targets yok"
                assert len(panel["targets"]) > 0, f"{dashboard_name} dashboard'ının {idx}. panel'inde target yok"

    def test_api_performance_dashboard(self, dashboards):
        """
        API Performance dashboard'ının doğru panel'leri içerip içermediğini test et.
        
        For the API Performance dashboard, it should have panels for response time and error rate.
        """
        dashboard = dashboards["api-performance"]
        
        # Dashboard başlığı kontrol et
        assert dashboard["title"] == "API Performance Dashboard"
        
        # Panel sayısı kontrol et (en az 3 panel olmalı)
        assert len(dashboard["panels"]) >= 3
        
        # Panel başlıklarını kontrol et
        panel_titles = [panel["title"] for panel in dashboard["panels"]]
        assert "API Response Time (95th percentile)" in panel_titles
        assert "Error Rate" in panel_titles
        assert "Request Rate by Status Code" in panel_titles

    def test_error_rate_dashboard(self, dashboards):
        """
        Error Rate dashboard'ının doğru panel'leri içerip içermediğini test et.
        
        For the Error Rate dashboard, it should have panels for error metrics.
        """
        dashboard = dashboards["error-rate"]
        
        # Dashboard başlığı kontrol et
        assert dashboard["title"] == "Error Rate Dashboard"
        
        # Panel sayısı kontrol et
        assert len(dashboard["panels"]) >= 3
        
        # Panel başlıklarını kontrol et
        panel_titles = [panel["title"] for panel in dashboard["panels"]]
        assert "Overall Error Rate" in panel_titles
        assert "Error Rate by Status Code" in panel_titles

    def test_system_metrics_dashboard(self, dashboards):
        """
        System Metrics dashboard'ının doğru panel'leri içerip içermediğini test et.
        
        For the System Metrics dashboard, it should have panels for CPU, memory, and disk.
        """
        dashboard = dashboards["system-metrics"]
        
        # Dashboard başlığı kontrol et
        assert dashboard["title"] == "System Metrics Dashboard"
        
        # Panel sayısı kontrol et
        assert len(dashboard["panels"]) >= 4
        
        # Panel başlıklarını kontrol et
        panel_titles = [panel["title"] for panel in dashboard["panels"]]
        assert "CPU Usage" in panel_titles
        assert "Memory Usage" in panel_titles
        assert "Disk Usage" in panel_titles

    def test_top_errors_dashboard(self, dashboards):
        """
        Top Errors dashboard'ının doğru panel'leri içerip içermediğini test et.
        
        For the Top Errors dashboard, it should have panels for error analysis.
        """
        dashboard = dashboards["top-errors"]
        
        # Dashboard başlığı kontrol et
        assert dashboard["title"] == "Top Errors Dashboard"
        
        # Panel sayısı kontrol et
        assert len(dashboard["panels"]) >= 3
        
        # Panel başlıklarını kontrol et
        panel_titles = [panel["title"] for panel in dashboard["panels"]]
        assert "Error Distribution by Level" in panel_titles
        assert "Top Error Modules" in panel_titles

    def test_dashboard_refresh_interval(self, dashboards):
        """
        Dashboard'ların refresh interval'ı ayarlanmış olup olmadığını test et.
        
        For any dashboard, it should have a refresh interval set (e.g., 30s).
        """
        for dashboard_name, dashboard in dashboards.items():
            assert "refresh" in dashboard, f"{dashboard_name} dashboard'ında refresh alanı yok"
            assert dashboard["refresh"] is not None, f"{dashboard_name} dashboard'ında refresh değeri yok"

    def test_dashboard_time_range(self, dashboards):
        """
        Dashboard'ların time range'i ayarlanmış olup olmadığını test et.
        
        For any dashboard, it should have a time range set (e.g., last 6 hours).
        """
        for dashboard_name, dashboard in dashboards.items():
            assert "time" in dashboard, f"{dashboard_name} dashboard'ında time alanı yok"
            assert "from" in dashboard["time"], f"{dashboard_name} dashboard'ında time.from alanı yok"
            assert "to" in dashboard["time"], f"{dashboard_name} dashboard'ında time.to alanı yok"

    def test_dashboard_tags(self, dashboards):
        """
        Dashboard'ların tag'leri olup olmadığını test et.
        
        For any dashboard, it should have tags for organization and categorization.
        """
        for dashboard_name, dashboard in dashboards.items():
            assert "tags" in dashboard, f"{dashboard_name} dashboard'ında tags alanı yok"
            assert len(dashboard["tags"]) > 0, f"{dashboard_name} dashboard'ında tag yok"
            assert "mami-ai" in dashboard["tags"], f"{dashboard_name} dashboard'ında mami-ai tag'i yok"


class TestGrafanaDataSources:
    """Grafana veri kaynakları test'leri."""

    @pytest.fixture
    def datasources_file(self):
        """Veri kaynakları konfigürasyon dosyası."""
        return Path("docker/grafana/provisioning/datasources/prometheus.yml")

    @pytest.fixture
    def datasources_config(self, datasources_file):
        """Veri kaynakları konfigürasyonunu yükle."""
        import yaml
        with open(datasources_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_datasources_file_exists(self, datasources_file):
        """
        Veri kaynakları konfigürasyon dosyasının var olup olmadığını test et.
        
        For any Grafana setup, the datasources configuration file should exist.
        """
        assert datasources_file.exists(), "Veri kaynakları konfigürasyon dosyası bulunamadı"

    def test_datasources_structure(self, datasources_config):
        """
        Veri kaynakları konfigürasyonunun yapısının doğru olup olmadığını test et.
        
        For any datasources configuration, it should have apiVersion and datasources.
        """
        assert "apiVersion" in datasources_config, "apiVersion alanı yok"
        assert "datasources" in datasources_config, "datasources alanı yok"
        assert len(datasources_config["datasources"]) > 0, "Veri kaynağı yok"

    def test_prometheus_datasource_exists(self, datasources_config):
        """
        Prometheus veri kaynağının var olup olmadığını test et.
        
        For any Grafana setup, Prometheus datasource should be configured.
        """
        datasources = datasources_config["datasources"]
        prometheus_ds = next((ds for ds in datasources if ds["name"] == "Prometheus"), None)
        
        assert prometheus_ds is not None, "Prometheus veri kaynağı bulunamadı"
        assert prometheus_ds["type"] == "prometheus", "Prometheus veri kaynağı türü yanlış"
        assert prometheus_ds["url"] == "http://prometheus:9090", "Prometheus URL'si yanlış"

    def test_elasticsearch_datasource_exists(self, datasources_config):
        """
        Elasticsearch veri kaynağının var olup olmadığını test et.
        
        For any Grafana setup, Elasticsearch datasource should be configured.
        """
        datasources = datasources_config["datasources"]
        es_ds = next((ds for ds in datasources if ds["name"] == "Elasticsearch"), None)
        
        assert es_ds is not None, "Elasticsearch veri kaynağı bulunamadı"
        assert es_ds["type"] == "elasticsearch", "Elasticsearch veri kaynağı türü yanlış"
        assert es_ds["url"] == "http://elasticsearch:9200", "Elasticsearch URL'si yanlış"

    def test_datasource_access_mode(self, datasources_config):
        """
        Veri kaynakları access mode'unun doğru olup olmadığını test et.
        
        For any datasource, access mode should be 'proxy' for security.
        """
        datasources = datasources_config["datasources"]
        for ds in datasources:
            assert ds["access"] == "proxy", f"{ds['name']} veri kaynağının access mode'u yanlış"


class TestGrafanaAlerts:
    """Grafana alert kuralları test'leri."""

    @pytest.fixture
    def alert_rules_file(self):
        """Alert kuralları dosyası."""
        return Path("docker/alert_rules.yml")

    @pytest.fixture
    def alert_rules(self, alert_rules_file):
        """Alert kurallarını yükle."""
        import yaml
        with open(alert_rules_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_alert_rules_file_exists(self, alert_rules_file):
        """
        Alert kuralları dosyasının var olup olmadığını test et.
        
        For any Prometheus setup, the alert rules file should exist.
        """
        assert alert_rules_file.exists(), "Alert kuralları dosyası bulunamadı"

    def test_alert_rules_structure(self, alert_rules):
        """
        Alert kurallarının yapısının doğru olup olmadığını test et.
        
        For any alert rules configuration, it should have groups with rules.
        """
        assert "groups" in alert_rules, "groups alanı yok"
        assert len(alert_rules["groups"]) > 0, "Alert grubu yok"

    def test_alert_group_structure(self, alert_rules):
        """
        Alert grubunun yapısının doğru olup olmadığını test et.
        
        For any alert group, it should have name, interval, and rules.
        """
        for group in alert_rules["groups"]:
            assert "name" in group, "Alert grubunda name alanı yok"
            assert "interval" in group, "Alert grubunda interval alanı yok"
            assert "rules" in group, "Alert grubunda rules alanı yok"
            assert len(group["rules"]) > 0, "Alert grubunda rule yok"

    def test_alert_rule_structure(self, alert_rules):
        """
        Alert kuralının yapısının doğru olup olmadığını test et.
        
        For any alert rule, it should have alert name, expr, for, labels, and annotations.
        """
        for group in alert_rules["groups"]:
            for rule in group["rules"]:
                assert "alert" in rule, "Alert kuralında alert alanı yok"
                assert "expr" in rule, "Alert kuralında expr alanı yok"
                assert "for" in rule, "Alert kuralında for alanı yok"
                assert "labels" in rule, "Alert kuralında labels alanı yok"
                assert "annotations" in rule, "Alert kuralında annotations alanı yok"

    def test_required_alerts_exist(self, alert_rules):
        """
        Gerekli alert'lerin var olup olmadığını test et.
        
        For any alert rules configuration, all required alerts should be defined.
        """
        required_alerts = [
            "HighErrorRate",
            "HighResponseTime",
            "HighDiskUsage",
            "HighMemoryUsage",
            "APIEndpointDown",
            "ElasticsearchDown",
            "PrometheusDown",
            "RedisDown",
        ]
        
        all_alerts = []
        for group in alert_rules["groups"]:
            for rule in group["rules"]:
                all_alerts.append(rule["alert"])
        
        for alert_name in required_alerts:
            assert alert_name in all_alerts, f"{alert_name} alert'i bulunamadı"

    def test_alert_severity_labels(self, alert_rules):
        """
        Alert'lerin severity label'ı olup olmadığını test et.
        
        For any alert rule, it should have a severity label (critical, warning, info).
        """
        valid_severities = ["critical", "warning", "info"]
        
        for group in alert_rules["groups"]:
            for rule in group["rules"]:
                assert "severity" in rule["labels"], f"{rule['alert']} alert'inde severity label'ı yok"
                assert rule["labels"]["severity"] in valid_severities, f"{rule['alert']} alert'inin severity'si geçersiz"

    def test_alert_annotations(self, alert_rules):
        """
        Alert'lerin annotation'ları olup olmadığını test et.
        
        For any alert rule, it should have summary and description annotations.
        """
        for group in alert_rules["groups"]:
            for rule in group["rules"]:
                annotations = rule["annotations"]
                assert "summary" in annotations, f"{rule['alert']} alert'inde summary annotation'ı yok"
                assert "description" in annotations, f"{rule['alert']} alert'inde description annotation'ı yok"

    def test_high_error_rate_alert(self, alert_rules):
        """
        HighErrorRate alert'inin doğru konfigüre edilip edilmediğini test et.
        
        For the HighErrorRate alert, it should trigger when error rate exceeds 5%.
        """
        all_rules = []
        for group in alert_rules["groups"]:
            all_rules.extend(group["rules"])
        
        high_error_rate = next((r for r in all_rules if r["alert"] == "HighErrorRate"), None)
        assert high_error_rate is not None, "HighErrorRate alert'i bulunamadı"
        
        # Expression'da 0.05 (5%) olmalı
        assert "0.05" in high_error_rate["expr"], "HighErrorRate alert'inde threshold yanlış"
        
        # For duration 5m olmalı
        assert high_error_rate["for"] == "5m", "HighErrorRate alert'inin for duration'ı yanlış"
        
        # Severity critical olmalı
        assert high_error_rate["labels"]["severity"] == "critical", "HighErrorRate alert'inin severity'si yanlış"

    def test_high_response_time_alert(self, alert_rules):
        """
        HighResponseTime alert'inin doğru konfigüre edilip edilmediğini test et.
        
        For the HighResponseTime alert, it should trigger when response time exceeds 5 seconds.
        """
        all_rules = []
        for group in alert_rules["groups"]:
            all_rules.extend(group["rules"])
        
        high_response_time = next((r for r in all_rules if r["alert"] == "HighResponseTime"), None)
        assert high_response_time is not None, "HighResponseTime alert'i bulunamadı"
        
        # Expression'da 5 (saniye) olmalı
        assert "5" in high_response_time["expr"], "HighResponseTime alert'inde threshold yanlış"
        
        # For duration 5m olmalı
        assert high_response_time["for"] == "5m", "HighResponseTime alert'inin for duration'ı yanlış"

    def test_api_endpoint_down_alert(self, alert_rules):
        """
        APIEndpointDown alert'inin doğru konfigüre edilip edilmediğini test et.
        
        For the APIEndpointDown alert, it should trigger when API is down for 5 minutes.
        """
        all_rules = []
        for group in alert_rules["groups"]:
            all_rules.extend(group["rules"])
        
        api_down = next((r for r in all_rules if r["alert"] == "APIEndpointDown"), None)
        assert api_down is not None, "APIEndpointDown alert'i bulunamadı"
        
        # Expression'da up == 0 olmalı
        assert "up{job=\"mami-ai\"} == 0" in api_down["expr"], "APIEndpointDown alert'inin expression'ı yanlış"
        
        # For duration 5m olmalı
        assert api_down["for"] == "5m", "APIEndpointDown alert'inin for duration'ı yanlış"
        
        # Severity critical olmalı
        assert api_down["labels"]["severity"] == "critical", "APIEndpointDown alert'inin severity'si yanlış"


class TestGrafanaProvisioning:
    """Grafana provisioning konfigürasyonu test'leri."""

    @pytest.fixture
    def dashboards_provisioning_file(self):
        """Dashboard provisioning konfigürasyon dosyası."""
        return Path("docker/grafana/provisioning/dashboards/dashboards.yml")

    @pytest.fixture
    def dashboards_provisioning(self, dashboards_provisioning_file):
        """Dashboard provisioning konfigürasyonunu yükle."""
        import yaml
        with open(dashboards_provisioning_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_dashboards_provisioning_file_exists(self, dashboards_provisioning_file):
        """
        Dashboard provisioning dosyasının var olup olmadığını test et.
        
        For any Grafana setup, the dashboards provisioning file should exist.
        """
        assert dashboards_provisioning_file.exists(), "Dashboard provisioning dosyası bulunamadı"

    def test_dashboards_provisioning_structure(self, dashboards_provisioning):
        """
        Dashboard provisioning yapısının doğru olup olmadığını test et.
        
        For any dashboards provisioning configuration, it should have apiVersion and providers.
        """
        assert "apiVersion" in dashboards_provisioning, "apiVersion alanı yok"
        assert "providers" in dashboards_provisioning, "providers alanı yok"
        assert len(dashboards_provisioning["providers"]) > 0, "Provider yok"

    def test_dashboard_provider_structure(self, dashboards_provisioning):
        """
        Dashboard provider'ının yapısının doğru olup olmadığını test et.
        
        For any dashboard provider, it should have name, type, and options.
        """
        for provider in dashboards_provisioning["providers"]:
            assert "name" in provider, "Provider'da name alanı yok"
            assert "type" in provider, "Provider'da type alanı yok"
            assert "options" in provider, "Provider'da options alanı yok"

    def test_dashboard_provider_type(self, dashboards_provisioning):
        """
        Dashboard provider'ının type'ının file olup olmadığını test et.
        
        For any dashboard provider, type should be 'file' for file-based provisioning.
        """
        for provider in dashboards_provisioning["providers"]:
            assert provider["type"] == "file", f"Provider {provider['name']}'inin type'ı yanlış"

    def test_dashboard_provider_path(self, dashboards_provisioning):
        """
        Dashboard provider'ının path'inin doğru olup olmadığını test et.
        
        For any dashboard provider, options should have a valid path.
        """
        for provider in dashboards_provisioning["providers"]:
            assert "path" in provider["options"], f"Provider {provider['name']}'inde path alanı yok"
            assert provider["options"]["path"] == "/etc/grafana/provisioning/dashboards/json", f"Provider {provider['name']}'inin path'i yanlış"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
