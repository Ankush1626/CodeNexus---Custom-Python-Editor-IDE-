from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.Qsci import * 

from pathlib import Path
import sys
import os
import subprocess

from editor import Editor
from file_manager import FileManager
from autocompleter import AutoCompleter

class MainWindow(QMainWindow):
    def __init__(self):
        super(QMainWindow, self).__init__()

        self.side_bar_clr = "#181818"

        self.init_ui()

        self.current_file = None
        self.current_side_bar = None

    def init_ui(self):
        self.app_name = "CodeNexus - Code Editor"
        self.setWindowTitle(self.app_name)

        # Set the window icon
        self.setWindowIcon(QIcon("./src/icons/icon.svg"))

        self.resize(1300, 900)

        self.setStyleSheet(open("./src/css/style.qss", "r").read())


        self.window_font = QFont("Consolas")
        self.window_font.setPointSize(12)
        self.setFont(self.window_font)


        self.set_up_menu()
        self.set_up_body()
        self.set_up_status_bar()

        self.show()

    def set_up_status_bar(self):
        # Create status bar
        stat = QStatusBar(self)
        stat.setStyleSheet("color: #D3D3D3;")
        stat.showMessage("Ready", 3000)
        self.setStatusBar(stat)

    def set_up_menu(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("File")
        
        new_file = file_menu.addAction("New")
        new_file.setShortcut("Ctrl+N")
        new_file.triggered.connect(self.new_file)

        file_menu.addSeparator()

        open_file = file_menu.addAction("Open File")
        open_file.setShortcut("Ctrl+O")
        open_file.triggered.connect(self.open_file)

        open_folder = file_menu.addAction("Open Folder")
        open_folder.setShortcut("Ctrl+K")
        open_folder.triggered.connect(self.open_folder)

        file_menu.addSeparator()
        
        save_file = file_menu.addAction("Save")
        save_file.setShortcut("Ctrl+S")
        save_file.triggered.connect(self.save_file)

        save_as = file_menu.addAction("Save As")
        save_as.setShortcut("Ctrl+Shift+S")
        save_as.triggered.connect(self.save_as)

        file_menu.addSeparator()

        run_action = file_menu.addAction("Run")
        run_action.setShortcut("Ctrl+R")
        run_action.triggered.connect(self.run_current_file)  # Connect to the run function

        file_menu.addSeparator()

        # Exit option
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close_application)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")

        undo_action = edit_menu.addAction("Undo")
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)

        redo_action = edit_menu.addAction("Redo")
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        
        edit_menu.addSeparator()

        cut_action = edit_menu.addAction("Cut")
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.cut)

        copy_action = edit_menu.addAction("Copy")
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy)

        paste_action = edit_menu.addAction("Paste")
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste)

    def get_editor(self, path: Path = None, is_python_file=True) -> QsciScintilla:
        editor = Editor(self, path=path, is_python_file=is_python_file)
        return editor

    def is_binary(self, path):
        '''
        Check if file is binary
        '''
        with open(path, 'rb') as f:
            return b'\0' in f.read(1024)

    def set_new_tab(self, path: Path, is_new_file=False):
        if not is_new_file and self.is_binary(path):
            self.statusBar().showMessage("Cannot Open Binary File", 2000)
            return

        if path.is_dir():
            return

        # add whichever extentions you consider as python file
        editor = self.get_editor(path, path.suffix in {".py", ".pyw"}) 
        
        if is_new_file:
            self.tab_view.addTab(editor, "untitled")
            self.setWindowTitle("untitled - " + self.app_name)
            self.statusBar().showMessage("Opened untitled")
            self.tab_view.setCurrentIndex(self.tab_view.count() - 1)
            self.current_file = None
            return
        
        # check if file already open
        for i in range(self.tab_view.count()):
            if self.tab_view.tabText(i) == path.name or self.tab_view.tabText(i) == "*"+path.name:
                self.tab_view.setCurrentIndex(i)
                self.current_file = path
                return

        # create new tab
        self.tab_view.addTab(editor, path.name)
        editor.setText(path.read_text(encoding="utf-8"))
        self.setWindowTitle(f"{path.name} - {self.app_name}")
        self.current_file = path
        self.tab_view.setCurrentIndex(self.tab_view.count() - 1)
        self.statusBar().showMessage(f"Opened {path.name}", 2000)

    def set_cursor_pointer(self, e):
        self.setCursor(Qt.PointingHandCursor)

    def set_cursor_arrow(self, e):
        self.setCursor(Qt.ArrowCursor)

    def get_side_bar_label(self, path, name):
        label = QLabel()
        label.setPixmap(QPixmap(path).scaled(QSize(30, 30)))
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        label.setFont(self.window_font)
        label.mousePressEvent = lambda e: self.show_hide_tab(e, name)
        # Chaning Cursor on hover
        label.enterEvent = self.set_cursor_pointer
        label.leaveEvent = self.set_cursor_arrow
        return label

    def get_frame(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.NoFrame)
        frame.setFrameShadow(QFrame.Plain)
        frame.setContentsMargins(0, 0, 0, 0)
        frame.setStyleSheet('''
            QFrame {
                background-color: #181818;
                border-radius: 5px;
                border: none;
                padding: 5px;
                color: #D3D3D3;  
            }
            QFrame:hover {
                color: white;
            }
        ''')
        return frame

    def set_up_body(self):

        # Body        
        body_frame = QFrame()
        body_frame.setFrameShape(QFrame.NoFrame)
        body_frame.setFrameShadow(QFrame.Plain)
        body_frame.setLineWidth(0)
        body_frame.setMidLineWidth(0)
        body_frame.setContentsMargins(0, 0, 0, 0)
        body_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body_frame.setLayout(body)

        ##############################
        ###### TAB VIEW ##########

        # Tab Widget to add editor to
        self.tab_view = QTabWidget()
        self.tab_view.setContentsMargins(0, 0, 0, 0)
        self.tab_view.setTabsClosable(True)
        self.tab_view.setMovable(True)
        self.tab_view.setDocumentMode(True)
        self.tab_view.tabCloseRequested.connect(self.close_tab)

        ##############################
        ###### SIDE BAR ##########
        
        self.side_bar = QFrame()
        self.side_bar.setFrameShape(QFrame.StyledPanel)
        self.side_bar.setFrameShadow(QFrame.Plain)
        self.side_bar.setStyleSheet(f'''
            background-color: {self.side_bar_clr};
        ''')   
        side_bar_layout = QVBoxLayout()
        side_bar_layout.setContentsMargins(5, 10, 5, 0)
        side_bar_layout.setSpacing(0)
        side_bar_layout.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        # setup labels
        folder_label = self.get_side_bar_label("./src/icons/folder-icon-blue.svg", "folder-icon")
        side_bar_layout.addWidget(folder_label)

        self.side_bar.setLayout(side_bar_layout)


        # split view
        self.hsplit = QSplitter(Qt.Horizontal)

        ##############################
        ###### FILE MANAGER ##########

        # frame and layout to hold tree view (file manager)
        self.file_manager_frame = self.get_frame()
        self.file_manager_frame.setMaximumWidth(400)
        self.file_manager_frame.setMinimumWidth(200)

        self.file_manager_layout = QVBoxLayout()
        self.file_manager_layout.setContentsMargins(0, 0, 0, 0)
        self.file_manager_layout.setSpacing(0)

        self.file_manager = FileManager(
            tab_view=self.tab_view, 
            set_new_tab=self.set_new_tab,
            main_window=self
        )

        # setup layout
        self.file_manager_layout.addWidget(self.file_manager)   
        self.file_manager_frame.setLayout(self.file_manager_layout)

        ##############################
        ###### SETUP WIDGETS ##########

        # add tree view and tab view
        self.hsplit.addWidget(self.file_manager_frame)
        self.hsplit.addWidget(self.tab_view)

        body.addWidget(self.side_bar)
        body.addWidget(self.hsplit)

        body_frame.setLayout(body)

        self.setCentralWidget(body_frame)     

    def show_dialog(self, title, msg) -> int:
        dialog = QMessageBox(self)
        dialog.setFont(self.window_font)
        dialog.font().setPointSize(14)
        dialog.setWindowTitle(title)
        dialog.setWindowIcon(QIcon(":/icons/close-icon.svg"))
        dialog.setText(msg)
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.No)
        dialog.setIcon(QMessageBox.Warning)

        # Apply your stylesheet here
        dialog.setStyleSheet("""
        QMessageBox {
            background-color: #181818; 
        }
        QLabel {
            color: #D3D3D3; 
        }
        QPushButton {
            background-color: #444; 
            color: #D3D3D3; 
            border: 1px solid #555; 
            padding: 5px; 
        }
        QPushButton:hover {
            background-color:
        }
        """)

        return dialog.exec_()

    def run_current_file(self):
        current_index = self.tab_view.currentIndex()
        
        # Check if there is a valid tab (current_index != -1)
        if current_index != -1:
            current_editor = self.tab_view.widget(current_index)
            if isinstance(current_editor, Editor):
                current_editor.run_code()  # Call the run_code method from the editor
        else:
            QMessageBox.warning(self, "No File", "No file is open to run.")


    def close_tab(self, index):
        editor: Editor = self.tab_view.currentWidget()
        if editor.current_file_changed:
            dialog = self.show_dialog(
                "Close", f"Do you want to save the changes made to {self.current_file.name}?"
            )
            if dialog == QMessageBox.Yes:
                self.save_file()

        self.tab_view.removeTab(index)

    def show_hide_tab(self, e, type_):
        if self.file_manager_frame.isHidden():
            self.file_manager_frame.show()
        else:
            self.file_manager_frame.hide()

    def tree_view_context_menu(self, pos):
        pass

    def new_file(self):
        self.set_new_tab(Path("untitled"), is_new_file=True)

    def save_file(self):
        if self.current_file is None and self.tab_view.count() > 0:
            self.save_as()
        
        editor = self.tab_view.currentWidget()
        self.current_file.write_text(editor.text())
        self.statusBar().showMessage(f"Saved {self.current_file.name}", 2000)
        editor.current_file_changed = False
    
    def save_as(self):
        # save as 
        editor = self.tab_view.currentWidget()
        if editor is None:
            return
        
        file_path = QFileDialog.getSaveFileName(self, "Save As", os.getcwd())[0]
        if file_path == '':
            self.statusBar().showMessage("Cancelled", 2000)
            return 
        path = Path(file_path)
        path.write_text(editor.text())
        self.tab_view.setTabText(self.tab_view.currentIndex(), path.name)
        self.statusBar().showMessage(f"Saved {path.name}", 2000)
        self.current_file = path
        editor.current_file_changed = False

    def open_file(self):
        # open file
        ops = QFileDialog.Options()
        new_file, _ = QFileDialog.getOpenFileName(self,
                    "Pick A File", "", "All Files (*);;Python Files (*.py)",
                    options=ops)
        if new_file == '':
            self.statusBar().showMessage("Cancelled", 2000)
            return
        f = Path(new_file)
        self.set_new_tab(f)

    def open_folder(self):
        new_folder = QFileDialog.getExistingDirectory(self, "Pick A Folder", "")
        if new_folder:
            self.file_manager.model.setRootPath(new_folder)  # Set the model's root path
            self.file_manager.setRootIndex(self.file_manager.model.index(new_folder))  # Set the tree view's root index
            self.statusBar().showMessage(f"Opened {new_folder}", 2000)

    def copy(self):
        editor = self.tab_view.currentWidget()
        if editor is not None:
            editor.copy()

    def paste(self):
        editor = self.tab_view.currentWidget()
        if editor is not None:
            editor.paste()

    def cut(self):
        editor = self.tab_view.currentWidget()
        if editor is not None:
            editor.cut()

    def undo(self):
        editor = self.tab_view.currentWidget()
        if editor is not None:
            editor.undo()

    def redo(self):
        editor = self.tab_view.currentWidget()
        if editor is not None:
            editor.redo()

    def close_application(self):
        # Show a confirmation dialog before exiting
        dialog = self.show_dialog("Exit", "Are you sure you want to exit?")
        if dialog == QMessageBox.Yes:
            QApplication.quit()

if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.setWindowState(Qt.WindowMaximized)
    sys.exit(app.exec())
