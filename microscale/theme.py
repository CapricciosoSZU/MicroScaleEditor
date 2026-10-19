"""A complete application palette, independent of the Windows light/dark theme."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette


def apply_dark_theme(app):
    # Native Windows widget styles can ignore palette roles for individual controls.
    # Fusion uses the same explicit palette for lists, forms, menus and dialogs.
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    app.setStyle("Fusion")
    palette = QPalette()
    colors = {
        "Window": "#202630", "WindowText": "#e6edf5",
        "Base": "#262d38", "AlternateBase": "#2e3744", "Text": "#e6edf5",
        "Button": "#343e4d", "ButtonText": "#e6edf5",
        "Light": "#617187", "Midlight": "#465367", "Dark": "#161c25",
        "Mid": "#455162", "Shadow": "#0b1018", "BrightText": "#ff8392",
        "Highlight": "#79c7dc", "HighlightedText": "#14212d", "Accent": "#79c7dc",
        "ToolTipBase": "#303a49", "ToolTipText": "#e6edf5",
        "Link": "#8bd6e8", "LinkVisited": "#cfb8f4", "PlaceholderText": "#abb8c9",
    }
    for role, color in colors.items():
        palette.setColor(QPalette.ColorGroup.All, getattr(QPalette.ColorRole, role), QColor(color))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#b1bbc8"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor("#455162"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor("#e6edf5"))
    app.setPalette(palette)
    # Keep layout styling app-wide too, including top-level Qt dialogs. Colors are
    # owned by the palette so enabled, inactive and disabled states stay coherent.
    app.setStyleSheet("""
        QTabWidget::pane { border: 1px solid #455162; }
        QPushButton { padding: 5px 8px; }
        QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QListWidget, QPlainTextEdit { min-height: 23px; }
        QGroupBox { margin-top: 12px; padding-top: 14px; }
    """)
