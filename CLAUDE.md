# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ArguPaper is a multi-agent research cognition system providing paper retrieval → understanding → evidence analysis → adversarial critique → consensus generation. It simulates a research team's thinking process, not just a summarization tool.

## Build/Test Commands

No code exists yet. When implemented, this will likely be a Python project with:
- Virtual environment management (uv, poetry, or pipenv)
- Linting: ruff or flake8
- Type checking: mypy
- Testing: pytest

## Architecture

### Agent Layer Design (5 layers)

1. **Analysis Layer** - Method principle breakdown, technical route analysis, structured report output
2. **Evidence Layer** - Experiment extraction (datasets, sample size, metrics), method condition analysis, result credibility analysis
3. **Critique Layer** - Evidence consistency check (claim↔experiment alignment), method validity, experimental sufficiency
4. **Debate Layer** - Multi-agent adversarial: Support Agent, Skeptic Agent, Comparator Agent, Evidence Agent
5. **Judge Layer** - Consensus/disagreement aggregation with supporting evidence

### Iteration Flow
```
Analysis → Evidence Extraction → Debate (multi-round) → Search-in-loop (supplement evidence) → Judge
```

### Core Modules

- **Paper Retrieval Module** - Query expansion, iterative search, search-in-the-loop, quality ranking
- **Paper Skimming Module** - Structured abstract generation, lightweight Q&A
- **Deep Analysis Module** - Multi-agent critique and adversarial debate
- **Global Paper Memory** - Structured long-term knowledge storage (Level 1: title, Level 2: abstract, Level 3: full markdown)
- **PDF → Markdown Converter** - PDF stored locally for traceability, markdown for agent parsing

### Dynamic Search Engine

Coupled with all agents:
- Analysis stage → retrieve baselines
- Debate stage → retrieve counterexamples
- Critique stage → retrieve evidence

### Output Structure

```
1. Research Overview
2. Method Comparison
3. Evidence Table
4. Debate Summary
5. Contradictions
6. Weakness Analysis
7. Consensus vs Disagreement
8. Confidence Score
```

### Priority

- **P0 (MVP)**: Retrieval + Search-in-loop, Skimming, Analysis + Evidence Layer, Simple Debate (2 agents), PDF parsing, basic memory
- **P1**: Full Debate system, Judge layer, confidence system, dynamic search engine
- **P2**: Knowledge graph, multi-round optimization, citation expansion

## Key Differences from Traditional Systems

| Dimension | Traditional | ArguPaper |
|-----------|-------------|-----------|
| Critique | Surface summarization | Evidence-driven critique |
| Reasoning | Single-path | Multi-agent adversarial |
| Retrieval | Static | Search-in-the-loop |
| Output | Text | Decision + confidence score |
