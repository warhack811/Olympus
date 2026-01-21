import sys
from datetime import datetime
from typing import Optional, Any

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Windows Encoding Fix
try:
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

class TerminalLogger:
    """
    Atlas Terminal Çıktı Yöneticisi
    Sistemin adımlarını renkli ve anlaşılır şekilde terminale basar.
    """
    
    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def step(emoji: str, title: str, details: Optional[str] = None):
        """Ana işlem adımı."""
        ts = TerminalLogger._timestamp()
        print(f"{Colors.CYAN}[{ts}]{Colors.ENDC} {emoji}  {Colors.BOLD}{title}{Colors.ENDC}")
        if details:
            print(f"           {Colors.BLUE}└─ {details}{Colors.ENDC}")

    @staticmethod
    def success(message: str):
        """Başarılı işlem."""
        print(f"           {Colors.GREEN}✔ {message}{Colors.ENDC}")

    @staticmethod
    def warning(message: str):
        """Uyarı mesajı."""
        print(f"           {Colors.WARNING}⚠️  {message}{Colors.ENDC}")

    @staticmethod
    def error(message: str, error: Optional[Any] = None):
        """Hata mesajı."""
        print(f"           {Colors.FAIL}❌ {message}{Colors.ENDC}")
        if error:
            print(f"           {Colors.FAIL}   Detay: {str(error)}{Colors.ENDC}")

    @staticmethod
    def info(message: str):
        """Bilgi mesajı."""
        print(f"           ℹ️  {message}")

    @staticmethod
    def section(title: str):
        """Bölüm başlığı."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== {title} ==={Colors.ENDC}")

    @staticmethod
    def legacy(message: str):
        """Legacy sistem mesajı (Gri/Sönük)."""
        # Gri ANSI kodu pek standart değil, Cyan kullanalım ama belirgin olsun
        print(f"{Colors.WARNING}[LEGACY] {message}{Colors.ENDC}")

# Global instance
log = TerminalLogger()
