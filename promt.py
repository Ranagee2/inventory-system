from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List

from flask import Flask, render_template_string, request

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


@dataclass
class PromptRequest:
    title: str
    language: str
    stack: str
    bug_description: str
    code_files: str
    output_mode: str


BASE_TEMPLATE = r'''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Debugger Prompt Builder</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #f6f8fb; }
    .card { border: 0; border-radius: 1.25rem; box-shadow: 0 10px 30px rgba(0,0,0,.06); }
    .form-control, .form-select, pre { border-radius: 0.9rem; }
    pre { white-space: pre-wrap; word-break: break-word; }
    .small-muted { color: #6c757d; font-size: .92rem; }
    .badge-soft { background: #e9f2ff; color: #2457a6; }
  </style>
</head>
<body>
  <div class="container py-4 py-lg-5">
    <div class="row justify-content-center">
      <div class="col-12 col-xl-10">
        <div class="mb-4 text-center">
          <h1 class="fw-bold mb-2">AI Debugger Prompt Builder</h1>
          <p class="small-muted mb-0">Code paste karo, masla likho apni zuban mein, aur ready-to-use strict prompt lo.</p>
        </div>

        <div class="card p-3 p-lg-4 mb-4">
          <form method="post" action="/generate">
            <div class="row g-3">
              <div class="col-12 col-md-6">
                <label class="form-label">Project Title</label>
                <input type="text" name="title" class="form-control" placeholder="My Flask App" value="{{ form.title or '' }}">
              </div>
              <div class="col-12 col-md-3">
                <label class="form-label">Language</label>
                <input type="text" name="language" class="form-control" placeholder="Roman Urdu" value="{{ form.language or 'Roman Urdu' }}">
              </div>
              <div class="col-12 col-md-3">
                <label class="form-label">Output Mode</label>
                <select name="output_mode" class="form-select">
                  <option value="code_only" {% if form.output_mode == 'code_only' %}selected{% endif %}>Code only</option>
                  <option value="full_code_with_minimal_notes" {% if form.output_mode == 'full_code_with_minimal_notes' %}selected{% endif %}>Full code + minimal notes</option>
                </select>
              </div>

              <div class="col-12">
                <label class="form-label">Stack</label>
                <input type="text" name="stack" class="form-control" placeholder="Flask, HTML, Bootstrap" value="{{ form.stack or 'Flask, HTML, Bootstrap' }}">
              </div>

              <div class="col-12">
                <label class="form-label">Masla / Bugs</label>
                <textarea name="bug_description" class="form-control" rows="5" placeholder="sidebar flicker karta hai, data save nahi hota, receipt print align nahi hai">{{ form.bug_description or '' }}</textarea>
              </div>

              <div class="col-12">
                <label class="form-label">Code Files</label>
                <textarea name="code_files" class="form-control" rows="12" placeholder='{
  "app.py": "paste full code here",
  "templates/dashboard.html": "paste full code here"
}'>{{ form.code_files or '' }}</textarea>
                <div class="small-muted mt-2">Har file ko JSON-style text me paste kar do. File name + full code best hota hai.</div>
              </div>

              <div class="col-12 d-flex gap-2 flex-wrap">
                <button type="submit" class="btn btn-primary px-4">Generate Prompt</button>
                <a href="/" class="btn btn-outline-secondary px-4">Reset</a>
              </div>
            </div>
          </form>
        </div>

        {% if generated_prompt %}
        <div class="card p-3 p-lg-4 mb-4">
          <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
            <div>
              <h2 class="h4 fw-bold mb-1">Generated Prompt</h2>
              <div class="small-muted">Copy this and send it to your AI tool.</div>
            </div>
            <span class="badge badge-soft rounded-pill px-3 py-2">Ready to use</span>
          </div>
          <pre class="bg-light p-3 border mb-0">{{ generated_prompt }}</pre>
        </div>
        {% endif %}

        {% if prompt_json %}
        <div class="card p-3 p-lg-4 mb-4">
          <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
            <div>
              <h2 class="h4 fw-bold mb-1">Structured JSON Prompt</h2>
              <div class="small-muted">Optional structured version for automation.</div>
            </div>
          </div>
          <pre class="bg-light p-3 border mb-0">{{ prompt_json }}</pre>
        </div>
        {% endif %}
      </div>
    </div>
  </div>
</body>
</html>
'''


def build_prompt(data: PromptRequest) -> str:
    output_rule = "only final fixed code" if data.output_mode == "code_only" else "full updated code with minimal notes"

    prompt = f"""Tum ek expert full-stack developer aur strict debugger ho.

Language: {data.language}
Stack: {data.stack}
Project: {data.title}

Task:
{data.bug_description}

Files:
{data.code_files}

Rules:
- no explanation
- no bug list
- no extra text
- {output_rule}
- return complete files only
- do not skip anything
- keep original structure unless a fix needs change

Instructions:
1. Read all provided files carefully
2. Identify the exact bug locations
3. Fix the issues
4. Merge fixes into the original code
5. Return the final working version only
"""
    return prompt.strip()


def build_json_prompt(data: PromptRequest) -> str:
    structured = {
        "role": "senior full-stack developer and strict debugger",
        "language": data.language,
        "project": {
            "title": data.title,
            "stack": [x.strip() for x in data.stack.split(",") if x.strip()],
        },
        "task": "fix bugs and return only final working code",
        "bugs": [x.strip() for x in data.bug_description.splitlines() if x.strip()],
        "files": data.code_files,
        "rules": [
            "no explanation",
            "no bug list",
            "no extra text",
            "return complete files only",
            "do not skip anything",
        ],
        "output": {
            "format": "file-wise full code only",
        },
    }
    return json.dumps(structured, indent=2, ensure_ascii=False)


@app.get("/")
def index():
    return render_template_string(BASE_TEMPLATE, form={}, generated_prompt=None, prompt_json=None)


@app.post("/generate")
def generate():
    data = PromptRequest(
        title=request.form.get("title", "My Project").strip() or "My Project",
        language=request.form.get("language", "Roman Urdu").strip() or "Roman Urdu",
        stack=request.form.get("stack", "Flask, HTML, Bootstrap").strip() or "Flask, HTML, Bootstrap",
        bug_description=request.form.get("bug_description", "").strip(),
        code_files=request.form.get("code_files", "").strip(),
        output_mode=request.form.get("output_mode", "code_only").strip() or "code_only",
    )

    generated_prompt = build_prompt(data)
    prompt_json = build_json_prompt(data)

    form = {
        "title": data.title,
        "language": data.language,
        "stack": data.stack,
        "bug_description": data.bug_description,
        "code_files": data.code_files,
        "output_mode": data.output_mode,
    }
    return render_template_string(
        BASE_TEMPLATE,
        form=form,
        generated_prompt=generated_prompt,
        prompt_json=prompt_json,
    )


if __name__ == "__main__":
    app.run(debug=True)
