import qrcode
import webbrowser
from pathlib import Path


class QRGenerator:
    """Generates QR codes for session URLs with terminal and image support."""

    @staticmethod
    def to_terminal(url: str) -> str:
        """Render QR as Unicode block characters for terminal display."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Capture the terminal output
        # Using the standard qrcode string output which uses unicode blocks
        # We need a small hack to get it as a string instead of printing
        import io
        f = io.StringIO()
        qr.print_ascii(out=f, invert=True)
        return f.getvalue()

    @staticmethod
    def to_png(url: str, path: Path, auto_open: bool = True) -> Path:
        """Save QR as PNG and optionally auto-open."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # Ensure parent directories exist
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(path))
        
        if auto_open:
            webbrowser.open(f"file://{path.absolute()}")
            
        return path
