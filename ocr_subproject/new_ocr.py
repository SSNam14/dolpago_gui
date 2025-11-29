import cv2
import numpy as np
import sys
import os
from pathlib import Path

class NewOcrEngine:
    def __init__(self, base_dir='ocr_subproject'):
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_path = Path(sys._MEIPASS)
            self.base_dir = base_path / base_dir
        else:
            # Running as script
            self.base_dir = Path(base_dir)
            
        self.templates = {'FHD': [], 'QHD': []}
        
        # Hyperparameters per Resolution
        self.params = {
            'FHD': {
                'target_size': (20, 20), 
                'thresh_block': 9,  # Tuned (100% Acc)
                'thresh_c': 2,      # Tuned
                'n_pixel_thresh': 50,
                'match_thresh': 0.4
            },
            'QHD': {
                'target_size': (20, 25), 
                'thresh_block': 15, # Tuned (87.3% Acc)
                'thresh_c': 3,      # Tuned
                'n_pixel_thresh': 80,
                'match_thresh': 0.4
            }
        }
        
        self.load_templates()
        
    def load_templates(self):
        for resolution in ['FHD', 'QHD']:
            res_path = self.base_dir / resolution
            if not res_path.exists():
                continue
            
            p = self.params[resolution]
            
            # Load "best" templates defined by filename: {label}_best.png
            for label in ['2', '3', '4', '5', '6', '7']:
                best_img_path = res_path / f"{label}_best.png"
                
                if not best_img_path.exists():
                    print(f"Warning: Best template not found for {resolution}/{label}")
                    continue
                    
                img = cv2.imread(str(best_img_path), cv2.IMREAD_GRAYSCALE)
                if img is None: continue
                
                # Use Template AS IS (User manually cropped)
                # Just threshold it
                thresh = self.apply_threshold(img, p)
                
                # CROP 1px from all sides (User Request)
                # This allows the template to "slide" more within the input image
                h, w = thresh.shape
                if h > 2 and w > 2:
                    cropped = thresh[1:h-1, 1:w-1]
                else:
                    cropped = thresh
                
                self.templates[resolution].append((label, cropped))
            
            print(f"Loaded {len(self.templates[resolution])} best templates for {resolution}")

    def apply_threshold(self, img, params):
        return cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, params['thresh_block'], params['thresh_c']
        )

    def preprocess_input(self, image, resolution):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        p = self.params[resolution]
            
        # 1. No Resize (As requested)
        # resized = cv2.resize(gray, p['target_size'], interpolation=cv2.INTER_AREA)
        
        # 2. Threshold
        thresh = self.apply_threshold(gray, p)
        
        return thresh

    def predict(self, image, resolution='FHD'):
        if resolution not in self.templates:
            return None, 0.0
            
        p = self.params[resolution]
        processed_input = self.preprocess_input(image, resolution)
        
        # 1. Fast N Check (Pixel Count)
        non_zero = cv2.countNonZero(processed_input)
        if non_zero < p['n_pixel_thresh']:
            return 'N', 1.0
        
        best_label = 'N'
        best_score = 0.0
        
        # 2. Sliding Window Matching
        for label, template in self.templates[resolution]:
            res = cv2.matchTemplate(processed_input, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            if max_val > best_score:
                best_score = max_val
                best_label = label
                
        if best_score < p['match_thresh']:
            return 'N', best_score
            
        return best_label, best_score
