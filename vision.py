import mss
import numpy as np
from PIL import Image
import pyautogui
import cv2

class Vision:
    def __init__(self, coords):
        self.coords = coords
        self.row_y_offsets = {
            'row1': self.coords['row1_y'],
            'row2': self.coords['row2_y'],
            'row3': self.coords['row3_y']
        }
        
    def update_coords(self, coords):
        self.coords = coords
        self.row_y_offsets = {
            'row1': self.coords['row1_y'],
            'row2': self.coords['row2_y'],
            'row3': self.coords['row3_y']
        }
        
    def capture_region(self, region):
        with mss.mss() as sct:
            screenshot = sct.grab(region)
            return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    def get_pixel_color(self, image, x, y):
        if 0 <= x < image.width and 0 <= y < image.height:
            return image.getpixel((x, y))
        return (0, 0, 0)

    def analyze_state(self, region_info, debug=False):
        monitor = {
            'top': region_info['y'],
            'left': region_info['x'],
            'width': region_info['width'],
            'height': region_info['height']
        }
        img = self.capture_region(monitor)
        
        row_states = {
            'row1': [],
            'row2': [],
            'row3': []
        }
        
        debug_info = {
            'row1': [],
            'row2': [],
            'row3': []
        }
        
        for row_name, y_offset in self.row_y_offsets.items():
            for i in range(10):
                x_offset = self.coords['start_x'] + (i * self.coords['spacing_x'])
                
                # Sample a 5x5 area
                colors = []
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        colors.append(self.get_pixel_color(img, x_offset + dx, y_offset + dy))
                
                avg_r = int(sum(c[0] for c in colors) / len(colors))
                avg_g = int(sum(c[1] for c in colors) / len(colors))
                avg_b = int(sum(c[2] for c in colors) / len(colors))
                
                state = self.classify_slot((avg_r, avg_g, avg_b), row_name)
                row_states[row_name].append(state)
                debug_info[row_name].append(f"[{avg_r}/{avg_g}/{avg_b}]")
                
        if debug:
            return row_states, debug_info
        return row_states

    def classify_slot(self, color, row_name):
        r, g, b = color
        brightness = (r + g + b) / 3
        
        # Calibration based on user data:
        # Empty: ~130 (due to overlay)
        # Fail: ~160
        # Threshold: 145
        
        if brightness < 145:
            return -1 # Empty
            
        # Success/Fail Check for non-empty slots
        if row_name in ['row1', 'row2']:
            # Blue Dominant
            # If Blue is significantly higher than Red
            if b > r + 20: 
                return 1 # Success
            else:
                return 0 # Fail (Gray)
                
        elif row_name == 'row3':
            # Red Dominant
            if r > b + 20:
                return 1 # Success
            else:
                return 0 # Fail
        
        return 0

    def click_button(self, row_name, region_info):
        y_offset = self.row_y_offsets[row_name]
        target_x = region_info['x'] + self.coords['button_x']
        target_y = region_info['y'] + y_offset
        pyautogui.click(target_x, target_y)

    def capture_ocr_area(self, region_info, ocr_coords, filename):
        monitor = {
            'top': region_info['y'] + ocr_coords['y1'],
            'left': region_info['x'] + ocr_coords['x1'],
            'width': ocr_coords['x2'] - ocr_coords['x1'],
            'height': ocr_coords['y2'] - ocr_coords['y1']
        }
        
        with mss.mss() as sct:
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img.save(filename)

    def get_ocr_image(self, region_info, ocr_coords):
        monitor = {
            'top': region_info['y'] + ocr_coords['y1'],
            'left': region_info['x'] + ocr_coords['x1'],
            'width': ocr_coords['x2'] - ocr_coords['x1'],
            'height': ocr_coords['y2'] - ocr_coords['y1']
        }
        
        with mss.mss() as sct:
            screenshot = sct.grab(monitor)
            # Convert to numpy array (BGRA -> BGR)
            img_np = np.array(screenshot)
            return cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
