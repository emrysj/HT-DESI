import sys
import time
import os
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QGridLayout, QHBoxLayout, QLabel,QFileDialog,
                            QFrame, QSizePolicy, QLineEdit, QComboBox, QToolBar, QDialog, QFormLayout, QDoubleSpinBox,
                            QListWidget, QListWidgetItem, QMessageBox, QInputDialog, QSpinBox)
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

class CustomPlateDialog(QDialog):
    def __init__(self, parent=None, existing_config=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Plate Configuration")
        self.setModal(True)
        
        layout = QFormLayout()
        
        # Create input fields with default values
        self.print_height = QDoubleSpinBox()
        self.print_width = QDoubleSpinBox()
        self.offset_x = QDoubleSpinBox()
        self.offset_y = QDoubleSpinBox()
        self.spot_distance_x = QDoubleSpinBox()
        self.spot_distance_y = QDoubleSpinBox()
        self.spot_diameter = QDoubleSpinBox()  # New field for spot diameter
        self.num_rows = QSpinBox()
        self.num_columns = QSpinBox()
        
        # Configure spin boxes
        self.print_height.setRange(1, 200)
        self.print_height.setValue(26 if not existing_config else existing_config.get('print_height', 26))
        self.print_height.setDecimals(2)
        self.print_height.setSuffix(" mm")
        
        self.print_width.setRange(1, 200)
        self.print_width.setValue(76 if not existing_config else existing_config.get('print_width', 76))
        self.print_width.setDecimals(2)
        self.print_width.setSuffix(" mm")
        
        self.offset_x.setRange(0, 100)
        self.offset_x.setValue(5 if not existing_config else existing_config.get('offset_x', 5))
        self.offset_x.setDecimals(2)
        self.offset_x.setSuffix(" mm")
        
        self.offset_y.setRange(0, 100)
        self.offset_y.setValue(23 if not existing_config else existing_config.get('offset_y', 23))
        self.offset_y.setDecimals(2)
        self.offset_y.setSuffix(" mm")
        
        self.spot_distance_x.setRange(0.1, 50)
        self.spot_distance_x.setValue(3 if not existing_config else existing_config.get('spot_distance_x', 3))
        self.spot_distance_x.setDecimals(2)
        self.spot_distance_x.setSuffix(" mm")
        
        self.spot_distance_y.setRange(0.1, 50)
        self.spot_distance_y.setValue(3 if not existing_config else existing_config.get('spot_distance_y', 3))
        self.spot_distance_y.setDecimals(2)
        self.spot_distance_y.setSuffix(" mm")
        
        # New spot diameter field
        self.spot_diameter.setRange(0.1, 10)
        self.spot_diameter.setValue(2 if not existing_config else existing_config.get('spot_diameter', 2))
        self.spot_diameter.setDecimals(2)
        self.spot_diameter.setSuffix(" mm")
        
        self.num_rows.setRange(1, 100)
        self.num_rows.setValue(16 if not existing_config else existing_config.get('num_rows', 16))
        
        self.num_columns.setRange(1, 100)
        self.num_columns.setValue(6 if not existing_config else existing_config.get('num_columns', 6))
        
        # Add widgets to layout
        layout.addRow("Print region Height:", self.print_height)
        layout.addRow("Print region Width:", self.print_width)
        layout.addRow("Top-Left Offset to first spot-X:", self.offset_x)
        layout.addRow("Top-Left Offset to first spot-Y:", self.offset_y)
        layout.addRow("Centre-to-centre distance between spots-X:", self.spot_distance_x)
        layout.addRow("Centre-to-centre distance between spots-Y:", self.spot_distance_y)
        layout.addRow("Spot diameter:", self.spot_diameter)  # Add the new field
        layout.addRow("Spots - number of rows:", self.num_rows)
        layout.addRow("Spots - number of columns:", self.num_columns)
        
        # Add buttons
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        
        layout.addRow(buttons_layout)
        self.setLayout(layout)
    
    def get_config(self):
        return {
            'print_height': self.print_height.value(),
            'print_width': self.print_width.value(),
            'offset_x': self.offset_x.value(),
            'offset_y': self.offset_y.value(),
            'spot_distance_x': self.spot_distance_x.value(),
            'spot_distance_y': self.spot_distance_y.value(),
            'spot_diameter': self.spot_diameter.value(),  # Include spot diameter
            'num_rows': self.num_rows.value(),
            'num_columns': self.num_columns.value()
        }

class PatternManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pattern Manager")
        self.setModal(True)
        self.parent_app = parent
        
        layout = QVBoxLayout()
        
        # Pattern list
        self.pattern_list = QListWidget()
        self.load_patterns()
        layout.addWidget(QLabel("Saved Patterns:"))
        layout.addWidget(self.pattern_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load Pattern")
        load_btn.clicked.connect(self.load_selected_pattern)
        
        delete_btn = QPushButton("Delete Pattern")
        delete_btn.clicked.connect(self.delete_selected_pattern)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(load_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_patterns(self):
        """Load saved patterns from file"""
        try:
            if os.path.exists('saved_patterns.json'):
                with open('saved_patterns.json', 'r') as f:
                    patterns = json.load(f)
                    for name in patterns.keys():
                        self.pattern_list.addItem(name)
        except Exception as e:
            print(f"Error loading patterns: {e}")
    
    def load_selected_pattern(self):
        """Load the selected pattern"""
        current_item = self.pattern_list.currentItem()
        if current_item:
            pattern_name = current_item.text()
            try:
                with open('saved_patterns.json', 'r') as f:
                    patterns = json.load(f)
                    if pattern_name in patterns:
                        points_data = patterns[pattern_name]
                        # Convert back to QPoint objects
                        points = [QPoint(p['x'], p['y']) for p in points_data]
                        self.parent_app.raster_widget.points = points
                        self.parent_app.raster_widget.update()
                        self.parent_app.updateRasterInfo()
                        QMessageBox.information(self, "Success", f"Pattern '{pattern_name}' loaded successfully!")
                        self.close()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load pattern: {e}")
    
    def delete_selected_pattern(self):
        """Delete the selected pattern"""
        current_item = self.pattern_list.currentItem()
        if current_item:
            pattern_name = current_item.text()
            reply = QMessageBox.question(self, "Confirm Delete", 
                                       f"Are you sure you want to delete pattern '{pattern_name}'?")
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    patterns = {}
                    if os.path.exists('saved_patterns.json'):
                        with open('saved_patterns.json', 'r') as f:
                            patterns = json.load(f)
                    
                    if pattern_name in patterns:
                        del patterns[pattern_name]
                        with open('saved_patterns.json', 'w') as f:
                            json.dump(patterns, f, indent=2)
                        
                        # Remove from list
                        row = self.pattern_list.row(current_item)
                        self.pattern_list.takeItem(row)
                        
                        QMessageBox.information(self, "Success", f"Pattern '{pattern_name}' deleted successfully!")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to delete pattern: {e}")

class WellButton(QPushButton):
    def __init__(self, row, col, plate_type, slide=None, custom_config=None):
        super().__init__()
        self.row = row
        self.col = col
        self.slide = slide  # 'A' or 'B' for 24-well plates
        self.custom_config = custom_config  # For custom plates
        self.selected = False
        self.completed = False
        self.updateSize(plate_type)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self.clicked.connect(self.handleClick)

    def updateSize(self, plate_type):
        if plate_type == "96-well":
            size = 40
        elif plate_type == "custom":
            size = 30  # Smaller size for custom plates
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
    
        # Update label format
        if self.custom_config:
            # For custom plates, use simple numbering
            spot_number = self.row * self.custom_config['num_columns'] + self.col + 1
            label = str(spot_number)
        elif self.slide:
            row_offset = 4 if self.slide == 'B' else 0  # Offset by 4 rows for slide B
            label = f"{chr(65 + self.row + row_offset)}{str(self.col + 1).zfill(2)}"
        else:
            label = f"{chr(65 + self.row)}{str(self.col + 1).zfill(2)}"

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

    def save_pattern(self):
        """Save the current pattern"""
        if not self.points:
            QMessageBox.warning(None, "Warning", "No pattern to save!")
            return
        
        name, ok = QInputDialog.getText(None, "Save Pattern", "Enter pattern name:")
        if ok and name:
            try:
                # Load existing patterns
                patterns = {}
                if os.path.exists('saved_patterns.json'):
                    with open('saved_patterns.json', 'r') as f:
                        patterns = json.load(f)
                
                # Convert QPoint objects to serializable format
                points_data = [{'x': p.x(), 'y': p.y()} for p in self.points]
                patterns[name] = points_data
                
                # Save back to file
                with open('saved_patterns.json', 'w') as f:
                    json.dump(patterns, f, indent=2)
                
                QMessageBox.information(None, "Success", f"Pattern '{name}' saved successfully!")
            except Exception as e:
                QMessageBox.warning(None, "Error", f"Failed to save pattern: {e}")


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
        
        # Add delay setting
        self.startup_delay = QDoubleSpinBox()
        self.startup_delay.setRange(0, 60)
        self.startup_delay.setValue(8)
        self.startup_delay.setDecimals(1)
        self.startup_delay.setSuffix(" seconds")
        
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
        layout.addRow("Startup delay:", self.startup_delay)
        
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
            '44-well-B': {'x': self.plate_44_B_x.value(), 'y': self.plate_44_B_y.value()},
            'startup_delay': self.startup_delay.value()
        }
    
    def set_values(self, values):
        self.plate_96_x.setValue(values['96-well']['x'])
        self.plate_96_y.setValue(values['96-well']['y'])
        self.plate_44_A_x.setValue(values['44-well-A']['x'])
        self.plate_44_A_y.setValue(values['44-well-A']['y'])
        self.plate_44_B_x.setValue(values['44-well-B']['x'])
        self.plate_44_B_y.setValue(values['44-well-B']['y'])
        if 'startup_delay' in values:
            self.startup_delay.setValue(values['startup_delay'])

class WellPlateApp(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize offset values
        self.offsets = {
            '96-well': {'x': 10, 'y': 1},      # Default values from original code
            '44-well-A': {'x': 46, 'y': 11},    # Default values for Slide A
            '44-well-B': {'x': 46, 'y': 45},    # Default values for Slide B
            'startup_delay': 8.0  # Default startup delay

        }
        
        # Custom plate configuration
        self.custom_plate_config = None
        self.custom_wells = []

        # Load settings on startup
        self.load_settings()

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

        self.method_file = "C:/HDI/lib/HTDESI_05Hz_neg_res.exp"
        self.base_directory = "C:/MassLynx/Default.pro/Data/"
        self.plate_type = "96-well"
        self.wells_A = []
        self.wells_B = []
        self.wells = []
        self.initUI()

        self.drag_start = None   
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

    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('app_settings.json'):
                with open('app_settings.json', 'r') as f:
                    settings = json.load(f)
                    if 'offsets' in settings:
                        self.offsets.update(settings['offsets'])
                    if 'custom_plate_config' in settings:
                        self.custom_plate_config = settings['custom_plate_config']
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                'offsets': self.offsets,
                'custom_plate_config': self.custom_plate_config
            }
            with open('app_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

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
        elif self.plate_type == "custom":
            selected_wells = sum(1 for well in self.custom_wells if well.selected)
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
        self.plate_selector.addItems(["96-well", "44-well", "custom"])
        self.plate_selector.currentTextChanged.connect(self.changePlateType)
        plate_selector_layout.addWidget(self.plate_selector)
        
        # Add custom plate configuration button
        self.config_custom_btn = QPushButton('Configure Custom Plate')
        self.config_custom_btn.clicked.connect(self.configure_custom_plate)
        self.config_custom_btn.setVisible(False)  # Initially hidden
        plate_selector_layout.addWidget(self.config_custom_btn)
        
        # Add connect button
        connect_btn = QPushButton('Connect to DESI-XS')
        connect_btn.clicked.connect(self.initiate_desi)
        plate_selector_layout.addWidget(connect_btn)
        
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
        
        # Container for custom plates
        self.custom_plate_container = QWidget()
        self.custom_plate_layout = QVBoxLayout(self.custom_plate_container)
        self.custom_plate_label = QLabel("Custom Plate")
        font_custom = QFont()
        font_custom.setPointSize(14)
        font_custom.setBold(True)
        self.custom_plate_label.setFont(font_custom)
        self.custom_plate_grid = QGridLayout()
        self.custom_plate_layout.addWidget(self.custom_plate_label)
        self.custom_plate_layout.addLayout(self.custom_plate_grid)
        
        left_panel.addWidget(self.grid_container)
        left_panel.addWidget(self.dual_plate_container)
        left_panel.addWidget(self.custom_plate_container)

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

        # Pattern control buttons
        pattern_button_layout = QHBoxLayout()
        clear_pattern_btn = QPushButton('Clear Pattern')
        clear_pattern_btn.clicked.connect(self.raster_widget.clear_pattern)
        save_pattern_btn = QPushButton('Save Pattern')
        save_pattern_btn.clicked.connect(self.raster_widget.save_pattern)
        manage_patterns_btn = QPushButton('Manage Patterns')
        manage_patterns_btn.clicked.connect(self.show_pattern_manager)
        
        pattern_button_layout.addWidget(clear_pattern_btn)
        pattern_button_layout.addWidget(save_pattern_btn)
        pattern_button_layout.addWidget(manage_patterns_btn)
        right_panel.addLayout(pattern_button_layout)

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

    def show_pattern_manager(self):
        """Show the pattern manager dialog"""
        dialog = PatternManagerDialog(self)
        dialog.exec()

    def configure_custom_plate(self):
        """Configure custom plate settings"""
        dialog = CustomPlateDialog(self, self.custom_plate_config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.custom_plate_config = dialog.get_config()
            self.save_settings()  # Save the configuration
            if self.plate_type == "custom":
                self.createWellGrid()  # Recreate the grid with new settings

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
        
        global fulldata, fulloutdata, fulloutCSVdata, WellList, run_info_data
        
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
        
        # Try to load the new JSON format first, fall back to legacy format
        run_info_file = os.path.join(fulldata, 'run_info.json')
        legacy_wells_file = os.path.join(fulldata, 'selected_wells.txt')
        
        run_info_data = None
        
        if os.path.exists(run_info_file):
            try:
                with open(run_info_file, 'r') as f:
                    run_info_data = json.load(f)
                WellList = ['Selected', 'Wells:'] + run_info_data['selected_wells']  # Maintain legacy format
                print(f"Loaded run info: {run_info_data['plate_type']} plate with {run_info_data['total_wells']} wells")
                
                # Save plate configuration to output directory for the processing app
                config_output_file = os.path.join(outdir, f'{outdata}_plate_config.json')
                with open(config_output_file, 'w') as f:
                    json.dump(run_info_data, f, indent=2)
                print(f"Plate configuration saved to: {config_output_file}")
                    
            except Exception as e:
                print(f"Error loading run_info.json: {e}, falling back to legacy format")
                run_info_data = None
        
        if run_info_data is None and os.path.exists(legacy_wells_file):
            WellList = open(legacy_wells_file).read().split()
            print("Using legacy selected_wells.txt format")
        elif run_info_data is None:
            raise FileNotFoundError("Neither run_info.json nor selected_wells.txt found in data directory")

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
        Updates the method file settings based on scan time and well timing calculations.
        
        Args:
            method_file_path (str): Path to the method file
            time_per_well (float): Calculated time per well in seconds
        """
        try:
            # Read the method file
            with open(method_file_path, 'r') as file:
                lines = file.readlines()
            
            # Find FunctionScanTime
            scan_time = None
            for line in lines:
                if 'FunctionScanTime' in line:
                    scan_time = float(line.split(',')[1].strip())
                    break
                    
            if scan_time is None:
                raise ValueError("FunctionScanTime not found in method file")
                
            # Calculate scans per well
            # Adding 0.014s overhead per scan
            scans_per_well = int(time_per_well / (scan_time + 0.014))
            
            # Calculate new X step size
            new_x_step = 5.0 / scans_per_well
            
            # Create modified content
            new_lines = []
            desi_settings = {
                'DesiXStart': '0',
                'DesiYStart': '0',
                'DesiXLength': '5',
                'DesiXStep': f'{new_x_step:.6f}',
                'DesiXRate': '2500',
                'DesiYLength': '500',
                'DesiYStep': '1',
                'DesiSlot': 'Full'
            }
            
            for line in lines:
                # Check if line starts with any of the DESI settings
                setting_found = False
                for setting, value in desi_settings.items():
                    if line.startswith(setting + ','):
                        new_lines.append(f'{setting},{value}\n')
                        setting_found = True
                        break
                
                if not setting_found:
                    new_lines.append(line)
            
            # Write modified content back to file
            with open(method_file_path, 'w') as file:
                file.writelines(new_lines)
                
            return {
                'scan_time': scan_time,
                'scans_per_well': scans_per_well,
                'new_x_step': new_x_step
            }
            
        except Exception as e:
            raise Exception(f"Error updating method file: {str(e)}")

    def Process_main(self,folder_name, fulldata, WellList, fulloutdata, fulloutCSVdata):
        try:
            print(f"Processing raw data file: {folder_name}")
            
            # Initialize reader
            import WatersIMGReader as wat
            reader = wat.WatersIMGReader(fulldata, 1)
            
            # Get basic information about the data
            scans = reader.getTotalScans()
            print(f"Data contains: {scans} scans")
            
            massRange = reader.getMassRange()
            print(f"Mass range: {massRange[0]} to {massRange[1]}")
            
            # Get X,Y coordinates
            X, Y, points = reader.getXYCoordinates()
            Ynp = np.array(Y)
            ScanR = np.arange(scans) + 1
            Number_of_wells = len(np.unique(Ynp))
            
            print(f"Number of unique Y positions: {Number_of_wells}")
            
            # Handle array length mismatch
            len1, len2 = len(ScanR), len(Ynp)
            if len2 < len1:
                padding = np.full(len1-len2, Ynp[-1])
                Ynp2 = np.concatenate([Ynp, padding])
            else:
                Ynp2 = Ynp
            
            # Check if we have run_info_data with custom plate information
            global run_info_data
            processing_summary = {
                'processed_wells': [],
                'processing_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_scans': scans,
                'mass_range': massRange
            }
            
            if 'run_info_data' in globals() and run_info_data:
                processing_summary['original_run_info'] = run_info_data
                print(f"Processing data from {run_info_data['plate_type']} plate")
            
            # Process each well
            for x in range(Number_of_wells):
                if x < len(WellList):
                    Rwell = WellList[x+2]
                    print(f"Processing well {Rwell} ({x+1}/{Number_of_wells})")
                    
                    # Get data for this well
                    Data = np.column_stack((ScanR, Ynp2))
                    Output = Data[np.where(Data[:,1]==x), 0]
                    
                    if len(Output[0]) > 0:
                        start = int(Output[0,0])
                        end = int(Output[0,-1])
                        
                        print(f"  Creating series file for scans {start} to {end}")
                        self.create_series_file(start, end)
                        
                        print("  Running maldichrom process")
                        prog_path = 'C:/HDI/lib/maldichrom.exe'
                        scans_path = 'C:/HDI/lib/outputScans.txt'
                        raw_out = f'{fulloutdata}_{Rwell}.raw'
                        self.create96_well_process(Rwell)
                        sleep(1)  # Small delay between processes
                        
                        print("  Converting to CSV format")
                        csv_out = f'{fulloutCSVdata}_{Rwell}.csv'
                        self.raw_to_csv(raw_out, csv_out)
                        print(raw_out)
                        print(f"  Well {Rwell} processing complete")
                        
                        # Add to processing summary
                        processing_summary['processed_wells'].append({
                            'well_id': Rwell,
                            'scan_range': {'start': start, 'end': end},
                            'output_files': {
                                'raw': f'{fulloutdata}_{Rwell}.raw',
                                'csv': f'{fulloutCSVdata}_{Rwell}.csv'
                            }
                        })
                    else:
                        print(f"  No data found for well {Rwell}")
                else:
                    print(f"Warning: More Y positions than well IDs. Skipping position {x}")
            
            # Save processing summary
            outdata = folder_name[0:-4]
            outdir = os.path.dirname(fulloutdata)
            summary_file = os.path.join(outdir, f'{outdata}_processing_summary.json')
            with open(summary_file, 'w') as f:
                json.dump(processing_summary, f, indent=2)
            print(f"Processing summary saved to: {summary_file}")
            
            print("\nProcessing complete!")
        
        except Exception as e:
            print(f"Error during processing: {str(e)}")
            raise

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Process Data")
        
        # Check if a folder was actually selected
        if folder_path:
            try:
                folder_name = os.path.basename(folder_path)
                parent_dir = os.path.dirname(folder_path)
                
                print('getting names')
                self.prepare_names(folder_name, parent_dir, folder_path)
                print('got names')
                self.Process_main(folder_name, fulldata, WellList, fulloutdata, fulloutCSVdata)
                print('done stuff')
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
            elif self.plate_type == "custom":
                wells_to_check = self.custom_wells
            else:
                wells_to_check = self.wells_A + self.wells_B
    
            for well in wells_to_check:
                well_rect = well.geometry()
                if self.plate_type == "96-well":
                    well_center = well.mapTo(self, QPoint(well.width() // 2, well.height() // 2))
                elif self.plate_type == "custom":
                    well_center = well.mapTo(self.custom_plate_container, QPoint(well.width() // 2, well.height() // 2))
                    well_center = self.custom_plate_container.mapTo(self, well_center)
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
        elif self.plate_type == "custom":
            for well in self.custom_wells:
                well.selected = True
                well.update()
        else:
            for well in self.wells_A + self.wells_B:
                well.selected = True
                well.update()
        self.updateStatusLabel()
        self.updateRasterInfo()

    def deselectAll(self):
        if self.plate_type == "96-well":
            for well in self.wells:
                well.selected = False
                well.update()
        elif self.plate_type == "custom":
            for well in self.custom_wells:
                well.selected = False
                well.update()
        else:
            for well in self.wells_A + self.wells_B:
                well.selected = False
                well.update()
        self.updateStatusLabel()
        self.updateRasterInfo()

    def updateStatusLabel(self):
        if self.plate_type == "96-well":
            selected_count = sum(1 for well in self.wells if well.selected)
        elif self.plate_type == "custom":
            selected_count = sum(1 for well in self.custom_wells if well.selected)
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
            self.custom_plate_container.hide()
            self.config_custom_btn.setVisible(False)
        elif plate_type == "44-well":
            self.grid_container.hide()
            self.dual_plate_container.show()
            self.custom_plate_container.hide()
            self.config_custom_btn.setVisible(False)
        else:  # custom
            self.grid_container.hide()
            self.dual_plate_container.hide()
            self.custom_plate_container.show()
            self.config_custom_btn.setVisible(True)
            
            # If no custom configuration exists, prompt user to create one
            if not self.custom_plate_config:
                QMessageBox.information(self, "Custom Plate", 
                                      "Please configure your custom plate settings first.")
                self.configure_custom_plate()
        
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
        for i in reversed(range(self.custom_plate_grid.count())): 
            self.custom_plate_grid.itemAt(i).widget().setParent(None)
        
        self.wells = []
        self.wells_A = []
        self.wells_B = []
        self.custom_wells = []
        
        if self.plate_type == "96-well":
            self.grid_container.show()
            self.dual_plate_container.hide()
            self.custom_plate_container.hide()
            rows, cols = 8, 12
            for row in range(rows):
                for col in range(cols):
                    well = WellButton(row, col, self.plate_type)
                    self.grid_layout.addWidget(well, row, col)
                    self.wells.append(well)
        elif self.plate_type == "44-well":
            self.grid_container.hide()
            self.dual_plate_container.show()
            self.custom_plate_container.hide()
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
        else:  # custom
            self.grid_container.hide()
            self.dual_plate_container.hide()
            self.custom_plate_container.show()
            
            if self.custom_plate_config:
                rows = self.custom_plate_config['num_rows']
                cols = self.custom_plate_config['num_columns']
                for row in range(rows):
                    for col in range(cols):
                        well = WellButton(row, col, self.plate_type, custom_config=self.custom_plate_config)
                        self.custom_plate_grid.addWidget(well, row, col)
                        self.custom_wells.append(well)

    def startRunProcess(self):
        # Get selected wells based on plate type
        if self.plate_type == "96-well":
            self.selected_wells = [well for well in self.wells if well.selected]
        elif self.plate_type == "custom":
            self.selected_wells = [well for well in self.custom_wells if well.selected]
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
    
        # Update method file settings
        try:
            results = self.update_method_file_settings(self.method_file, time_per_well)
            print(f"Method file updated: {results['scans_per_well']} scans per well, "
                  f"X step size: {results['new_x_step']:.6f}")
        except Exception as e:
            print(f"Error updating method file: {str(e)}")
            return

        GoHome()
        filename = self.filename_input.text()
        
        # Create the main queue file
        with open(f'C:/MassLynx/AutoLynxQueue/{filename}.raw.txt', 'w') as file:    
            file.write(f'INDEX\tFILE_NAME\tFILE_TEXT\tMS_FILE\tMS_TUNE_FILE\tPROCESS\tPROCESS_PARAMS\n')
            file.write(f'1\t"{self.base_directory}{filename}.raw"\t"HT-DESI"\t"{self.method_file}"\t""\t""\t""\n')
            
        print('going to sleep')
        
        # Use configurable startup delay instead of hard-coded 8 seconds
        startup_delay = self.offsets.get('startup_delay', 8.0)
        time.sleep(startup_delay) 
        
        print('woken up')  
        GoToPos(20,20)
        print('gone to 20 20')

        self.current_well_index = 0
        self.current_coord_index = 0
        self.is_running = True
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.processNextWell()

    def stopRunProcess(self):
        self.is_running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        print("Process stopped.")
        GoHome()
        sleep(2)
        self.StopMS()
        self.resetWellColors()

    def adjustWellSpacing(self):
        if self.plate_type == "96-well":
            well_size = 9  # 9mm apart
            well_diam = 2
        elif self.plate_type == "custom":
            if self.custom_plate_config:
                well_size = max(self.custom_plate_config['spot_distance_x'], 
                              self.custom_plate_config['spot_distance_y'])
                well_diam = 2
            else:
                well_size = 3
                well_diam = 2
        else:  # 24-well
            well_size = 4  # Double the spacing for 24-well plate
            well_diam = 2

    def show_offset_settings(self):
        dialog = OffsetSettingsDialog(self)
        dialog.set_values(self.offsets)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.offsets = dialog.get_values()
            self.save_settings()  # Save settings when changed
            print("New offset values:", self.offsets)

    def processNextWell(self):
        if not self.is_running:
            return

        if self.plate_type == "96-well":
            current_selected_wells = [well for well in self.wells if well.selected]
        elif self.plate_type == "custom":
            current_selected_wells = [well for well in self.custom_wells if well.selected]
        else:
            current_selected_wells = ([well for well in self.wells_A if well.selected] + 
                                    [well for well in self.wells_B if well.selected])

        if self.current_well_index >= len(selected_wells):
            print("All selected wells processed.")
            GoHome()
            self.StopMS()
            self.is_running = False
            self.run_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            QTimer.singleShot(1000, self.resetWellColors)
            filename = self.filename_input.text()
            
        wells_output = []
        for well in current_selected_wells:  # Use the current list
            try:
                if self.plate_type == "custom":
                    if self.custom_plate_config:  # Check if config exists
                        spot_number = well.row * self.custom_plate_config['num_columns'] + well.col + 1
                        well_id = f"Spot_{spot_number}"
                    else:
                        well_id = f"Spot_{well.row * 6 + well.col + 1}"  # Fallback
                elif hasattr(well, 'slide') and well.slide:
                    row_offset = 4 if well.slide == 'B' else 0
                    well_id = f"{chr(65 + well.row + row_offset)}{str(well.col + 1).zfill(2)}"
                else:
                    well_id = f"{chr(65 + well.row)}{str(well.col + 1).zfill(2)}"
                wells_output.append(well_id)
            except Exception as e:
                print(f"Error processing well at row {well.row}, col {well.col}: {e}")
                wells_output.append(f"Unknown_{len(wells_output)}")
            }
            
            # Add custom plate configuration if applicable
            if self.plate_type == "custom" and self.custom_plate_config:
                run_info['custom_plate_config'] = self.custom_plate_config.copy()
                
                # Create detailed well mapping for custom plates
                well_mapping = []
                for well in self.selected_wells:
                    spot_number = well.row * self.custom_plate_config['num_columns'] + well.col + 1
                    well_mapping.append({
                        'spot_id': f"Spot_{spot_number}",
                        'row': well.row,
                        'col': well.col,
                        'x_position_mm': well.col * self.custom_plate_config['spot_distance_x'] + self.custom_plate_config['offset_x'],
                        'y_position_mm': well.row * self.custom_plate_config['spot_distance_y'] + self.custom_plate_config['offset_y'],
                        'spot_diameter_mm': self.custom_plate_config['spot_diameter']
                    })
                run_info['well_mapping'] = well_mapping

            # Save comprehensive run information as JSON
            data_dir = f'C:/MassLynx/Default.pro/Data/{filename}.raw'
            with open(f'{data_dir}/run_info.json', 'w') as f:
                json.dump(run_info, f, indent=2)
            
            # Save legacy format for backward compatibility
            with open(f'{data_dir}/selected_wells.txt', 'w') as f:
                f.write("Selected Wells:\n")
                f.write("\n".join(wells_output))
            
            return

        well = selected_wells[self.current_well_index]
        
        # Get appropriate offsets based on plate type and slide
        if self.plate_type == "96-well":
            x_offset = self.offsets['96-well']['x']
            y_offset = self.offsets['96-well']['y']
            well_size = 9
            well_diam = 2
        elif self.plate_type == "custom":
            # For custom plates, use the configured spacing
            x_offset = self.custom_plate_config['offset_x']
            y_offset = self.custom_plate_config['offset_y']
            well_size_x = self.custom_plate_config['spot_distance_x']
            well_size_y = self.custom_plate_config['spot_distance_y']
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

        # Calculate well center based on plate type
        if self.plate_type == "custom":
            well_center_x = well.col * well_size_x + x_offset
            well_center_y = well.row * well_size_y + y_offset
            # Use custom spot diameter for raster pattern scaling
            well_diam = self.custom_plate_config['spot_diameter']
        else:
            well_center_x = (well.col + 1) * well_size + well_diam / 2 + x_offset
            well_center_y = (well.row) * well_size + well_diam / 2 + y_offset

        raster_pattern = self.raster_widget.points
        if not raster_pattern:
            raster_pattern = [QPoint(100, 100)]  # Use center if no pattern defined

        self.current_well_coords = []
        for point in raster_pattern:
            # Scale the raster pattern based on the actual spot diameter
            # The raster widget is 180px diameter (from 10 to 190), center at 100
            # Map this to the actual spot diameter
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
        elif self.plate_type == "custom":
            for well in self.custom_wells:
                well.reset()
        else:  # 24-well
            for well in self.wells_A + self.wells_B:
                well.reset()
        print("Well colors reset.")

    def StopMS(self):
        mainPath = r"C:/HDI/lib"
        command = 'MSStartStop.exe/stop'
        subprocess.Popen(command,cwd=mainPath,shell=True)

    def closeEvent(self, event):
        """Save settings when the application is closed"""
        self.save_settings()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = WellPlateApp()
    ex.show()
    sys.exit(app.exec())