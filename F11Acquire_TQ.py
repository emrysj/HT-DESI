import sys
import time
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QGridLayout, QHBoxLayout, QLabel,QFileDialog,
                            QFrame, QSizePolicy, QLineEdit, QComboBox, QToolBar, QDialog, QFormLayout, QDoubleSpinBox)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QAction, QRegion
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from FreeMoveDESI_5 import *
import subprocess
import csv
#os.chdir(libpath)
import WatersIMGReader as wat 
from ctypes import *
import numpy as np
reader = cdll.LoadLibrary("C:/Users/Emrys/watersimgreader.dll") # This will need to change 
mainPath='C:/HDI/lib/'
from time import sleep

class WellButton(QPushButton):
    def __init__(self, row, col, plate_type, slide=None):
        super().__init__()
        self.row = row
        self.col = col
        self.slide = slide  # 'A' or 'B' for 24-well plates
        self.selected = False
        self.completed = False
        self.updateSize(plate_type)
        #  self.updateStyle()
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self.clicked.connect(self.handleClick)

    

    def updateSize(self, plate_type):
        if plate_type == "96-well":
            size = 40
        else:  # 44-well
            size = 60
        self.setFixedSize(size, size)
        # Make sure the button's hit area is a circle
        self.setMask(QRegion(0, 0, size, size, QRegion.RegionType.Ellipse))



    def handleClick(self):
        self.selected = not self.selected
        self.update()
        # Find parent WellPlateApp and update timing
        parent = self.parent()
        while parent and not isinstance(parent, WellPlateApp):
            parent = parent.parent()
        if parent:
            parent.updateStatusLabel()

    def updateStyle(self):
        self.setStyleSheet(
            "WellButton {"
            "background-color: darkgray;"
            "border: none;"
            "border-radius: 20px;"
            "}"
            "WellButton:hover {"
            "background-color: lightgray;"
            "}"
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        rect = self.rect()
        diameter = min(rect.width(), rect.height())
        x = (rect.width() - diameter) // 2
        y = (rect.height() - diameter) // 2

        # Draw the outer circle border
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        font = QFont('Calibri', 8)
        font.setBold(True)  # Make text bold
        painter.setFont(font)
        
        # Set the fill color based on state
        if self.completed:
            painter.setBrush(QColor(30, 214, 131))  # Green
        elif self.selected:
            painter.setBrush(QColor(75, 112, 173))  # Blue
        else:
            painter.setBrush(QColor(107, 110, 115))  # Dark Grey

        # Draw the main circle
        painter.drawEllipse(x, y, diameter, diameter)
        #painter.drawEllipse(x, y, diameter - 1, diameter - 1)
    
    # Update label format to use continuous row counting across slides
        if self.slide:
            row_offset = 4 if self.slide == 'B' else 0  # Offset by 4 rows for slide B
            label = f"{chr(65 + self.row + row_offset)}{str(self.col + 1).zfill(2)}"
        else:
            label = f"{chr(65 + self.row)}{str(self.col + 1).zfill(2)}"

        
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, label),

    def toggle(self):
        self.selected = not self.selected
        self.update()

    def reset(self):
        self.completed = False
        self.update()


class RasterPatternWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(200, 200)
        self.points = []
        self.drawing = False
        self.completed = False
        self.selected = False
        self.points_changed = None  # Callback for when points change

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the circle representing the well
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawEllipse(10, 10, 180, 180)

        # Draw the center point
        painter.setBrush(Qt.GlobalColor.red)
        painter.drawEllipse(98, 98, 4, 4)

        # Draw the raster pattern
        if len(self.points) > 1:
            painter.setPen(QPen(Qt.GlobalColor.blue, 2))
            for i in range(len(self.points) - 1):
                painter.drawLine(self.points[i], self.points[i + 1])

    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            if self.points_changed:
                self.points_changed()
        elif event.button() == Qt.MouseButton.RightButton:
            self.drawing = False


    def mouseMoveEvent(self, event):
        if self.drawing:
            self.points.append(event.pos())
            self.update()

    def clear_pattern(self):
        self.points = []
        self.update()
        if self.points_changed:
            self.points_changed()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.points.append(event.pos())
            self.drawing = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.drawing = False

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.points.append(event.pos())
            self.update()

    def clear_pattern(self):
        self.points = []
        self.update()




class OffsetSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plate Offset Settings")
        self.setModal(True)
        
        layout = QFormLayout()
        
        # Create spin boxes for X and Y offsets for each plate type
        self.plate_96_x = QDoubleSpinBox()
        self.plate_96_y = QDoubleSpinBox()
        self.plate_44_A_x = QDoubleSpinBox()
        self.plate_44_A_y = QDoubleSpinBox()
        self.plate_44_B_x = QDoubleSpinBox()
        self.plate_44_B_y = QDoubleSpinBox()
        
        # Configure spin boxes
        spinboxes = [self.plate_96_x, self.plate_96_y, 
                    self.plate_44_A_x, self.plate_44_A_y,
                    self.plate_44_B_x, self.plate_44_B_y]
        
        for spinbox in spinboxes:
            spinbox.setRange(-100, 100)
            spinbox.setDecimals(2)
            spinbox.setSingleStep(0.1)
        
        # Add widgets to layout
        layout.addRow("96-well plate X offset:", self.plate_96_x)
        layout.addRow("96-well plate Y offset:", self.plate_96_y)
        layout.addRow("44-well Slide A X offset:", self.plate_44_A_x)
        layout.addRow("44-well Slide A Y offset:", self.plate_44_A_y)
        layout.addRow("44-well Slide B X offset:", self.plate_44_B_x)
        layout.addRow("44-well Slide B Y offset:", self.plate_44_B_y)
        
        # Add OK and Cancel buttons
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        
        # Add buttons to main layout
        layout.addRow(buttons_layout)
        
        self.setLayout(layout)
    
    def get_values(self):
        return {
            '96-well': {'x': self.plate_96_x.value(), 'y': self.plate_96_y.value()},
            '44-well-A': {'x': self.plate_44_A_x.value(), 'y': self.plate_44_A_y.value()},
            '44-well-B': {'x': self.plate_44_B_x.value(), 'y': self.plate_44_B_y.value()}
        }
    
    def set_values(self, values):
        self.plate_96_x.setValue(values['96-well']['x'])
        self.plate_96_y.setValue(values['96-well']['y'])
        self.plate_44_A_x.setValue(values['44-well-A']['x'])
        self.plate_44_A_y.setValue(values['44-well-A']['y'])
        self.plate_44_B_x.setValue(values['44-well-B']['x'])
        self.plate_44_B_y.setValue(values['44-well-B']['y'])

class WellPlateApp(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize offset values
        self.offsets = {
            '96-well': {'x': 10, 'y': 1},      # Default values from original code
            '44-well-A': {'x': 46, 'y': 11},    # Default values for Slide A
            '44-well-B': {'x': 46, 'y': 45}    # Default values for Slide B

        }

        # Set application-wide style including background color
        # Set application-wide style including background color
        app = QApplication.instance()
        if app:
            app.setStyleSheet("""
                QWidget, QMainWindow, QDialog {
                    background-color: #f0f0f0;
                }
            """)
            
        # Set detailed styles for specific widgets
        self.setStyleSheet("""
            * {
                background-color: #f0f0f0;
            }
            QWidget, QMainWindow, QDialog, QFrame {
                background-color: #f0f0f0;
            }
            QScrollArea, QScrollBar {
                background-color: #f0f0f0;
            }
            QLabel {
                background-color: transparent;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid #b0b0b0;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #b0b0b0;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QComboBox {
                background-color: #e0e0e0;
                border: 1px solid #b0b0b0;
                padding: 5px;
                border-radius: 3px;
            }
            QToolBar {
                background-color: #f0f0f0;
                border: none;
            }
            QFrame {
                background-color: #f0f0f0;
            }
        """)


            
        self.method_file = "C:/MassLynx/Default.pro/Acqudb/HT_DESI_MRM_001.exp"
        self.base_directory = "C:/MassLynx/Default.pro/Data/"
        self.plate_type = "96-well"
        self.wells_A = []
        self.wells_B = []
        self.wells = []
        self.initUI()

        self.drag_start = None   # This have been added, are they needed?
        self.drag_end = None
        self.current_well_index = 0
        self.current_coord_index = 0
        self.is_running = False
        self.start_times = {}
        self.end_times = {}
        self.run_start_time = 0

        self.movement_time = 0.1  # Average time in seconds for stage movement
        self.dwell_time = 0.5    # Time spent at each point
        self.setup_time = 12     # Time for initial setup (from ContactCarm call)
        self.between_wells_time = 1  # Time between wells





    

    def calculate_pattern_time(self):
        # """Calculate estimated time for the current raster pattern"""
        if not self.raster_widget.points:
            return 0
            
        num_points = len(self.raster_widget.points)
        num_movements = num_points - 1
        
        # Time per well = movement time between points + dwell time at each point
        time_per_well = (num_movements * self.movement_time) + (num_points * self.dwell_time)
        return time_per_well

    def calculate_total_time(self):
        # """Calculate total estimated time for all selected wells"""
        if self.plate_type == "96-well":
            selected_wells = sum(1 for well in self.wells if well.selected)
        else:
            selected_wells = sum(1 for well in self.wells_A + self.wells_B if well.selected)
            
        if selected_wells == 0:
            return 0
            
        pattern_time = self.calculate_pattern_time()
        total_time = (
            self.setup_time +  # Initial setup
            (selected_wells * pattern_time) +  # Time for all wells
            (selected_wells - 1) * self.between_wells_time  # Time between wells
        )
        
        return total_time  

    def format_time(self, seconds):
            # """Format time in seconds to hours:minutes:seconds"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
            
    def updateRasterInfo(self):
            # """Update the display with pattern information and timing estimates"""
        num_points = len(self.raster_widget.points)
        pattern_time = self.calculate_pattern_time()
        total_time = self.calculate_total_time()
        
        info_text = f"Pattern points: {num_points}\n"
        info_text += f"Time per well: {self.format_time(pattern_time)}\n"
        info_text += f"Total estimated time: {self.format_time(total_time)}"
        
        self.pattern_info_label.setText(info_text)
    
    def initUI(self):
        self.setWindowTitle('Well Plate Sample Selector')
        self.setGeometry(100, 100, 800, 700)

        main_layout = QVBoxLayout()

        # Add toolbar
        toolbar = QToolBar()
        settings_action = QAction("Offset Settings", self)
        settings_action.triggered.connect(self.show_offset_settings)
        toolbar.addAction(settings_action)
        main_layout.addWidget(toolbar)

        # Add file path configuration section at the top
        file_config_layout = QGridLayout()
        
        # Method file selection
        method_label = QLabel('Method File:')
        self.method_path_display = QLineEdit(self.method_file)
        self.method_path_display.setReadOnly(True)
        select_method_btn = QPushButton('Select Method')
        select_method_btn.clicked.connect(self.select_method_file)
        
        # Base directory selection
        base_dir_label = QLabel('Data Directory:')
        self.base_dir_display = QLineEdit(self.base_directory)
        self.base_dir_display.setReadOnly(True)
        select_base_dir_btn = QPushButton('Select Directory')
        select_base_dir_btn.clicked.connect(self.select_base_directory)
        
        # Add widgets to grid layout
        file_config_layout.addWidget(method_label, 0, 0)
        file_config_layout.addWidget(self.method_path_display, 0, 1)
        file_config_layout.addWidget(select_method_btn, 0, 2)
        file_config_layout.addWidget(base_dir_label, 1, 0)
        file_config_layout.addWidget(self.base_dir_display, 1, 1)
        file_config_layout.addWidget(select_base_dir_btn, 1, 2)
        
        main_layout.addLayout(file_config_layout)

         # Add plate type selector
        plate_selector_layout = QHBoxLayout()
        plate_selector_layout.addWidget(QLabel('Plate Type:'))
        self.plate_selector = QComboBox()
        self.plate_selector.addItems(["96-well", "44-well"])
        self.plate_selector.currentTextChanged.connect(self.changePlateType)
        plate_selector_layout.addWidget(self.plate_selector)
        
        # Add connect button
        connect_btn = QPushButton('Connect to DESI-XS')
        connect_btn.clicked.connect(self.initiate_desi)
        plate_selector_layout.addWidget(connect_btn)
        
        plate_selector_layout.addStretch()
        main_layout.addLayout(plate_selector_layout)

        # Top panel for filename
        top_panel = QVBoxLayout()

        
        # Filename input
        filename_layout = QHBoxLayout()
        filename_label = QLabel('Filename:')
        self.filename_input = QLineEdit()
        self.filename_input.setText('Insert File Name')
        filename_layout.addWidget(filename_label)
        filename_layout.addWidget(self.filename_input)

        top_panel.addLayout(filename_layout)
        top_panel.addLayout(self.add_scans_per_second_input())
    
        main_layout.addLayout(top_panel)

        # Middle panel layout containing both left and right panels
        middle_panel = QHBoxLayout()

        # Left panel setup
        left_panel = QVBoxLayout()
        
        # Create containers for well grids
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        
        # Container for 44-well plates
        self.dual_plate_container = QWidget()
        self.dual_plate_layout = QVBoxLayout(self.dual_plate_container)
        
        # Create separate layouts for slides A and B
        self.slide_A_container = QWidget()
        self.slide_A_layout = QVBoxLayout(self.slide_A_container)
        self.slide_A_label = QLabel("Slide A")
        font_A = QFont()
        font_A.setPointSize(14)  # Increase font size to 14 points
        font_A.setBold(True)     # Make it bold for better visibility
        self.slide_A_label.setFont(font_A)



        
        self.slide_A_grid = QGridLayout()
        self.slide_A_layout.addWidget(self.slide_A_label)
        self.slide_A_layout.addLayout(self.slide_A_grid)
        
        self.slide_B_container = QWidget()
        self.slide_B_layout = QVBoxLayout(self.slide_B_container)
        self.slide_B_label = QLabel("Slide B")
        font_B = QFont()
        font_B.setPointSize(14)  # Match Slide A's font size
        font_B.setBold(True)     # Match Slide A's bold style
        self.slide_B_label.setFont(font_B)
        
        self.slide_B_grid = QGridLayout()

        
        self.slide_B_layout.addWidget(self.slide_B_label)
   
        self.slide_B_layout.addLayout(self.slide_B_grid)
        
        self.dual_plate_layout.addWidget(self.slide_A_container)
        self.dual_plate_layout.addSpacing(20)  # Add space between plates
        self.dual_plate_layout.addWidget(self.slide_B_container)
        
        left_panel.addWidget(self.grid_container)
        left_panel.addWidget(self.dual_plate_container)

        # Control buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton('Select All')
        select_all_btn.clicked.connect(self.selectAll)
        deselect_all_btn = QPushButton('Deselect All')
        deselect_all_btn.clicked.connect(self.deselectAll)
        self.run_btn = QPushButton('Run')
        self.run_btn.clicked.connect(self.startRunProcess)
        self.stop_btn = QPushButton('Stop')
        self.stop_btn.clicked.connect(self.stopRunProcess)
        self.stop_btn.setEnabled(False)


        select_folder_button = QPushButton("Process Data")
        select_folder_button.clicked.connect(self.select_folder)
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(select_folder_button)
        
        left_panel.addLayout(button_layout)

        self.status_label = QLabel('No wells selected')
        left_panel.addWidget(self.status_label)

        # Right panel setup
        right_panel = QVBoxLayout()
        pattern_label = QLabel('Define Raster Pattern:')
        pattern_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_panel.addWidget(pattern_label)
        
        self.raster_widget = RasterPatternWidget()
        right_panel.addWidget(self.raster_widget)

        clear_pattern_btn = QPushButton('Clear Pattern')
        clear_pattern_btn.clicked.connect(self.raster_widget.clear_pattern)
        right_panel.addWidget(clear_pattern_btn)

        pattern_info_frame = QFrame()
        pattern_info_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        pattern_info_layout = QVBoxLayout(pattern_info_frame)
        
        self.pattern_info_label = QLabel("Draw a pattern to see timing estimates")
        self.pattern_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pattern_info_layout.addWidget(self.pattern_info_label)
        
        # Add to right panel after raster widget
        right_panel.addWidget(pattern_info_frame)
        
        # Connect to raster pattern changes
        # This needs to be added after raster_widget is created
        self.raster_widget.points_changed = self.updateRasterInfo

        

      #  home_btn = QPushButton('Stage Home')
       # home_btn.clicked.connect(self.GoToHome)
      #  right_panel.addWidget(home_btn)
        
        # Add spacer to push everything to the top
        right_panel.addStretch(1)

        # Add both panels to middle panel
        middle_panel.addLayout(left_panel)
        middle_panel.addLayout(right_panel)

        # Add middle panel to main layout
        main_layout.addLayout(middle_panel)
        
        self.setLayout(main_layout)
        
        # Initialize with default plate type
        self.createWellGrid()

    def select_method_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Method File",
            self.method_file,
            "Method Files (*.exp);;All Files (*.*)"
        )
        if file_name:
            self.method_file = file_name
            self.method_path_display.setText(file_name)

    def select_base_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Base Directory",
            self.base_directory,
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.base_directory = directory + '/'  # Add trailing slash
            self.base_dir_display.setText(self.base_directory)


    def initiate_desi(self):
        Initiate_DESI()
        sleep(1)
        GoToPos(3000,3000)
        GoHome()
            


    def prepare_names(self,folder_name, parent_dir, folder_path):
        """Prepare file paths and create output directories"""
        
        global fulldata, fulloutdata, fulloutCSVdata, WellList
        
        # Setup output paths
        outdata = folder_name[0:-4]
        outdir = os.path.join(folder_path, 'outputs')
        csvoutdir = os.path.join(folder_path, 'CSVoutputs')
        fulldata = os.path.join(folder_path)
        fulloutdata = os.path.join(outdir, outdata)
        fulloutCSVdata = os.path.join(csvoutdir, outdata)
    
        # Create output directories
        os.makedirs(outdir, exist_ok=True)
        os.makedirs(csvoutdir, exist_ok=True)
        
        WellList = open(f'{fulldata}/selected_wells.txt').read().split()

    def create_series_file(self,start, end, filename="C:/HDI/lib/outputScans.txt"):
        """Create a file containing scan series information"""
        with open(filename, "w") as file:
            for i in range(start, end + 1):
                file.write(f"1\t{i}\n")

    def create96_well_process(self,Rwell):
        prog = 'C:/HDI/lib/maldichrom.exe'
        raw_in = fulldata
        raw_out = f'{fulloutdata}_{Rwell}.raw'
        scans = 'C:/HDI/lib/outputScans.txt'
        command = f'{prog} -d "{raw_in}" -p "{scans}" -w "{raw_out}"'
        subprocess.Popen(command,cwd=mainPath,shell=True)

    def raw_to_csv(self,input_raw, output_csv):
        """Convert raw data to CSV format"""
        try:
            reader = wat.WatersIMGReader(input_raw, 1)
            masses, intens, npoints = reader.getCombinedScans(1, 1, 0, 0)
            with open(output_csv, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                for i in range(len(masses)):
                    writer.writerow([masses[i], intens[i]])
        except Exception as e:
            print(f"Error converting raw to CSV: {str(e)}")


    def update_method_file_settings(self, method_file_path, time_per_well):
        """
        Updates the MRM method file settings based on scan time, channels, and well timing calculations.
        """
        try:
            # Read the method file
            with open(method_file_path, 'r') as file:
                lines = file.readlines()
            
            # Get scans per second from UI
            scans_per_second = self.scans_per_sec_input.value()
            
            # Find NoOfChannels
            num_channels = None
            for line in lines:
                if 'NoOfChannels,' in line:
                    num_channels = int(line.split(',')[1].strip())
                    break
                    
            if num_channels is None:
                raise ValueError("NoOfChannels not found in method file")
            
            # Calculate timing parameters
            scan_time = 1.0 / scans_per_second
            dwell_time = scan_time / num_channels
            # Calculate total scans per well
            scans_per_well = int(time_per_well * scans_per_second)
            x_step = 5.0 / (scans_per_well*num_channels)  # Using the 5.0 from DesiXLength
            
            print(f"Calculated parameters:")
            print(f"Scans per second: {scans_per_second}")
            print(f"Number of channels: {num_channels}")
            print(f"Scan time: {scan_time:.6f}")
            print(f"Dwell time: {dwell_time:.6f}")
            print(f"Scans per well: {scans_per_well}")
            print(f"X step: {x_step:.6f}")
            
            # Create modified content
            new_lines = []
            for line in lines:
                if 'FunctionScanTime(sec)' in line:
                    new_lines.append(f'FunctionScanTime(sec),{scan_time:.6f}\n')
                elif 'SIRDwellTime' in line:
                    new_lines.append(f'{line.split(",")[0]},{dwell_time:.6f}\n')
                elif line.strip().startswith('Dwell(s)_'):
                    new_lines.append(f'{line.split(",")[0]},{dwell_time:.6f}\n')
                elif 'DesiXStep' in line:
                    new_lines.append(f'DesiXStep,{x_step:.6f}\n')
                else:
                    new_lines.append(line)
            
            # Write modified content back to file
            with open(method_file_path, 'w') as file:
                file.writelines(new_lines)
                
            return {
                'scan_time': scan_time,
                'dwell_time': dwell_time,
                'num_channels': num_channels,
                'x_step': x_step,
                'scans_per_well': scans_per_well
            }
                
        except Exception as e:
            raise Exception(f"Error updating method file: {str(e)}")


    def add_scans_per_second_input(self):
        scans_per_sec_layout = QHBoxLayout()
        scans_per_sec_label = QLabel('Scans per Second:')
        self.scans_per_sec_input = QDoubleSpinBox()  # Using QDoubleSpinBox for decimal values
        self.scans_per_sec_input.setRange(0.1, 100.0)  # Reasonable range for scans/second
        self.scans_per_sec_input.setValue(5.0)  # Default value
        self.scans_per_sec_input.setDecimals(1)  # Show one decimal place
        self.scans_per_sec_input.setSingleStep(0.1)  # Allow fine adjustment
        scans_per_sec_layout.addWidget(scans_per_sec_label)
        scans_per_sec_layout.addWidget(self.scans_per_sec_input)
        scans_per_sec_layout.addStretch()
        return scans_per_sec_layout

    
    

 


    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Process Data")
        
        # Check if a folder was actually selected
        if folder_path:
            try:
                folder_name = os.path.basename(folder_path)
                
                # Run MRMProcessing.exe with the selected folder name
                mrm_processor = 'C:/Program Files (x86)/Waters/DESI Method Editor/MRMProcessing.exe'
                command = f'"{mrm_processor}" "{folder_path}"'
                
                print(f"Running command: {command}")
                
                # Run the process
                process = subprocess.Popen(command, 
                                        shell=True,
                                        cwd='C:/Program Files (x86)/Waters/DESI Method Editor',  # Set working directory
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                
                # Get output and error messages
                stdout, stderr = process.communicate()
                
                # Print any output or errors
                if stdout:
                    print("Process output:", stdout.decode())
                if stderr:
                    print("Process errors:", stderr.decode())
                    
                print("MRM Processing completed")
                
            except Exception as e:
                print(f"Error processing folder: {str(e)}")
        else:
            print("No folder selected")


    
    def mousePressEvent(self, event):
        self.drag_start = event.position().toPoint()
        self.updateSelection(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.updateSelection(event)

    def mouseReleaseEvent(self, event):
        self.drag_start = None
        self.drag_end = None
        self.updateStatusLabel()

    def updateSelection(self, event):
        if self.drag_start is None:
            self.drag_start = event.position().toPoint()
        
        self.drag_end = event.position().toPoint()
        
        if self.drag_start is not None and self.drag_end is not None:
            selection_rect = QRect(self.drag_start, self.drag_end).normalized()
    
            if self.plate_type == "96-well":
                wells_to_check = self.wells
            else:
                wells_to_check = self.wells_A + self.wells_B
    
            for well in wells_to_check:
                well_rect = well.geometry()
                if self.plate_type == "96-well":
                    well_center = well.mapTo(self, QPoint(well.width() // 2, well.height() // 2))
                else:
                    # For 24-well plates, we need to map through the correct parent container
                    if well in self.wells_A:
                        well_center = well.mapTo(self.slide_A_container, QPoint(well.width() // 2, well.height() // 2))
                        well_center = self.slide_A_container.mapTo(self, well_center)
                    else:
                        well_center = well.mapTo(self.slide_B_container, QPoint(well.width() // 2, well.height() // 2))
                        well_center = self.slide_B_container.mapTo(self, well_center)
    
                if selection_rect.contains(well_center):
                    well.selected = True
                else:
                    well.selected = False
                well.update()
                self.updateRasterInfo()

    def selectAll(self):
        if self.plate_type == "96-well":
            for well in self.wells:
                well.selected = True
                well.update()
        else:
            for well in self.wells_A + self.wells_B:
                well.selected = True
                well.update()
        self.updateStatusLabel()
        self.updateRasterInfo()  # Add this line

    def deselectAll(self):
        if self.plate_type == "96-well":
            for well in self.wells:
                well.selected = False
                well.update()
        else:
            for well in self.wells_A + self.wells_B:
                well.selected = False
                well.update()
        self.updateStatusLabel()
        self.updateRasterInfo()  # Add this line

    def updateStatusLabel(self):
        if self.plate_type == "96-well":
            selected_count = sum(1 for well in self.wells if well.selected)
        else:
            selected_count = sum(1 for well in self.wells_A + self.wells_B if well.selected)
        self.status_label.setText(f'{selected_count} wells selected')


    def changePlateType(self, plate_type):
        """
        Changes the plate type and updates the UI accordingly
        """
        self.plate_type = plate_type
        self.deselectAll()  # Clear any existing selections
        
        if plate_type == "96-well":
            self.grid_container.show()
            self.dual_plate_container.hide()
        else:  # 44-well
            self.grid_container.hide()
            self.dual_plate_container.show()
        
        self.createWellGrid()
        self.adjustWellSpacing()
        self.updateStatusLabel()

    def createWellGrid(self):
        # Clear existing grids
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.slide_A_grid.count())): 
            self.slide_A_grid.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.slide_B_grid.count())): 
            self.slide_B_grid.itemAt(i).widget().setParent(None)
        
        self.wells = []
        self.wells_A = []
        self.wells_B = []
        
        if self.plate_type == "96-well":
            self.grid_container.show()
            self.dual_plate_container.hide()
            rows, cols = 8, 12
            for row in range(rows):
                for col in range(cols):
                    well = WellButton(row, col, self.plate_type)
                    self.grid_layout.addWidget(well, row, col)
                    self.wells.append(well)
        else:  # 44-well
            self.grid_container.hide()
            self.dual_plate_container.show()
            rows, cols = 4, 11
            # Create wells for Slide A
            for row in range(rows):
                for col in range(cols):
                    well = WellButton(row, col, self.plate_type, slide='A')
                    self.slide_A_grid.addWidget(well, row, col)
                    self.wells_A.append(well)
            # Create wells for Slide B
            for row in range(rows):
                for col in range(cols):
                    well = WellButton(row, col, self.plate_type, slide='B')
                    self.slide_B_grid.addWidget(well, row, col)
                    self.wells_B.append(well)





    def startRunProcess(self):
        # Get selected wells based on plate type
        if self.plate_type == "96-well":
            self.selected_wells = [well for well in self.wells if well.selected]
        else:
            self.selected_wells = ([well for well in self.wells_A if well.selected] + 
                                 [well for well in self.wells_B if well.selected])
            
        if not self.selected_wells:
            print("No wells selected.")
            return

        # Calculate time per well from raster pattern
        time_per_well = self.calculate_pattern_time()
        
        # Enforce minimum time of 1 second per well
        if time_per_well < 1.0:
            print(f"Warning: Calculated time per well ({time_per_well:.2f}s) is less than minimum. Using 1.0s instead.")
            time_per_well = 1.0
    
        # Update method file settings - Note the change here to use self
        try:
            results = self.update_method_file_settings(self.method_file, time_per_well)
            print(f"Method file updated: {results['scans_per_well']} scans per well, "
                  f"X step size: {results['x_step']:.6f}")
        except Exception as e:
            print(f"Error updating method file: {str(e)}")
            return



        GoHome()
        filename = self.filename_input.text()
        
        # Create the main queue file
        with open(f'C:/MassLynx/AutoLynxQueue/{filename}.raw.txt', 'w') as file:    
            file.write(f'INDEX\tFILE_NAME\tFILE_TEXT\tMS_FILE\tMS_TUNE_FILE\tPROCESS\tPROCESS_PARAMS\n')
            file.write(f'1\t"{self.base_directory}{filename}.raw"\t"HT-DESI"\t"{self.method_file}"\t""\t""\t""\n')
            
        # Create a new file with selected wells
        #wells_output = []
        #for well in self.selected_wells:
         #   if well.slide:
        #        well_id = f"{well.slide}{chr(65 + well.row)}{str(well.col + 1).zfill(2)}"
         #   else:
        #        well_id = f"{chr(65 + well.row)}{str(well.col + 1).zfill(2)}"
         #   wells_output.append(well_id)
        
        print('going to sleep')
        
       #  ContactCarm(200) #Don't need this, or do we? Test again Feb 10th. 
        time.sleep(15) 
        
        print('woken up')  
        GoToPos(20,20)
        print('gone to 20 20')

        self.current_well_index = 0
        self.current_coord_index = 0
        self.is_running = True
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
       # self.start_times = {}
       # self.end_times = {}
       # self.run_start_time = time.time()
        
        self.processNextWell()

    def stopRunProcess(self):
        self.is_running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
      #  fsem=open('C:/abort.sem','x')  # add these back in when needed
    #    fsem.close()
        print("Process stopped.")
        GoHome()
        sleep(2)
        self.StopMS()
        self.resetWellColors()
       #  self.saveTimingData()



   # def GoToHome(self):
      #  self.is_running = False
   #     GoHome()



    def adjustWellSpacing(self):
        if self.plate_type == "96-well":
            well_size = 9  # 9mm apart
            well_diam = 2
        else:  # 24-well
            well_size = 4  # Double the spacing for 24-well plate
            well_diam = 2


    def show_offset_settings(self):
        dialog = OffsetSettingsDialog(self)
        dialog.set_values(self.offsets)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.offsets = dialog.get_values()
            print("New offset values:", self.offsets)

    def processNextWell(self):
        if not self.is_running:
            return

        if self.plate_type == "96-well":
            selected_wells = [well for well in self.wells if well.selected]
        else:
            selected_wells = ([well for well in self.wells_A if well.selected] + 
                            [well for well in self.wells_B if well.selected])

        if self.current_well_index >= len(selected_wells):
            print("All selected wells processed.")
            GoHome()
            self.StopMS()
            self.is_running = False
            self.run_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            # self.saveTimingData()
            QTimer.singleShot(1000, self.resetWellColors)
            filename = self.filename_input.text()
            
            wells_output = []
            for well in self.selected_wells:
                if well.slide:
                    row_offset = 4 if well.slide == 'B' else 0  # Offset by 4 rows for slide B
                    well_id = f"{chr(65 + well.row + row_offset)}{str(well.col + 1).zfill(2)}"
                else:
                    well_id = f"{chr(65 + well.row)}{str(well.col + 1).zfill(2)}"
                wells_output.append(well_id)

            
            with open(f'C:/MassLynx/Default.pro/Data/{filename}.raw/selected_wells.txt', 'w') as f:
                f.write("Selected Wells:\n")
                f.write("\n".join(wells_output))

            
            return

            
            QTimer.singleShot(1000, self.resetWellColors)
            return

        well = selected_wells[self.current_well_index]
        
        # Get appropriate offsets based on plate type and slide
        if self.plate_type == "96-well":
            x_offset = self.offsets['96-well']['x']
            y_offset = self.offsets['96-well']['y']
            well_size = 9
            well_diam = 2
        else:  # 44-well
            well_size = 4
            well_diam = 2
            if well.slide == 'A':
                x_offset = self.offsets['44-well-A']['x']
                y_offset = self.offsets['44-well-A']['y']
            else:  # Slide B
                x_offset = self.offsets['44-well-B']['x']
                y_offset = self.offsets['44-well-B']['y']

        well_center_x = (well.col + 1) * well_size + well_diam / 2 + x_offset
        well_center_y = (well.row) * well_size + well_diam / 2 + y_offset

        raster_pattern = self.raster_widget.points
        if not raster_pattern:
            raster_pattern = [QPoint(100, 100)]  # Use center if no pattern defined

        self.current_well_coords = []
        for point in raster_pattern:
            x = well_center_x + (point.x() - 100) * well_diam / 180
            y = well_center_y + (point.y() - 100) * well_diam / 180
            self.current_well_coords.append((x, y))

        self.current_coord_index = 0
        ContactCarm(200)    # This helps with incrementing the Y-co-ordinate for data-split.
        self.start_times[f"{chr(65 + well.row)}{well.col + 1}"] = time.time() - self.run_start_time 

        # This will take stage to wait for 0.5 seconds 1mm away from start of the well. 

        x, y = self.current_well_coords[self.current_coord_index]
        xs=round((x*400)-600)
        ys=round((y*400))
        GoToPos(ys, xs)

        self.processNextCoordinate()

    def processNextCoordinate(self):
        if not self.is_running:
            return

        if self.current_coord_index >= len(self.current_well_coords):
            # Well completed
            well = self.selected_wells[self.current_well_index]
            well.completed = True
            well.update()
            self.end_times[f"{chr(65 + well.row)}{well.col + 1}"] = time.time() - self.run_start_time
            self.current_well_index += 1
            QTimer.singleShot(1000, self.processNextWell)  # 1 second delay before next well
            return

        x, y = self.current_well_coords[self.current_coord_index]
        x1=round(x*400)
        y1=round(y*400)
        GoToPos(y1, x1)
        self.current_coord_index += 1
        QTimer.singleShot(100, self.processNextCoordinate)  # Small delay between coordinates

    def resetWellColors(self):
        if self.plate_type == "96-well":
            for well in self.wells:
                well.reset()
        else:  # 24-well
            for well in self.wells_A + self.wells_B:
                well.reset()
        print("Well colors reset.")

    # def saveTimingData(self):
     #    filename = self.filename_input.text()
     #    with open(filename, 'w') as f:
     #        f.write(f"Run start time: {self.run_start_time:.2f}\n")
     #        for well, start_time in self.start_times.items():
     #            end_time = self.end_times.get(well, time.time() - self.run_start_time)
     #            f.write(f"{well}: Start time {start_time:.2f}, End time {end_time:.2f}, Duration {end_time - start_time:.2f} seconds\n")
     #    print(f"Timing data saved to {filename}")



    def StopMS(self):
        mainPath = r"C:/HDI/lib"
        command = 'MSStartStop.exe/stop'
        subprocess.Popen(command,cwd=mainPath,shell=True)
        fsem=open('C:/abort.sem','x')  # add these back in when needed
        fsem.close()
        sleep(5)
        os.remove('C:/abort.sem')
        print('removed file')
        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = WellPlateApp()
    ex.show()
    sys.exit(app.exec())