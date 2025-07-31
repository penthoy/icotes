# Agent Code Audit Instructions

## 1. Overview

This document provides instructions for an AI agent to perform a code audit on the `ilaborcode` repository. The goal is to identify areas for improvement in code quality, security, performance, and documentation.

**Your Task**: Follow the guidelines below to audit the section specified in the `Audit Focus` section. Provide a clear, concise report with actionable recommendations.

---

## 2. Audit Focus

**Instructions for Human**: Specify the exact file or directory to be audited. The agent will only focus on this target.

*   **Current Target**: `[Specify file or directory here, e.g., backend/icpy/services/terminal_service.py]`

---

## 3. General Audit Guidelines

When auditing, focus on the following key areas:

-   **Code Quality & Readability**: Is the code clean, well-structured, and easy to understand? Check for overly complex functions or modules.
-   **Security Vulnerabilities**: Are there any potential security risks, such as injection vulnerabilities, improper error handling, or exposed secrets?
-   **Performance**: Are there any performance bottlenecks, such as inefficient algorithms, unnecessary computations, or blocking I/O calls in async code?
-   **Documentation & Comments**: Are there Google-style docstrings for all public modules, classes, and functions? Is the documentation accurate and helpful?
-   **Error Handling**: Is error handling robust? Does it use specific exception types and provide meaningful error messages?
-   **Adherence to Standards**: Does the code follow established project conventions and best practices (e.g., PEP 8 for Python, standard React hooks rules)?

---

## 4. Backend Audit Checklist (`/backend/icpy`)

When the audit target is within the backend, use this checklist:

-   [ ] **Correctness**: Does the code function as described in the project's design documents (`icpy_plan.md`)?
-   [ ] **Docstrings**: Verify all public methods have complete and accurate Google-style docstrings.
-   [ ] **Async Usage**: Ensure `async`/`await` is used correctly. Look for blocking calls that could freeze the event loop.
-   [ ] **Modularity**: Are services well-defined and loosely coupled? Is communication handled correctly through the message broker?
-   [ ] **Dependencies**: Are there any unused or unnecessary third-party libraries?
-   [ ] **Configuration**: Are configuration values handled safely? Avoid hardcoded secrets.
-   [ ] **Test Coverage**: Does the corresponding test file (e.g., `tests/icpy/test_...`) provide adequate coverage for the feature?

---

## 5. Frontend Audit Checklist (`/src`)

When the audit target is within the frontend, use this checklist:

-   [ ] **Component Structure**: Are components modular, reusable, and follow the single responsibility principle?
-   [ ] **State Management**: Is state managed efficiently? Look for unnecessary re-renders caused by improper state updates or prop drilling.
-   [ ] **React Hooks**: Are React hooks (`useState`, `useEffect`, `useCallback`, etc.) used correctly and according to best practices?
-   [ ] **Props & Types**: Are component props clearly defined with TypeScript types?
-   [ ] **API/WebSocket Communication**: Is communication with the backend handled in a clean, centralized way (e.g., through services)? Is loading and error state handled gracefully in the UI?
-   [ ] **Accessibility (a11y)**: Does the UI use semantic HTML? Is it navigable via keyboard? Are ARIA attributes used where necessary?
-   [ ] **Styling**: Is the styling consistent and implemented according to the ICUI design system principles?

---

## 6. Reporting Format

Structure your audit report as follows:

1.  **Summary**: A brief, high-level overview of your findings.
2.  **Issues & Recommendations**: A list of specific issues found, categorized by severity (Critical, High, Medium, Low).
3.  **Code Snippets**: For each issue, provide a code snippet demonstrating the problem and a suggested fix.
