import sys
import time
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QGridLayout, QHBoxLayout, QLabel,
                             QFrame, QSizePolicy, QLineEdit, QComboBox)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from FreeMoveDESI_4 import *
import subprocess


class WellButton(QPushButton):
    def __init__(self, row, col, plate_type, slide=None):
        super().__init__()
        self.row = row
        self.col = col
        self.slide = slide  # 'A' or 'B' for 24-well plates
        self.selected = False
        self.completed = False
        self.updateSize(plate_type)
        self.updateStyle()

    def updateSize(self, plate_type):
        if plate_type == "96-well":
            self.setFixedSize(40, 40)
        else:  # 24-well
            self.setFixedSize(60, 60)

    def updateStyle(self):
        self.setStyleSheet(
            "WellButton {"
            "background-color: white;"
            "border: 1px solid black;"
            "border-radius: 20px;"
            "}"
            "WellButton:hover {"
            "background-color: lightgray;"
            "}"
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        if self.completed:
            painter.setBrush(QColor(100, 255, 100))  # Green
        elif self.selected:
            painter.setBrush(QColor(100, 100, 255))  # Blue
        painter.drawEllipse(2, 2, self.width() - 4, self.height() - 4)
        
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont('Arial', 8))
        # Update label to include slide identifier for 24-well plates
        if self.slide:
            label = f"{self.slide}{chr(65 + self.row)}{self.col + 1}"
        else:
            label = f"{chr(65 + self.row)}{self.col + 1}"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, label)

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

class WellPlateApp(QWidget):
    def __init__(self):
        super().__init__()
        self.plate_type = "96-well"  # Default plate type
        self.wells_A = []  # Wells for slide A in 24-well mode
        self.wells_B = []  # Wells for slide B in 24-well mode
        self.wells = []    # Wells for 96-well mode
        self.initUI()
        
        self.drag_start = None   # This have been added, are they needed?
        self.drag_end = None
        self.current_well_index = 0
        self.current_coord_index = 0
        self.is_running = False
        self.start_times = {}
        self.end_times = {}
        self.run_start_time = 0

    def initUI(self):
        self.setWindowTitle('Well Plate Sample Selector')
        self.setGeometry(100, 100, 800, 700)  # Increased height for dual plates

        main_layout = QVBoxLayout()

        # Add plate type selector
        plate_selector_layout = QHBoxLayout()
        plate_selector_layout.addWidget(QLabel('Plate Type:'))
        self.plate_selector = QComboBox()
        self.plate_selector.addItems(["96-well", "24-well"])
        self.plate_selector.currentTextChanged.connect(self.changePlateType)
        plate_selector_layout.addWidget(self.plate_selector)
        plate_selector_layout.addStretch()
        main_layout.addLayout(plate_selector_layout)

        # Top panel for filename
        top_panel = QHBoxLayout()
        filename_label = QLabel('Filename:')
        self.filename_input = QLineEdit()
        self.filename_input.setText('Insert File Name')
        top_panel.addWidget(filename_label)
        top_panel.addWidget(self.filename_input)
        main_layout.addLayout(top_panel)

        # Middle panel layout containing both left and right panels
        middle_panel = QHBoxLayout()

        # Left panel setup
        left_panel = QVBoxLayout()
        
        # Create containers for well grids
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        
        # Container for 24-well plates
        self.dual_plate_container = QWidget()
        self.dual_plate_layout = QVBoxLayout(self.dual_plate_container)
        
        # Create separate layouts for slides A and B
        self.slide_A_container = QWidget()
        self.slide_A_layout = QVBoxLayout(self.slide_A_container)
        self.slide_A_label = QLabel("Slide A")
        self.slide_A_grid = QGridLayout()
        self.slide_A_layout.addWidget(self.slide_A_label)
        self.slide_A_layout.addLayout(self.slide_A_grid)
        
        self.slide_B_container = QWidget()
        self.slide_B_layout = QVBoxLayout(self.slide_B_container)
        self.slide_B_label = QLabel("Slide B")
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
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.stop_btn)
        
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
        self.drag_end = event.position().toPoint()
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
            well.update()

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
        else:  # 24-well
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
        else:  # 24-well
            self.grid_container.hide()
            self.dual_plate_container.show()
            rows, cols = 4, 6
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
        
        try:
            os.remove('C:/abort.sem')
        except OSError:
            pass
        
        GoHome()
        filename = self.filename_input.text()
            
        with open(f'C:/MassLynx/AutoLynxQueue/{filename}.raw.txt','w') as file:    
            file.write(f'INDEX\tFILE_NAME\tFILE_TEXT\tMS_FILE\tMS_TUNE_FILE\tPROCESS\tPROCESS_PARAMS\n1\t"C:/MassLynx/Default.pro/Data/{filename}.raw"\t"HT-DESI"\t"C:/HDI/lib/HTDESI_05Hz_neg_res.exp"\t""\t""\t""\n')
        file.close()
        
        ContactCarm(200)
        time.sleep(12) 
        GoToPos(20,20)
        
        self.current_well_index = 0
        self.current_coord_index = 0
        self.is_running = True
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.start_times = {}
        self.end_times = {}
        self.run_start_time = time.time()
        
        self.processNextWell()

    def stopRunProcess(self):
        self.is_running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        fsem=open('C:/abort.sem','x')
        fsem.close()
        print("Process stopped.")
        GoHome()
        sleep(2)
        self.StopMS()
        self.resetWellColors()
        self.saveTimingData()




    def adjustWellSpacing(self):
        if self.plate_type == "96-well":
            well_size = 9  # 9mm apart
            well_diam = 2
        else:  # 24-well
            well_size = 18  # Double the spacing for 24-well plate
            well_diam = 4

    def processNextWell(self):
        if not self.is_running:
            return

        # Get the current list of selected wells based on plate type
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
            self.saveTimingData()
            QTimer.singleShot(1000, self.resetWellColors)
            return

        well = selected_wells[self.current_well_index]
        
        # Adjust well spacing based on plate type
        if self.plate_type == "96-well":
            well_size = 9
            well_diam = 2
            y_offset = 1
        else:  # 24-well
            well_size = 18
            well_diam = 4
            # Adjust y_offset based on slide (A or B)
            y_offset = 1 if well.slide == 'A' else 19  # Offset for slide B
            
        x_offset = 10

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
        for well in self.wells:
            well.reset()
        print("Well colors reset.")

    def saveTimingData(self):
        filename = self.filename_input.text()
        with open(filename, 'w') as f:
            f.write(f"Run start time: {self.run_start_time:.2f}\n")
            for well, start_time in self.start_times.items():
                end_time = self.end_times.get(well, time.time() - self.run_start_time)
                f.write(f"{well}: Start time {start_time:.2f}, End time {end_time:.2f}, Duration {end_time - start_time:.2f} seconds\n")
        print(f"Timing data saved to {filename}")



    def StopMS(self):
        mainPath = r"C:/HDI/lib"
        command = 'MSStartStop.exe/stop'
        subprocess.Popen(command,cwd=mainPath,shell=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = WellPlateApp()
    ex.show()
    sys.exit(app.exec())

