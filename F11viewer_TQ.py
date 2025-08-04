import sys
import os
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QVBoxLayout, 
                           QHBoxLayout, QWidget, QPushButton, QSizePolicy, 
                           QComboBox, QLabel, QGridLayout, QTableWidget, QTableWidgetItem,
                           QStackedWidget, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, rgb2hex
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.cm import ScalarMappable
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

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
        self.layout_combo.addItems(['96 Well Plate', '2x 44 Well Plates'])
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

        # self.normalized = False  # Track normalization state
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
        self.setup_96_well_plate()


        self.colormap = plt.get_cmap('viridis')
        
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
        else:
            self.setup_44_well_plates()

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
    
        # Initialize data structures
        self.data_format = None
        self.mrm_info = None
        self.data = {}
        self.original_data = {}
        self.current_well = None

        
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

 

        
    
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
    
        # Create WellPlate
        self.well_plate = WellPlate(analyzer=self)
        self.well_plate.well_clicked.connect(self.update_well_data)
        self.layout.addWidget(self.well_plate)
    
        # Create stacked widget to switch between spectrum plot and MRM table
        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)
    
        # Create spectrum plot widget
        self.spectrum_widget = QWidget()
        spectrum_layout = QVBoxLayout(self.spectrum_widget)
        
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.figure.patch.set_facecolor('#f0f0f0')
        self.canvas = FigureCanvas(self.figure)
        spectrum_layout.addWidget(self.canvas)
        
        self.toolbar = NavigationToolbar(self.canvas, self)
        spectrum_layout.addWidget(self.toolbar)
        
        self.stacked_widget.addWidget(self.spectrum_widget)
    
        # Create MRM table widget
        self.mrm_widget = QWidget()
        mrm_layout = QVBoxLayout(self.mrm_widget)
        
        self.mrm_table = QTableWidget()
        self.mrm_table.setColumnCount(3)  # MRM, Precursor/Product, Intensity
        self.mrm_table.setHorizontalHeaderLabels(['MRM', 'Precursor/Product', 'Intensity'])
        self.mrm_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # Connect table clicks after creating the table
        self.mrm_table.itemClicked.connect(self.on_table_click)
        
        mrm_layout.addWidget(self.mrm_table)
        
        self.stacked_widget.addWidget(self.mrm_widget)
    
        # Create button layout
        button_layout = QHBoxLayout()
        
       # self.select_folder_button = QPushButton("Load Spectrum Data (Folder)")
       # self.select_folder_button.clicked.connect(self.load_spectrum_folder)
       # button_layout.addWidget(self.select_folder_button)
    
        self.select_mrm_button = QPushButton("Load MRM Data (Text File)")
        self.select_mrm_button.clicked.connect(self.load_mrm_file)
        button_layout.addWidget(self.select_mrm_button)
    
        #self.average_spectrum_button = QPushButton("Show Average")
        #self.average_spectrum_button.clicked.connect(self.show_average_data)
       # button_layout.addWidget(self.average_spectrum_button)
    
        self.export_csv_button = QPushButton("Export to CSV")
        self.export_csv_button.clicked.connect(self.export_to_csv)
        button_layout.addWidget(self.export_csv_button)
    
        self.pca_button = QPushButton("Perform PCA")
        self.pca_button.clicked.connect(self.perform_pca)
        button_layout.addWidget(self.pca_button)
    
        self.layout.addLayout(button_layout)
    
        # Initialize other attributes
        self.average_spectrum = None
        self.current_spectrum = None
        self.span = None
        self.last_selected_range = None

        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)




    def on_table_click(self, item):
        """Handle clicks on the MRM table"""
        # Calculate which MRM was clicked based on the column group
        col = item.column()
        row = item.row()
        col_group = col // 3
        mrm_index = row * 2 + col_group  # 2 is the number of columns
        
        if mrm_index >= len(self.mrm_info):
            return
            
        # If no well is selected, use the first well
        if not self.current_well and self.data:
            self.current_well = sorted(self.data.keys())[0]
            
        print(f"Table clicked: MRM {mrm_index + 1}, current well: {self.current_well}")
        
        # Store last clicked MRM for highlighting
        self.last_clicked_mrm = mrm_index
        
        # Get all intensities for highlighting
        values = []
        for well in sorted(self.data.keys()):
            well_data = self.data[well]
            values.append(well_data.iloc[mrm_index]['intensity'])
        
        # Update well plate heatmap with just this MRM's values
        self.well_plate.update_heatmap(values)
        
        # Update the bar chart with highlighted MRM
        self.update_bar_chart(self.current_well, highlight_mrm=mrm_index)
        
        # Highlight the selected MRM in the table
        self.highlight_mrm(mrm_index)


    def highlight_mrm(self, mrm_index):
        """Highlight the selected MRM in the table"""
        # Reset all cell backgrounds
        for row in range(self.mrm_table.rowCount()):
            for col in range(self.mrm_table.columnCount()):
                item = self.mrm_table.item(row, col)
                if item:
                    item.setBackground(QColor('#ffffff'))
        
        # Highlight the selected MRM
        row = mrm_index // 2  # 2 is the number of columns
        col_group = mrm_index % 2
        base_col = col_group * 3
        
        # Highlight all cells in the MRM's group
        for col in range(3):  # 3 cells per MRM
            item = self.mrm_table.item(row, base_col + col)
            if item:
                item.setBackground(QColor('#f0f0f0'))

    
    def update_well_data(self, well):
        """Update display for selected well"""
        if not self.data or well not in self.data:
            return
    
        # Store current well
        self.current_well = well
        
        if self.data_format == 'mrm':
            self.stacked_widget.setCurrentIndex(1)  # Show MRM table
            self.update_mrm_table(well)
        else:
            self.stacked_widget.setCurrentIndex(0)  # Show spectrum plot
            self.update_well_spectrum(well)

    
    def update_mrm_table(self, well):
        """Update MRM table with data for selected well"""
        if not self.mrm_info or not self.data or well not in self.data:
            print(f"Cannot update table: mrm_info={bool(self.mrm_info)}, data={bool(self.data)}, well={well}")
            return
    
        well_data = self.data[well]
        num_mrms = len(self.mrm_info)
        
        # Calculate optimal layout (2 columns)
        num_columns = 4 # Change this to change the layout of the table
        num_rows = (num_mrms + num_columns - 1) // num_columns  # Ceiling division
        
        # Set up table
        self.mrm_table.setRowCount(num_rows)
        self.mrm_table.setColumnCount(num_columns * 3)  # 3 columns per MRM section
        
        # Create headers for each section
        headers = []
        for col in range(num_columns):
            headers.extend(['MRM', 'Precursor/Product', 'Intensity'])
        self.mrm_table.setHorizontalHeaderLabels(headers)
    
        # Fill table
        for i in range(num_mrms):
            row = i // num_columns
            col_group = i % num_columns
            base_col = col_group * 3
            
            # Get data
            mrm_num = f"MRM {i+1}"
            precursor_product = well_data.iloc[i]['precursor_product']
            intensity = well_data.iloc[i]['intensity']
            
            # Create read-only items
            mrm_item = QTableWidgetItem(mrm_num)
            mrm_item.setFlags(mrm_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Remove editable flag
            
            pp_item = QTableWidgetItem(str(precursor_product))
            pp_item.setFlags(pp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            intensity_item = QTableWidgetItem(f"{intensity:.2f}")
            intensity_item.setFlags(intensity_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Add to table
            self.mrm_table.setItem(row, base_col, mrm_item)
            self.mrm_table.setItem(row, base_col + 1, pp_item)
            self.mrm_table.setItem(row, base_col + 2, intensity_item)
    
        # Adjust column widths and row heights
        for col in range(self.mrm_table.columnCount()):
            self.mrm_table.resizeColumnToContents(col)
        for row in range(self.mrm_table.rowCount()):
            self.mrm_table.resizeRowToContents(row)
            
        # Style improvements
        self.mrm_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                border: 1px solid #d0d0d0;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)
        
        # Update highlighting based on last clicked MRM (if any)
        if hasattr(self, 'last_clicked_mrm'):
            self.highlight_mrm(self.last_clicked_mrm)


    def update_bar_chart(self, well, highlight_mrm=None):
        """Update bar chart for selected well with optional MRM highlighting"""
        if not self.data or well not in self.data:
            print("Cannot update bar chart: missing data")
            return
    
        well_data = self.data[well]
        print(f"\nUpdating bar chart for well {well} with data:\n{well_data}")
    
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')
        
        # Create bar chart
        x = range(len(well_data))
        intensities = well_data['intensity'].values
        bars = ax.bar(x, intensities)
        
        # If we have a highlighted MRM, color it differently
        if highlight_mrm is not None and 0 <= highlight_mrm < len(bars):
            # Set all bars to a lighter color
            for bar in bars:
                bar.set_facecolor('#CCCCCC')  # Light gray
            # Highlight the selected MRM
            bars[highlight_mrm].set_facecolor('#FF6B6B')  # Highlight color
        
        # Set labels
        ax.set_xticks(x)
        ax.set_xticklabels([f"MRM {i+1}" for i in range(len(well_data))], rotation=45, ha='right')
        ax.set_ylabel('Intensity')
        ax.set_title(f'MRM Intensities for Well {well}')
        
        # Adjust layout
        self.figure.subplots_adjust(bottom=0.2)
        self.canvas.draw()
    

    def update_heatmap_for_well(self, well):
        """Update the heatmap when a well is selected"""
        if not self.data or well not in self.data:
            return
    
        well_data = self.data[well]
        values = well_data['intensity'].values.tolist()
        
        # If we have mrm_info, use it to update the heatmap with proper labels
        if self.mrm_info:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_facecolor('white')
            
            # Create bar chart
            x = range(len(values))
            ax.bar(x, values)
            
            # Set labels
            ax.set_xticks(x)
            ax.set_xticklabels([f"MRM {i+1}" for i in x], rotation=45, ha='right')
            ax.set_ylabel('Intensity')
            ax.set_title(f'MRM Intensities for Well {well}')
            
            # Adjust layout with more space for labels
            self.figure.subplots_adjust(bottom=0.2)  # Add more space at bottom
            self.canvas.draw()



        
      

    def show_average_data(self):
        """Show average spectrum or MRM data"""
        if self.data_format == 'mrm':
            self.show_average_mrm()
        else:
            self.plot_average_spectrum()

    def show_average_mrm(self):
        """Show average MRM data in table and update bar chart"""
        if not self.data or not self.mrm_info:
            return
    
        # Calculate average intensities across all wells
        all_intensities = []
        for well_data in self.data.values():
            all_intensities.append(well_data['intensity'].values)
        
        average_intensities = np.mean(all_intensities, axis=0)
        
        # Update table
        self.mrm_table.setRowCount(len(self.mrm_info))
        
        for i, mrm in enumerate(self.mrm_info):
            mrm_num = f"MRM {i+1}"
            precursor_product = mrm.split(': ')[1]
            intensity = average_intensities[i]
    
            self.mrm_table.setItem(i, 0, QTableWidgetItem(mrm_num))
            self.mrm_table.setItem(i, 1, QTableWidgetItem(precursor_product))
            self.mrm_table.setItem(i, 2, QTableWidgetItem(f"{intensity:.2f}"))
    
        self.mrm_table.resizeColumnsToContents()
        
        # Update bar chart with averages
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')
        
        x = range(len(self.mrm_info))
        ax.bar(x, average_intensities)
        
        ax.set_xticks(x)
        ax.set_xticklabels([f"MRM {i+1}" for i in x], rotation=45, ha='right')
        ax.set_ylabel('Average Intensity')
        ax.set_title('Average MRM Intensities Across All Wells')
        
        # Adjust layout with more space for labels
        self.figure.subplots_adjust(bottom=0.2)  # Add more space at bottom
        self.canvas.draw()
        
        self.stacked_widget.setCurrentIndex(1)  # Show MRM table


    

    def select_folder(self):
        # First try to select a folder for spectrum data
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            # Check if folder contains CSV files
            csv_files = [f for f in os.listdir(folder) if f.endswith(('.csv', '.CSV'))]
            if csv_files:
                self.data_format = 'spectrum'
                self.load_spectrum_data(folder)
                self.plot_average_spectrum()
            else:
                # If no CSV files, prompt for MRM text file
                file_name, _ = QFileDialog.getOpenFileName(self, 
                    "Select MRM Data File", folder, "Text Files (*.txt);;All Files (*)")
                if file_name:
                    self.data_format = 'mrm'
                    self.load_mrm_data(file_name)

    #def load_spectrum_folder(self):
      #  """Handle loading of spectrum data from folder of CSVs"""
       # folder = QFileDialog.getExistingDirectory(self, "Select Folder with Spectrum CSV Files")
      #  if folder:
       #     csv_files = [f for f in os.listdir(folder) if f.endswith(('.csv', '.CSV'))]
         #   if csv_files:
         #       self.data_format = 'spectrum'
         #       self.load_spectrum_data(folder)
         #       self.plot_average_spectrum()
          #  else:
          #      QMessageBox.warning(self, "No Data Found", 
           #        "No CSV files found in selected folder.")



    def load_mrm_file(self):
        """Handle loading of MRM data from text file"""
        file_name, _ = QFileDialog.getOpenFileName(self, 
            "Select MRM Data File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            # Get the directory and look for selected_wells.txt
            directory = os.path.dirname(file_name)
            wells_file = os.path.join(os.path.dirname(directory), "selected_wells.txt")
            
            if not os.path.exists(wells_file):
                QMessageBox.warning(self, "Missing File", 
                    "Could not find selected_wells.txt in the same folder.")
                return
                
            # Load the well mapping
            well_mapping = self.load_well_mapping(wells_file)
            
            self.data_format = 'mrm'
            self.load_mrm_data(file_name, well_mapping)
            
            # Show MRM data right away
            # Skip average spectrum calculation for now as we don't need it for MRM view
            self.stacked_widget.setCurrentIndex(1)  # Show MRM table/chart
            if self.data:
                # Show first well's data
                first_well = list(self.data.keys())[0]
                self.update_mrm_table(first_well)

    def load_well_mapping(self, wells_file):
        """Load the mapping between numerical indices and well positions"""
        well_mapping = {}
        try:
            with open(wells_file, 'r') as f:
                lines = f.readlines()
                # Skip the header line "Selected Wells:"
                well_list = [line.strip() for line in lines[1:] if line.strip()]
                # Create mapping from index to well position
                for idx, well in enumerate(well_list):
                    well_mapping[idx] = well
            return well_mapping
        except Exception as e:
            print(f"Error loading well mapping: {str(e)}")
            return None




        
    
    def load_mrm_data(self, file_path, well_mapping):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
    
            # Get number of MRM functions from the third line (line index 2)
            # Split by whitespace and get the non-empty values starting from column 4
            mrm_line = [x for x in lines[2].split() if x.strip()]
            mrm_count = len(mrm_line)
            print(f"Number of MRM functions found: {mrm_count}")
            
            # Get Precursor and Product ion masses (using whitespace splitting)
            precursor_masses = [float(x) for x in lines[3].split() if x.strip()][-mrm_count:]
            product_masses = [float(x) for x in lines[4].split() if x.strip()][-mrm_count:]
            
            print(f"Precursor masses: {precursor_masses}")
            print(f"Product masses: {product_masses}")
            
            # Create MRM labels
            self.mrm_info = [f'MRM {i+1}: {precursor_masses[i]}/{product_masses[i]}' 
                           for i in range(mrm_count)]
            print(f"MRM info created: {self.mrm_info}")
    
            # Process data rows
            data_rows = []
            for line in lines[5:]:
                parts = [x for x in line.split() if x.strip()]
                if len(parts) >= 7:  # We expect at least 7 columns
                    try:
                        well_num = int(float(parts[2]))  # Well number is in column 3
                        # Get the MRM values (should be 4 values)
                        intensities = [float(parts[i]) for i in range(3, 3 + mrm_count)]
                        row_data = {'well': well_num}
                        for i, intensity in enumerate(intensities):
                            row_data[f'MRM_{i+1}'] = intensity
                        data_rows.append(row_data)
                    except (ValueError, IndexError) as e:
                        print(f"Error processing line: {line.strip()}")
                        print(f"Error: {str(e)}")
                        continue
    
            # Convert to DataFrame and group by well
            raw_data = pd.DataFrame(data_rows)
            grouped_data = raw_data.groupby('well').sum().reset_index()
            print(f"Grouped data example:\n{grouped_data.head()}")
    
            # Convert to format compatible with existing code
            self.data = {}
            for _, row in grouped_data.iterrows():
                well_num = int(row['well'])
                if well_num in well_mapping:
                    well = well_mapping[well_num]  # Use the actual well position from mapping
                    
                    # Create DataFrame with all MRM data
                    intensities = [row[f'MRM_{i+1}'] for i in range(mrm_count)]
                    
                    mrm_data = pd.DataFrame({
                        'mrm_number': range(1, mrm_count + 1),
                        'precursor_product': [f"{precursor_masses[i]}/{product_masses[i]}" for i in range(mrm_count)],
                        'intensity': intensities
                    })
                    
                    print(f"\nWell {well} data:\n{mrm_data}")
                    
                    self.data[well] = mrm_data
                    self.original_data[well] = mrm_data.copy()
    
            active_wells = list(self.data.keys())
            print(f"Active wells: {active_wells}")
            self.well_plate.set_active_wells(active_wells)
            
            # Set and display first well's data automatically
            if active_wells:
                self.current_well = active_wells[0]  # Set current well
                self.update_mrm_table(self.current_well)

        except Exception as e:
            print(f"Error loading MRM file: {str(e)}")
            import traceback
            traceback.print_exc()
        

        
  #  def _create_average_spectrum(self):
     #   if not self.data:
      #      return
    
       # if self.data_format == 'mrm':
      #      # For MRM data, create averages from intensities
       #     intensities = []
       #     for df in self.data.values():
        #        intensities.append(df['intensity'].values)
            
      #      average_intensities = np.mean(intensities, axis=0)
      #      # For MRM data, we'll just use MRM numbers as index
      #      self.average_spectrum = pd.Series(
      #          data=average_intensities,
       #         index=range(len(self.mrm_info))
        #    )
       # else:
       #     # Original spectrum averaging code
        #    min_mz = min(df['mass_to_charge'].min() for df in self.data.values())
        #    max_mz = max(df['mass_to_charge'].max() for df in self.data.values())
        #    step = 0.01
        #    common_mz = np.arange(min_mz, max_mz + step, step)
            
        #    aligned_intensities = []
         #   for df in self.data.values():
         #       interpolated = np.interp(
         #           common_mz,
         #           df['mass_to_charge'],
         #           df['intensity'],
        #            left=0,
        #            right=0
        #        )
        #        aligned_intensities.append(interpolated)
            
        #    average_intensities = np.mean(aligned_intensities, axis=0)
        #    self.average_spectrum = pd.Series(
        #        data=average_intensities,
       #         index=common_mz
        #    )
        

    def plot_average_spectrum(self):
        if not hasattr(self, 'average_spectrum'):
            return
            
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')

        if self.data_format == 'mrm':
            # For MRM data, create bar plot
            ax.bar(range(len(self.mrm_info)), self.average_spectrum.values)
            ax.set_xticks(range(len(self.mrm_info)))
            ax.set_xticklabels(self.mrm_info, rotation=45, ha='right')
            ax.set_title('Average MRM Intensities')
        else:
            # Original spectrum plot
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
        ax.set_facecolor('white')
        
        spectrum = self.data[well]
        
        if self.data_format == 'mrm':
            # For MRM data, create bar plot
            ax.bar(range(len(self.mrm_info)), spectrum['intensity'])
            ax.set_xticks(range(len(self.mrm_info)))
            ax.set_xticklabels(self.mrm_info, rotation=45, ha='right')
            ax.set_title(f'MRM Intensities for Well {well}')
        else:
            # Original spectrum plot
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
        """Export MRM data to CSV"""
        if not self.data:
            return
    
        file_name, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if file_name:
            # Create a list to hold all data rows
            export_data = []
            
            # Go through each well
            for well in sorted(self.data.keys()):  # Sort wells for consistent order
                data_row = {'Well': well}
                
                # Add data for each MRM
                well_data = self.data[well]
                for i, (intensity, mrm_info) in enumerate(zip(well_data['intensity'], well_data['precursor_product'])):
                    # Add both the intensity and the precursor/product info
                    data_row[f'MRM_{i+1}_Intensity'] = intensity
                    data_row[f'MRM_{i+1}_Mass'] = mrm_info
                
                export_data.append(data_row)
            
            # Convert to DataFrame and save
            df = pd.DataFrame(export_data)
            df.to_csv(file_name, index=False)
            print(f"Data exported to {file_name}")
    

    # Update the perform_pca method in MassSpectrumAnalyzer to pass self as parent
    def perform_pca(self):
        if not self.data:
            return
        
        # Prepare data for PCA - each well is a row, each MRM is a column
        X = []
        wells = []
        for well in sorted(self.data.keys()):  # Sort wells to maintain consistent order
            intensities = self.data[well]['intensity'].values
            X.append(intensities)
            wells.append(well)
    
        X = np.array(X)
        print(f"PCA input data shape: {X.shape}")  # Debug print
    
        # Standardize the data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
    
        # Perform PCA
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(X_scaled)
        
        # Print explained variance ratio for insight
        print(f"Explained variance ratio: {pca.explained_variance_ratio_}")
    
        # Create and show PCA window
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
        
        # Get all selected wells across all colorssum_n
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