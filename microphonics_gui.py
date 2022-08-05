import sys
from os import path

from PyQt5.Qt import Qt
from PyQt5.QtWidgets import QFileDialog, QGridLayout, QTreeWidget, QTreeWidgetItem, QVBoxLayout
from lcls_tools.common.pydm_tools.displayUtils import showDisplay
from lcls_tools.superconducting.scLinac import L1BHL, LINAC_TUPLES
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pydm import Display
from pyqtgraph.widgets.MatplotlibWidget import MatplotlibWidget

BUFFER_LENGTH = 16384
DEFAULT_SAMPLING_RATE = 2000

DATA_DIR_PATH = "/u1/lcls/physics/rf_lcls2/microphonics"
SCRIPT_PATH = "/usr/local/lcls/package/lcls2_llrf/srf/software/res_ctl/res_data_acq.py"


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(PlotCanvas, self).__init__(fig)


class MicrophonicsGUI(Display):
    def ui_filename(self):
        return "microphonics_gui.ui"

    def __init__(self, parent=None, args=None):
        super(MicrophonicsGUI, self).__init__(parent=parent, args=args)

        self.plot_spectrogram = None
        self.plot_timeseries = None
        self.plot_fft = None
        self.plot_histogram = None
        self.plotwindow = None
        self.pathHere = path.dirname(sys.modules[self.__module__].__file__)

        self.cm_selection_window: Display = None
        self.button_cm_selection.clicked.connect(self.open_cm_selection_window)

        self.ui.button_open_data.clicked.connect(self.load_data)
        self.ui.button_start_measurement.clicked.connect(self.plot_data)

        self.ui.comboBox_decimation.currentIndexChanged.connect(self.update_daq_setting)
        self.ui.spinBox_buffers.valueChanged.connect(self.update_daq_setting)
        self.update_daq_setting()

        # self.plotwindow: Display = Display(ui_filename=self.get_path("plot_window.ui"))

    def get_path(self, fileName):
        return path.join(self.pathHere, fileName)

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

    def update_daq_setting(self):

        number_of_buffers = int(self.ui.spinBox_buffers.value())
        decimation_num = int(self.ui.comboBox_decimation.currentText())
        sampling_rate = DEFAULT_SAMPLING_RATE / decimation_num
        self.ui.label_samplingrate.setNum(sampling_rate)
        self.ui.label_acq_time.setNum(
            BUFFER_LENGTH * decimation_num * number_of_buffers / DEFAULT_SAMPLING_RATE)

    def load_data(self):
        file_picker = QFileDialog()
        (file_name, _) = file_picker.getOpenFileName(None, 'Pick a file', self.pathHere, '')

    def plot_data(self):
        if not self.plotwindow:
            self.plotwindow = Display()
            self.plotwindow.setWindowTitle('Data plots')
            layout: QGridLayout = QGridLayout()
            self.plot_histogram: MatplotlibWidget = MatplotlibWidget()
            # self.plot_histogram.setTitle("Histogram")
            self.plot_timeseries: MatplotlibWidget = MatplotlibWidget()
            # self.plot_timeseries.setTitle("Time domain data")
            self.plot_fft: MatplotlibWidget = MatplotlibWidget()
            # self.plot_fft.setTitle("FFT")
            self.plot_spectrogram: MatplotlibWidget = MatplotlibWidget()
            # self.plot_spectrogram.setTitle("Spectrogram")
            layout.addWidget(self.plot_timeseries, 1, 1, 1, 1)
            layout.addWidget(self.plot_histogram, 1, 2, 1, 2)
            layout.addWidget(self.plot_fft, 2, 1, 2, 1)
            layout.addWidget(self.plot_spectrogram, 2, 2, 2, 2)
            self.plotwindow.setLayout(layout)

            showDisplay(self.plotwindow)
