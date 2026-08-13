from sqlalchemy.orm import Session
from app.repositories.user import user_repo
from app.core.security import get_password_hash
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User

class UserService:
    def create_user(self, db: Session, user_in: UserCreate) -> User:
        user_data = user_in.model_dump()
        password = user_data.pop("password")
        user_data["password_hash"] = get_password_hash(password)
        
        # Save to DB
        db_obj = User(**user_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_user(self, db: Session, db_obj: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            password = update_data.pop("password")
            if password:
                update_data["password_hash"] = get_password_hash(password)
                
        for field in update_data:
            setattr(db_obj, field, update_data[field])
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

user_service = UserService()
