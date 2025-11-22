import random
import numpy as np
from functools import lru_cache

class StoneFacetingLogic:
    def __init__(self, target_success_rates=None):
        """
        Initialize the logic.
        Target: (Row1 >= 9 and Row2 >= 6) OR (Row1 >= 6 and Row2 >= 9)
        Row3 <= 4 (Failures, which are successes in game terms)
        """
        self.target_r1_primary = 9
        self.target_r2_secondary = 6
        self.target_r3_max = 4
        
        # Probability levels: 0.25, 0.35, 0.45, 0.55, 0.65, 0.75
        self.probs = [0.25, 0.35, 0.45, 0.55, 0.65, 0.75]
        self.min_probability = 0.25
        self.max_probability = 0.75
        self.current_probability = 0.75
        
        self.slots = {
            'row1': [-1] * 10,
            'row2': [-1] * 10,
            'row3': [-1] * 10
        }

    def reset(self):
        self.current_probability = 0.75
        self.slots = {
            'row1': [-1] * 10,
            'row2': [-1] * 10,
            'row3': [-1] * 10
        }

    def update_probability(self, success):
        """
        Update probability based on the result of the last click.
        Success -> Decrease probability by 10%
        Fail -> Increase probability by 10%
        """
        if success:
            self.current_probability = max(self.min_probability, self.current_probability - 0.10)
        else:
            self.current_probability = min(self.max_probability, self.current_probability + 0.10)
            
        # Round to avoid floating point errors
        self.current_probability = round(self.current_probability, 2)

    def get_current_counts(self):
        """Return current success count for each row."""
        counts = {}
        for row, slots in self.slots.items():
            counts[row] = slots.count(1)
        return counts

    def get_state_params(self):
        """
        Calculate parameters for the solver:
        c1, c2, c3: Remaining slots
        s1, s2, s3: Current successes
        p_idx: Current probability index
        """
        c1 = self.slots['row1'].count(-1)
        c2 = self.slots['row2'].count(-1)
        c3 = self.slots['row3'].count(-1)
        
        s1 = self.slots['row1'].count(1)
        s2 = self.slots['row2'].count(1)
        s3 = self.slots['row3'].count(1)
        
        # Prob index
        # 0.25 -> 0, ... 0.75 -> 5
        p_idx = int(round((self.current_probability - 0.25) * 10))
        
        return c1, c2, c3, s1, s2, s3, p_idx

    @lru_cache(maxsize=None)
    def solve(self, c1, c2, c3, s1, s2, s3, p_idx):
        """
        Calculate Q-values (Win Probability) for clicking Row 1, 2, or 3.
        Returns tuple (q1, q2, q3).
        """
        # Pruning: If Row 3 successes exceed max, we lost.
        if s3 > self.target_r3_max:
            return (0.0, 0.0, 0.0)

        # Base Case: All slots filled
        if c1 == 0 and c2 == 0 and c3 == 0:
            # Check Win Condition
            # 9/6 OR 6/9
            cond1 = (s1 >= 9 and s2 >= 6)
            cond2 = (s1 >= 6 and s2 >= 9)
            
            if (cond1 or cond2) and s3 <= self.target_r3_max:
                return (0.0, 0.0, 0.0) # Values don't matter, but we need a return format. 
                # Wait, this function returns Q-values for *moves*.
                # If no moves left, we shouldn't be calling this?
                # Actually, the recursive calls take max(solve(...)).
                # So if base case, we return the Value of the state.
                # But the signature returns (q1, q2, q3).
                # Let's change signature or handle base case differently.
                pass
        
        # Helper for recursion
        def get_value(nc1, nc2, nc3, ns1, ns2, ns3, np_idx):
            if nc1 == 0 and nc2 == 0 and nc3 == 0:
                if ns3 > self.target_r3_max: return 0.0
                c1_win = (ns1 >= 9 and ns2 >= 6)
                c2_win = (ns1 >= 6 and ns2 >= 9)
                return 1.0 if (c1_win or c2_win) else 0.0
            
            qs = self.solve(nc1, nc2, nc3, ns1, ns2, ns3, np_idx)
            # We pick the best move
            best = -1.0
            if nc1 > 0: best = max(best, qs[0])
            if nc2 > 0: best = max(best, qs[1])
            if nc3 > 0: best = max(best, qs[2])
            return best if best >= 0 else 0.0

        # Helper to get next prob index
        def p_fail(pidx): return min(5, pidx + 1)
        def p_succ(pidx): return max(0, pidx - 1)
        
        prob = self.probs[p_idx]
        
        # --- Row 1 ---
        q1 = -1.0
        if c1 > 0:
            # Success
            v_succ = get_value(c1-1, c2, c3, s1+1, s2, s3, p_succ(p_idx))
            # Fail
            v_fail = get_value(c1-1, c2, c3, s1, s2, s3, p_fail(p_idx))
            q1 = prob * v_succ + (1 - prob) * v_fail

        # --- Row 2 ---
        q2 = -1.0
        if c2 > 0:
            # Success
            v_succ = get_value(c1, c2-1, c3, s1, s2+1, s3, p_succ(p_idx))
            # Fail
            v_fail = get_value(c1, c2-1, c3, s1, s2, s3, p_fail(p_idx))
            q2 = prob * v_succ + (1 - prob) * v_fail

        # --- Row 3 ---
        q3 = -1.0
        if c3 > 0:
            # Success (Bad)
            v_succ = get_value(c1, c2, c3-1, s1, s2, s3+1, p_succ(p_idx))
            # Fail (Good)
            v_fail = get_value(c1, c2, c3-1, s1, s2, s3, p_fail(p_idx))
            q3 = prob * v_succ + (1 - prob) * v_fail
            
        return (q1, q2, q3)

    def recommend_move(self):
        """
        Recommend which row to click.
        """
        c1, c2, c3, s1, s2, s3, p_idx = self.get_state_params()
        
        # Optimization: Clamp s1, s2 to 9 (since >9 is same as 9 for goal)
        # s3 clamp to 5
        s1_c = min(s1, 9)
        s2_c = min(s2, 9)
        s3_c = min(s3, 5)
        
        q_values = self.solve(c1, c2, c3, s1_c, s2_c, s3_c, p_idx)
        
        # Filter out invalid moves (where c=0)
        valid_qs = []
        if c1 > 0: valid_qs.append((q_values[0], 'row1'))
        if c2 > 0: valid_qs.append((q_values[1], 'row2'))
        if c3 > 0: valid_qs.append((q_values[2], 'row3'))
        
        if not valid_qs:
            return None
            
        # Pick max
        # Find max q value
        max_q = max(q for q, r in valid_qs)
        
        # Find all rows with max q (within tolerance)
        best_rows = [r for q, r in valid_qs if abs(q - max_q) < 1e-9]
        
        return best_rows

    def calculate_max_win_probability(self):
        """
        Calculate the maximum possible probability of winning.
        """
        c1, c2, c3, s1, s2, s3, p_idx = self.get_state_params()
        s1_c = min(s1, 9)
        s2_c = min(s2, 9)
        s3_c = min(s3, 5)
        
        q_values = self.solve(c1, c2, c3, s1_c, s2_c, s3_c, p_idx)
        
        best = 0.0
        if c1 > 0: best = max(best, q_values[0])
        if c2 > 0: best = max(best, q_values[1])
        if c3 > 0: best = max(best, q_values[2])
        
        return best
