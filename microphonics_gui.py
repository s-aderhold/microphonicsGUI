import sys
from os import path

import numpy as np
from PyQt5.Qt import Qt
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QFileDialog, QGridLayout, QPushButton, QTreeWidget, QTreeWidgetItem, \
    QTreeWidgetItemIterator, QVBoxLayout
from lcls_tools.common.pydm_tools.displayUtils import showDisplay
from lcls_tools.superconducting.scLinac import CRYOMODULE_OBJECTS, L1BHL, LINAC_TUPLES, Rack
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pydm import Display
from pyqtgraph.widgets.MatplotlibWidget import MatplotlibWidget
from scipy import signal
from scipy.fftpack import fft, fftfreq

import microphonics_utils as utils

BUFFER_LENGTH = 16384
DEFAULT_SAMPLING_RATE = 2000

DATA_DIR_PATH = "/u1/lcls/physics/rf_lcls2/microphonics"
SCRIPT_PATH = "/usr/local/lcls/package/lcls2_llrf/srf/software/res_ctl/res_data_acq.py"


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(PlotCanvas, self).__init__(fig)


class QTreeRackItem(QTreeWidgetItem):
    def __init__(self, parent, cm_name, rackName):
        super().__init__(parent)
        self.cm_name = cm_name
        self.rackName = rackName
        self._rack = None

    @property
    def rack(self):
        if not self._rack:
            self._rack = CRYOMODULE_OBJECTS[self.cm_name].racks[self.rackName]
        return self._rack


class MicrophonicsRack(Rack):
    def __init__(self, rackName, cryoObject):
        super().__init__(rackName, cryoObject)

        self.res_chassis_address = "ca://" + self.cryomodule.pvPrefix + f"RES{rackName}:"


class MicrophonicsGUI(Display):
    def ui_filename(self):
        return "microphonics_gui.ui"

    def __init__(self, parent=None, args=None):
        super(MicrophonicsGUI, self).__init__(parent=parent, args=args)

        self.plot_spectrogram = None
        self.plot_timeseries = None
        self.plot_fft = None
        self.plot_histogram = None
        self.button_confirm_selection = None
        self.rack_selection = None
        self.tree_widget = None
        self.widget_spectrogram = None
        self.widget_timeseries = None
        self.widget_fft = None
        self.widget_histogram = None
        self.plotwindow = None
        self.selected_racks = None
        self.pathHere = path.dirname(sys.modules[self.__module__].__file__)

        self.cm_selection_window: Display = None
        self.button_cm_selection.clicked.connect(self.open_cm_selection_window)

        self.ui.button_open_data.clicked.connect(self.plot_data)
        self.ui.button_start_measurement.clicked.connect(self.plot_data)

        self.ui.comboBox_decimation.currentIndexChanged.connect(self.update_daq_setting)
        self.ui.spinBox_buffers.valueChanged.connect(self.update_daq_setting)
        self.update_daq_setting()

    def get_path(self, fileName):
        return path.join(self.pathHere, fileName)

    def open_cm_selection_window(self):
        if not self.cm_selection_window:
            self.cm_selection_window: Display = Display()
            self.cm_selection_window.setWindowTitle("CM and rack selection")
            vlayout: QVBoxLayout = QVBoxLayout()
            self.tree_widget: QTreeWidget = QTreeWidget()
            self.button_confirm_selection: QPushButton = QPushButton()
            self.button_confirm_selection.setText("Confirm selection and close window")
            vlayout.addWidget(self.button_confirm_selection)
            vlayout.addWidget(self.tree_widget)
            self.tree_widget.setHeaderLabel("")
            self.cm_selection_window.setLayout(vlayout)
            self.button_confirm_selection.clicked.connect(self.update_rack_selection)

            for linac_name, cm_list in LINAC_TUPLES:
                if linac_name == "L1B":
                    cm_list += L1BHL
                linac_item = QTreeWidgetItem(self.tree_widget)
                linac_item.setText(0, linac_name)
                linac_item.setFlags(linac_item.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)

                for cm_name in cm_list:
                    cm_item = QTreeWidgetItem(linac_item)
                    cm_item.setText(0, f"CM{cm_name}")
                    cm_item.setFlags(cm_item.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
                    for rack in ['A', 'B']:
                        rack_item = QTreeRackItem(cm_item, rackName=rack, cm_name=cm_name)
                        rack_item.setFlags(rack_item.flags() | Qt.ItemIsUserCheckable)
                        if rack == 'A':
                            rack_item.setText(0, f"Rack {rack}: cavities 1-4")
                        else:
                            rack_item.setText(0, f"Rack {rack}: cavities 5-8")
                        rack_item.setCheckState(0, Qt.Unchecked)
            self.tree_widget.show()
        showDisplay(self.cm_selection_window)

    @pyqtSlot()
    def update_rack_selection(self):
        self.rack_selection = QTreeWidgetItemIterator(self.tree_widget, QTreeWidgetItemIterator.Checked)
        self.selected_racks = []
        # print statement for debugging purposes
        while self.rack_selection.value():
            item = self.rack_selection.value()
            if isinstance(item, QTreeRackItem):
                self.selected_racks.append(item.rack)
                print(type(item))
            self.rack_selection += 1
        self.cm_selection_window.close()

    @property
    def decimation_num(self):
        return int(self.ui.comboBox_decimation.currentText())

    @property
    def sampling_rate(self):
        return DEFAULT_SAMPLING_RATE / self.decimation_num

    def update_daq_setting(self):

        number_of_buffers = int(self.ui.spinBox_buffers.value())
        self.ui.label_samplingrate.setNum(self.sampling_rate)
        self.ui.label_acq_time.setNum(
            BUFFER_LENGTH * self.decimation_num * number_of_buffers / DEFAULT_SAMPLING_RATE)

    def load_data(self):
        file_picker = QFileDialog()
        (file_name, _) = file_picker.getOpenFileName(None, 'Pick a file', self.pathHere, '')
        with open(file_name) as f:
            line = f.readline()
            while line.startswith('#') or not line.strip():
                line = f.readline()
            read_data = f.readlines()
        f.close()
        return read_data

    def plot_data(self):
        # TODO add tabs for plotting multiple cavities
        if not self.plotwindow:
            self.plotwindow = Display()
            self.plotwindow.setWindowTitle('Data plots')
            layout: QGridLayout = QGridLayout()
            self.widget_histogram: MatplotlibWidget = MatplotlibWidget()
            self.widget_timeseries: MatplotlibWidget = MatplotlibWidget()
            self.widget_fft: MatplotlibWidget = MatplotlibWidget()
            self.widget_spectrogram: MatplotlibWidget = MatplotlibWidget()
            layout.addWidget(self.widget_timeseries, 1, 1, 1, 1)
            layout.addWidget(self.widget_histogram, 1, 2, 1, 2)
            layout.addWidget(self.widget_fft, 2, 1, 2, 1)
            layout.addWidget(self.widget_spectrogram, 2, 2, 2, 2)
            self.plotwindow.setLayout(layout)

            self.plot_histogram = self.widget_histogram.getFigure().add_subplot(111)
            # self.plot_histogram.set
            self.plot_histogram.set_xlabel('Detune (Hz)')
            self.plot_histogram.set_ylabel('Counts')

            self.plot_fft = self.widget_fft.getFigure().add_subplot(111)
            self.plot_fft.set_xlabel('Frequency (Hz)')
            self.plot_fft.set_ylabel('Relative amplitude')
            self.plot_fft.set_xlim(0, 150)
            self.plot_fft.grid(True)

            self.plot_timeseries = self.widget_timeseries.getFigure().add_subplot(111)
            self.plot_timeseries.set_xlabel('Time (sec)')
            self.plot_timeseries.set_ylabel('Detune (Hz)')

            self.plot_spectrogram = self.widget_spectrogram.getFigure().add_subplot(111)
            self.plot_spectrogram.set_xlabel('Time (sec)')
            self.plot_spectrogram.set_ylabel('Frequency (Hz)')
            self.plot_spectrogram.set_ylim(150)

        raw_data = self.load_data()
        parsed_data = utils.parse_data(raw_data)

        for index, cavity_data in enumerate(parsed_data):
            if len(cavity_data) > 0:
                self.plot_histogram.hist(cavity_data, bins=140, histtype='step', log='True')
                self.make_fft_plot(cavity_data, self.plot_fft)
                self.make_timeseries_plot(cavity_data, self.plot_timeseries)
                self.make_spectrogram_plot(cavity_data, self.plot_spectrogram)
        showDisplay(self.plotwindow)

    @property
    def sample_spacing(self):
        return 1.0 / (DEFAULT_SAMPLING_RATE / int(self.ui.comboBox_decimation.currentText()))

    def make_fft_plot(self, cavity_data, plot_widget):
        number_of_points = len(cavity_data)

        fft_data = fft(cavity_data)
        frequencies = fftfreq(number_of_points, self.sample_spacing)[0:number_of_points // 2]
        plot_widget.plot(frequencies, 2.0 / number_of_points * np.abs(fft_data[0:number_of_points // 2]))

    def make_timeseries_plot(self, cavity_data, plot_widget):
        time_vector = list(
            map(lambda x: x * self.sample_spacing, np.linspace(1, len(cavity_data), num=len(cavity_data))))
        plot_widget.plot(time_vector, cavity_data)

    def make_spectrogram_plot(self, cavity_data, plot_widget):
        data_array = np.array(cavity_data)
        f, t, Sxx = signal.spectrogram(data_array, self.sampling_rate)
        plot_widget.pcolormesh(t, f, Sxx, shading='gouraud')
