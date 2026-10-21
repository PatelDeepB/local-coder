"""Curated repository of clean architecture patterns, templates, and production idioms."""

from dataclasses import dataclass, field
import re
from typing import Optional


@dataclass(frozen=True)
class PatternFileBlueprint:
    """Blueprint for a single file in a clean architecture pattern."""

    file_path: str
    purpose: str
    boilerplate_skeleton: str
    key_requirements: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArchitecturalPattern:
    """A complete verified architectural template."""

    name: str
    domain: str
    keywords: tuple[str, ...]
    description: str
    files: tuple[PatternFileBlueprint, ...]


REACT_DASHBOARD_PATTERN = ArchitecturalPattern(
    name="Modern React Dashboard",
    domain="frontend",
    keywords=("react", "dashboard", "frontend", "ui", "web app", "spa", "counter"),
    description="Production-grade React 18 single-page application with modern hooks and CSS variables.",
    files=(
        PatternFileBlueprint(
            file_path="package.json",
            purpose="Project dependencies and execution scripts",
            boilerplate_skeleton="""{
  "name": "react-app",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  }
}""",
            key_requirements=("Valid JSON", "react and react-dom 18+", "start and build scripts"),
        ),
        PatternFileBlueprint(
            file_path="public/index.html",
            purpose="HTML5 entry point with responsive viewport",
            boilerplate_skeleton="""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Application Dashboard</title>
  <link rel="stylesheet" href="./styles.css">
</head>
<body>
  <div id="root"></div>
</body>
</html>""",
            key_requirements=("Mobile viewport tag", "root div mount point", "semantic HTML"),
        ),
        PatternFileBlueprint(
            file_path="src/styles.css",
            purpose="CSS variables and responsive layout system",
            boilerplate_skeleton=""":root {
  --primary: #0284c7;
  --primary-hover: #0369a1;
  --bg-color: #f8fafc;
  --card-bg: #ffffff;
  --text-primary: #0f172a;
  --text-muted: #64748b;
  --border-color: #e2e8f0;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg-color); color: var(--text-primary); }
.container { max-width: 1200px; margin: 0 auto; padding: 24px 16px; }""",
            key_requirements=("CSS custom properties", "CSS reset", "Responsive container"),
        ),
        PatternFileBlueprint(
            file_path="src/App.jsx",
            purpose="Root application component with state management",
            boilerplate_skeleton="""import React, { useState } from 'react';

export default function App() {
  const [items, setItems] = useState([]);
  const [inputVal, setInputVal] = useState('');

  const handleAdd = () => {
    if (!inputVal.trim()) return;
    setItems(prev => [...prev, { id: Date.now(), text: inputVal.trim(), completed: false }]);
    setInputVal('');
  };

  const handleToggle = (id) => {
    setItems(prev => prev.map(item => item.id === id ? { ...item, completed: !item.completed } : item));
  };

  const handleDelete = (id) => {
    setItems(prev => prev.filter(item => item.id !== id));
  };

  return (
    <div className="container">
      <header className="header"><h1>Application Dashboard</h1></header>
      <main>
        <section className="input-card">
          <input value={inputVal} onChange={e => setInputVal(e.target.value)} placeholder="Enter item..." />
          <button onClick={handleAdd}>Add</button>
        </section>
        <ul className="item-list">
          {items.map(item => (
            <li key={item.id} className={item.completed ? 'completed' : ''}>
              <span onClick={() => handleToggle(item.id)}>{item.text}</span>
              <button onClick={() => handleDelete(item.id)}>Delete</button>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}""",
            key_requirements=("Self-contained state", "Input validation", "No placeholder stubs"),
        ),
    ),
)

FASTAPI_REST_PATTERN = ArchitecturalPattern(
    name="FastAPI Clean REST Service",
    domain="backend",
    keywords=("fastapi", "rest", "api", "backend", "python api", "crud", "endpoint"),
    description="Layered Python REST service with Pydantic validation and health checks.",
    files=(
        PatternFileBlueprint(
            file_path="requirements.txt",
            purpose="Python dependencies",
            boilerplate_skeleton="fastapi>=0.100.0\nuvicorn>=0.22.0\npydantic>=2.0.0\npytest>=7.0.0\nhttpx>=0.24.0\n",
            key_requirements=("fastapi", "pydantic", "uvicorn"),
        ),
        PatternFileBlueprint(
            file_path="schemas.py",
            purpose="Pydantic models and request/response contracts",
            boilerplate_skeleton="""from pydantic import BaseModel, Field
from typing import Optional

class ItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    is_active: bool = True""",
            key_requirements=("Pydantic models", "Field validations", "Separate create/response types"),
        ),
        PatternFileBlueprint(
            file_path="main.py",
            purpose="FastAPI application router and service endpoints",
            boilerplate_skeleton="""from fastapi import FastAPI, HTTPException, status
from typing import list
from schemas import ItemCreate, ItemResponse

app = FastAPI(title="Production Service API", version="1.0.0")

_db: dict[int, dict] = {}
_id_counter = 0

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "api"}

@app.get("/api/v1/items", response_model=list[ItemResponse])
def list_items() -> list[dict]:
    return list(_db.values())

@app.post("/api/v1/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate) -> dict:
    global _id_counter
    _id_counter += 1
    new_item = {"id": _id_counter, "title": payload.title, "description": payload.description, "is_active": True}
    _db[_id_counter] = new_item
    return new_item""",
            key_requirements=("/health endpoint", "/api/v1/ versioned routes", "HTTP status codes"),
        ),
        PatternFileBlueprint(
            file_path="test_main.py",
            purpose="Pytest suite verifying endpoints",
            boilerplate_skeleton="""from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_create_and_list_item() -> None:
    resp = client.post("/api/v1/items", json={"title": "Test Item", "description": "Demo"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] > 0
    assert data["title"] == "Test Item"

    list_resp = client.get("/api/v1/items")
    assert list_resp.status_code == 200
    assert any(item["title"] == "Test Item" for item in list_resp.json())""",
            key_requirements=("Health test", "Create item test", "List items test"),
        ),
    ),
)


DJANGO_CRUD_PATTERN = ArchitecturalPattern(
    name="Django Production CRUD Application",
    domain="backend_fullstack",
    keywords=("django", "django app", "django task", "models.py", "views.py"),
    description="Production-grade Django MVC application with ModelForm, clean settings, and test cases.",
    files=(
        PatternFileBlueprint(
            file_path="manage.py",
            purpose="Django administrative entry point",
            boilerplate_skeleton="""#!/usr/bin/env python
import os, sys
def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_project.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
if __name__ == "__main__":
    main()""",
            key_requirements=("DJANGO_SETTINGS_MODULE", "execute_from_command_line"),
        ),
        PatternFileBlueprint(
            file_path="core_project/settings.py",
            purpose="Django project settings",
            boilerplate_skeleton="""from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "django-insecure-local-coder-dev-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "tasks",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "core_project.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.debug", "django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "core_project.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
LANGUAGE_CODE, TIME_ZONE, USE_TZ = "en-us", "UTC", True
STATIC_URL, DEFAULT_AUTO_FIELD = "static/", "django.db.models.BigAutoField" """,
            key_requirements=("INSTALLED_APPS with tasks", "ROOT_URLCONF", "DATABASES sqlite3"),
        ),
        PatternFileBlueprint(
            file_path="core_project/urls.py",
            purpose="Project URL routing",
            boilerplate_skeleton="""from django.contrib import admin
from django.urls import include, path
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tasks.urls")),
]""",
            key_requirements=("include tasks.urls", "admin site"),
        ),
        PatternFileBlueprint(
            file_path="tasks/models.py",
            purpose="Task ORM Model",
            boilerplate_skeleton="""from django.db import models
class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=[("TODO", "To Do"), ("DONE", "Done")], default="TODO")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.title} [{self.status}]" """,
            key_requirements=("models.Model", "CharField title", "choices for status"),
        ),
        PatternFileBlueprint(
            file_path="tasks/forms.py",
            purpose="Django ModelForm",
            boilerplate_skeleton="""from django import forms
from tasks.models import Task
class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "status"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }""",
            key_requirements=("forms.ModelForm", "Meta model = Task", "fields list"),
        ),
        PatternFileBlueprint(
            file_path="tasks/views.py",
            purpose="Task view controllers with all required imports",
            boilerplate_skeleton="""from django.shortcuts import render, redirect, get_object_or_404
from tasks.models import Task
from tasks.forms import TaskForm

def task_list(request):
    tasks = Task.objects.all().order_by("-created_at")
    return render(request, "tasks/task_list.html", {"tasks": tasks})

def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("tasks:task_list")
    else:
        form = TaskForm()
    return render(request, "tasks/task_form.html", {"form": form})

def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        task.delete()
    return redirect("tasks:task_list")""",
            key_requirements=("from django.shortcuts import render, redirect, get_object_or_404", "from tasks.models import Task", "from tasks.forms import TaskForm"),
        ),
        PatternFileBlueprint(
            file_path="tasks/urls.py",
            purpose="Task application URLs",
            boilerplate_skeleton="""from django.urls import path
from tasks import views
app_name = "tasks"
urlpatterns = [
    path("", views.task_list, name="task_list"),
    path("create/", views.task_create, name="task_create"),
    path("<int:pk>/delete/", views.task_delete, name="task_delete"),
]""",
            key_requirements=("app_name = 'tasks'", "views.task_list", "views.task_create"),
        ),
        PatternFileBlueprint(
            file_path="tasks/tests.py",
            purpose="Django TestCase suite",
            boilerplate_skeleton="""from django.test import TestCase, Client
from django.urls import reverse
from tasks.models import Task

class TaskTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.task = Task.objects.create(title="Test Task")

    def test_task_list_view(self):
        resp = self.client.get(reverse("tasks:task_list"))
        self.assertEqual(resp.status_code, 200)

    def test_task_create_view(self):
        resp = self.client.post(reverse("tasks:task_create"), {"title": "New Task", "status": "TODO"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Task.objects.filter(title="New Task").exists())""",
            key_requirements=("TestCase", "reverse tasks:task_list", "assertEqual status_code 200 and 302"),
        ),
        PatternFileBlueprint(
            file_path="templates/tasks/task_list.html",
            purpose="HTML task list template",
            boilerplate_skeleton="""<!DOCTYPE html>
<html>
<head><title>Task Manager</title></head>
<body>
  <h1>Tasks</h1>
  <a href="{% url 'tasks:task_create' %}">+ New Task</a>
  <ul>
    {% for task in tasks %}
      <li>{{ task.title }} [{{ task.status }}]</li>
    {% empty %}
      <li>No tasks yet.</li>
    {% endfor %}
  </ul>
</body>
</html>""",
            key_requirements=("HTML5", "url tasks:task_create", "for task in tasks loop"),
        ),
    ),
)


class CleanPatternBank:
    """Provides instant architectural skeletons and clean-code guidance."""

    def __init__(self) -> None:
        self._patterns = [REACT_DASHBOARD_PATTERN, FASTAPI_REST_PATTERN, DJANGO_CRUD_PATTERN]

    def match_pattern(self, goal: str) -> Optional[ArchitecturalPattern]:
        """Finds matching architectural pattern for user goal."""
        lower_goal = goal.lower()
        best_match: Optional[ArchitecturalPattern] = None
        max_hits = 0

        for pattern in self._patterns:
            hits = sum(1 for kw in pattern.keywords if kw in lower_goal)
            if hits > max_hits:
                max_hits = hits
                best_match = pattern

        return best_match if max_hits > 0 else None

    def get_file_blueprint(
        self, pattern: ArchitecturalPattern, file_path: str
    ) -> Optional[PatternFileBlueprint]:
        """Finds specific file blueprint within matched pattern."""
        norm = file_path.replace("\\", "/").lower()
        for fb in pattern.files:
            if fb.file_path.lower() == norm or norm.endswith(fb.file_path.lower()):
                return fb
        return None

    def build_guidance_prompt(self, goal: str, target_file: str) -> str:
        """Injects clean architectural skeleton into prompt context."""
        pattern = self.match_pattern(goal)
        if not pattern:
            return ""

        blueprint = self.get_file_blueprint(pattern, target_file)
        if not blueprint:
            return f"Architectural Style: {pattern.name}\nDomain: {pattern.domain}\n"

        reqs = ", ".join(blueprint.key_requirements)
        return (
            f"=== VERIFIED ARCHITECTURAL PATTERN: {pattern.name} ===\n"
            f"Target: {blueprint.file_path}\n"
            f"Key Requirements: {reqs}\n"
            f"Production Skeleton (Use as reference for clean syntax and structure):\n"
            f"```\n{blueprint.boilerplate_skeleton}\n```\n"
        )
