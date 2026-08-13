from app.repositories.base import CRUDBase
from app.models.branch import Branch

class CRUDBranch(CRUDBase[Branch]):
    pass

branch_repo = CRUDBranch(Branch)
