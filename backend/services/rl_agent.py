"""
GridMind Reinforcement Learning Agent
========================================
This module implements a Q-Learning based Reinforcement Learning agent
for prescriptive load balancing on the APDCL distribution grid.

The agent learns to take the optimal action when a transformer is critical,
by deciding how much load to shift to neighboring transformers.

Key RL Concepts Used:
  - State:   Current grid condition (load, temp of 2 transformers)
  - Action:  How much load to shift (0%, 10%, 20%, 30%, 40%)
  - Reward:  +ve for reducing thermal stress, -ve for causing overload/blackout
  - Policy:  Epsilon-greedy (exploration vs exploitation)
  - Q-Table: Stores expected future rewards for each (state, action) pair

Why Q-Learning over PPO (Deep RL)?
  - Our state space (discretized load + temp bins) is small enough for a Q-Table.
  - Q-Learning is deterministic and fully explainable (guide can see the Q-Table).
  - PPO would require a neural network and much more training time.
  - Q-Learning result is easy to explain: "Given this state, the table says action 3 is best."
"""

import os
import json
import logging
import numpy as np
import joblib

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# GRID ENVIRONMENT — The World the Agent Lives In
# ═══════════════════════════════════════════════════════════════════════════════

class GridLoadBalancingEnv:
    """
    A simplified 2-transformer grid environment for RL training.

    State:
        (load_A_bin, temp_A_bin, load_B_bin)
        Each dimension is discretized into 5 bins (0-4).
        Total state space: 5 × 5 × 5 = 125 states

    Actions:
        0: No transfer (do nothing)
        1: Transfer 10% load from A to B
        2: Transfer 20% load from A to B
        3: Transfer 30% load from A to B
        4: Transfer 40% load from A to B

    Reward Logic:
        +10.0: Transformer A temperature dropped below 75°C (success!)
        +2.0:  Temperature reduced (partial improvement)
        -5.0:  Transformer B became overloaded (>110%) — bad transfer
        -15.0: Transformer A still critical AND B is overloaded (blackout risk)
        -1.0:  No improvement (status quo penalty)
    """

    NUM_LOAD_BINS = 5   # 0-20%, 20-40%, 40-60%, 60-80%, 80%+
    NUM_TEMP_BINS = 5   # 0-50, 50-65, 65-80, 80-90, 90+°C
    NUM_ACTIONS   = 5   # 0%, 10%, 20%, 30%, 40% transfer

    TRANSFER_STEPS = [0, 10, 20, 30, 40]  # % load to shift per action

    def __init__(self):
        self.state_space  = (self.NUM_LOAD_BINS, self.NUM_TEMP_BINS, self.NUM_LOAD_BINS)
        self.action_space = self.NUM_ACTIONS
        self.reset()

    def _bin_load(self, load_pct: float) -> int:
        """Discretize continuous load % into 5 bins."""
        thresholds = [20, 40, 60, 80]
        for i, t in enumerate(thresholds):
            if load_pct < t:
                return i
        return 4

    def _bin_temp(self, temp_c: float) -> int:
        """Discretize continuous temperature into 5 bins."""
        thresholds = [50, 65, 80, 90]
        for i, t in enumerate(thresholds):
            if temp_c < t:
                return i
        return 4

    def _get_state(self) -> tuple:
        return (
            self._bin_load(self.load_a),
            self._bin_temp(self.temp_a),
            self._bin_load(self.load_b)
        )

    def reset(self) -> tuple:
        """
        Reset to a random critical scenario.
        Transformer A is critical (high load + high temp).
        Transformer B has capacity available.
        """
        self.load_a = np.random.uniform(90, 130)   # Critical transformer
        self.temp_a = np.random.uniform(80, 105)   # High temperature
        self.load_b = np.random.uniform(20, 60)    # Healthy transformer with headroom
        self.steps  = 0
        self.max_steps = 10
        return self._get_state()

    def step(self, action: int) -> tuple:
        """
        Apply action, compute next state and reward.

        Returns:
            next_state (tuple), reward (float), done (bool), info (dict)
        """
        transfer_pct = self.TRANSFER_STEPS[action]
        prev_temp_a  = self.temp_a

        # Physics-based state transition
        self.load_a  = max(0, self.load_a - transfer_pct)
        self.load_b  = min(150, self.load_b + transfer_pct)

        # Temperature reduces proportionally as load is transferred
        # (simplified thermal model: temp drop ≈ load reduction × 0.5)
        self.temp_a = max(30, self.temp_a - (transfer_pct * 0.5) + np.random.normal(0, 2))
        self.steps += 1

        # ─── Reward Calculation ───────────────────────────────────────────────
        reward = 0.0
        done   = False
        info   = {}

        if self.temp_a < 75 and self.load_a < 90:
            # Perfect resolution
            reward = +10.0
            done   = True
            info["result"] = "SUCCESS: Transformer A normalized"
        elif self.load_b > 110:
            # Overloaded B — bad action
            reward = -5.0
            if self.load_b > 130:
                # Severe overload — blackout risk
                reward = -15.0
                done   = True
                info["result"] = "FAILURE: Transformer B overloaded (blackout risk)"
        elif self.temp_a < prev_temp_a:
            # Partial improvement — encourage this direction
            reward = +2.0
        else:
            # No improvement
            reward = -1.0

        if self.steps >= self.max_steps:
            done = True
            info["result"] = "TIMEOUT"

        return self._get_state(), reward, done, info


# ═══════════════════════════════════════════════════════════════════════════════
# Q-LEARNING AGENT
# ═══════════════════════════════════════════════════════════════════════════════

class QLearningAgent:
    """
    Q-Learning agent with epsilon-greedy exploration policy.

    Q-Table: shape (5, 5, 5, 5) = (load_bins, temp_bins, load_bins, actions)
    Stores the expected cumulative reward for each (state, action) pair.

    The Bellman Update Equation:
        Q(s,a) = Q(s,a) + α × [R + γ × max(Q(s',a')) - Q(s,a)]

    Where:
        α (alpha)   = Learning rate: How quickly to update Q-values (0.1)
        γ (gamma)   = Discount factor: How much to value future rewards (0.95)
        R           = Immediate reward from current action
        max(Q(s',a')= Maximum expected reward from next state s'
    """

    def __init__(self, env: GridLoadBalancingEnv,
                 alpha: float = 0.1,      # Learning rate
                 gamma: float = 0.95,     # Discount factor
                 epsilon: float = 1.0,    # Initial exploration rate (100%)
                 epsilon_min: float = 0.05,  # Minimum exploration (5%)
                 epsilon_decay: float = 0.995):  # Decay per episode
        self.env           = env
        self.alpha         = alpha
        self.gamma         = gamma
        self.epsilon       = epsilon
        self.epsilon_min   = epsilon_min
        self.epsilon_decay = epsilon_decay

        # Initialize Q-table with zeros
        q_shape = env.state_space + (env.action_space,)
        self.q_table = np.zeros(q_shape)

    def choose_action(self, state: tuple) -> int:
        """
        Epsilon-greedy policy:
          - With probability epsilon: Explore (random action)
          - With probability 1-epsilon: Exploit (best known action from Q-table)
        """
        if np.random.random() < self.epsilon:
            return np.random.randint(self.env.action_space)
        return int(np.argmax(self.q_table[state]))

    def update_q_table(self, state: tuple, action: int, reward: float,
                       next_state: tuple, done: bool):
        """Bellman equation update for Q-table."""
        current_q   = self.q_table[state][action]
        future_max  = 0.0 if done else np.max(self.q_table[next_state])
        new_q       = current_q + self.alpha * (reward + self.gamma * future_max - current_q)
        self.q_table[state][action] = new_q

    def train(self, n_episodes: int = 5000) -> dict:
        """
        Runs training loop for n_episodes episodes.

        Each episode:
          1. Reset environment to random critical state.
          2. Agent chooses actions until episode ends.
          3. Q-table updated after each step.
          4. Epsilon decays (shifts from exploration to exploitation).
        """
        episode_rewards = []
        success_count   = 0

        for episode in range(n_episodes):
            state       = self.env.reset()
            total_reward = 0
            done        = False

            while not done:
                action                          = self.choose_action(state)
                next_state, reward, done, info  = self.env.step(action)
                self.update_q_table(state, action, reward, next_state, done)
                state       = next_state
                total_reward += reward

            # Epsilon decay: reduce exploration as agent learns
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            episode_rewards.append(total_reward)

            if info.get("result", "").startswith("SUCCESS"):
                success_count += 1

        success_rate = success_count / n_episodes
        avg_reward   = np.mean(episode_rewards[-500:])  # Last 500 episodes

        logger.info(f"=== Q-Learning Training Complete ===")
        logger.info(f"  Success Rate (last 500 ep): {success_rate:.2%}")
        logger.info(f"  Avg Reward (last 500 ep):   {avg_reward:.2f}")

        return {
            "model": "Q-Learning Agent",
            "algorithm": "Tabular Q-Learning (Bellman Equation)",
            "state_space": "125 discrete states (load_A_bin × temp_A_bin × load_B_bin)",
            "action_space": "5 actions (0%, 10%, 20%, 30%, 40% load transfer)",
            "hyperparameters": {
                "alpha_learning_rate":  self.alpha,
                "gamma_discount_factor": self.gamma,
                "epsilon_initial":      1.0,
                "epsilon_final":        self.epsilon,
                "epsilon_decay":        self.epsilon_decay,
                "n_episodes":           n_episodes
            },
            "results": {
                "success_rate":    round(success_rate, 4),
                "avg_reward_last_500_episodes": round(float(avg_reward), 2)
            }
        }

    def get_policy_summary(self) -> dict:
        """Returns the learned policy as a human-readable dict."""
        action_labels = ["No Transfer", "Transfer 10%", "Transfer 20%",
                         "Transfer 30%", "Transfer 40%"]
        policy = {}
        env = self.env
        for la in range(env.NUM_LOAD_BINS):
            for ta in range(env.NUM_TEMP_BINS):
                for lb in range(env.NUM_LOAD_BINS):
                    best_action = int(np.argmax(self.q_table[la, ta, lb]))
                    key = f"load_A_bin={la}, temp_A_bin={ta}, load_B_bin={lb}"
                    policy[key] = action_labels[best_action]
        return policy


# ─── Entry Point ──────────────────────────────────────────────────────────────

def train_rl_agent(save_path: str = "ml_models/rl_agent.pkl",
                   n_episodes: int = 5000) -> dict:
    """Trains the Q-Learning agent and saves Q-table + results."""
    logger.info("=== Training Reinforcement Learning Agent ===")

    env   = GridLoadBalancingEnv()
    agent = QLearningAgent(env)
    results = agent.train(n_episodes=n_episodes)

    # Save Q-table and agent state
    os.makedirs("ml_models", exist_ok=True)
    joblib.dump({
        "q_table":         agent.q_table,
        "epsilon":         agent.epsilon,
        "hyperparameters": results["hyperparameters"]
    }, save_path)

    # Save results JSON
    with open("ml_models/rl_results.json", "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"RL Agent saved to {save_path}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    results = train_rl_agent()
    print(f"\n=== RL AGENT RESULTS ===")
    print(f"Success Rate: {results['results']['success_rate']:.2%}")
    print(f"Avg Reward:   {results['results']['avg_reward_last_500_episodes']:.2f}")
