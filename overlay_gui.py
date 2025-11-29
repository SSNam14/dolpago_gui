import tkinter as tk
from ctypes import windll

class VisualOverlay(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Visual Guide (Align This)")
        self.attributes('-alpha', 0.5)
        self.attributes('-topmost', True)
        
        # Initial geometry will be set by update_window_size
        self.geometry("600x400") 
        
        self.canvas = tk.Canvas(self, width=600, height=400, bg='white', highlightthickness=0)
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
        self.scale_factor = 1.0 # Default Scale
        
        # Tighter margins
        self.anchor_x = 30 
        self.anchor_y = 120 # Increased from 80 to 120 to fit QHD OCR box (row1_y - 92)
        
        self.update_coords()
        self.update_window_size()
        self.draw_guides()
        
    def set_resolution(self, res):
        if res in self.configs:
            self.current_res = res
            self.update_coords()
            self.update_window_size()
            self.draw_guides()

    def set_scale(self, factor):
        self.scale_factor = factor
        self.update_coords()
        self.update_window_size()
        self.draw_guides()

    def update_window_size(self):
        cfg = self.configs[self.current_res]
        # Calculate required width/height
        # Width: anchor_x + (9 * spacing) + last_to_btn + btn_size + padding
        # Width: anchor_x + (9 * spacing) + last_to_btn + btn_size + padding
        # Apply scaling to intervals
        s_spacing = cfg['spacing_x'] * self.scale_factor
        s_last = cfg['last_slot_to_button'] * self.scale_factor
        s_btn = cfg['button_size'] * self.scale_factor
        
        total_width = self.anchor_x + (9 * s_spacing) + s_last + s_btn + 30
        # Height: anchor_y + row1_to_row2 + row2_to_row3 + padding
        s_r1r2 = cfg['row1_to_row2'] * self.scale_factor
        s_r2r3 = cfg['row2_to_row3'] * self.scale_factor
        
        total_height = self.anchor_y + s_r1r2 + s_r2r3 + 50
        
        self.geometry(f"{int(total_width)}x{int(total_height)}")
        self.canvas.config(width=int(total_width), height=int(total_height))

    def update_coords(self):
        cfg = self.configs[self.current_res]
        sf = self.scale_factor
        
        # Apply scaling to vertical offsets
        r1r2 = cfg['row1_to_row2'] * sf
        r2r3 = cfg['row2_to_row3'] * sf
        
        self.coords = {
            'row1_y': int(self.anchor_y),
            'row2_y': int(self.anchor_y + r1r2),
            'row3_y': int(self.anchor_y + r1r2 + r2r3),
            'start_x': int(self.anchor_x),
            'spacing_x': cfg['spacing_x'] * sf, 
            'button_x': int((self.anchor_x + 9 * (cfg['spacing_x'] * sf)) + (cfg['last_slot_to_button'] * sf)),
        }
        
        # Add OCR Box coords (Centered on button, 50-70px above row1)
        # User requested: "Size is 100% maintained, position changes accordingly"
        # So we scale the Position Offsets, but keep Width/Height fixed.
        
        if self.current_res == 'QHD':
            # QHD Fixed Sizes (100% Scale)
            w = 16
            h = 24
            # Base Offsets (at scale 1.0)
            off_x = 10
            off_y = -92
        else:
            # FHD Fixed Sizes (100% Scale)
            w = 14
            h = 18
            # Base Offsets (at scale 1.0)
            off_x = 5
            off_y = -68
            
        # Apply Scale to Position Offsets
        s_off_x = off_x * sf
        s_off_y = off_y * sf
        
        self.coords['prob_ocr_box'] = {
            'x1': int(self.coords['button_x'] + s_off_x),
            'y1': int(self.coords['row1_y'] + s_off_y),
            'x2': int(self.coords['button_x'] + s_off_x + w), # Fixed Width
            'y2': int(self.coords['row1_y'] + s_off_y + h)  # Fixed Height
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
            
        # Draw OCR Box
        ocr = self.coords['prob_ocr_box']
        self.canvas.create_rectangle(ocr['x1'], ocr['y1'], ocr['x2'], ocr['y2'], 
                                   outline='orange', width=2, tags=('guide', 'ocr_box'))
        # Win Probability Text
        # Aligned with OCR text (Y) and First Slot (X)
        ocr_center_y = (ocr['y1'] + ocr['y2']) / 2
        self.prob_text_id = self.canvas.create_text(
            self.coords['start_x'], 
            ocr_center_y, 
            text="Target Prob: Calculating...", 
            fill='purple', 
            font=('Arial', 12, 'bold'), 
            anchor='w',
            tags='guide'
        )

        # OCR Result Text (Left of OCR Box)
        # User requested: FHD 67px left, QHD 100px left
        # We scale this offset too so it maintains relative distance
        base_text_offset = 100 if self.current_res == 'QHD' else 67
        text_offset = base_text_offset * self.scale_factor
        
        self.ocr_text_id = self.canvas.create_text(
            ocr['x1'] - text_offset, 
            (ocr['y1'] + ocr['y2']) / 2, 
            text="", 
            fill='darkblue', 
            font=('Arial', 14, 'bold'), 
            anchor='e',
            tags='guide'
        )

    def set_ocr_box_visibility(self, visible):
        state = 'normal' if visible else 'hidden'
        self.canvas.itemconfigure('ocr_box', state=state)
        self.update() # Force update to ensure it's drawn/hidden before capture

    def update_probability_text(self, text):
        self.canvas.itemconfig(self.prob_text_id, text=text)

    def update_ocr_text(self, text):
        self.canvas.itemconfig(self.ocr_text_id, text=text)

    # update_current_prob_text removed as requested

    def highlight_recommendation(self, row_names, color='#00FF00'):
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
                # Draw thick box with specified color
                self.canvas.create_rectangle(bx-25, y-25, bx+25, y+25, outline=color, width=5, tags='highlight')

    def update_debug_circles(self, row_states):
        self.canvas.delete('debug_circle')
        
        r = 8 # Slightly larger than the guide circle (r=6)
        
        # Colors
        colors = {
            'row1': 'blue',
            'row2': 'blue',
            'row3': 'red'
        }
        
        for row_name, states in row_states.items():
            if row_name not in self.coords:
                # Construct y coord from coords dict if not directly available (it is available as row1_y etc)
                pass
            
            y = self.coords[f"{row_name}_y"]
            color = colors.get(row_name, 'black')
            
            for i, state in enumerate(states):
                x = self.coords['start_x'] + (i * self.coords['spacing_x'])
                
                if state == 1: # Success
                    # Draw thick circle
                    self.canvas.create_oval(x-r, y-r, x+r, y+r, outline=color, width=4, tags='debug_circle')
                elif state == 0: # Fail
                    # Draw thin gray circle (optional, but good for feedback)
                    self.canvas.create_oval(x-r, y-r, x+r, y+r, outline='gray', width=2, tags='debug_circle')

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
    def __init__(self, root, start_callback, stop_callback, test_vision_callback, test_click_callback, reset_callback, resolution_callback=None, goal_callback=None, penalty_callback=None, scale_callback=None):
        self.root = root
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.test_vision_callback = test_vision_callback
        self.test_click_callback = test_click_callback
        self.reset_callback = reset_callback
        self.resolution_callback = resolution_callback
        self.goal_callback = goal_callback
        self.penalty_callback = penalty_callback
        self.scale_callback = scale_callback
        
        self.is_running = False
        
        self.root.title("Control Panel")
        self.root.geometry("300x450") # Increased height for scale control
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
        self.auto_reset_var = tk.BooleanVar(value=True)
        self.auto_reset_chk = tk.Checkbutton(root, text="Auto Reset", variable=self.auto_reset_var)
        self.auto_reset_chk.pack(pady=2)

        # Goal Selection
        tk.Label(root, text="Target Goal:").pack(pady=2)
        self.goal_var = tk.StringVar(value="97")
        goal_frame = tk.Frame(root)
        goal_frame.pack(pady=2)
        self.rb_97 = tk.Radiobutton(goal_frame, text="9/7 or 7/9", variable=self.goal_var, value="97", command=self.on_goal_change)
        self.rb_97.pack(anchor='w')
        self.rb_96 = tk.Radiobutton(goal_frame, text="9/6 or 6/9", variable=self.goal_var, value="96", command=self.on_goal_change)
        self.rb_96.pack(anchor='w')

        # Penalty Limit
        self.penalty_var = tk.BooleanVar(value=False)
        self.penalty_chk = tk.Checkbutton(root, text="Allow Penalty 5+", variable=self.penalty_var, command=self.on_penalty_change)
        self.penalty_chk.pack(pady=5)

        # Resolution Selection
        tk.Label(root, text="Resolution:").pack(pady=2)
        self.resolution_var = tk.StringVar(value="FHD")
        res_frame = tk.Frame(root)
        res_frame.pack(pady=5)
        
        self.rb_fhd = tk.Radiobutton(res_frame, text="FHD (1080p)", variable=self.resolution_var, value="FHD", command=self.on_resolution_change)
        self.rb_fhd.pack(side='left', padx=5)
        self.rb_qhd = tk.Radiobutton(res_frame, text="QHD (1440p)", variable=self.resolution_var, value="QHD", command=self.on_resolution_change)
        self.rb_qhd = tk.Radiobutton(res_frame, text="QHD (1440p)", variable=self.resolution_var, value="QHD", command=self.on_resolution_change)
        self.rb_qhd.pack(side='left', padx=5)
        
        # UI Scale Control
        tk.Label(root, text="UI Scale:").pack(pady=2)
        scale_frame = tk.Frame(root)
        scale_frame.pack(pady=2)
        
        self.scale_down_btn = tk.Button(scale_frame, text="<", command=lambda: self.change_scale(-0.002))
        self.scale_down_btn.pack(side='left', padx=5)
        
        self.scale_var = tk.StringVar(value="100.0%")
        self.scale_label = tk.Label(scale_frame, textvariable=self.scale_var, width=8)
        self.scale_label.pack(side='left', padx=5)
        
        self.scale_up_btn = tk.Button(scale_frame, text=">", command=lambda: self.change_scale(0.002))
        self.scale_up_btn.pack(side='left', padx=5)
        
        self.current_scale = 1.0
        
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
            
            # Disable Controls
            self.set_controls_state('disabled')
            
            self.on_start()
        else:
            self.stop(from_logic=False)

    def stop(self, from_logic=True):
        self.is_running = False
        
        def _update_ui():
            self.start_btn.config(text="START", bg='green')
            self.status_label.config(text="Stopped")
            self.overlay.set_click_through(False)
            
            # Enable Controls
            self.set_controls_state('normal')
            
        self.root.after(0, _update_ui)
        
        if not from_logic:
            self.on_stop()

    def set_controls_state(self, state):
        self.rb_97.config(state=state)
        self.rb_96.config(state=state)
        self.penalty_chk.config(state=state)
        self.rb_fhd.config(state=state)
        self.rb_qhd.config(state=state)
        self.auto_reset_chk.config(state=state)
        self.scale_down_btn.config(state=state)
        self.scale_up_btn.config(state=state)
        
    def set_start_enabled(self, enabled):
        state = 'normal' if enabled else 'disabled'
        self.start_btn.config(state=state)
        
    def update_status(self, text):
        self.status_label.config(text=text)
            
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

    def on_goal_change(self):
        if self.goal_callback:
            self.goal_callback(self.goal_var.get())

    def on_penalty_change(self):
        if self.penalty_callback:
            self.penalty_callback(self.penalty_var.get())

    def change_scale(self, delta):
        self.current_scale += delta
        self.current_scale = round(self.current_scale, 4) # Avoid float drift
        self.scale_var.set(f"{self.current_scale*100:.1f}%")
        
        self.overlay.set_scale(self.current_scale)
        if self.scale_callback:
            self.scale_callback(self.current_scale)
            
    def set_scale(self, scale):
        self.current_scale = scale
        self.scale_var.set(f"{self.current_scale*100:.1f}%")
        self.overlay.set_scale(scale)

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

    def highlight_recommendation(self, row_name, color='#00FF00'):
        self.root.after(0, lambda: self.overlay.highlight_recommendation(row_name, color))

    def update_probability_text(self, text):
        self.root.after(0, lambda: self.overlay.update_probability_text(text))

    def update_debug_circles(self, row_states):
        self.root.after(0, lambda: self.overlay.update_debug_circles(row_states))

    def update_ocr_text(self, text):
        self.root.after(0, lambda: self.overlay.update_ocr_text(text))

    def set_ocr_box_visibility(self, visible):
        self.root.after(0, lambda: self.overlay.set_ocr_box_visibility(visible))

if __name__ == "__main__":
    root = tk.Tk()
    # Hide root window if we want, but here root is the controller
    app = ControlPanel(root, lambda: print("Start"), lambda: print("Stop"), lambda: print("Vis"), lambda: print("Clk"), lambda: print("Reset"))
    root.mainloop()
