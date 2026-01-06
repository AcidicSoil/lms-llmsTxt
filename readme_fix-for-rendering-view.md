Your fenced ```bash blocks are inside custom HTML container tags (`<Steps>`, `<Step>`, etc.), so GitHub treats that region as an **HTML block** and passes it through “as-is” instead of parsing Markdown—meaning the triple backticks display literally and the code block doesn’t render. CommonMark explicitly describes this HTML-block passthrough behavior. ([CommonMark Spec][1])

GitHub also supports “alerts” (admonitions) via blockquotes like `> [!NOTE]`, so you can replace `<Info>`, `<Warning>`, `<Tip>`, `<Check>` with native GitHub syntax. ([GitHub Docs][2])
(And keep fenced code blocks surrounded by blank lines as GitHub recommends.) ([GitHub Docs][3])

Below is a drop-in patch for the broken sections in your README :

````diff
@@
-<Info>
-The pipeline validates curated links, detects default branches automatically, and writes artifacts to `artifacts/<owner>/<repo>/`.
-</Info>
+> [!NOTE]
+> The pipeline validates curated links, detects default branches automatically, and writes artifacts to `artifacts/<owner>/<repo>/`.

@@
-<Warning>
-Install dependencies inside a virtual environment to avoid PEP 668 “externally managed environment” errors.
-</Warning>
+> [!WARNING]
+> Install dependencies inside a virtual environment to avoid PEP 668 “externally managed environment” errors.

@@
 ## Install
-
-<Steps>
-  <Step title="Create a virtual environment">
-    ```bash
-    python3 -m venv .venv
-    source .venv/bin/activate
-    ```
-  </Step>
-  <Step title="Install the package with developer extras">
-    ```bash
-    pip install -e .[dev]
-    ```
-    Installing the editable package exposes the `lmstxt` CLI and the `lmstxt-mcp` server.
-  </Step>
-</Steps>
-
-<Tip>
-Keep the virtual environment active while running the CLI or tests so the SDK-based unload logic can import `lmstudio`.
-</Tip>
+### Create a virtual environment
+
+```bash
+python3 -m venv .venv
+source .venv/bin/activate
+```
+
+### Install the package with developer extras
+
+```bash
+pip install -e '.[dev]'
+```
+
+Installing the editable package exposes the `lmstxt` CLI and the `lmstxt-mcp` server.
+
+> [!TIP]
+> Keep the virtual environment active while running the CLI or tests so the SDK-based unload logic can import `lmstudio`.

@@
 ## Configure LM Studio
-
-<Steps>
-  <Step title="Load the CLI">
-    ```bash
-    npx lmstudio install-cli
-    lms server start --port 1234
-    ```
-    The server must expose an OpenAI-compatible endpoint, commonly `http://localhost:1234/v1`.
-  </Step>
-  <Step title="Ensure the target model is downloaded">
-    Open LM Studio, download the model (for example `qwen/qwen3-4b-2507`), and confirm it appears in the **Server** tab.
-  </Step>
-</Steps>
+### Load the CLI and start the server
+
+```bash
+npx lmstudio install-cli
+lms server start --port 1234
+```
+
+The server must expose an OpenAI-compatible endpoint, commonly `http://localhost:1234/v1`.
+
+### Ensure the target model is downloaded
+
+Open LM Studio, download the model (for example `qwen/qwen3-4b-2507`), and confirm it appears in the **Server** tab.
````

If you want the rest of the README to render consistently on GitHub, apply the same pattern elsewhere:

* Replace `<Info>…</Info>`, `<Warning>…</Warning>`, `<Tip>…</Tip>`, `<Check>…</Check>` with GitHub alerts `> [!NOTE]`, `> [!WARNING]`, `> [!TIP]`, `> [!IMPORTANT]`, etc. ([GitHub Docs][2])

[1]: https://spec.commonmark.org/0.29/?utm_source=chatgpt.com "HTML blocks"
[2]: https://docs.github.com/github/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax?utm_source=chatgpt.com "Basic writing and formatting syntax"
[3]: https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-and-highlighting-code-blocks?utm_source=chatgpt.com "Creating and highlighting code blocks"
