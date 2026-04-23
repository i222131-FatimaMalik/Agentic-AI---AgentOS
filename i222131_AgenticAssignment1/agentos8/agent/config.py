from dataclasses import dataclass

@dataclass(frozen=True)
class AgentConfig:
    # Global budgets (hidden tests will vary these)
    max_steps: int = 18
    reflection_max_rounds: int = 3

    # ToT controls
    tot_node_budget: int = 24
    tot_branching: int = 3

    # Planning controls
    plan_steps: int = 4
    max_replans: int = 1

    # Determinism
    seed: int = 123

    # Safety / runtime
    llm_timeout_s: int = 60
