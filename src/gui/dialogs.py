import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


class TextInputDialog(Adw.MessageDialog):
    def __init__(self, parent, title, message):
        super().__init__(transient_for=parent, modal=True, title=title, body=message)
        self.entry = Gtk.Entry()
        self.set_extra_child(self.entry)
        self.add_response("ok", "OK")
        self.add_response("cancel", "Cancel")
        self.set_default_response("ok")

    def get_input(self):
        return self.entry.get_text()


class ConfirmationDialog(Adw.MessageDialog):
    def __init__(self, parent, title, message):
        super().__init__(transient_for=parent, modal=True, title=title, body=message)
        self.add_response("ok", "OK")
        self.add_response("cancel", "Cancel")
        self.set_default_response("cancel")
