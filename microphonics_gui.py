from PyQt5.Qt import Qt
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout
from lcls_tools.common.pydm_tools.displayUtils import showDisplay
from lcls_tools.superconducting.scLinac import L1BHL, LINAC_TUPLES
from pydm import Display


class MicrophonicsGUI(Display):
    def ui_filename(self):
        return "microphonics_gui.ui"

    def __init__(self, parent=None, args=None):
        super(MicrophonicsGUI, self).__init__(parent=parent, args=args)

        self.cm_selection_window: Display = None
        self.button_cm_selection.clicked.connect(self.open_cm_selection_window)

    def open_cm_selection_window(self):
        if not self.cm_selection_window:
            self.cm_selection_window: Display = Display()
            self.cm_selection_window.setWindowTitle("CM and cavity selection")
            vlayout: QVBoxLayout = QVBoxLayout()
            tree_widget: QTreeWidget = QTreeWidget()
            vlayout.addWidget(tree_widget)
            tree_widget.setHeaderLabel("")
            self.cm_selection_window.setLayout(vlayout)

            for linac_name, cm_list in LINAC_TUPLES:
                if linac_name == "L1B":
                    cm_list += L1BHL
                linac_item = QTreeWidgetItem(tree_widget)
                linac_item.setText(0, linac_name)
                linac_item.setFlags(linac_item.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)

                for cm_name in cm_list:
                    cm_item = QTreeWidgetItem(linac_item)
                    cm_item.setText(0, f"CM{cm_name}")
                    cm_item.setFlags(cm_item.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
                    for cavity in range(1, 9):
                        cavity_item = QTreeWidgetItem(cm_item)
                        cavity_item.setFlags(cavity_item.flags() | Qt.ItemIsUserCheckable)
                        cavity_item.setText(0, f"Cavity {cavity}")
                        cavity_item.setCheckState(0, Qt.Unchecked)
            tree_widget.show()
        showDisplay(self.cm_selection_window)
