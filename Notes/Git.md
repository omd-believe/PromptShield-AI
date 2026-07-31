Since you are **leading the project**, I recommend this workflow.

## Team Roles

### 👨‍💻 You (Project Lead / Repository Maintainer)

Responsibilities:

* Create the GitHub repository.
* Protect the `main` branch.
* Review all Pull Requests.
* Merge into `develop`.
* Merge `develop` into `main` after testing.
* Maintain documentation.
* Create releases/tags.

### 👨‍💻 Gaurav

* Work only on the `gaurav` branch.
* Raise Pull Requests to `develop`.

### 👩‍💻 Shruti

* Work only on the `shruti` branch.
* Raise Pull Requests to `develop`.

---

# Branch Strategy

```text
main
│
└── develop
      ├── om
      ├── gaurav
      └── shruti
```

Never commit directly to `main`.

---

# Workflow

### Step 1

You create the repository.

```
PromptShield-AI
```

---

### Step 2

Create branches.

```
main
develop
om
gaurav
shruti
```

---

### Step 3

Everyone clones the repository.

```
git clone ...
```

---

### Step 4

Suppose Gaurav completes the login page.

He commits on:

```
gaurav
```

Then pushes.

```
git push origin gaurav
```

---

### Step 5

He creates a **Pull Request**

```
gaurav

↓

develop
```

---

### Step 6

You review it.

Check:

* Does it compile?
* Any bugs?
* Coding style?
* Naming conventions?
* No unnecessary files?
* No secrets or API keys committed?
* Feature works as expected?

If everything is good:

✅ Approve

↓

Merge

If not:

❌ Request changes

He fixes it.

Creates another commit.

Pushes again.

You review again.

---

### Step 7

After all three branches are merged into `develop`:

```
develop

↓

Testing
```

Run the project.

Test everything.

If everything works:

```
develop

↓

main
```

---

# Example Weekly Workflow

Monday

```
om
```

Add Authentication

Tuesday

```
gaurav
```

Add React UI

Wednesday

```
shruti
```

Add Regex

Thursday

Everyone

↓

Create Pull Requests

↓

Review

↓

Merge into develop

Friday

Test

↓

Merge develop

↓

main

---

# GitHub Settings (Highly Recommended)

Enable:

* ✅ Require Pull Request before merging.
* ✅ Prevent direct pushes to `main`.
* ✅ Require at least **1 approval** before merging (you can be the reviewer).

This prevents accidental changes to your stable branch.

---

# Commit Message Format

Keep commit messages consistent:

```
feat: Add login module

feat: Implement Regex privacy detection

fix: Resolve JWT authentication issue

docs: Update README

test: Add unit tests for compression module

refactor: Improve preprocessing pipeline

style: Format frontend components
```

---

# Milestones

Create GitHub Milestones like:

```
Milestone 1
Synopsis Approved

Milestone 2
Frontend Completed

Milestone 3
Backend Completed

Milestone 4
AI Module Completed

Milestone 5
Integration

Milestone 6
Testing

Milestone 7
Deployment

Milestone 8
Final Report
```

---

## My suggestion

Instead of thinking of this as just a college repository, treat it like a **real software company**.

* **You** → Tech Lead / Maintainer
* **Gaurav** → Frontend or Backend Developer
* **Shruti** → AI/ML Developer (or whichever module you assign)

Use:

* **GitHub Issues** for tasks.
* **Projects (Kanban Board)** to track progress (`To Do → In Progress → Done`).
* **Pull Requests** for every feature.
* **Protected `main` branch** with no direct commits.

By the time the project is finished, you'll not only have a strong AI application but also experience with a professional Git workflow that mirrors how many software teams collaborate.
