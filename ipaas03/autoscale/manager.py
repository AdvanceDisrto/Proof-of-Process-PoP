from dataclasses import dataclass

@dataclass(frozen=True)
class ScalePolicy:
    service: str
    min_replicas: int
    max_replicas: int

class Autoscaler:
    def __init__(self, store) -> None:
        self.store = store
        self.policies: dict[str, ScalePolicy] = {}

    def set_policy(self, policy: ScalePolicy) -> None:
        if policy.min_replicas < 0 or policy.max_replicas < policy.min_replicas:
            raise ValueError("invalid replica bounds")
        self.policies[policy.service] = policy

    def get_policy(self, service: str) -> dict[str, int]:
        policy = self.policies[service]
        return {"min_replicas": policy.min_replicas, "max_replicas": policy.max_replicas}
