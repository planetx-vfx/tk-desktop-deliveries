from sgtk.platform.qt5 import QtGui, QtCore, QtWidgets

# # For development only
# try:
#     from PySide6 import QtGui, QtCore, QtWidgets
# except ImportError:
#     pass


class Collapse(QtWidgets.QWidget):
    def __init__(self, parent=None, title=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self._is_collapsed = True
        self._header = None
        self._content, self._content_layout = (None, None)

        self._main_v_layout = QtWidgets.QVBoxLayout(self)
        self._main_v_layout.setSpacing(0)
        self._main_v_layout.setContentsMargins(0, 0, 0, 0)

        self._header = self.Header(title=title, collapsed=self._is_collapsed)
        self._main_v_layout.addWidget(self._header)

        self._content_layout = QtWidgets.QVBoxLayout()
        self._content_layout.setSpacing(16)
        self._content = QtWidgets.QWidget()
        self._content.setObjectName("collapse")
        self._content.setStyleSheet(
            "QWidget#collapse { background-color: rgba(0, 0, 0, 0.14); }"
        )

        self._content.setLayout(self._content_layout)
        self._content.setVisible(not self._is_collapsed)
        self._main_v_layout.addWidget(self._content)

        QtCore.QObject.connect(
            self._header, QtCore.SIGNAL("clicked()"), self.toggleCollapse
        )

    def addWidget(self, widget):
        self._content_layout.addWidget(widget)

    def toggleCollapse(self):
        self._content.setVisible(self._is_collapsed)
        self._is_collapsed = not self._is_collapsed
        self._header.caret.set_caret(int(self._is_collapsed))

    def setCollapsed(self, collapsed: bool) -> None:
        self._content.setVisible(not collapsed)
        self._is_collapsed = collapsed
        self._header.caret.set_caret(int(collapsed))

    class Header(QtWidgets.QFrame):
        def __init__(self, parent=None, title="", collapsed=False):
            QtWidgets.QFrame.__init__(self, parent=parent)

            self.setMinimumHeight(24)
            self.move(QtCore.QPoint(24, 0))
            self.setStyleSheet("background-color: #5d5d5d;")

            self._hlayout = QtWidgets.QHBoxLayout(self)
            self._hlayout.setContentsMargins(0, 0, 0, 0)
            self._hlayout.setSpacing(0)

            self.caret = Collapse.Caret(collapsed=collapsed)
            self.caret.setStyleSheet("border: 0;")

            self._hlayout.addWidget(self.caret)

            self._text = QtWidgets.QLabel(title)
            self._text.setMinimumHeight(24)
            self._text.move(QtCore.QPoint(24, 0))
            self._text.setStyleSheet("border: 0;")

            self._hlayout.addWidget(self._text)

        def mousePressEvent(self, event):
            self.emit(QtCore.SIGNAL("clicked()"))

            return super(Collapse.Header, self).mousePressEvent(event)

    class Caret(QtWidgets.QFrame):
        def __init__(self, parent=None, collapsed=False):
            QtWidgets.QFrame.__init__(self, parent=parent)

            self.setMaximumSize(24, 24)

            self._caret_horizontal = (
                QtCore.QPointF(7.0, 8.0),
                QtCore.QPointF(17.0, 8.0),
                QtCore.QPointF(12.0, 13.0),
            )
            self._caret_vertical = (
                QtCore.QPointF(8.0, 7.0),
                QtCore.QPointF(13.0, 12.0),
                QtCore.QPointF(8.0, 17.0),
            )
            self._caret = None
            self.set_caret(int(collapsed))

        def set_caret(self, caret_dir):
            if caret_dir:
                self._caret = self._caret_vertical
            else:
                self._caret = self._caret_horizontal

        def paintEvent(self, event):
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setBrush(QtGui.QColor(192, 192, 192))
            painter.drawPolygon(self._caret)
            painter.end()
