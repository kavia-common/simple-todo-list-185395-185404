import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, Integer, String, create_engine

from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Database setup
DB_FILE = os.environ.get("SQLITE_DB", os.path.join(os.path.dirname(__file__), "..", "..", "todo.db"))
DB_FILE = os.path.abspath(DB_FILE)
DB_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TodoORM(Base):
    """SQLAlchemy ORM model for Todo items."""
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)


# Pydantic Schemas

class TodoBase(BaseModel):
    """Base properties for a Todo item."""
    title: str = Field(..., description="Title of the todo")
    description: Optional[str] = Field(default=None, description="Optional description for the todo")
    completed: bool = Field(default=False, description="Completion status of the todo")


class TodoCreate(BaseModel):
    """Payload to create a Todo."""
    title: str = Field(..., description="Title of the todo")
    description: Optional[str] = Field(default=None, description="Optional description for the todo")


class TodoUpdate(BaseModel):
    """Payload to fully update a Todo (PUT)."""
    title: str = Field(..., description="Title of the todo")
    description: Optional[str] = Field(default=None, description="Optional description for the todo")
    completed: bool = Field(..., description="Completion status of the todo")


class TodoOut(TodoBase):
    """Response schema for a Todo item including its ID."""
    id: int = Field(..., description="Unique identifier of the todo")

    class Config:
        from_attributes = True


def init_db() -> None:
    """Create database tables and seed initial data if empty."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        count = db.query(TodoORM).count()
        if count == 0:
            samples = [
                TodoORM(title="Buy groceries", description="Milk, Bread, Eggs", completed=False),
                TodoORM(title="Read a book", description="Finish reading 'Atomic Habits'", completed=True),
            ]
            db.add_all(samples)
            db.commit()


# FastAPI app initialization with OpenAPI metadata and CORS
app = FastAPI(
    title="Todo API",
    description="A minimal CRUD API for managing Todos.",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Health check endpoints"},
        {"name": "todos", "description": "Operations on todo items"},
    ],
)

# Allow requests from React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get DB session
def get_db() -> Session:
    """Yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check")
def health_check() -> dict:
    """Health check endpoint.

    Returns:
        JSON object indicating service health.
    """
    return {"message": "Healthy"}


# Helper functions
def get_todo_or_404(db: Session, todo_id: int) -> TodoORM:
    """Retrieve a Todo by ID or raise 404."""
    todo = db.query(TodoORM).filter(TodoORM.id == todo_id).one_or_none()
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    return todo


# Routes

# PUBLIC_INTERFACE
@app.get("/todos", response_model=List[TodoOut], tags=["todos"], summary="List all todos")
def list_todos() -> List[TodoOut]:
    """List all todo items.

    Returns:
        List[TodoOut]: All todos in the system.
    """
    with SessionLocal() as db:
        todos = db.query(TodoORM).order_by(TodoORM.id.asc()).all()
        return [TodoOut.model_validate(t) for t in todos]


# PUBLIC_INTERFACE
@app.get("/todos/{todo_id}", response_model=TodoOut, tags=["todos"], summary="Get todo by ID")
def get_todo(todo_id: int) -> TodoOut:
    """Get a todo item by its ID.

    Args:
        todo_id: The ID of the todo to retrieve.

    Returns:
        TodoOut: The requested todo item.
    """
    with SessionLocal() as db:
        todo = get_todo_or_404(db, todo_id)
        return TodoOut.model_validate(todo)


# PUBLIC_INTERFACE
@app.post(
    "/todos",
    response_model=TodoOut,
    status_code=status.HTTP_201_CREATED,
    tags=["todos"],
    summary="Create a new todo",
)
def create_todo(payload: TodoCreate) -> TodoOut:
    """Create a new todo.

    Args:
        payload: TodoCreate payload containing title and optional description.

    Returns:
        TodoOut: The created todo item.
    """
    with SessionLocal() as db:
        todo = TodoORM(title=payload.title, description=payload.description or None, completed=False)
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return TodoOut.model_validate(todo)


# PUBLIC_INTERFACE
@app.put("/todos/{todo_id}", response_model=TodoOut, tags=["todos"], summary="Update a todo by ID")
def update_todo(todo_id: int, payload: TodoUpdate) -> TodoOut:
    """Update an existing todo by replacing its fields.

    Args:
        todo_id: The ID of the todo to update.
        payload: TodoUpdate payload with title, description, and completed.

    Returns:
        TodoOut: The updated todo item.
    """
    with SessionLocal() as db:
        todo = get_todo_or_404(db, todo_id)
        todo.title = payload.title
        todo.description = payload.description
        todo.completed = payload.completed
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return TodoOut.model_validate(todo)


# PUBLIC_INTERFACE
@app.patch(
    "/todos/{todo_id}/toggle",
    response_model=TodoOut,
    tags=["todos"],
    summary="Toggle completion status of a todo",
)
def toggle_todo(todo_id: int) -> TodoOut:
    """Flip the 'completed' status of a todo.

    Args:
        todo_id: The ID of the todo to toggle.

    Returns:
        TodoOut: The updated todo item with flipped completion.
    """
    with SessionLocal() as db:
        todo = get_todo_or_404(db, todo_id)
        todo.completed = not todo.completed
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return TodoOut.model_validate(todo)


# PUBLIC_INTERFACE
@app.delete(
    "/todos/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["todos"],
    summary="Delete a todo by ID",
)
def delete_todo(todo_id: int) -> None:
    """Delete a todo by ID.

    Args:
        todo_id: The ID of the todo to delete.

    Returns:
        None
    """
    with SessionLocal() as db:
        todo = get_todo_or_404(db, todo_id)
        db.delete(todo)
        db.commit()
    # 204 No Content has no response body
    return None


# Initialize DB and seed on import
init_db()

# Uvicorn entrypoint for running on port 3001 per preview system
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "3001"))
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=False)
