import logging
import sys
from pathlib import Path
from typing import List, Optional

from gi.repository import Adw, Gdk, Gtk


class StyleManagerError(Exception):
    """Custom exception for errors raised by the StyleManager."""
    pass


class StyleManager:
    """
    Manages CSS styling for the Proton-Coop GUI application.

    This class handles loading, applying, and managing CSS stylesheets.
    It supports loading from files and strings, handling theme changes
    automatically, and providing fallbacks for frozen executables.
    """

    def __init__(self, styles_dir: Optional[Path] = None):
        """
        Initializes the StyleManager.

        Args:
            styles_dir (Optional[Path]): The path to the styles directory.
                If None, it defaults to the 'styles' directory alongside this
                script or within the PyInstaller bundle.

        Raises:
            StyleManagerError: If the styles directory cannot be found and
                               no fallback is possible.
        """
        self.logger = logging.getLogger(__name__)
        self._styles_dir = styles_dir or self._get_default_styles_dir()
        self._providers: List[Gtk.CssProvider] = []
        self._applied_styles: List[str] = []
        self._theme_provider: Optional[Gtk.CssProvider] = None

        if not self._styles_dir.exists():
            self.logger.warning(f"Styles directory not found: {self._styles_dir}")
            if getattr(sys, 'frozen', False):
                self._use_fallback_styles = True
            else:
                raise StyleManagerError(f"Styles directory not found: {self._styles_dir}")
        else:
            self._use_fallback_styles = False

        try:
            adw_style_manager = Adw.StyleManager.get_default()
            adw_style_manager.connect("notify::dark", self._on_system_theme_changed)
        except Exception as e:
            self.logger.warning(f"Could not connect to Adwaita StyleManager: {e}")

    @staticmethod
    def _get_default_styles_dir() -> Path:
        """Determines the default directory for styles."""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS) / 'src' / 'gui' / 'styles'
        return Path(__file__).parent

    def load_default_styles(self) -> None:
        """
        Loads all default CSS files in a predefined order.

        This ensures a consistent styling cascade, with base styles applied
        first, followed by component, layout, and interaction styles.
        """
        default_styles = ['base.css', 'components.css', 'layout.css', 'interactions.css']
        for style_file in default_styles:
            try:
                self.load_css_file(style_file)
            except StyleManagerError as e:
                self.logger.warning(f"Failed to load default style {style_file}: {e}")
        self._load_theme_specific_styles()

    def load_css_file(self, filename: str) -> None:
        """
        Loads a CSS file from the styles directory and applies it globally.

        Args:
            filename (str): The name of the CSS file to load.

        Raises:
            StyleManagerError: If the file cannot be found, loaded, or applied.
        """
        css_path = self._styles_dir / filename
        if not css_path.exists():
            if self._use_fallback_styles:
                self.logger.warning(f"CSS file not found: {css_path}. Using fallback.")
                self._load_fallback_css(filename)
                return
            raise StyleManagerError(f"CSS file not found: {css_path}")

        try:
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path(str(css_path))
            display = Gdk.Display.get_default()
            if not display:
                raise StyleManagerError("No default GDK display available.")

            Gtk.StyleContext.add_provider_for_display(
                display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            self._providers.append(css_provider)
            self._applied_styles.append(filename)
            self.logger.info(f"Successfully loaded CSS file: {filename}")
        except Exception as e:
            raise StyleManagerError(f"Failed to load CSS file {filename}: {e}") from e

    def load_css_from_string(self, css_content: str, identifier: str = "custom") -> None:
        """
        Loads CSS from a string and applies it globally.

        Args:
            css_content (str): The CSS rules to apply.
            identifier (str): A name to identify this style block.

        Raises:
            StyleManagerError: If the CSS string is invalid or cannot be applied.
        """
        try:
            css_provider = Gtk.CssProvider()
            css_provider.load_from_data(css_content.encode('utf-8'))
            display = Gdk.Display.get_default()
            if not display:
                raise StyleManagerError("No default GDK display available.")

            Gtk.StyleContext.add_provider_for_display(
                display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            self._providers.append(css_provider)
            self._applied_styles.append(identifier)
            self.logger.info(f"Successfully loaded CSS from string: {identifier}")
        except Exception as e:
            raise StyleManagerError(f"Failed to load CSS from string {identifier}: {e}") from e

    def reload_styles(self) -> None:
        """
        Reloads all previously applied styles from their original sources.

        This is useful for live-editing styles during development.
        """
        self.logger.info("Reloading all styles...")
        styles_to_reload = self._applied_styles.copy()
        self.clear_styles()
        for style in styles_to_reload:
            if style.endswith('.css'):
                try:
                    self.load_css_file(style)
                except StyleManagerError as e:
                    self.logger.error(f"Failed to reload style {style}: {e}")

    def clear_styles(self) -> None:
        """Removes all CSS providers managed by this instance."""
        display = Gdk.Display.get_default()
        if not display:
            return
        for provider in self._providers:
            Gtk.StyleContext.remove_provider_for_display(display, provider)
        self._providers.clear()
        self._applied_styles.clear()
        self.logger.info("Cleared all applied styles.")

    def _on_system_theme_changed(self, style_manager, param):
        """Callback for when the system's dark/light theme preference changes."""
        is_dark = style_manager.get_dark()
        self.logger.info(f"System theme changed to: {'dark' if is_dark else 'light'}")
        self._load_theme_specific_styles()

    def _load_theme_specific_styles(self):
        """Loads a theme-specific CSS file (e.g., theme-dark.css) if available."""
        if self._theme_provider:
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.remove_provider_for_display(display, self._theme_provider)
            self._theme_provider = None

        adw_style_manager = Adw.StyleManager.get_default()
        if adw_style_manager.get_dark():
            theme_file = "theme-dark.css"
            theme_path = self._styles_dir / theme_file
            if theme_path.exists():
                try:
                    provider = Gtk.CssProvider()
                    provider.load_from_path(str(theme_path))
                    display = Gdk.Display.get_default()
                    if display:
                        Gtk.StyleContext.add_provider_for_display(
                            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
                        )
                        self._theme_provider = provider
                        self.logger.info("Applied dark theme styling.")
                except Exception as e:
                    self.logger.error(f"Failed to load dark theme CSS: {e}")

    def _load_fallback_css(self, filename: str) -> None:
        """Loads a minimal, hardcoded CSS as a fallback."""
        fallback_css = """
        .suggested-action { background: #3584e4; color: white; }
        .destructive-action { background: #e01b24; color: white; }
        """
        try:
            self.load_css_from_string(fallback_css, f"fallback-{filename}")
        except StyleManagerError as e:
            self.logger.error(f"Failed to load fallback CSS: {e}")


_style_manager_instance: Optional[StyleManager] = None


def get_style_manager() -> StyleManager:
    """
    Provides access to the global singleton instance of the StyleManager.

    Returns:
        StyleManager: The singleton StyleManager instance.
    """
    global _style_manager_instance
    if _style_manager_instance is None:
        _style_manager_instance = StyleManager()
    return _style_manager_instance


def initialize_styles() -> None:
    """
    Initializes the global style manager and loads the default styles.

    This function should be called once during application startup.
    """
    try:
        style_manager = get_style_manager()
        style_manager.load_default_styles()
    except StyleManagerError as e:
        logging.getLogger(__name__).warning(f"Failed to initialize styles: {e}")
