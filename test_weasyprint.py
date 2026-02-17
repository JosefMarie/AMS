try:
    from weasyprint import HTML
    print("WeasyPrint imported successfully!")
except OSError as e:
    print(f"WeasyPrint failed: {e}")
except ImportError as e:
    print(f"ImportError: {e}")
