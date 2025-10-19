### **Refactoring Directive: Correcting GitHub Fetch Errors in `llms.txt` Generator**

**1.0 Executive Summary**

The `llms.txt` generator is currently failing to build the `mlflow-llms-full.txt` file, citing `403 Forbidden` errors on all GitHub API requests. This failure stems from a design flaw where the "private-aware" build process unconditionally uses a complex, authenticated API-fetching method that is unnecessary and failing for public repositories. The simpler, direct-linking method used for the `dspy` repository works correctly.

This directive mandates a refactor of the generator's orchestration logic to use the appropriate fetching strategy based on repository visibility.

**2.0 Problem Description**

Analysis of the generated artifacts shows a critical discrepancy:
*   **`dspy-llms.txt` & `mlflow-llms.txt` (Simplified):** Generation is successful. These files use direct links to `raw.githubusercontent.com`.
*   **`mlflow-llms-full.txt` (Full Build):** Generation fails. This file shows `[fetch-error]` for every file, indicating that authenticated calls to `api.github.com` are being denied.

The root cause is not that the `mlflow/mlflow` repository is private (it is public), but that the generator's "full build" mode incorrectly uses a fragile, authentication-dependent process for all cases.

**3.0 Root Cause Analysis**

The generator employs two distinct methods for fetching file content:

*   **Method A: Authenticated API Fetching.** This complex method, located in `src/lmstudiotxt_generator/github.py`, is designed for private repositories. It is the source of the `403 Forbidden` errors, likely due to an invalid, expired, or insufficiently scoped API token.
*   **Method B: Direct URL Generation.** This simple method generates public `raw.githubusercontent.com` links. It is robust for public repositories and is used by the successful build processes.

The core design flaw is in the orchestration logic, which defaults to using Method A for the "full build" without first checking if the repository is public.

**4.0 Corrective Actions**

To resolve this issue, the following refactoring is required:

**4.1 Directive 1: Implement Conditional Fetching Logic**

*   **File to Modify:** `src/lmstudiotxt_generator/pipeline.py` (or `src/lmstudiotxt_generator/full_builder.py`).
*   **Function to Refactor:** The primary orchestration function responsible for the "full build" process (e.g., `build_full_output`, `process_repository`).
*   **Action:** Modify this function to be strategy-aware. Before fetching files, it **must** determine if the target repository is public.
    *   If the repository is **public**, the function **must** use the simple, direct URL generation (Method B).
    *   If the repository is **private**, and only then, should it use the authenticated API fetching (Method A).

**4.2 Directive 2: Improve Error Handling (Recommended)**

*   **File to Modify:** `src/lmstudiotxt_generator/github.py`.
*   **Function to Refactor:** The function that makes the authenticated API call (e.g., `get_file_content_authenticated`).
*   **Action:** While the primary fix is in the orchestration logic, this function should be enhanced to provide more descriptive error messages upon receiving a `403` status code. The error should suggest checking the validity, expiration, and permission scopes of the GitHub token to aid future debugging.

**5.0 Expected Outcome**

Upon completion of this refactoring:
1.  The `llms.txt` generator will successfully build documentation for public repositories like `mlflow/mlflow` without any `[fetch-error]` messages.
2.  The system will be more robust, reserving the complex and fragile authenticated API calls only for private repositories where they are strictly necessary.
3.  Future authentication-related failures will be easier to diagnose due to improved error handling.
