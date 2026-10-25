class RBAC:
    ROLES = {
        "admin": {"*"},
        "deployer": {"deploy:create", "service:read", "service:create"},
        "viewer": {"service:read"},
    }

    def __init__(self, store) -> None:
        self.store = store
        self.users: dict[str, str] = {}

    def add_user(self, email: str, role: str) -> None:
        if role not in self.ROLES:
            raise ValueError(f"Unknown role: {role}")
        self.users[email] = role

    def remove_user(self, email: str) -> None:
        self.users.pop(email, None)

    def list_users(self) -> list[dict[str, str]]:
        return [{"email": email, "role": role} for email, role in self.users.items()]

    def has_permission(self, email: str, permission: str) -> bool:
        role = self.users.get(email)
        return role == "admin" or permission in self.ROLES.get(role, set())
