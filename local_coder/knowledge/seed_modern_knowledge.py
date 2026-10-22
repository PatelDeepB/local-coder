"""Populates CodingKnowledgeDB with canonical modern 2024-2026 framework idioms."""

from local_coder.knowledge.coding_knowledge_db import CodingKnowledgeDB


CANONICAL_ENTRIES = [
    {
        "topic": "django.views.generic.ListView",
        "category": "django",
        "version": "Django 5.1",
        "signature": "class ListView(MultipleObjectTemplateResponseMixin, BaseListView): ...",
        "canonical_code": """from django.views.generic import ListView
from .models import Item

class ItemListView(ListView):
    model = Item
    template_name = "items/list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        return Item.objects.select_related("category").filter(is_active=True)""",
        "docstring": "Django 5.1 Class-Based View for rendering list of objects with automatic pagination and ORM prefetching.",
        "anti_patterns": "Function-based views with raw SQL or manual pagination without select_related.",
    },
    {
        "topic": "django.forms.ModelForm",
        "category": "django",
        "version": "Django 5.1",
        "signature": "class ModelForm(BaseModelForm, metaclass=ModelFormMetaclass): ...",
        "canonical_code": """from django import forms
from .models import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "description", "due_date", "is_completed")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Task title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_title(self) -> str:
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 3:
            raise forms.ValidationError("Title must be at least 3 characters.")
        return title""",
        "docstring": "Django 5.1 ModelForm binding directly to model with custom widgets and clean validation methods.",
        "anti_patterns": "Manually parsing request.POST without form validation.",
    },
    {
        "topic": "react.functional_state",
        "category": "react",
        "version": "React 19 / 18",
        "signature": "const [state, setState] = useState<T>(initialState);",
        "canonical_code": """import React, { useState, useCallback } from 'react';

interface CounterProps {
  initialCount?: number;
}

export const ModernCounter: React.FC<CounterProps> = ({ initialCount = 0 }) => {
  const [count, setCount] = useState<number>(initialCount);

  const increment = useCallback(() => setCount(c => c + 1), []);
  const decrement = useCallback(() => setCount(c => Math.max(0, c - 1)), []);

  return (
    <div className="counter-container">
      <h3>Count: {count}</h3>
      <button onClick={decrement}>-</button>
      <button onClick={increment}>+</button>
    </div>
  );
};""",
        "docstring": "React 18/19 functional component with typed state and memoized callbacks.",
        "anti_patterns": "React class components, this.setState, mutate state directly without setter.",
    },
    {
        "topic": "fastapi.lifespan_handler",
        "category": "fastapi",
        "version": "FastAPI 0.115+",
        "signature": "@asynccontextmanager async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]: ...",
        "canonical_code": """from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: initialize connection pools
    yield
    # Shutdown: release resources

app = FastAPI(title="Modern API", lifespan=lifespan)""",
        "docstring": "FastAPI modern lifespan context manager replacing deprecated @app.on_event startup/shutdown.",
        "anti_patterns": "@app.on_event('startup') or @app.on_event('shutdown') which are deprecated.",
    },
    {
        "topic": "fastapi.dependency_injection",
        "category": "fastapi",
        "version": "FastAPI 0.115+",
        "signature": "Annotated[T, Depends(dependency)]",
        "canonical_code": """from typing import Annotated
from fastapi import Depends, APIRouter
from pydantic import BaseModel

class UserDTO(BaseModel):
    id: str
    username: str

async def get_current_user() -> UserDTO:
    return UserDTO(id="u1", username="admin")

router = APIRouter()

@router.get("/profile")
async def read_profile(user: Annotated[UserDTO, Depends(get_current_user)]) -> UserDTO:
    return user""",
        "docstring": "FastAPI modern typing with typing.Annotated and Depends for clean testable dependency injection.",
        "anti_patterns": "user: UserDTO = Depends(...) without Annotated typing.",
    },
    {
        "topic": "python.modern_typing",
        "category": "python",
        "version": "Python 3.12+",
        "signature": "def process_items[T](items: list[T]) -> list[T]: ...",
        "canonical_code": """from dataclasses import dataclass
from typing import TypedDict

class ConfigDict(TypedDict):
    host: str
    port: int

@dataclass(slots=True, frozen=True)
class ServiceEndpoint:
    name: str
    url: str

def find_first[T](items: list[T], default: T) -> T:
    return items[0] if items else default""",
        "docstring": "Python 3.12+ modern type syntax with PEP 695 type parameters and slots dataclasses.",
        "anti_patterns": "Typing.List, typing.Dict, typing.Optional from pre-3.9 legacy typing.",
    },
]


def seed_knowledge_database(db: CodingKnowledgeDB) -> int:
    """Inserts all canonical entries into the database."""
    count = 0
    for entry in CANONICAL_ENTRIES:
        db.insert_entry(
            topic=entry["topic"],
            category=entry["category"],
            version=entry["version"],
            signature=entry["signature"],
            canonical_code=entry["canonical_code"],
            docstring=entry["docstring"],
            anti_patterns=entry.get("anti_patterns", ""),
        )
        count += 1
    return count


if __name__ == "__main__":
    database = CodingKnowledgeDB()
    total = seed_knowledge_database(database)
    print(f"Seeded {total} canonical framework entries into CodingKnowledgeDB.")
