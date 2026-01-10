"""
Dialog module for the Twinverse application.

This module provides custom dialog classes for user interaction in the
Twinverse application.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


class TextInputDialog(Adw.MessageDialog):
    """A dialog for getting text input from the user."""

    def __init__(self, parent, title, message):
        """Initialize the text input dialog with a parent, title, and message."""
        super().__init__(transient_for=parent, modal=True, title=title, body=message)
        self.entry = Gtk.Entry()
        self.set_extra_child(self.entry)
        self.add_response("ok", "OK")
        self.add_response("cancel", "Cancel")
        self.set_default_response("ok")

    def get_input(self):
        """Get the text input from the dialog's entry widget."""
        return self.entry.get_text()


class ConfirmationDialog(Adw.MessageDialog):
    """A dialog for confirming user actions."""

    def __init__(self, parent, title, message):
        """Initialize the confirmation dialog with a parent, title, and message."""
        super().__init__(transient_for=parent, modal=True, title=title, body=message)
        self.add_response("ok", "OK")
        self.add_response("cancel", "Cancel")
        self.set_default_response("cancel")
