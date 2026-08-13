from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    RECEPTION = "reception"
    TECHNICIAN = "technician"
    REVIEWER = "reviewer"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
