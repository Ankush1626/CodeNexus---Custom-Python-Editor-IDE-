from PyQt5.QtCore import *
from PyQt5.Qsci import *
from PyQt5.QtWidgets import *
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtGui import *

from pathlib import Path
import subprocess  # Import subprocess for running commands
import resources
import os
import platform

from lexer import PyCustomLexer
from autocompleter import AutoCompleter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainWindow

class Editor(QsciScintilla):
    def __init__(self, main_window, parent=None, path: Path = None, is_python_file=True):
        super(Editor, self).__init__(parent)

        self.main_window: MainWindow = main_window
        self._current_file_changed = False
        self.first_launch = True

        self.path = path
        self.is_python_file = is_python_file

        # Connect the textChanged signal to track changes
        self.textChanged.connect(self._textChanged)

        # Font setup
        self.window_font = parent.window_font if parent else QFont("Consolas", 12)
        self.setFont(self.window_font)

        self.setUtf8(True)
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.setIndentationGuides(True)
        self.setTabWidth(4)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(True)

        self.cursorPositionChanged.connect(self._cursorPositionChanged)

        # Caret setup
        self.setCaretForegroundColor(QColor("#ffffff"))
        self.setCaretLineVisible(True)
        self.setCaretWidth(2)
        self.setCaretLineBackgroundColor(QColor("#3b3a3a"))

        # EOL setup
        self.setEolMode(QsciScintilla.EolWindows)
        self.setEolVisibility(False)

        # Autocomplete setup
        self.setAutoCompletionSource(QsciScintilla.AcsAll)
        self.setAutoCompletionThreshold(1)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionUseSingle(QsciScintilla.AcusNever)

        if self.is_python_file:
            self.setup_python_lexer()
        else:
            self.setPaper(QColor("#1f1f1f"))
            self.setColor(QColor("#abb2bf"))

        # Line numbers
        self.setMarginType(0, QsciScintilla.NumberMargin)
        self.setMarginWidth(0, "00000")
        self.setMarginsForegroundColor(QColor("#626e82"))
        self.setMarginsBackgroundColor(QColor("#1f1f1f"))

        self.keyPressEvent = self.keyPressEvent

        self.svg_icon = QSvgWidget("./src/icons/run.svg")  # Replace with your SVG file path
        self.svg_icon.setFixedSize(60, 60)  # Set size as needed
        self.svg_icon.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # Create a layout to place the SVG in the top right corner
        layout = QVBoxLayout(self)
        layout.addWidget(self.svg_icon, alignment=Qt.AlignTop | Qt.AlignRight)

        # Connect the SVG icon click to run_code
        self.svg_icon.mousePressEvent = self.svg_icon_clicked

    def setup_python_lexer(self):
        self.lexer = PyCustomLexer(self)
        self.lexer.setDefaultFont(self.window_font)

        # Autocomplete API setup
        self._api = QsciAPIs(self.lexer)
        self.auto_completer = AutoCompleter(self.path, self._api)
        self.auto_completer.finished.connect(self.loaded_autocomplete)

        self.setLexer(self.lexer)

    @property
    def current_file_changed(self):
        return self._current_file_changed

    @current_file_changed.setter
    def current_file_changed(self, value: bool):
        curr_index = self.main_window.tab_view.currentIndex()
        if value:
            self.main_window.tab_view.setTabText(curr_index, "*"+self.path.name)
            self.main_window.setWindowTitle(f"*{self.path.name} - {self.main_window.app_name}")
        else:
            if self.main_window.tab_view.tabText(curr_index).startswith("*"):
                self.main_window.tab_view.setTabText(
                    curr_index,
                    self.main_window.tab_view.tabText(curr_index)[1:]
                )
                self.main_window.setWindowTitle(self.main_window.windowTitle()[1:])

        self._current_file_changed = value

    def svg_icon_clicked(self, event):
        if event.button() == Qt.LeftButton:
            self.run_code()  # Call the run_code method

    def toggle_comment(self, text: str):
        lines = text.split('\n')
        toggled_lines = []
        for line in lines:
            if line.startswith('#'):
                toggled_lines.append(line[1:].lstrip())
            else:
                toggled_lines.append("# " + line)

        return '\n'.join(toggled_lines)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.modifiers() == Qt.ControlModifier and e.key() == Qt.Key_Space:
            if self.is_python_file:
                pos = self.getCursorPosition()
                self.auto_completer.get_completions(pos[0]+1, pos[1], self.text())
                self.autoCompleteFromAPIs()
                return

        if e.modifiers() == Qt.ControlModifier and e.key() == Qt.Key_X:  # CUT SHORTCUT
            if not self.hasSelectedText():
                line, index = self.getCursorPosition()
                self.setSelection(line, 0, line, self.lineLength(line))
                self.cut()
                return

        if e.modifiers() == Qt.ControlModifier and e.text() == "/":  # COMMENT SHORTCUT
            if self.hasSelectedText():
                start, srow, end, erow = self.getSelection()
                self.setSelection(start, 0, end, self.lineLength(end)-1)
                self.replaceSelectedText(self.toggle_comment(self.selectedText()))
                self.setSelection(start, srow, end, erow)
            else:
                line, _ = self.getCursorPosition()
                self.setSelection(line, 0, line, self.lineLength(line)-1)
                self.replaceSelectedText(self.toggle_comment(self.selectedText()))
                self.setSelection(-1, -1, -1, -1)  # reset selection
            return

        if e.modifiers() == Qt.ControlModifier and (e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter):
            current_line, current_index = self.getCursorPosition()
            self.insertAt("\n", current_line + 1, 0)
            self.setCursorPosition(current_line + 1, 0)
            return

        if e.modifiers() == Qt.ControlModifier and e.key() == Qt.Key_W:
            if self.main_window.tab_view.count() == 0:
                self.main_window.close()
            else:
                current_index = self.main_window.tab_view.currentIndex()
                self.main_window.close_tab(current_index)
            return

        return super().keyPressEvent(e)

    def _cursorPositionChanged(self, line: int, index: int) -> None:
        if self.is_python_file:
            self.auto_completer.get_completions(line + 1, index, self.text())

    def loaded_autocomplete(self):
        pass

    def _textChanged(self):
        # Check if the file is not saved and it's not the first launch
        if not self.current_file_changed and not self.first_launch:
            self.current_file_changed = True  # This will trigger the property setter
        if self.first_launch:
            self.first_launch = False  # Mark the first launch as done

    def run_code(self):
        # Ensure the file is saved before running
        if self.path is not None:
            # Save the file if it has unsaved changes
            if self.current_file_changed:
                self.main_window.save_file()

            file_path = str(self.path)
            folder_path = os.path.dirname(file_path)  # Get the folder containing the file

            try:
                # Only handling Windows
                if platform.system() == "Windows":
                    # Ensure we get absolute paths
                    folder_path = os.path.abspath(folder_path)
                    file_name = os.path.basename(file_path)

                    # Command to change directory and run the Python file
                    cmd = f'cd "{folder_path}" && python "{file_name}"'
                    
                    # Run the command in a new cmd window
                subprocess.Popen(
                    ["cmd.exe", "/k", "cd", folder_path, "&&", "python", file_name],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            except Exception as e:
                QMessageBox.critical(self, "Run Error", f"Failed to run the file: {e}")
        else:
            QMessageBox.warning(self, "No File", "Please save the file before running.")
