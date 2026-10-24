"""Backend and CLI architectural patterns including Django and statistical tools."""

from local_coder.knowledge.pattern_models import ArchitecturalPattern, PatternFileBlueprint

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

CLI_DATA_ANALYSIS_PATTERN = ArchitecturalPattern(
    name="CLI Data Analysis Suite",
    domain="data_tools",
    keywords=("cli", "data analysis", "analyzer", "statistics", "csv", "summary"),
    description="High-performance numerical analysis CLI with pure-logic algorithms and pytest coverage.",
    files=(
        PatternFileBlueprint(
            file_path="requirements.txt",
            purpose="Tool dependencies",
            boilerplate_skeleton="pytest>=7.0.0\n",
            key_requirements=("pytest",),
        ),
        PatternFileBlueprint(
            file_path="analyzer.py",
            purpose="Core statistical calculation algorithms",
            boilerplate_skeleton="""import math
from typing import Dict, List, Optional

def compute_summary_statistics(numbers: List[float]) -> Dict[str, float]:
    \"\"\"Calculates count, mean, median, standard deviation, min, and max.\"\"\"
    if not numbers:
        return {"count": 0.0, "mean": 0.0, "median": 0.0, "std_dev": 0.0, "min": 0.0, "max": 0.0}
    
    n = len(numbers)
    s = sum(numbers)
    mean = s / n
    sorted_vals = sorted(numbers)
    
    if n % 2 == 1:
        median = sorted_vals[n // 2]
    else:
        median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
        
    variance = sum((x - mean) ** 2 for x in numbers) / n if n > 0 else 0.0
    std_dev = math.sqrt(variance)
    
    return {
        "count": float(n),
        "mean": mean,
        "median": median,
        "std_dev": std_dev,
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
    }

def detect_anomalies(numbers: List[float], threshold_std: float = 2.0) -> List[float]:
    \"\"\"Identifies values further than threshold standard deviations from mean.\"\"\"
    if len(numbers) < 3:
        return []
    stats = compute_summary_statistics(numbers)
    mean, std = stats["mean"], stats["std_dev"]
    if std == 0.0:
        return []
    return [x for x in numbers if abs(x - mean) > threshold_std * std]""",
            key_requirements=("compute_summary_statistics", "detect_anomalies", "pure math calculations"),
        ),
        PatternFileBlueprint(
            file_path="cli.py",
            purpose="Command-line interface entry point",
            boilerplate_skeleton="""import argparse
import sys
from analyzer import compute_summary_statistics, detect_anomalies

def main(args: list = None) -> int:
    parser = argparse.ArgumentParser(description="High-Performance Data Analyzer")
    parser.add_argument("numbers", nargs="+", type=float, help="Series of numbers to analyze")
    parser.add_argument("--anomalies", action="store_true", help="Flag anomalous values")
    
    parsed = parser.parse_args(args)
    stats = compute_summary_statistics(parsed.numbers)
    
    print("=== SUMMARY STATISTICS ===")
    for k, v in stats.items():
        print(f"  {k}: {v:.2f}")
        
    if parsed.anomalies:
        anomalies = detect_anomalies(parsed.numbers)
        print(f"\\nDetected Anomalies (threshold=2.0): {anomalies}")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())""",
            key_requirements=("argparse", "calls analyzer", "returns exit code"),
        ),
        PatternFileBlueprint(
            file_path="test_analyzer.py",
            purpose="Unit test suite for analyzer",
            boilerplate_skeleton="""from analyzer import compute_summary_statistics, detect_anomalies

def test_should_compute_exact_statistics_for_odd_series():
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = compute_summary_statistics(data)
    assert stats["count"] == 5.0
    assert stats["mean"] == 3.0
    assert stats["median"] == 3.0
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0

def test_should_detect_outliers():
    data = [10.0, 10.1, 9.9, 10.0, 10.2, 100.0]
    anomalies = detect_anomalies(data)
    assert 100.0 in anomalies""",
            key_requirements=("test odd series", "test detect outliers"),
        ),
    ),
)
