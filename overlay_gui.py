
import tkinter as tk
from ctypes import windll

class VisualOverlay(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Visual Guide (Align This)")
        self.attributes('-alpha', 0.5)
        self.attributes('-topmost', True)
        self.geometry("950x600")
        
        self.canvas = tk.Canvas(self, width=950, height=600, bg='white', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        
        # Configurations
        self.configs = {
            'FHD': {
                'spacing_x': 38,
                'row1_to_row2': 92,
                'row2_to_row3': 128,
                'last_slot_to_button': 95,
                'button_size': 30
            },
            'QHD': {
                'spacing_x': 50.5,
                'row1_to_row2': 123,
                'row2_to_row3': 171,
                'last_slot_to_button': 127,
                'button_size': 40
            }
        }
        
        self.current_res = 'FHD'
        
        # Tighter margins
        self.anchor_x = 30 
        self.anchor_y = 80 # Space for text above
        
        self.update_coords()
        self.update_window_size()
        self.draw_guides()
        
    def set_resolution(self, res):
        if res in self.configs:
            self.current_res = res
            self.update_coords()
            self.update_window_size()
            self.draw_guides()

    def update_window_size(self):
        cfg = self.configs[self.current_res]
        # Calculate required width/height
        # Width: anchor_x + (9 * spacing) + last_to_btn + btn_size + padding
        total_width = self.anchor_x + (9 * cfg['spacing_x']) + cfg['last_slot_to_button'] + cfg['button_size'] + 30
        # Height: anchor_y + row1_to_row2 + row2_to_row3 + padding
        total_height = self.anchor_y + cfg['row1_to_row2'] + cfg['row2_to_row3'] + 50
        
        self.geometry(f"{int(total_width)}x{int(total_height)}")
        self.canvas.config(width=int(total_width), height=int(total_height))

    def update_coords(self):
        cfg = self.configs[self.current_res]
        self.coords = {
            'row1_y': self.anchor_y,
            'row2_y': self.anchor_y + cfg['row1_to_row2'],
            'row3_y': self.anchor_y + cfg['row1_to_row2'] + cfg['row2_to_row3'],
            'start_x': self.anchor_x,
            'spacing_x': cfg['spacing_x'],
            'button_x': (self.anchor_x + 9 * cfg['spacing_x']) + cfg['last_slot_to_button']
        }

    def draw_guides(self):
        self.canvas.delete('guide')
        r = 6
        rows = [
            ('row1', self.coords['row1_y'], 'blue'),
            ('row2', self.coords['row2_y'], 'blue'),
            ('row3', self.coords['row3_y'], 'red')
        ]
        for name, y, color in rows:
            for i in range(10):
                x = self.coords['start_x'] + (i * self.coords['spacing_x'])
                self.canvas.create_oval(x-r, y-r, x+r, y+r, outline=color, width=2, tags='guide')
            bx = self.coords['button_x']
            self.canvas.create_rectangle(bx-15, y-15, bx+15, y+15, outline=color, width=3, tags='guide')
            
        # Removed "Visual Guide - Align with Game" text as requested
        
        # Win Probability Text
        # Win Probability Text
        self.prob_text_id = self.canvas.create_text(
            self.coords['start_x'], 
            self.coords['row1_y'] - 45, 
            text="Win Prob: Calculating...", 
            fill='purple', 
            font=('Arial', 12, 'bold'), 
            anchor='w',
            tags='guide'
        )
        
        # Current Success Probability Text - Moved to above the first row button
        self.current_prob_text_id = self.canvas.create_text(
            self.coords['button_x'], 
            self.coords['row1_y'] - 40, 
            text="Current Prob: 75%", 
            fill='blue', 
            font=('Arial', 12, 'bold'), 
            anchor='center',
            tags='guide'
        )

    def update_probability_text(self, text):
        self.canvas.itemconfig(self.prob_text_id, text=text)

    def update_current_prob_text(self, text):
        self.canvas.itemconfig(self.current_prob_text_id, text=text)

    def highlight_recommendation(self, row_names):
        self.canvas.delete('highlight')
        if not row_names:
            return
            
        # If single string, convert to list
        if isinstance(row_names, str):
            row_names = [row_names]
            
        # Map row name to y coord
        y_map = {
            'row1': self.coords['row1_y'],
            'row2': self.coords['row2_y'],
            'row3': self.coords['row3_y']
        }
        
        bx = self.coords['button_x']
        
        for row_name in row_names:
            if row_name in y_map:
                y = y_map[row_name]
                # Draw thick green box
                self.canvas.create_rectangle(bx-25, y-25, bx+25, y+25, outline='#00FF00', width=5, tags='highlight')

    def set_click_through(self, enable):
        """Set this window to be transparent to mouse clicks."""
        try:
            hwnd = windll.user32.GetParent(self.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x80000
            WS_EX_TRANSPARENT = 0x20
            
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            if enable:
                # Add Transparent flag
                new_style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED
            else:
                # Remove Transparent flag
                new_style = style & ~WS_EX_TRANSPARENT
            
            if style != new_style:
                windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
                # Force window update using SetWindowPos
                # SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED (0x27)
                windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x27)
                print(f"Click-through {'ENABLED' if enable else 'DISABLED'} (Style: {hex(new_style)})")
        except Exception as e:
            print(f"Error setting click-through: {e}")

    def get_geometry(self):
        return {
            'x': self.winfo_rootx(),
            'y': self.winfo_rooty(),
            'width': self.winfo_width(),
            'height': self.winfo_height()
        }
    
    def get_coords(self):
        return self.coords

class ControlPanel:
    def __init__(self, root, start_callback, stop_callback, test_vision_callback, test_click_callback, reset_callback, resolution_callback=None):
        self.root = root
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.test_vision_callback = test_vision_callback
        self.test_click_callback = test_click_callback
        self.reset_callback = reset_callback
        self.resolution_callback = resolution_callback
        
        self.is_running = False
        
        self.root.title("Control Panel")
        self.root.geometry("300x400")
        self.root.attributes('-topmost', True)
        
        # Status
        self.status_label = tk.Label(root, text="Stopped", font=('Arial', 12))
        self.status_label.pack(pady=10)
        
        # Start/Stop Button
        self.start_btn = tk.Button(root, text="START", bg='green', fg='white', font=('Arial', 12, 'bold'), command=self.toggle_start)
        self.start_btn.pack(fill='x', padx=20, pady=5)
        
        # Reset Button
        self.reset_btn = tk.Button(root, text="RESET", bg='orange', fg='black', font=('Arial', 10, 'bold'), command=self.reset)
        self.reset_btn.pack(fill='x', padx=20, pady=5)

        # Auto Reset Checkbox
        self.auto_reset_var = tk.BooleanVar(value=False)
        self.auto_reset_chk = tk.Checkbutton(root, text="Auto Reset", variable=self.auto_reset_var)
        self.auto_reset_chk.pack(pady=5)

        # Resolution Selection
        tk.Label(root, text="Resolution:").pack(pady=2)
        self.resolution_var = tk.StringVar(value="FHD")
        res_frame = tk.Frame(root)
        res_frame.pack(pady=5)
        
        tk.Radiobutton(res_frame, text="FHD (1080p)", variable=self.resolution_var, value="FHD", command=self.on_resolution_change).pack(side='left', padx=5)
        tk.Radiobutton(res_frame, text="QHD (1440p)", variable=self.resolution_var, value="QHD", command=self.on_resolution_change).pack(side='left', padx=5)
        
        # Test Buttons
        self.test_vision_btn = tk.Button(root, text="Test Vision", command=self.test_vision)
        self.test_vision_btn.pack(fill='x', padx=20, pady=5)
        
        self.test_click_btn = tk.Button(root, text="Test Click (Click-Through)", command=self.test_click)
        self.test_click_btn.pack(fill='x', padx=20, pady=5)
        
        # Instructions
        tk.Label(root, text="Press 'Q' to Stop").pack(pady=5)
        
        # Create Overlay Window
        self.overlay = VisualOverlay(root)

    def toggle_start(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(text="STOP", bg='red')
            self.status_label.config(text="Running - Overlay Click-Through ON")
            self.overlay.set_click_through(True)
            self.on_start()
        else:
            self.stop(from_logic=False)

    def stop(self, from_logic=True):
        self.is_running = False
        
        def _update_ui():
            self.start_btn.config(text="START", bg='green')
            self.status_label.config(text="Stopped")
            self.overlay.set_click_through(False)
            
        self.root.after(0, _update_ui)
        
        if not from_logic:
            self.on_stop()
            
    def reset(self):
        self.reset_callback()

    def on_resolution_change(self):
        res = self.resolution_var.get()
        self.overlay.set_resolution(res)
        if self.resolution_callback:
            self.resolution_callback(res)

    def on_start(self):
        self.start_callback()

    def on_stop(self):
        self.stop_callback()

    def test_vision(self):
        self.test_vision_callback()

    def test_click(self):
        self.test_click_callback()
        
    def get_overlay_geometry(self):
        return self.overlay.get_geometry()
    
    def get_overlay_coords(self):
        return self.overlay.get_coords()
    
    def set_overlay_click_through(self, enable):
        self.overlay.set_click_through(enable)

    def highlight_recommendation(self, row_name):
        self.root.after(0, lambda: self.overlay.highlight_recommendation(row_name))

    def update_probability_text(self, text):
        self.root.after(0, lambda: self.overlay.update_probability_text(text))

    def update_current_prob_text(self, text):
        self.root.after(0, lambda: self.overlay.update_current_prob_text(text))

if __name__ == "__main__":
    root = tk.Tk()
    # Hide root window if we want, but here root is the controller
    app = ControlPanel(root, lambda: print("Start"), lambda: print("Stop"), lambda: print("Vis"), lambda: print("Clk"), lambda: print("Reset"))
    root.mainloop()
