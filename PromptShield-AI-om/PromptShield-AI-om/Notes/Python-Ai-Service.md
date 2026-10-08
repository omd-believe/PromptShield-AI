
## Overall Architecture

```text
React Frontend
        │
        ▼
Spring Boot Backend
        │ REST API
        ▼
Python FastAPI AI Service
        │
        ├── Preprocessing
        ├── Privacy Detection
        ├── Rule-Based Pre-Compression
        ├── Prompt Compression Model
        ├── Grammar Correction
        ├── Semantic Evaluation
        │
        ▼
Optimized Prompt + Reports
```

---

# Phase 1 — Learn the Required Python Stack (1–2 weeks)

You don't need to master all of AI. Learn only what's needed.

### Core Python

* Functions
* Classes
* File handling
* Virtual environments
* pip

### FastAPI

* Create REST APIs
* Request/Response models
* Dependency Injection
* File upload
* Run with Uvicorn

### NLP Basics

* Tokenization
* Stop words
* Lemmatization
* Sentence splitting

Libraries:

* spaCy
* NLTK

---

# Phase 2 — Build the AI Service Skeleton

Structure:

```text
ai-service/
│
├── app/
│   ├── api/
│   │   └── optimize.py
│   │
│   ├── services/
│   │   ├── preprocessing.py
│   │   ├── privacy.py
│   │   ├── compression.py
│   │   ├── grammar.py
│   │   └── semantic.py
│   │
│   ├── models/
│   │   ├── request.py
│   │   └── response.py
│   │
│   ├── utils/
│   │
│   └── main.py
│
├── training/
│
├── datasets/
│
├── trained_models/
│
├── tests/
│
├── requirements.txt
│
└── Dockerfile
```

---

# Phase 3 — Preprocessing

Input:

```text
Hello ChatGPT,

Can you please explain Java Streams?
```

Output:

```text
Can you explain Java Streams?
```

Tasks:

* Normalize spaces
* Remove greetings
* Remove repeated punctuation
* Sentence segmentation

---

# Phase 4 — Privacy Detection

Modules:

## Regex

Detect:

* Email
* Phone
* PAN
* Aadhaar
* API Keys
* Credit card numbers
* URLs (optional)

Replace:

```text
My email is omd@gmail.com
```

↓

```text
My email is [EMAIL]
```

---

## NER

Use spaCy.

Detect:

* Person
* Organization
* Location

Example

```text
I am OMD from Walchand College.
```

↓

```text
I am [PERSON] from [ORG].
```

---

# Phase 5 — Rule-Based Compression

Remove:

* Greetings
* Thank you
* Extra words
* Duplicate phrases

Example

```text
Please can you kindly explain...
```

↓

```text
Explain...
```

---

# Phase 6 — ML Prompt Compression ⭐

This is your research contribution.

Model options:

* FLAN-T5 Small ✅
* T5 Small
* Gemma 3 1B (if resources allow)

Training dataset:

```
Verbose Prompt
↓

Optimized Prompt
```

Example

```
Could you kindly explain Java Streams with examples?

↓

Explain Java Streams with examples.
```

Tasks:

* Fine-tune model
* Save trained weights
* Load model in FastAPI
* Run inference

---

# Phase 7 — Grammar Correction

Options:

* LanguageTool
* T5-based grammar model

Purpose:

Make compressed prompts grammatically correct.

---

# Phase 8 — Semantic Evaluation

Compare:

Original Prompt

vs

Optimized Prompt

Use:

Sentence Transformers

Example:

```
Similarity

0.96
```

If similarity < threshold:

Reject optimization.

---

# Phase 9 — Token Analysis

Calculate

Original Tokens

↓

Optimized Tokens

↓

Reduction %

Example

```
Original : 120

Optimized : 68

Reduction : 43%
```

---

# Phase 10 — AI REST API

Example endpoint

```
POST /optimize
```

Request

```json
{
  "prompt": "Please kindly explain Java Streams."
}
```

Response

```json
{
  "originalPrompt": "...",
  "optimizedPrompt": "...",
  "privacyReport": {
    "emails": 1,
    "phones": 0,
    "persons": 1
  },
  "similarity": 0.95,
  "originalTokens": 120,
  "optimizedTokens": 74,
  "tokenReduction": 38
}
```

Spring Boot simply calls this endpoint and returns the result to React.

---

# Phase 11 — Model Training

Create:

```
datasets/

raw/

cleaned/

training/

validation/

test/
```

Then:

* Clean dataset
* Fine-tune
* Evaluate
* Save model

---

# Phase 12 — Docker

Create one Docker image for the AI service.

Later:

```
React

↓

Spring Boot

↓

FastAPI

↓

PostgreSQL
```

can run together with Docker Compose.

---

# Learning Order

1. Python refresher
2. FastAPI
3. spaCy + Regex
4. Hugging Face Transformers
5. Sentence Transformers
6. Fine-tuning T5/FLAN-T5
7. Docker
8. Spring Boot ↔ FastAPI integration

## Final Recommendation

Don't jump straight to training the model. Build the service incrementally:

* **Milestone 1:** FastAPI endpoint returning a dummy response.
* **Milestone 2:** Add preprocessing and privacy detection.
* **Milestone 3:** Add rule-based compression.
* **Milestone 4:** Integrate a pre-trained compression model.
* **Milestone 5:** Fine-tune your own model and replace the pre-trained one.
* **Milestone 6:** Add grammar correction, semantic evaluation, and token analytics.

This incremental approach gives you a working system early, while leaving room to improve the AI component as your machine learning knowledge grows during the semester.
