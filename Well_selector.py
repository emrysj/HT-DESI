import sys
import time
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QGridLayout, QHBoxLayout, QLabel,
                             QFrame, QSizePolicy, QLineEdit)
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from FreeMoveDESI_4 import *
import subprocess


class WellButton(QPushButton):
    def __init__(self, row, col):
        super().__init__()
        self.row = row
        self.col = col
        self.selected = False
        self.completed = False
        self.setFixedSize(40, 40)
        self.updateStyle()

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
        
class WellPlateApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.drag_start = None
        self.drag_end = None
        self.current_well_index = 0
        self.current_coord_index = 0
        self.is_running = False
        self.start_times = {}
        self.end_times = {}
        self.run_start_time = 0

    def initUI(self):
        self.setWindowTitle('96-Well Plate Sample Selector')
        self.setGeometry(100, 100, 800, 500)

        main_layout = QVBoxLayout()

        # Top panel for filename
        top_panel = QHBoxLayout()
        filename_label = QLabel('Filename:')
        self.filename_input = QLineEdit()
        self.filename_input.setText('Insert File Name')
        top_panel.addWidget(filename_label)
        top_panel.addWidget(self.filename_input)

        main_layout.addLayout(top_panel)

        # Middle panel for well plate
        middle_panel = QHBoxLayout()

        # Left panel for well plate
        left_panel = QVBoxLayout()

        # Create grid for wells
        grid_layout = QGridLayout()
        self.wells = []
        for row in range(8):
            for col in range(12):
                well = WellButton(row, col)
                grid_layout.addWidget(well, row, col)
                self.wells.append(well)

        left_panel.addLayout(grid_layout)

        # Add control buttons
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

        middle_panel.addLayout(left_panel)

        # Right panel for raster pattern
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel('Define Raster Pattern:'))
        self.raster_widget = RasterPatternWidget()
        right_panel.addWidget(self.raster_widget)

        clear_pattern_btn = QPushButton('Clear Pattern')
        clear_pattern_btn.clicked.connect(self.raster_widget.clear_pattern)
        right_panel.addWidget(clear_pattern_btn)

        right_panel.addStretch(1)

        middle_panel.addLayout(right_panel)

        main_layout.addLayout(middle_panel)

        self.setLayout(main_layout)


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

        for well in self.wells:
            well_rect = well.geometry()
            well_center = well.mapTo(self, QPoint(well.width() // 2, well.height() // 2))
            if selection_rect.contains(well_center):
                well.selected = True
            else:
                well.selected = False
            well.update()

    def selectAll(self):
        for well in self.wells:
            well.selected = True
            well.update()
        self.updateStatusLabel()

    def deselectAll(self):
        for well in self.wells:
            well.selected = False
            well.update()
        self.updateStatusLabel()



    def startRunProcess(self):
        self.selected_wells = [well for well in self.wells if well.selected]
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

    def processNextWell(self):
        if not self.is_running:
            return
        if self.current_well_index >= len(self.selected_wells):
        #if self.current_well_index > len(self.selected_wells):
            print("All selected wells processed.")
            GoHome()
            self.StopMS()
            self.is_running = False
            self.run_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.saveTimingData()
            QTimer.singleShot(1000, self.resetWellColors)
            return

        well = self.selected_wells[self.current_well_index]
        well_size = 9  # 9mm apart
        well_diam = 2
        x_offset = 10  # example offset, adjust as needed
        y_offset = 1 # example offset, adjust as needed

        well_center_x = (well.col+1) * well_size + well_diam / 2 + x_offset
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
        ContactCarm(200)
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

    def updateStatusLabel(self):
        selected_count = sum(1 for well in self.wells if well.selected)
        self.status_label.setText(f'{selected_count} wells selected')


    def StopMS(self):
        mainPath = r"C:/HDI/lib"
        command = 'MSStartStop.exe/stop'
        subprocess.Popen(command,cwd=mainPath,shell=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = WellPlateApp()
    ex.show()
    sys.exit(app.exec())
