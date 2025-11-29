import tkinter as tk
import threading
import time
import keyboard
import pyautogui
import ctypes
import os
import cv2
from overlay_gui import ControlPanel
from game_logic import StoneFacetingLogic
from vision import Vision
from ocr_subproject.new_ocr import NewOcrEngine
from settings_manager import SettingsManager

class BotController:
    SAVE_CAPTURES = False # Configuration flag

    def __init__(self):
        self.root = tk.Tk()
        self.gui = ControlPanel(
            self.root, 
            self.start_bot, 
            self.stop_bot,
            None, # test_vision removed
            None, # test_click removed
            self.reset_bot,
            self.on_resolution_change,
            self.on_goal_change,
            self.on_penalty_change,
            self.on_scale_change
        )
        self.vision = Vision(self.gui.get_overlay_coords())
        self.ocr = NewOcrEngine()
        self.logic = StoneFacetingLogic()
        self.settings_manager = SettingsManager()
        
        # Load Settings
        saved_goal = self.settings_manager.get("goal")
        saved_res = self.settings_manager.get("resolution")
        saved_penalty = self.settings_manager.get("penalty_allowed")
        saved_scale = self.settings_manager.get("ui_scale")
        if saved_scale is None: saved_scale = 1.0
        
        # Apply to GUI (Update Vars)
        self.gui.goal_var.set(saved_goal)
        self.gui.resolution_var.set(saved_res)
        self.gui.penalty_var.set(saved_penalty)
        
        # Apply to Logic
        if saved_goal == "97":
            self.logic.set_targets(9, 7)
        else:
            self.logic.set_targets(9, 6)
            
        self.logic.set_penalty_limit(5 if saved_penalty else 4)
        
        # Apply Resolution to Overlay
        self.gui.overlay.set_resolution(saved_res)
        
        # Apply Scale
        self.gui.set_scale(saved_scale)
        
        # Restore Overlay Position
        x = self.settings_manager.get("overlay_x")
        y = self.settings_manager.get("overlay_y")
        self.gui.overlay.geometry(f"+{x}+{y}")
        
        self.running = False
        self.thread = None
        self.needs_reset = False
        self.is_calculating = False
        
        # Start initial calculation
        self.recalculate_logic()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        print("Closing Application...")
        
        # Save Overlay Position
        try:
            geo = self.gui.overlay.geometry()
            # Format: WxH+X+Y
            parts = geo.replace('+', 'x').split('x')
            # parts = [W, H, X, Y]
            if len(parts) >= 4:
                x = int(parts[2])
                y = int(parts[3])
                self.settings_manager.set("overlay_x", x)
                self.settings_manager.set("overlay_y", y)
                print(f"Saved Overlay Position: {x}, {y}")
        except Exception as e:
            print(f"Error saving position: {e}")
            
        self.running = False
        self.root.destroy()
        import os
        os._exit(0) # Force exit to kill any hanging threads

    def on_resolution_change(self, res):
        print(f"Resolution changed to {res}")
        self.settings_manager.set("resolution", res)
        # Update Vision coordinates
        new_coords = self.gui.get_overlay_coords()
        self.vision.update_coords(new_coords)

    def on_goal_change(self, value):
        self.settings_manager.set("goal", value)
        if value == "97":
            self.logic.set_targets(9, 7)
        elif value == "96":
            self.logic.set_targets(9, 6)
        
        self.recalculate_logic()

    def on_penalty_change(self, value):
        self.settings_manager.set("penalty_allowed", value)
        # value is boolean
        limit = 5 if value else 4
        self.logic.set_penalty_limit(limit)
        
        self.recalculate_logic()

    def on_scale_change(self, value):
        print(f"UI Scale changed to {value}")
        self.settings_manager.set("ui_scale", value)
        # Vision coords update is handled by overlay update -> get_overlay_coords
        # But we need to push new coords to vision
        new_coords = self.gui.get_overlay_coords()
        self.vision.update_coords(new_coords)

    def recalculate_logic(self):
        """
        Calculate probability for CURRENT settings only.
        Blocks start button until done.
        """
        if self.is_calculating: return

        self.is_calculating = True
        self.gui.set_start_enabled(False)
        self.gui.update_status("Calculating... Please Wait")
        self.gui.update_probability_text("Win Prob: Calculating...")
        self.gui.highlight_recommendation(None)
        
        def _calc():
            print("Starting calculation for current settings...")
            # Initial state: 10 empty slots per row, 75% prob (p_idx=5)
            c1, c2, c3 = 10, 10, 10
            s1, s2, s3 = 0, 0, 0
            p_idx = 5 # 0.75
            
            # Use current targets from logic
            t1 = self.logic.target_r1_primary
            t2 = self.logic.target_r2_secondary
            t3 = self.logic.target_r3_max
            
            # Run calculation
            self.logic.solve(c1, c2, c3, s1, s2, s3, p_idx, t1, t2, t3)
            print("Calculation Complete.")
            
            # Update UI on main thread
            def _done():
                self.is_calculating = False
                self.gui.set_start_enabled(True)
                self.gui.update_status("Ready - Press START")
                self.update_recommendation(force=True)
                
            self.root.after(0, _done)
                
        threading.Thread(target=_calc, daemon=True).start()

    def reset_bot(self):
        print("Resetting Bot State...")
        self.logic.reset()
        self.gui.highlight_recommendation(None)
        # Clear debug circles
        self.gui.update_debug_circles({'row1':[-1]*10, 'row2':[-1]*10, 'row3':[-1]*10})
        self.needs_reset = True
        
        # Immediately update recommendation (should be fast if cached)
        self.update_recommendation(force=True)

    def start_bot(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_loop)
            self.thread.start()
            print("Bot Started - Assist Mode")

    def stop_bot(self):
        self.running = False
        # Do not join() here, as it freezes the GUI. 
        # The thread will exit on its own since we set running=False.
        # if self.thread and self.thread.is_alive():
        #     self.thread.join()
        
        self.gui.stop(from_logic=True) 
        print("Bot Stopped")

    def test_click(self):
        print("Test Click Disabled in Assist Mode")

    def capture_ocr_clean(self, region, coords):
        """
        Captures OCR image while temporarily hiding the orange box.
        Handles both Main Thread and Background Thread calls safely.
        """
        # We need to access the overlay window directly to force update
        # self.gui is ControlPanel, self.gui.overlay is VisualOverlay
        overlay_window = self.gui.overlay

        if threading.current_thread() is threading.main_thread():
            # Main Thread: Direct Call
            overlay_window.set_ocr_box_visibility(False)
            # Force update is already in set_ocr_box_visibility, but let's be sure
            # overlay_window.update() 
            
            img = self.vision.get_ocr_image(region, coords)
            
            overlay_window.set_ocr_box_visibility(True)
            return img
        else:
            # Background Thread: Schedule and Wait
            event = threading.Event()
            def _hide():
                # Call directly on overlay to avoid another root.after in ControlPanel wrapper
                overlay_window.set_ocr_box_visibility(False)
                event.set()
            
            self.root.after(0, _hide)
            event.wait() # Block until hidden and updated
            
            # Tiny sleep to ensure OS compositor has painted the transparency
            # time.sleep(0.01) 
            
            img = self.vision.get_ocr_image(region, coords)
            
            # Show (Async is fine, no need to wait)
            self.root.after(0, lambda: overlay_window.set_ocr_box_visibility(True))
            return img

    def run_loop(self):
        print("Bot Running - Continuous Scan Mode")
        
        # Initial State
        last_row_states = {
            'row1': [-1]*10,
            'row2': [-1]*10,
            'row3': [-1]*10
        }
        
        # Force initial recommendation
        self.update_recommendation(force=True)
        
        # Initial OCR Check
        try:
            region = self.gui.get_overlay_geometry()
            ocr_coords = self.gui.get_overlay_coords()['prob_ocr_box']
            ocr_img = self.capture_ocr_clean(region, ocr_coords)
            
            current_res = self.gui.resolution_var.get()
            
            label, conf = self.ocr.predict(ocr_img, resolution=current_res)
            if label and label in ['2', '3', '4', '5', '6', '7']:
                self.logic.set_probability_from_ocr(label)
                self.gui.update_ocr_text(f"{int(self.logic.current_probability*100)}%")
        except:
            pass
        
        while self.running:
            if keyboard.is_pressed('q'):
                self.stop_bot()
                break
            
            if self.needs_reset:
                last_row_states = {
                    'row1': [-1]*10,
                    'row2': [-1]*10,
                    'row3': [-1]*10
                }
                self.needs_reset = False
                print("Loop State Reset")
                self.gui.update_ocr_text("") # Clear OCR text on reset
            
            try:
                region = self.gui.get_overlay_geometry()
                current_row_states = self.vision.analyze_state(region)
                
                # Update Debug Circles (Always show what we see immediately)
                self.gui.update_debug_circles(current_row_states)
                
                # Check for changes
                if current_row_states != last_row_states:
                    print("State Change Detected! Waiting for UI to settle...")
                    
                    # Hide recommendation during transition
                    self.gui.highlight_recommendation(None)
                    
                    # Wait for 1-3 frames (approx 50ms) for text/animations to finish
                    # User requested increase to 0.1s (1 frame of bot logic) for better stability
                    time.sleep(0.1)
                    
                    # Check for Auto Reset Condition (All slots became empty)
                    current_filled_count = sum(1 for row in current_row_states.values() for x in row if x != -1)
                    last_filled_count = sum(1 for row in last_row_states.values() for x in row if x != -1)
                    
                    if last_filled_count > 0 and current_filled_count == 0:
                        if self.gui.auto_reset_var.get():
                            print("Auto Reset Triggered!")
                            self.reset_bot()
                            last_row_states = {
                                'row1': [-1]*10,
                                'row2': [-1]*10,
                                'row3': [-1]*10
                            }
                            continue 
                    
                    # Calculate Probability Change based on what changed
                    box_color = '#00FF00' # Default Green
                    
                    for row in ['row1', 'row2', 'row3']:
                        for i in range(10):
                            prev = last_row_states[row][i]
                            curr = current_row_states[row][i]
                            
                            if prev == -1 and curr != -1:
                                # A slot was filled!
                                is_success = (curr == 1)
                                print(f"Slot Filled: {row}[{i}] = {'Success' if is_success else 'Fail'}")
                                
                                # 1. Calculate Expected Probability (Game Rule)
                                expected_prob = self.logic.calculate_next_probability(is_success)
                                
                                # OCR Probability Check
                                try:
                                    ocr_coords = self.gui.get_overlay_coords()['prob_ocr_box']
                                    ocr_img = self.capture_ocr_clean(region, ocr_coords)
                                    
                                    current_res = self.gui.resolution_var.get()
                                    
                                    # Save Capture if enabled
                                    if self.SAVE_CAPTURES:
                                        if not os.path.exists('captures'):
                                            os.makedirs('captures')
                                        timestamp = int(time.time() * 1000)
                                        filename = f"captures/ocr_{timestamp}_{row}_{i}_{'succ' if is_success else 'fail'}.png"
                                        cv2.imwrite(filename, ocr_img)
                                        print(f"Saved capture: {filename}")

                                    label, conf = self.ocr.predict(ocr_img, resolution=current_res)
                                    print(f"OCR Prediction: {label} (Conf: {conf:.2f})")
                                    
                                    if label and label in ['2', '3', '4', '5', '6', '7']:
                                        # OCR Succeeded
                                        ocr_prob_map = {'2':0.25, '3':0.35, '4':0.45, '5':0.55, '6':0.65, '7':0.75}
                                        ocr_prob = ocr_prob_map.get(label, 0.75)
                                        
                                        # Compare with Expected
                                        if abs(ocr_prob - expected_prob) > 0.01:
                                            print(f"WARNING: Probability Mismatch! Expected {expected_prob}, OCR saw {ocr_prob}")
                                            box_color = 'yellow'
                                        else:
                                            box_color = '#00FF00' # Match -> Green
                                        
                                        # Always trust OCR for next state (Self-correction)
                                        self.logic.set_probability_from_ocr(label)
                                        self.gui.update_ocr_text(f"{int(self.logic.current_probability*100)}%")
                                    else:
                                        # OCR Failed (N or invalid)
                                        print("OCR failed or invalid label. Using fallback logic.")
                                        self.gui.update_ocr_text("?") # Show ? on failure
                                        self.logic.update_probability(is_success)
                                        
                                        # User Request: Show Yellow if OCR fails
                                        box_color = 'yellow'
                                        
                                except Exception as e:
                                    print(f"OCR Error: {e}")
                                    self.gui.update_ocr_text("?") # Show ? on error
                                    self.logic.update_probability(is_success)
                                    box_color = 'yellow' # Error -> Yellow
                    
                    # Update Logic State
                    self.logic.slots = current_row_states
                    
                    # Get New Recommendation
                    move = self.logic.recommend_move()
                    
                    # Calculate Win Probability
                    win_prob = self.logic.calculate_max_win_probability()
                    win_prob_pct = win_prob * 100
                    
                    # Update GUI
                    self.gui.update_probability_text(f"Target Prob: {win_prob_pct:.2f}%")
                    
                    if win_prob_pct <= 0.0:
                        self.gui.highlight_recommendation(None) 
                        print(f"Win Prob is 0%. Stopping recommendation.")
                    else:
                        self.gui.highlight_recommendation(move, color=box_color)
                        print(f"New Prob: {int(self.logic.current_probability*100)}% -> Rec: {move} (Win: {win_prob_pct:.2f}%)")
                    
                    last_row_states = current_row_states
            
            except Exception as e:
                print(f"Error in loop: {e}")
                
            time.sleep(0.1) # 0.1s Scan Interval

    def update_recommendation(self, force=False):
        # Helper for initial run or reset
        try:
            region = self.gui.get_overlay_geometry()
            
            # 1. Analyze Slots
            current_row_states = self.vision.analyze_state(region)
            self.logic.slots = current_row_states
            
            # 2. Check OCR (Sync Probability)
            try:
                ocr_coords = self.gui.get_overlay_coords()['prob_ocr_box']
                ocr_img = self.capture_ocr_clean(region, ocr_coords)
                
                # QHD Scaling: Removed in favor of native QHD templates
                current_res = self.gui.resolution_var.get()
                
                label, conf = self.ocr.predict(ocr_img, resolution=current_res)
                if label and label in ['2', '3', '4', '5', '6', '7']:
                    self.logic.set_probability_from_ocr(label)
                    self.gui.update_ocr_text(f"{int(self.logic.current_probability*100)}%")
                else:
                    self.gui.update_ocr_text("?") # Indicate OCR failed/uncertain
            except Exception as e:
                print(f"OCR Sync Error: {e}")
            
            # 3. Get Recommendation
            move = self.logic.recommend_move()
            self.gui.highlight_recommendation(move, color='#00FF00') # Default green for initial/reset
            
            # 4. Update Win Probability Text
            win_prob = self.logic.calculate_max_win_probability()
            win_prob_pct = win_prob * 100
            self.gui.update_probability_text(f"Target Prob: {win_prob_pct:.2f}%")
            
            if force:
                print(f"Synced State: Prob={int(self.logic.current_probability*100)}%, Win={win_prob_pct:.2f}% -> Rec: {move}")
                
        except Exception as e:
            print(f"Update Recommendation Error: {e}")

if __name__ == "__main__":
    bot = BotController()
    bot.root.mainloop()
