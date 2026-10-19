"""Exercise actual widgets after startup from light and dark platform palettes."""
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QMenu, QPushButton, QVBoxLayout

from microscale.gui import MainWindow


def contrast(a, b):
    def luminance(color):
        rgb = [color.redF(), color.greenF(), color.blueF()]
        rgb = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
        return sum(v * weight for v, weight in zip(rgb, (.2126, .7152, .0722)))
    lo, hi = sorted((luminance(a), luminance(b)))
    return (hi + .05) / (lo + .05)


@pytest.mark.parametrize("scheme", [Qt.ColorScheme.Light, Qt.ColorScheme.Dark], ids=["light", "dark"])
def test_editor_controls_keep_readable_dark_theme(qapp, tmp_path, scheme):
    # Reproduce the inherited platform palette before constructing the editor.
    qapp.setStyleSheet("")
    qapp.setStyle("Fusion")
    qapp.styleHints().setColorScheme(scheme)
    inherited = QPalette()
    background, foreground = ("#ffffff", "#000000") if scheme == Qt.ColorScheme.Light else ("#202020", "#eeeeee")
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button):
        inherited.setColor(role, QColor(background))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        inherited.setColor(role, QColor(foreground))
    qapp.setPalette(inherited)
    window = MainWindow()
    window.settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window.recovery_dir = tmp_path / "recovery"
    dialog = QDialog()  # App-owned top-level dialogs must also inherit the theme.
    layout = QVBoxLayout(dialog)
    label, field, button = QLabel("Dialog label"), QLineEdit("Readable text"), QPushButton("Disabled action")
    button.setEnabled(False)
    for widget in (label, field, button):
        layout.addWidget(widget)
    try:
        window.show()
        dialog.show()
        qapp.processEvents()
        assert qapp.styleHints().colorScheme() == Qt.ColorScheme.Dark
        surfaces = [window.image_list.viewport(), dialog]
        for index in range(window.properties.count()):
            window.properties.setCurrentIndex(index)
            qapp.processEvents()
            surfaces.append(window.properties.widget(index).widget())
        for widget in surfaces:
            palette = widget.palette()
            assert palette.color(widget.backgroundRole()).lightnessF() < .3
            assert contrast(palette.color(widget.foregroundRole()), palette.color(widget.backgroundRole())) >= 4.5
        # Check real painted pixels in the empty image list, not just QPalette.
        viewport = window.image_list.viewport()
        pixels = viewport.grab().toImage()
        assert pixels.pixelColor(pixels.width() // 2, pixels.height() // 2).lightnessF() < .3
        pairs = [(QPalette.ColorRole.Text, QPalette.ColorRole.Base),
                 (QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
                 (QPalette.ColorRole.ButtonText, QPalette.ColorRole.Button),
                 (QPalette.ColorRole.HighlightedText, QPalette.ColorRole.Highlight),
                 (QPalette.ColorRole.ToolTipText, QPalette.ColorRole.ToolTipBase),
                 (QPalette.ColorRole.PlaceholderText, QPalette.ColorRole.Base)]
        widgets = [window.menuBar(), window.progress, window.tool, window.tool.view(),
                   window.view_tabs.tabBar(), label, field, button, *window.findChildren(QMenu)]
        for widget in widgets:
            for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
                for fg, bg in pairs:
                    assert contrast(widget.palette().color(group, fg), widget.palette().color(group, bg)) >= 4.5
    finally:
        dialog.close()
        window.close()
        qapp.processEvents()
