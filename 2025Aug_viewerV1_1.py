import sys
import os
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Optional, Tuple
from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QVBoxLayout, 
                           QHBoxLayout, QWidget, QPushButton, QSizePolicy, 
                           QComboBox, QLabel, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, rgb2hex
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.cm import ScalarMappable
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

class PlateConfigReader:
    """
    Class to read and interpret plate configuration data from the well plate app
    """
    
    def __init__(self, data_folder_path: str):
        self.data_folder_path = data_folder_path
        self.plate_config = None
        self.well_mapping = None
        self.processing_summary = None
        
    def load_plate_data(self, experiment_name: str) -> bool:
        """
        Load all plate-related data for a given experiment
        
        Args:
            experiment_name: Name of the experiment (filename without extension)
            
        Returns:
            bool: True if data loaded successfully, False otherwise
        """
        try:
            # Try to load the plate configuration
            config_file = os.path.join(self.data_folder_path, 'outputs', f'{experiment_name}_plate_config.json')
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self.plate_config = json.load(f)
                    
                print(f"Loaded plate configuration: {self.plate_config['plate_type']}")
                
                # Extract well mapping if available
                if 'well_mapping' in self.plate_config:
                    self.well_mapping = self.plate_config['well_mapping']
                    
                return True
            else:
                print(f"No plate config found at: {config_file}")
                return False
                
        except Exception as e:
            print(f"Error loading plate data: {e}")
            return False
    
    def get_plate_type(self) -> str:
        """Get the type of plate used"""
        if self.plate_config:
            return self.plate_config.get('plate_type', 'unknown')
        return 'unknown'
    
    def get_plate_dimensions(self) -> Optional[Dict]:
        """Get physical dimensions of the plate"""
        if not self.plate_config:
            return None
            
        if self.plate_config['plate_type'] == 'custom':
            config = self.plate_config['custom_plate_config']
            return {
                'width_mm': config['print_width'],
                'height_mm': config['print_height'],
                'rows': config['num_rows'],
                'columns': config['num_columns'],
                'spot_spacing_x': config['spot_distance_x'],
                'spot_spacing_y': config['spot_distance_y'],
                'spot_diameter': config['spot_diameter'],
                'offset_x': config['offset_x'],
                'offset_y': config['offset_y']
            }
        elif self.plate_config['plate_type'] == '96-well':
            return {
                'width_mm': 127.76,  # Standard 96-well plate
                'height_mm': 85.48,
                'rows': 8,
                'columns': 12,
                'spot_spacing_x': 9.0,
                'spot_spacing_y': 9.0,
                'spot_diameter': 2.0
            }
        elif self.plate_config['plate_type'] == '44-well':
            return {
                'width_mm': 44.0,  # Approximate
                'height_mm': 16.0,
                'rows': 4,
                'columns': 11,
                'spot_spacing_x': 4.0,
                'spot_spacing_y': 4.0,
                'spot_diameter': 2.0
            }
        
        return None
    
    def get_well_positions(self) -> List[Dict]:
        """
        Get physical positions of all wells/spots
        
        Returns:
            List of dictionaries with well position information
        """
        positions = []
        
        if not self.plate_config:
            return positions
            
        # For custom plates, use the detailed well mapping
        if (self.plate_config['plate_type'] == 'custom' and 
            'well_mapping' in self.plate_config):
            
            for well in self.plate_config['well_mapping']:
                positions.append({
                    'id': well['spot_id'],
                    'row': well['row'],
                    'col': well['col'],
                    'x_mm': well['x_position_mm'],
                    'y_mm': well['y_position_mm'],
                    'diameter_mm': well.get('spot_diameter_mm', 2.0),
                    'selected': True  # These were the selected wells
                })
        
        # For standard plates, calculate positions
        else:
            dimensions = self.get_plate_dimensions()
            if dimensions:
                selected_wells = self.plate_config.get('selected_wells', [])
                
                for well_id in selected_wells:
                    # Parse well ID (e.g., "A01", "B12")
                    if len(well_id) >= 2:
                        row_letter = well_id[0]
                        col_num = int(well_id[1:])
                        
                        row = ord(row_letter) - ord('A')
                        col = col_num - 1
                        
                        x_mm = col * dimensions['spot_spacing_x']
                        y_mm = row * dimensions['spot_spacing_y']
                        
                        positions.append({
                            'id': well_id,
                            'row': row,
                            'col': col,
                            'x_mm': x_mm,
                            'y_mm': y_mm,
                            'diameter_mm': dimensions['spot_diameter'],
                            'selected': True
                        })
        
        return positions
    
    def get_selected_wells(self) -> List[str]:
        """Get list of selected well IDs"""
        if not self.plate_config:
            return []
            
        if self.plate_config['plate_type'] == 'custom' and 'well_mapping' in self.plate_config:
            return [well['spot_id'] for well in self.plate_config['well_mapping']]
        else:
            return self.plate_config.get('selected_wells', [])

class RoundButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(40, 40)
        self.setStyleSheet("""
            QPushButton {
                border-radius: 20px;
                border: 2px solid #444444;
                font-weight: bold;
                color: white;
                background-color: #808080;
            }
        """)
        
    def set_inactive(self):
        self.setStyleSheet("""
            QPushButton {
                border-radius: 20px;
                border: 2px solid #444444;
                font-weight: bold;
                color: white;
                background-color: #D3D3D3;
            }
        """)
        self.setEnabled(False)

class WellPlate(QWidget):
    well_clicked = pyqtSignal(str)

    def __init__(self, analyzer, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer  # Store direct reference to analyzer
        self.normalized = False
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        plt.rcParams['font.family'] = 'Calibri'
        
        # Add layout selector
        layout_selector = QHBoxLayout()
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(['96 Well Plate', '2x 44 Well Plates', 'Load Custom Plate'])
        self.layout_combo.currentTextChanged.connect(self.change_plate_layout)
        layout_selector.addWidget(QLabel("Plate Layout:"))
        layout_selector.addWidget(self.layout_combo)
        layout_selector.addStretch()
        self.layout.addLayout(layout_selector)

        self.info_label = QLabel()
        self.layout.addWidget(self.info_label)

        # Create horizontal layout for plates and barchart
        plate_and_chart = QHBoxLayout()
        self.layout.addLayout(plate_and_chart)

        # Create a horizontal layout for controls
        controls_layout = QHBoxLayout()
        
        # Create a container for the colormap selection with fixed width
        colormap_container = QWidget()
        colormap_container.setFixedWidth(200)  # Could change this if needed
        colormap_layout = QHBoxLayout(colormap_container)

       # Add colormap selection
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(['viridis', 'plasma', 'inferno', 'magma', 'cividis'])
        self.colormap_combo.currentTextChanged.connect(self.change_colormap)
        colormap_layout.addWidget(QLabel("Colormap:"))
        colormap_layout.addWidget(self.colormap_combo)

        # Add the colormap container to controls layout
        controls_layout.addWidget(colormap_container)
        
        # Add sum normalize button
        self.normalize_button = QPushButton("Sum Normalize")
        self.normalize_button.clicked.connect(self.sum_normalize_data)
        controls_layout.addWidget(self.normalize_button)

        # Add stretch to push everything to the left
        controls_layout.addStretch()
        
        # Add controls layout to main layout
        self.layout.addLayout(controls_layout)
        
        self.colormap = plt.get_cmap('viridis')

        # Left side: Plates
        left_side = QWidget()
        left_layout = QVBoxLayout()
        left_side.setLayout(left_layout)
        
        self.plates_widget = QWidget()
        self.plates_layout = QVBoxLayout()
        self.plates_widget.setLayout(self.plates_layout)
        left_layout.addWidget(self.plates_widget)
        
        plate_and_chart.addWidget(left_side)

        # Initialize with 96 well plate
        self.current_layout = "96"
        self.buttons = {}
        self.active_wells = set()
        self.plate_config_reader = None
        self.custom_well_positions = None
        self.setup_96_well_plate()

        # Right side: Barchart
        right_side = QWidget()
        right_layout = QVBoxLayout()
        right_side.setLayout(right_layout)
        
        self.barchart_figure = Figure(figsize=(6, 8))
        self.barchart_canvas = FigureCanvas(self.barchart_figure)
        self.barchart_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.barchart_canvas)
        
        plate_and_chart.addWidget(right_side)
        
        # Set stretch factors to control relative sizes
        plate_and_chart.setStretch(0, 1)  # Plate layout
        plate_and_chart.setStretch(1, 1)  # Barchart

    def sum_normalize_data(self):
        print("Starting normalization...")
        
        if not hasattr(self.analyzer, 'data') or not self.analyzer.data:
            print("No data found in analyzer")
            return
        print(f"Found data with {len(self.analyzer.data)} wells")
        
        print(f"Current normalized state: {self.normalized}")
        self.normalized = not self.normalized
        print(f"New normalized state: {self.normalized}")
        
        if self.normalized:
            print("Setting button text to 'Raw Data'")
            self.normalize_button.setText("Raw Data")
            
            # Store original data if not already stored
            if not hasattr(self.analyzer, 'original_data'):
                print("Creating backup of original data")
                self.analyzer.original_data = {
                    well: df.copy() for well, df in self.analyzer.data.items()
                }
                print(f"Backed up {len(self.analyzer.original_data)} wells")
            
            # Normalize each spectrum by its own sum
            print("Starting normalization of spectra")
            for well in self.analyzer.data.keys():
                try:
                    spectrum_sum = self.analyzer.data[well]['intensity'].sum()
                    print(f"Well {well} sum: {spectrum_sum}")
                    if spectrum_sum > 0:  # Avoid division by zero
                        self.analyzer.data[well]['intensity'] = (
                            self.analyzer.data[well]['intensity'] / spectrum_sum
                        )
                        # Verify normalization
                        new_sum = self.analyzer.data[well]['intensity'].sum()
                        print(f"Well {well} new sum: {new_sum}")  # Should be close to 1.0
                except Exception as e:
                    print(f"Error processing well {well}: {str(e)}")
        else:
            print("Setting button text to 'Sum Normalize'")
            self.normalize_button.setText("Sum Normalize")
            # Restore original data
            if hasattr(self.analyzer, 'original_data'):
                print("Restoring original data")
                self.analyzer.data = {
                    well: df.copy() for well, df in self.analyzer.original_data.items()
                }
        
        # Update current view
        print("Updating view...")
        if hasattr(self.analyzer, 'current_spectrum'):
            try:
                if self.analyzer.current_spectrum == 'average':
                    self.analyzer.plot_average_spectrum()
                else:
                    self.analyzer.update_well_spectrum(self.analyzer.current_spectrum)
            except Exception as e:
                print(f"Error updating spectrum view: {str(e)}")
                
        # Update heatmap if a range is selected
        if hasattr(self.analyzer, 'last_selected_range') and self.analyzer.last_selected_range:
            try:
                print("Updating heatmap")
                self.analyzer.update_heatmap(self.analyzer.last_selected_range)
            except Exception as e:
                print(f"Error updating heatmap: {str(e)}")
        
        print("Normalization process complete")

    def load_custom_plate_config(self):
        """Load custom plate configuration from JSON file"""
        folder = QFileDialog.getExistingDirectory(self, "Select Data Folder with Plate Config")
        if folder:
            # Try to find experiment name from CSV files in the folder
            csv_files = [f for f in os.listdir(folder) if f.endswith(('.csv', '.CSV'))]
            if not csv_files:
                QMessageBox.warning(self, "Warning", "No CSV files found in selected folder")
                return False
            
            # Extract experiment name from first CSV file
            experiment_name = csv_files[0].rsplit('_', 1)[0]  # Remove well ID suffix
            
            self.plate_config_reader = PlateConfigReader(folder)
            if self.plate_config_reader.load_plate_data(experiment_name):
                plate_type = self.plate_config_reader.get_plate_type()
                
                if plate_type == 'custom':
                    self.custom_well_positions = self.plate_config_reader.get_well_positions()
                    active_wells = self.plate_config_reader.get_selected_wells()
                    self.setup_custom_plate(active_wells)
                    
                    # Update analyzer's data folder and reload data
                    self.analyzer.load_data(folder)
                    self.analyzer.plot_average_spectrum()
                    
                    QMessageBox.information(self, "Success", 
                                          f"Loaded custom plate configuration with {len(active_wells)} wells")
                    return True
                else:
                    QMessageBox.information(self, "Info", 
                                          f"Found {plate_type} plate configuration. Use standard layouts for this plate type.")
                    return False
            else:
                QMessageBox.warning(self, "Warning", "Could not load plate configuration")
                return False
        return False

    def setup_custom_plate(self, active_wells):
        """Setup custom plate layout based on well positions"""
        self.clear_plates()
        self.active_wells = set(active_wells)
        
        if not self.custom_well_positions:
            return
            
        # Determine grid size based on well positions
        max_row = max(pos['row'] for pos in self.custom_well_positions)
        max_col = max(pos['col'] for pos in self.custom_well_positions)
        
        plate_layout = QGridLayout()
        self.plates_layout.addLayout(plate_layout)
        
        # Add title
        title_label = QLabel("Custom Plate Layout")
        font = title_label.font()
        font.setPointSize(16)
        font.setBold(True)
        title_label.setFont(font)
        self.plates_layout.insertWidget(0, title_label)
        
        self.buttons = {}
        
        # Create buttons for each well position
        for pos in self.custom_well_positions:
            well_id = pos['id']
            row = pos['row']
            col = pos['col']
            
            button = RoundButton(well_id)
            button.clicked.connect(lambda _, w=well_id: self.on_well_clicked(w))
            plate_layout.addWidget(button, row, col)
            self.buttons[well_id] = button
            
            if well_id not in self.active_wells:
                button.set_inactive()
        
        # Fill empty positions with spacers if needed for visual clarity
        for row in range(max_row + 1):
            for col in range(max_col + 1):
                if plate_layout.itemAtPosition(row, col) is None:
                    spacer = QWidget()
                    spacer.setFixedSize(40, 40)
                    plate_layout.addWidget(spacer, row, col)
        
    def setup_96_well_plate(self):
        self.clear_plates()
        plate_layout = QGridLayout()
        self.plates_layout.addLayout(plate_layout)
        
        self.buttons = {}
        for i in range(8):  # A-H
            for j in range(12):  # 1-12
                well = f"{chr(65+i)}{j+1:02d}"
                button = RoundButton(well)
                button.clicked.connect(lambda _, w=well: self.on_well_clicked(w))
                plate_layout.addWidget(button, i, j)
                self.buttons[well] = button
                if well not in self.active_wells:
                    button.set_inactive()

    def setup_44_well_plates(self):
        self.clear_plates()
        
        # Create two plate layouts
        for plate_num in range(2):
            plate_layout = QGridLayout()
            plate_label = QLabel(f"Slide {plate_num + 1}")
            # Set the font size for plate labels
            font = plate_label.font()
            font.setPointSize(20)  # You can adjust this number to make it bigger or smaller
            font.setBold(True)     # Optional: make it bold
            plate_label.setFont(font)
            
            self.plates_layout.addWidget(plate_label)
            self.plates_layout.addLayout(plate_layout)
            
            # 44 well plate is 4x11
            for i in range(4):  # A-D
                for j in range(11):  # 1-11
                    well = f"{chr(65+i)}{j+1:02d}"
                    if plate_num == 1:
                        # For second plate, use wells E-H
                        well = f"{chr(69+i)}{j+1:02d}"  # E-H, 1-11
                    button = RoundButton(well)
                    button.clicked.connect(lambda _, w=well: self.on_well_clicked(w))
                    plate_layout.addWidget(button, i, j)
                    self.buttons[well] = button
                    if well not in self.active_wells:
                        button.set_inactive()
            
            if plate_num == 0:
                self.plates_layout.addSpacing(20)  # Add space between plates

    def clear_plates(self):
        # Clear existing plate layouts
        while self.plates_layout.count():
            item = self.plates_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    subitem = item.layout().takeAt(0)
                    if subitem.widget():
                        subitem.widget().deleteLater()

    def change_plate_layout(self, layout_text):
        if layout_text == "Load Custom Plate":
            success = self.load_custom_plate_config()
            if success:
                self.current_layout = "custom"
            else:
                # Reset to previous selection if loading failed
                self.layout_combo.setCurrentText("96 Well Plate")
                return
        else:
            self.current_layout = "96" if layout_text == "96 Well Plate" else "44"
            if self.current_layout == "96":
                self.setup_96_well_plate()
            else:
                self.setup_44_well_plates()
        
        # Reapply any existing heatmap
        if hasattr(self, 'last_values'):
            self.update_heatmap(self.last_values)

    def set_active_wells(self, wells):
        self.active_wells = set(wells)
        if self.current_layout == "96":
            self.setup_96_well_plate()
        elif self.current_layout == "44":
            self.setup_44_well_plates()
        # For custom plates, the wells are already set up during load

    def on_well_clicked(self, well):
        if well in self.active_wells:
            self.well_clicked.emit(well)

    def change_colormap(self, colormap_name):
        self.colormap = plt.get_cmap(colormap_name)
        if hasattr(self, 'last_values'):
            self.update_heatmap(self.last_values)

    def update_heatmap(self, values):
        if not values or not self.buttons:
            return
                
        self.last_values = values
        norm = Normalize(vmin=min(values), vmax=max(values))
        
        # Create list of active wells in same order as data dictionary
        ordered_wells = sorted(self.active_wells)
        
        # Create dictionary of well:value pairs
        value_dict = {well: value for well, value in zip(ordered_wells, values)}
        
        # Update button colors
        for well, button in self.buttons.items():
            if well in self.active_wells:
                value = value_dict[well]
                color = self.colormap(norm(value))
                hex_color = rgb2hex(color)
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_color};
                        color: white;
                        border-radius: 20px;
                        border: 2px solid #444444;
                        font-weight: bold;
                    }}
                """)
                button.setEnabled(True)
        
        # Update bar chart with properly ordered data
        self.barchart_figure.clear()
        self.barchart_figure.patch.set_facecolor('#f0f0f0')

        ax = self.barchart_figure.add_subplot(111)
        ax.set_facecolor('white') 
        
        y_pos = np.arange(len(ordered_wells))
        wells = list(ordered_wells)
        values_ordered = [value_dict[well] for well in ordered_wells]
        colors = [self.colormap(norm(value)) for value in values_ordered]
        
        # Calculate dynamic font size based on number of bars
        # More bars = smaller font
        num_wells = len(wells)
        if num_wells <= 20:
            font_size = 8
        elif num_wells <= 40:
            font_size = 6
        elif num_wells <= 60:
            font_size = 4
        else:
            font_size = 3
        
        # Create bars with drop shadow
        bars = ax.barh(y_pos, values_ordered, align='center', color=colors, 
                      edgecolor='dimgrey', linewidth=1)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(wells, fontsize=font_size)
        ax.invert_yaxis()
        ax.set_xlabel('Intensity', fontsize=10)
        ax.set_title('Intensity by Well', fontsize=12)
    
        # Add mean and std dev lines
        mean_value = np.mean(values)
        std_dev = np.std(values)
        ax.axvline(mean_value, color='blue', linestyle=':', label='Mean', zorder=3)
        ax.axvline(mean_value + std_dev, color='red', linestyle=':', label='+1 Std Dev', zorder=3)
        ax.axvline(mean_value - std_dev, color='red', linestyle=':', label='-1 Std Dev', zorder=3)
        ax.legend(fontsize='x-small')
    
        self.barchart_figure.tight_layout()
        self.barchart_canvas.draw()

    def set_info_label(self, mass_range, mean, std_dev):
        # Create and set the text
        # Use scientific notation for small values
        if abs(mean) < 0.01 or abs(std_dev) < 0.01:
            info_text = f"Mass Range: {mass_range[0]:.2f} - {mass_range[1]:.2f}, Mean: {mean:.2e}, Std Dev: {std_dev:.2e}"
        else:
            info_text = f"Mass Range: {mass_range[0]:.2f} - {mass_range[1]:.2f}, Mean: {mean:.2f}, Std Dev: {std_dev:.2f}"
        self.info_label.setText(info_text)
        
        # Create and set a font for the label
        font = self.info_label.font()
        font.setPointSize(12)  # Increase font size (default is usually around 8-9)
        font.setBold(True)     # Make the text bold
        self.info_label.setFont(font)
        
        # Optional: Add some padding and styling
        self.info_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: #f0f0f0;
                border-radius: 5px;
            }
        """)

    def update_rgb_colors(self, color_dict):
        """
        Update well colors using direct RGB values
        color_dict: Dictionary mapping well names to hex color strings
        """
        # First grey out all active wells
        for well, button in self.buttons.items():
            if well in self.active_wells:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #D3D3D3;
                        color: white;
                        border-radius: 20px;
                        border: 2px solid #444444;
                        font-weight: bold;
                    }
                """)
        
        # Then color the selected wells
        for well, color in color_dict.items():
            if well in self.buttons:
                self.buttons[well].setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        color: white;
                        border-radius: 20px;
                        border: 2px solid #444444;
                        font-weight: bold;
                }}
            """)
    
    def reset_colors(self):
        """Reset to last heatmap state"""
        if hasattr(self, 'last_values'):
            self.update_heatmap(self.last_values)

class MassSpectrumAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mass Spectrum Analyzer")
        self.setGeometry(100, 100, 1400, 800)
        # Set application-wide style including background color
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #f0f0f0;
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
        """)

        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Create WellPlate with reference to this analyzer
        self.well_plate = WellPlate(analyzer=self)
        self.well_plate.well_clicked.connect(self.update_well_spectrum)
        self.layout.addWidget(self.well_plate)

        # Rest of initialization remains the same...
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.figure.patch.set_facecolor('#f0f0f0')  # Match Qt background
        self.canvas = FigureCanvas(self.figure)
        # Set the mass spectrum plot to have a larger minimum height
        self.canvas.setMinimumHeight(250)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.canvas, stretch=2)  # Add stretch factor to give it more space

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)

        button_layout = QHBoxLayout()
        self.select_folder_button = QPushButton("Select Folder")
        self.select_folder_button.clicked.connect(self.select_folder)
        button_layout.addWidget(self.select_folder_button)

        self.average_spectrum_button = QPushButton("Show Average Spectrum")
        self.average_spectrum_button.clicked.connect(self.plot_average_spectrum)
        button_layout.addWidget(self.average_spectrum_button)

        self.export_csv_button = QPushButton("Export to CSV")
        self.export_csv_button.clicked.connect(self.export_to_csv)
        button_layout.addWidget(self.export_csv_button)

        self.pca_button = QPushButton("Perform PCA")
        self.pca_button.clicked.connect(self.perform_pca)
        button_layout.addWidget(self.pca_button)

        self.layout.addLayout(button_layout)

        self.data = {}
        self.average_spectrum = None
        self.current_spectrum = None
        self.span = None
        self.last_selected_range = None

        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.load_data(folder)
            self.plot_average_spectrum()

    def load_data(self, folder):
        self.data = {}
        self.original_data = {}  # Store original data for normalization resets
        active_wells = []
        
        for file in os.listdir(folder):
            if file.endswith(('.csv', '.CSV')):
                well = file[-7:-4]  # Extract well ID from filename
                file_path = os.path.join(folder, file)
                df = pd.read_csv(file_path, names=["mass_to_charge", "intensity"])
                df = df.groupby('mass_to_charge')['intensity'].mean().reset_index()
                self.data[well] = df
                self.original_data[well] = df.copy()  # Store a copy of original data
                active_wells.append(well)
    
        # Set active wells in well plate (only if not custom plate)
        if self.well_plate.current_layout != "custom":
            self.well_plate.set_active_wells(active_wells)
    
        # Create average spectrum
        min_mz = min(df['mass_to_charge'].min() for df in self.data.values())
        max_mz = max(df['mass_to_charge'].max() for df in self.data.values())
        
        step = 0.01
        common_mz = np.arange(min_mz, max_mz + step, step)
        
        aligned_intensities = []
        for df in self.data.values():
            interpolated = np.interp(
                common_mz,
                df['mass_to_charge'],
                df['intensity'],
                left=0,
                right=0
            )
            aligned_intensities.append(interpolated)
        
        average_intensities = np.mean(aligned_intensities, axis=0)
        self.average_spectrum = pd.Series(
            data=average_intensities,
            index=common_mz
        )

    def plot_average_spectrum(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')  # Keep plot area white
        ax.plot(self.average_spectrum.index, self.average_spectrum.values)
        ax.set_xlabel('Mass to Charge')
        ax.set_ylabel('Intensity')
        ax.set_title('Average Mass Spectrum')
        
        self.span = SpanSelector(ax, self.on_select, 'horizontal', useblit=True, 
                                 props=dict(alpha=0.5, facecolor='red'))
        self.canvas.draw()
        self.current_spectrum = 'average'

        if self.last_selected_range:
            self.update_heatmap(self.last_selected_range)
            
    def update_well_spectrum(self, well):
        if well not in self.data:
            return
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')  # Keep plot area white
        spectrum = self.data[well]
        ax.plot(spectrum['mass_to_charge'], spectrum['intensity'])
        ax.set_xlabel('Mass to Charge')
        ax.set_ylabel('Intensity')
        ax.set_title(f'Mass Spectrum for Well {well}')
        
        self.span = SpanSelector(ax, self.on_select, 'horizontal', useblit=True, 
                                 props=dict(alpha=0.5, facecolor='red'))
        self.canvas.draw()
        self.current_spectrum = well
    
        if self.last_selected_range:
            self.update_heatmap(self.last_selected_range)
    
    def on_select(self, xmin, xmax):
        self.last_selected_range = (xmin, xmax)
        self.update_heatmap((xmin, xmax))
    
    def update_heatmap(self, mass_range):
        ordered_wells = sorted(self.data.keys())
        values = []
        for well in ordered_wells:
            spectrum = self.data[well]
            mask = (spectrum['mass_to_charge'] >= mass_range[0]) & (spectrum['mass_to_charge'] <= mass_range[1])
            mean_intensity = spectrum.loc[mask, 'intensity'].mean()
            values.append(mean_intensity)
        
        self.well_plate.update_heatmap(values)
        
        mean_value = np.mean(values)
        std_dev = np.std(values)
        self.well_plate.set_info_label(mass_range, mean_value, std_dev)
    
    def export_to_csv(self):
        if not self.last_selected_range:
            return
    
        file_name, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if file_name:
            data = []
            for well, spectrum in self.data.items():
                mask = (spectrum['mass_to_charge'] >= self.last_selected_range[0]) & (spectrum['mass_to_charge'] <= self.last_selected_range[1])
                mean_intensity = spectrum.loc[mask, 'intensity'].mean()
                data.append({
                    'Well': well,
                    'Mass Range': f"{self.last_selected_range[0]:.2f} - {self.last_selected_range[1]:.2f}",
                    'Intensity': mean_intensity
                })
            
            df = pd.DataFrame(data)
            df.to_csv(file_name, index=False)

    def perform_pca(self):
        if not self.data or not self.last_selected_range:
            return
    
        # Create a common mass-to-charge axis within the selected range
        step = 0.01  # Adjust based on your data resolution
        common_mz = np.arange(
            self.last_selected_range[0],
            self.last_selected_range[1] + step,
            step
        )
        
        # Prepare aligned data for PCA
        X = []
        wells = []
        for well, spectrum in self.data.items():
            # Interpolate this spectrum onto the common axis
            interpolated = np.interp(
                common_mz,
                spectrum['mass_to_charge'],
                spectrum['intensity'],
                left=0,
                right=0
            )
            X.append(interpolated)
            wells.append(well)
    
        X = np.array(X)
    
        # Standardize the data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
    
        # Perform PCA
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(X_scaled)
    
        # Create and show PCA window, passing self as parent
        self.pca_window = PCAWindow(pca_result, wells, parent=self)
        self.pca_window.show()
        
    def on_mouse_press(self, event):
        if event.button == 3:  # Right mouse button
            self.zoom_start = (event.xdata, event.ydata)
    
    def on_mouse_release(self, event):
        if event.button == 3:  # Right mouse button
            if event.dblclick:
                self.reset_zoom()
            elif hasattr(self, 'zoom_start'):
                self.zoom(self.zoom_start, (event.xdata, event.ydata))
    
    def zoom(self, start, end):
        ax = self.figure.gca()
        x_min, x_max = sorted([start[0], end[0]])
        y_min, y_max = sorted([start[1], end[1]])
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        self.canvas.draw()
    
    def reset_zoom(self):
        ax = self.figure.gca()
        ax.relim()
        ax.autoscale_view()
        self.canvas.draw()

class PCAWindow(QMainWindow):
    def __init__(self, pca_result, wells, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PCA Analysis")
        self.setGeometry(200, 200, 800, 600)
        
        # Store the data
        self.pca_result = pca_result
        self.wells = wells
        self.parent = parent
        
        # Initialize drawing variables and storage
        self.drawing = False
        self.draw_mode = False
        self.path = []
        self.drawn_line = None
        self.regions = []  # List of (path, color) tuples
        self.selected_wells = {}  # Dictionary of {color: set of wells}
        
        # Define colors
        self.colors = {
            'red': ('#FF0000', 1.0),
            'green': ('#00FF00', 2.0),
            'blue': ('#0000FF', 3.0)
        }
        self.current_color = 'red'
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Add toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        
        # Create button layout
        button_layout = QHBoxLayout()
        
        # Button for toggling draw mode
        self.draw_button = QPushButton("Toggle Draw Mode")
        self.draw_button.setCheckable(True)
        self.draw_button.clicked.connect(self.toggle_draw_mode)
        button_layout.addWidget(self.draw_button)
        
        # Color selection buttons
        color_group = QWidget()
        color_layout = QHBoxLayout(color_group)
        color_layout.addWidget(QLabel("Select Color:"))
        
        for color_name in self.colors:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background-color: {self.colors[color_name][0]}; border: none;")
            btn.clicked.connect(lambda checked, c=color_name: self.set_color(c))
            color_layout.addWidget(btn)
            
        button_layout.addWidget(color_group)
        
        # Clear button
        self.clear_button = QPushButton("Clear All Regions")
        self.clear_button.clicked.connect(self.clear_regions)
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)
        
        # Initialize the plot
        self.ax = self.figure.add_subplot(111)
        self.plot_pca()
        
        # Connect events
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)

    def closeEvent(self, event):
        # Reset well plate colors when window is closed
        if hasattr(self.parent, 'well_plate'):
            self.parent.well_plate.reset_colors()
        event.accept()
        
    def set_color(self, color):
        self.current_color = color
        
    def clear_regions(self):
        self.regions = []
        self.selected_wells = {}
        self.plot_pca()
        self.update_well_plate_colors()
        
    def plot_pca(self):
        self.ax.clear()
        self.ax.scatter(self.pca_result[:, 0], self.pca_result[:, 1], c='black', alpha=0.6)
        
        # Add well labels
        for i, well in enumerate(self.wells):
            self.ax.annotate(well, (self.pca_result[i, 0], self.pca_result[i, 1]), 
                            xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        # Draw existing regions
        for path_array, color in self.regions:
            polygon = PathPatch(Path(path_array), facecolor=self.colors[color][0], 
                              alpha=0.2, edgecolor=self.colors[color][0])
            self.ax.add_patch(polygon)
        
        self.ax.set_xlabel('PC1')
        self.ax.set_ylabel('PC2')
        self.ax.set_title('PCA Results')
        self.figure.tight_layout()
        self.canvas.draw()
        
    def toggle_draw_mode(self):
        self.draw_mode = self.draw_button.isChecked()
        if self.draw_mode:
            self.toolbar.setEnabled(False)
        else:
            self.toolbar.setEnabled(True)
            
    def on_mouse_press(self, event):
        if not self.draw_mode or event.inaxes != self.ax:
            return
        self.drawing = True
        self.path = [(event.xdata, event.ydata)]
        
    def on_mouse_move(self, event):
        if not self.drawing or not self.draw_mode or event.inaxes != self.ax:
            return
        self.path.append((event.xdata, event.ydata))
        
        # Remove previous line if it exists
        if self.drawn_line:
            self.drawn_line.pop(0).remove()
        
        # Draw the current path
        path_array = np.array(self.path)
        self.drawn_line = self.ax.plot(path_array[:, 0], path_array[:, 1], 
                                     c=self.colors[self.current_color][0])
        self.canvas.draw_idle()
        
    def on_mouse_release(self, event):
        if not self.drawing or not self.draw_mode:
            return
        self.drawing = False
        
        # Convert path to polygon
        path_array = np.array(self.path)
        if len(path_array) < 3:  # Need at least 3 points for a polygon
            return
            
        # Add the region to our list
        self.regions.append((path_array, self.current_color))
        
        # Update the plot with all regions
        self.plot_pca()
        
        # Update selected wells for this color
        polygon = Path(path_array)
        points = self.pca_result[:, :2]
        mask = polygon.contains_points(points)
        self.selected_wells[self.current_color] = set([self.wells[i] for i in range(len(self.wells)) if mask[i]])
        
        # Update well plate colors
        self.update_well_plate_colors()
            
    def update_well_plate_colors(self):
        # Create a dictionary mapping wells to colors
        well_colors = {}
        
        # Get all selected wells across all colors
        all_selected_wells = set()
        for color_wells in self.selected_wells.values():
            all_selected_wells.update(color_wells)
        
        # Assign colors to wells (most recent color takes precedence)
        for well in all_selected_wells:
            for color in reversed(list(self.colors.keys())):
                if color in self.selected_wells and well in self.selected_wells[color]:
                    well_colors[well] = self.colors[color][0]  # Use hex color string
                    break
                    
        # Update well plate with RGB colors (non-selected wells will be greyed out)
        self.parent.well_plate.update_rgb_colors(well_colors)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MassSpectrumAnalyzer()
    window.show()
    sys.exit(app.exec())