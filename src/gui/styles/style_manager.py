"""
StyleManager - Professional CSS management for Linux-Coop GUI

This module provides a centralized way to manage and apply CSS styles
following SOLID principles for maintainable and modular styling.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional
from gi.repository import Gtk, Gdk, Adw


class StyleManagerError(Exception):
    """Custom exception for StyleManager errors"""
    pass


class StyleManager:
    """
    Manages CSS styling for the Linux-Coop GUI application.

    This class follows the Single Responsibility Principle by handling
    only CSS-related operations and the Dependency Inversion Principle
    by depending on abstractions (file paths) rather than concrete implementations.
    """

    def __init__(self, styles_dir: Optional[Path] = None):
        """
        Initialize the StyleManager.

        Args:
            styles_dir: Path to the styles directory. If None, uses default location.
        """
        self.logger = logging.getLogger(__name__)
        self._styles_dir = styles_dir or self._get_default_styles_dir()
        self._providers: List[Gtk.CssProvider] = []
        self._applied_styles: List[str] = []
        self._theme_provider: Optional[Gtk.CssProvider] = None

        # Validate styles directory
        if not self._styles_dir.exists():
            self.logger.warning(f"Styles directory not found: {self._styles_dir}")
            # In frozen executables, try to create a fallback
            if getattr(sys, 'frozen', False):
                self.logger.info("Running in frozen mode, attempting fallback CSS loading")
                self._use_fallback_styles = True
            else:
                raise StyleManagerError(f"Styles directory not found: {self._styles_dir}")
        else:
            self._use_fallback_styles = False

        # Connect to Adwaita style manager for automatic theme switching
        try:
            adw_style_manager = Adw.StyleManager.get_default()
            adw_style_manager.connect("notify::dark", self._on_system_theme_changed)
        except Exception as e:
            self.logger.warning(f"Could not connect to Adwaita StyleManager for theme detection: {e}")

    @staticmethod
    def _get_default_styles_dir() -> Path:
        """Get the default styles directory path."""
        # Check if running as PyInstaller bundle
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller bundle - use _MEIPASS directory
            return Path(sys._MEIPASS) / 'src' / 'gui' / 'styles'
        else:
            # Normal Python execution
            return Path(__file__).parent

    def load_default_styles(self) -> None:
        """
        Load all default CSS files in the correct order.

        The order ensures that base styles are applied first,
        followed by components, layout, and theme styles.
        """
        default_styles = [
            'base.css',
            'components.css',
            'layout.css',
            'theme.css',
            'interactions.css' # New: for modern UI/UX animations and micro-interactions
        ]

        for style_file in default_styles:
            try:
                self.load_css_file(style_file)
            except StyleManagerError as e:
                self.logger.warning(f"Failed to load default style {style_file}: {e}")

        # Load theme-specific CSS based on current system theme
        self._load_theme_specific_styles()

    def load_css_file(self, filename: str) -> None:
        """
        Load a CSS file and apply it to the application.

        Args:
            filename: Name of the CSS file to load

        Raises:
            StyleManagerError: If the file cannot be loaded or applied
        """
        css_path = self._styles_dir / filename

        if not css_path.exists():
            if self._use_fallback_styles and getattr(sys, 'frozen', False):
                # Try to load from embedded resources in frozen executable
                self.logger.warning(f"CSS file not found: {css_path}, using fallback styles")
                self._load_fallback_css(filename)
                return
            else:
                raise StyleManagerError(f"CSS file not found: {css_path}")

        try:
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path(str(css_path))

            display = Gdk.Display.get_default()
            if display is None:
                raise StyleManagerError("No default display available")

            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            self._providers.append(css_provider)
            self._applied_styles.append(filename)

            self.logger.info(f"Successfully loaded CSS file: {filename}")

        except Exception as e:
            raise StyleManagerError(f"Failed to load CSS file {filename}: {e}") from e

    def load_css_from_string(self, css_content: str, identifier: str = "custom") -> None:
        """
        Load CSS from a string and apply it to the application.

        Args:
            css_content: CSS content as string
            identifier: Identifier for this CSS content (for logging/tracking)

        Raises:
            StyleManagerError: If the CSS cannot be loaded or applied
        """
        try:
            css_provider = Gtk.CssProvider()
            css_provider.load_from_data(css_content.encode('utf-8'))

            display = Gdk.Display.get_default()
            if display is None:
                raise StyleManagerError("No default display available")

            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            self._providers.append(css_provider)
            self._applied_styles.append(identifier)

            self.logger.info(f"Successfully loaded CSS from string: {identifier}")

        except Exception as e:
            raise StyleManagerError(f"Failed to load CSS from string {identifier}: {e}") from e

    def apply_theme_variant(self, variant: str = "light") -> None:
        """
        Apply a specific theme variant.

        Args:
            variant: Theme variant ("light" or "dark")
        """
        if variant not in ["light", "dark"]:
            self.logger.warning(f"Unknown theme variant: {variant}. Using 'light'.")
            variant = "light"

        # This could be extended to load variant-specific CSS files
        theme_css = f"theme-{variant}.css"
        theme_path = self._styles_dir / theme_css

        if theme_path.exists():
            try:
                self.load_css_file(theme_css)
                self.logger.info(f"Applied theme variant: {variant}")
            except StyleManagerError as e:
                self.logger.warning(f"Failed to apply theme variant {variant}: {e}")
        else:
            self.logger.debug(f"Theme variant file not found: {theme_css}")

    def reload_styles(self) -> None:
        """
        Reload all previously applied styles.

        This method clears all current providers and reapplies styles,
        useful for development or dynamic theme switching.
        """
        self.logger.info("Reloading all styles...")

        # Store applied styles before clearing
        styles_to_reload = self._applied_styles.copy()

        # Clear current providers
        self.clear_styles()

        # Reload styles
        for style in styles_to_reload:
            if style.endswith('.css'):
                try:
                    self.load_css_file(style)
                except StyleManagerError as e:
                    self.logger.error(f"Failed to reload style {style}: {e}")

    def clear_styles(self) -> None:
        """Remove all applied CSS providers."""
        display = Gdk.Display.get_default()
        if display is None:
            self.logger.warning("No default display available for clearing styles")
            return

        for provider in self._providers:
            Gtk.StyleContext.remove_provider_for_display(display, provider)

        self._providers.clear()
        self._applied_styles.clear()
        self.logger.info("Cleared all applied styles")

    def get_applied_styles(self) -> List[str]:
        """
        Get a list of currently applied style identifiers.

        Returns:
            List of applied style identifiers
        """
        return self._applied_styles.copy()

    def has_style(self, identifier: str) -> bool:
        """
        Check if a specific style is currently applied.

        Args:
            identifier: Style identifier to check

        Returns:
            True if the style is applied, False otherwise
        """
        return identifier in self._applied_styles

    def get_styles_directory(self) -> Path:
        """
        Get the current styles directory path.

        Returns:
            Path to the styles directory
        """
        return self._styles_dir

    def set_styles_directory(self, new_dir: Path) -> None:
        """
        Set a new styles directory.

        Args:
            new_dir: New path to the styles directory

        Raises:
            StyleManagerError: If the directory doesn't exist
        """
        if not new_dir.exists():
            raise StyleManagerError(f"Styles directory not found: {new_dir}")

        self._styles_dir = new_dir
        self.logger.info(f"Styles directory changed to: {new_dir}")

    def _on_system_theme_changed(self, style_manager, param):
        """Handle system theme changes automatically"""
        try:
            is_dark = style_manager.get_dark()
            theme_name = "dark" if is_dark else "light"
            self.logger.info(f"System theme changed to: {theme_name}")

            # Reload theme-specific styles
            self._load_theme_specific_styles()
        except Exception as e:
            self.logger.error(f"Error handling system theme change: {e}")

    def _load_theme_specific_styles(self):
        """Load CSS file specific to current system theme"""
        try:
            # Remove existing theme provider if it exists
            if self._theme_provider:
                display = Gdk.Display.get_default()
                if display:
                    Gtk.StyleContext.remove_provider_for_display(display, self._theme_provider)
                self._theme_provider = None

            # Detect current theme
            adw_style_manager = Adw.StyleManager.get_default()
            is_dark = adw_style_manager.get_dark()

            if is_dark:
                theme_file = "theme-dark.css"
                theme_path = self._styles_dir / theme_file

                if theme_path.exists():
                    try:
                        self._theme_provider = Gtk.CssProvider()
                        self._theme_provider.load_from_path(str(theme_path))

                        display = Gdk.Display.get_default()
                        if display:
                            Gtk.StyleContext.add_provider_for_display(
                                display,
                                self._theme_provider,
                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1  # Higher priority than base styles
                            )

                            self.logger.info(f"Applied dark theme styling")
                            self._applied_styles.append(f"theme-dark")
                        else:
                            self.logger.warning("No default display available for dark theme")
                    except Exception as e:
                        self.logger.error(f"Failed to load dark theme CSS: {e}")
                else:
                    self.logger.debug("Dark theme CSS not found, using default styling")
            else:
                self.logger.info("Applied light theme styling")

        except Exception as e:
            self.logger.error(f"Error loading theme-specific styles: {e}")

    def _load_fallback_css(self, filename: str) -> None:
        """Load minimal fallback CSS when resources are not available."""
        fallback_css = """
        /* Minimal fallback styles for Linux-Coop */
        .suggested-action { background: #3584e4; color: white; }
        .destructive-action { background: #e01b24; color: white; }
        .heading { font-weight: bold; font-size: 1.2em; }
        .dim-label { opacity: 0.7; }
        """
        try:
            self.load_css_from_string(fallback_css, f"fallback-{filename}")
        except StyleManagerError as e:
            self.logger.error(f"Failed to load fallback CSS: {e}")


# Singleton instance for global access
_style_manager_instance: Optional[StyleManager] = None


def get_style_manager() -> StyleManager:
    """
    Get the global StyleManager instance.

    Returns:
        Global StyleManager instance
    """
    global _style_manager_instance
    if _style_manager_instance is None:
        _style_manager_instance = StyleManager()
    return _style_manager_instance


def initialize_styles() -> None:
    """
    Initialize the global style manager with default styles.

    This function should be called once during application startup.
    """
    try:
        style_manager = get_style_manager()
        style_manager.load_default_styles()
    except StyleManagerError as e:
        # In case of style loading errors, continue without styles
        logging.getLogger(__name__).warning(f"Failed to initialize styles: {e}")
