import tkinter as tk
import threading
import time
import keyboard
import pyautogui
import ctypes
from overlay_gui import ControlPanel
from game_logic import StoneFacetingLogic
from vision import Vision

class BotController:
    def __init__(self):
        self.root = tk.Tk()
        self.gui = ControlPanel(
            self.root, 
            self.start_bot, 
            self.stop_bot,
            self.test_vision,
            self.test_click,
            self.reset_bot,
            self.on_resolution_change
        )
        self.vision = Vision(self.gui.get_overlay_coords())
        self.logic = StoneFacetingLogic()
        self.running = False
        self.thread = None
        self.needs_reset = False
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        print("Closing Application...")
        self.running = False
        self.root.destroy()
        import os
        os._exit(0) # Force exit to kill any hanging threads

    def on_resolution_change(self, res):
        print(f"Resolution changed to {res}")
        # Update Vision coordinates
        new_coords = self.gui.get_overlay_coords()
        self.vision.update_coords(new_coords)

    def reset_bot(self):
        print("Resetting Bot State...")
        self.logic.reset()
        self.gui.highlight_recommendation(None)
        self.gui.update_probability_text("Win Prob: Calculating...")
        self.gui.update_current_prob_text("Current Prob: 75%")
        self.needs_reset = True
        # Force update recommendation for initial state
        self.root.after(100, lambda: self.update_recommendation(force=True))

    def start_bot(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_loop)
            self.thread.start()
            print("Bot Started - Assist Mode")

    def stop_bot(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.gui.stop(from_logic=True) 
        print("Bot Stopped")

    def test_vision(self):
        print("\n--- Testing Vision ---")
        region = self.gui.get_overlay_geometry()
        row_states, debug_info = self.vision.analyze_state(region, debug=True)
        for row in ['row1', 'row2', 'row3']:
            states = row_states[row]
            colors = debug_info[row]
            state_str = " ".join(["[S]" if s==1 else "[F]" if s==0 else "[ ]" for s in states])
            print(f"{row} States: {state_str}")
            color_str = " ".join(colors)
            print(f"{row} Colors: {color_str}")
            print("-" * 20)
        print("----------------------\n")

    def test_click(self):
        print("Test Click Disabled in Assist Mode")

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
            
            try:
                region = self.gui.get_overlay_geometry()
                current_row_states = self.vision.analyze_state(region)
                
                # Check for changes
                if current_row_states != last_row_states:
                    print("State Change Detected!")
                    
                    # Check for Auto Reset Condition (All slots became empty)
                    # We need to know if we HAD stones before.
                    
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
                            continue # Skip the rest of the loop for this iteration
                    
                    # Calculate Probability Change based on what changed
                    
                    # Calculate Probability Change based on what changed
                    # We iterate to find the new move result
                    for row in ['row1', 'row2', 'row3']:
                        for i in range(10):
                            prev = last_row_states[row][i]
                            curr = current_row_states[row][i]
                            
                            if prev == -1 and curr != -1:
                                # A slot was filled!
                                is_success = (curr == 1)
                                print(f"Slot Filled: {row}[{i}] = {'Success' if is_success else 'Fail'}")
                                self.logic.update_probability(is_success)
                    
                    # Update Logic State
                    self.logic.slots = current_row_states
                    
                    # Get New Recommendation
                    move = self.logic.recommend_move()
                    
                    # Calculate Win Probability
                    win_prob = self.logic.calculate_max_win_probability()
                    win_prob_pct = win_prob * 100
                    
                    # Update GUI
                    self.gui.update_probability_text(f"Win Prob: {win_prob_pct:.2f}%")
                    self.gui.update_current_prob_text(f"Current Prob: {int(self.logic.current_probability*100)}%")
                    
                    if win_prob_pct <= 0.0:
                        self.gui.highlight_recommendation(None) # Clear highlight
                        print(f"Win Prob is 0%. Stopping recommendation.")
                    else:
                        self.gui.highlight_recommendation(move)
                        print(f"New Prob: {int(self.logic.current_probability*100)}% -> Rec: {move} (Win: {win_prob_pct:.2f}%)")
                    
                    last_row_states = current_row_states
            
            except Exception as e:
                print(f"Error in loop: {e}")
                
            time.sleep(0.1) # 0.1s Scan Interval

    def update_recommendation(self, force=False):
        # Helper for initial run
        try:
            region = self.gui.get_overlay_geometry()
            current_row_states = self.vision.analyze_state(region)
            self.logic.slots = current_row_states
            move = self.logic.recommend_move()
            self.gui.highlight_recommendation(move)
            if force:
                print(f"Initial Prob: {int(self.logic.current_probability*100)}% -> Rec: {move}")
        except:
            pass

if __name__ == "__main__":
    bot = BotController()
    bot.root.mainloop()
