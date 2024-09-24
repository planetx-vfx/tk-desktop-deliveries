from sgtk.platform.qt5 import QtWidgets

# # For development only
# try:
#     from PySide6 import QtWidgets
# except ImportError:
#     pass


class OrderedListItem(QtWidgets.QWidget):
    """A custom widget representing a key-value pair with controls for ordering and deletion."""

    def __init__(self, parent=None):
        super(OrderedListItem, self).__init__(parent)

        # Create widgets for key, value, and control buttons
        self.move_up_button = QtWidgets.QPushButton("▲", self)
        self.move_up_button.setFixedWidth(24)
        self.move_down_button = QtWidgets.QPushButton("▼", self)
        self.move_down_button.setFixedWidth(24)

        self.key_edit = QtWidgets.QLineEdit(self)
        self.value_edit = QtWidgets.QLineEdit(self)

        self.delete_button = QtWidgets.QPushButton("×", self)
        self.delete_button.setFixedWidth(24)

        # Layout for the widget
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add widgets to layout
        layout.addWidget(self.move_up_button)
        layout.addWidget(self.move_down_button)
        layout.addWidget(self.key_edit)
        layout.addWidget(self.value_edit)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def get_content(self):
        """Get the key value pair"""
        return self.key_edit.text(), self.value_edit.text()

    def fail_validation(self):
        self.value_edit.setProperty("cssClass", "validation-failed")
        self.value_edit.style().unpolish(self.value_edit)
        self.value_edit.style().polish(self.value_edit)

    def reset_validation(self):
        self.value_edit.setProperty("cssClass", "")
        self.value_edit.style().unpolish(self.value_edit)
        self.value_edit.style().polish(self.value_edit)


class OrderedList(QtWidgets.QWidget):
    """A widget for managing an ordered list of key-value pairs."""

    def __init__(self, parent=None):
        super(OrderedList, self).__init__(parent)

        # Vertical layout to hold list items
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # Initialize the list of items
        self.items: list[OrderedListItem] = []

    def add_item(self, key="", value=""):
        """Add a new item to the ordered list."""
        item = OrderedListItem(self)
        item.key_edit.setText(key)
        item.value_edit.setText(value)

        # Connect buttons to appropriate functions
        item.move_up_button.clicked.connect(lambda: self.move_item_up(item))
        item.move_down_button.clicked.connect(
            lambda: self.move_item_down(item)
        )
        item.delete_button.clicked.connect(lambda: self.delete_item(item))

        # Add item to the list and update the layout
        self.items.append(item)
        self.layout.insertWidget(self.layout.count(), item)
        self.update_buttons()

    def move_item_up(self, item):
        """Move the given item up in the list."""
        index = self.items.index(item)
        if index > 0:
            self.items[index], self.items[index - 1] = (
                self.items[index - 1],
                self.items[index],
            )
            self.layout.removeWidget(item)
            self.layout.insertWidget(index - 1, item)
            self.update_buttons()

    def move_item_down(self, item):
        """Move the given item down in the list."""
        index = self.items.index(item)
        if index < len(self.items) - 1:
            self.items[index], self.items[index + 1] = (
                self.items[index + 1],
                self.items[index],
            )
            self.layout.removeWidget(item)
            self.layout.insertWidget(index + 1, item)
            self.update_buttons()

    def update_buttons(self):
        """Update the first and last items' buttons."""
        for item in self.items:
            item.move_up_button.setDisabled(False)
            item.move_down_button.setDisabled(False)

        self.items[0].move_up_button.setDisabled(True)
        self.items[len(self.items) - 1].move_down_button.setDisabled(True)

    def delete_item(self, item):
        """Remove the given item from the list."""
        index = self.items.index(item)
        self.items.pop(index)
        item.deleteLater()

    def clear(self):
        """Clear all items from the list."""
        for item in self.items:
            item.deleteLater()

        self.items.clear()

    def size(self):
        """Get the amount of items"""
        return len(self.items)

    def get_items(self):
        """Return a list of key-value pairs."""
        return [item.get_content() for item in self.items]
