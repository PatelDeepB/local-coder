"""Web and REST architectural patterns including React and FastAPI."""

from local_coder.knowledge.pattern_models import ArchitecturalPattern, PatternFileBlueprint

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
              <button onClick={handleDelete}>Delete</button>
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
from typing import List, Optional
from schemas import ItemCreate, ItemResponse

app = FastAPI(title="Production Service API", version="1.0.0")

_db: dict[int, dict] = {}
_id_counter = 0

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "api"}

@app.get("/api/v1/items", response_model=List[ItemResponse])
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
