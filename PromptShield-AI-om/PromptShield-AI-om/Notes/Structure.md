I like this idea. If you organize the project well from **Day 1**, your development, Git workflow, documentation, and final report will all be much easier.

One thing I'd change is your branch strategy:

❌ Don't keep both `main` and `master`. Modern Git uses **`main`** as the default branch, and having both `main` and `master` usually causes confusion.

Instead, use:

```text
main        → Stable production branch
develop     → Integration branch
om          → Your feature branch
gaurav      → Gaurav's feature branch
shruti      → Shruti's feature branch
```

Workflow:

```text
om --------\
            \
gaurav ----- > develop -------> main
            /
shruti -----/
```

Everyone works on their own branch, merges into **develop** after review/testing, and only stable versions go into **main**.

---

# Suggested Folder Structure

```text
Mini-Project/
│
├── PromptShield-AI/
│
│   ├── docs/
│   │
│   │   ├── Synopsis/
│   │   ├── Research-Papers/
│   │   ├── UML/
│   │   ├── Architecture/
│   │   ├── Meeting-Notes/
│   │   ├── SRS/
│   │   ├── API-Documentation/
│   │   ├── Weekly-Progress/
│   │   ├── Dataset/
│   │   └── Final-Report/
│   │
│   ├── code/
│   │
│   │   ├── frontend/
│   │   │      (React)
│   │   │
│   │   ├── backend/
│   │   │      (Spring Boot)
│   │   │
│   │   ├── ai-service/
│   │   │      (FastAPI)
│   │   │
│   │   ├── model/
│   │   │      (trained models)
│   │   │
│   │   ├── datasets/
│   │   │
│   │   ├── scripts/
│   │   │
│   │   ├── docker/
│   │   │
│   │   ├── tests/
│   │   │
│   │   └── README.md
│   │
│   ├── assets/
│   │
│   │   ├── Images/
│   │   ├── Logos/
│   │   ├── UI/
│   │   ├── Screenshots/
│   │   └── Demo/
│   │
│   ├── presentations/
│   │
│   │   ├── PPT-1
│   │   ├── PPT-2
│   │   └── Final-PPT
│   │
│   ├── references/
│   │
│   │   ├── Blogs
│   │   ├── Papers
│   │   ├── APIs
│   │   └── Books
│   │
│   ├── .gitignore
│   ├── LICENSE
│   └── README.md
│
└── Personal-Notes/
```

---

# Inside `docs/`

```text
docs/

01_Project_Idea.md

02_Problem_Statement.md

03_Abstract.md

04_Methodology.md

05_UML/

06_API/

07_Model/

08_Testing/

09_Deployment/

10_Final_Report/
```

---

# AI Service Structure

```text
ai-service/

app.py

requirements.txt

models/

preprocessing.py

privacy_detector.py

regex_detector.py

ner_detector.py

rule_engine.py

prompt_compressor.py

grammar_corrector.py

semantic_evaluator.py

utils.py
```

---

# Backend Structure

```text
backend/

src/

controller/

service/

repository/

entity/

dto/

config/

security/

exception/

util/
```

---

# Frontend

```text
frontend/

src/

components/

pages/

services/

hooks/

assets/

utils/

contexts/
```

---

# Dataset Folder

```text
datasets/

raw/

cleaned/

training/

validation/

testing/

README.md
```

---

# Weekly Progress

```text
Week-1

Week-2

Week-3

...

Week-16
```

Each week's folder can contain:

* What was completed
* Issues faced
* Screenshots
* Next week's plan

---

# README Structure

```text
Project Overview

Architecture

Tech Stack

Installation

Folder Structure

API

Contributors

License
```

---

# Git Workflow

```text
main
│
└── develop
      │
      ├── om
      ├── gaurav
      └── shruti
```

* Work only on your personal branch.
* Merge into `develop` after testing.
* Merge `develop` into `main` only when the feature is stable and reviewed.

## One extra suggestion

Since this project will span several months, create a **`journal/`** (or `daily-log/`) folder where you record:

* Daily progress
* Decisions made
* Problems encountered
* Solutions tried
* Useful links
* Future ideas

This becomes incredibly useful when writing the final report, preparing presentations, and answering viva questions because you'll have a complete development history instead of trying to remember everything at the end.
