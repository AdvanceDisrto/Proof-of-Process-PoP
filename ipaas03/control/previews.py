import re

class PreviewManager:
    def __init__(self, store) -> None:
        self.store = store

    def create(self, service: str, branch: str) -> dict[str, object]:
        if branch == "main":
            return {"ok": False, "reason": "main does not create previews"}
        safe = re.sub(r"[^a-z0-9]+", "-", branch.lower()).strip("-")
        return {"ok": True, "hostname": f"{service}-{safe}.preview.localhost"}
