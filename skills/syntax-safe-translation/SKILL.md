---
name: syntax-safe-translation
description: Use this skill when translating, localizing, or rewriting scripts and source files while preserving original syntax, control flow, string boundaries, placeholders, and runtime behavior. Best for batch, PowerShell, shell, config-like source, embedded loaders, and any code-adjacent text where naive translation can break execution.
---

# Syntax-Safe Translation

## Overview

Use this skill when the user wants translated or localized code, scripts, prompts, UI strings inside source files, or generated artifacts, and correctness matters more than maximum translation coverage.

Goal: translate user-facing text without changing parser-visible structure, execution flow, validation logic, placeholders, quoting, escaping, or machine-meaningful strings.

## Workflow

1. Identify the execution surface before translating.
   Execution surface includes syntax tokens, operators, delimiters, variable expansion, placeholders, command names, URLs, hashes, regexes, format strings, and strings used in comparisons or protocol behavior.

2. Classify each string as one of:
   `ui-text`: safe to translate.
   `logic-string`: used in comparisons, lookups, parsing, filenames, flags, protocol values, or command invocation. Do not translate unless the surrounding logic is also updated safely.
   `mixed-string`: contains both UI text and protected tokens. Translate only the UI span.

3. Extract translatable spans instead of translating whole lines.
   Prefer span-based replacement using original start/end offsets.
   When multiple spans exist on one line, apply replacements from right to left so earlier length changes do not corrupt later offsets.

4. Protect placeholders before translation.
   Replace variables and machine tokens with temporary placeholders, translate the remaining text, then restore placeholders exactly.
   Protect items such as `%var%`, `!var!`, `$var`, `$()`, `{0}`, `%~dp0`, `%%i`, URLs, hashes, registry paths, file extensions, command names, and product terms the code expects literally.

5. Constrain extraction to trusted UI contexts.
   Prefer explicit contexts like `echo`, `Write-Host`, `Write-Warning`, `Write-Progress -Activity/-Status`, menu labels, and known prompt variables.
   Avoid broad patterns like "any quoted string with English text" unless the file format is purely content and not executable code.

6. Rebuild the file without normalizing semantics accidentally.
   Preserve quoting style, escaping, newline style, BOM policy, indentation, and file encoding unless there is a deliberate compatibility fix.

7. Validate after regeneration.
   Run a parser or syntax checker for the target language when possible.
   Also verify a few logic-sensitive lines manually: comparisons, hash checks, command invocations, download URLs, and generated command lines.

## CMD and Batch Rules

- Treat labels, flow control, and environment manipulation as logic, not content.
- Do not translate lines starting with `:label`, `rem`, `if`, `for`, `set`, `setlocal`, `endlocal`, `goto`, `exit`, `call` to external tools, or executable invocations unless you are extracting a known UI-only substring.
- Protect batch expansions exactly, including `%var%`, `!var!`, `%~dp0`, `%1`, `%*`, and loop variables like `%%i`.
- Be careful with `echo` lines. Only translate the portion after `echo` when the remainder is plain UI text. If it contains pipes, redirects, escaped operators, variables with control meaning, or command composition, treat it as logic.
- For helper calls like `call :dk_color "text"` or other label-based UI helpers, extract only the quoted user-facing text spans and leave the command structure untouched.
- Keep spacing and escaping stable. In batch files, small changes to `^`, `%`, `!`, `&`, `|`, `<`, `>`, or trailing spaces can change behavior.
- If a translated line ends with non-ASCII text, verify the target runtime and encoding strategy. Some CMD flows need explicit `chcp 65001` or a trailing ASCII-safe character to avoid line-join issues.

## Guardrails

- Never translate strings that are compared against command output unless the produced output is also translated in the same execution path.
- Never translate command names, flags, registry keys, environment variable names, file paths, URLs, hashes, or structured literals.
- Never remove or rewrite integrity checks unless the task explicitly requires changing the trust model.
- Do not assume comments are always safe; some scripts embed structured directives in comments.
- If extraction is heuristic, review every changed line that contains multiple quoted strings, interpolation, or escaping.

## Patterns

### Safe pattern

- Extract only the user-facing segment from:
  `Write-Progress -Activity "Downloading..." -Status "Please wait"`

### Unsafe pattern

- Translating the entire line:
  `if ($chkcmd -notcontains "CMD is working")`
  This breaks runtime logic because the string is part of a comparison, not UI.

### Mixed pattern

- Translate only the explanatory prefix in a string like:
  `"Help - https://example.com/fix"`
  Keep the URL literal.

### CMD-safe pattern

- Extract only the visible text from:
  `echo Press any key to continue`
  or
  `call :dk_color "Checking activation status..."`

### CMD-unsafe pattern

- Do not translate lines like:
  `if %errorlevel% neq 0 goto error`
  or
  `echo %windir% ^| findstr /i system32`
  because the text is part of control flow or command composition.

## Editing Strategy

- Prefer fixing the generator over patching generated output by hand.
- If the repo generates translated artifacts, update the extraction and replacement logic first, then regenerate outputs and validate them.
- Keep translation memory or cache entries aligned with protected placeholders, not raw machine tokens.

## Minimum Validation

- Regenerate the output artifact.
- Run a parser or syntax check on the generated file.
- Diff the result against the source and inspect:
  quoted strings
  comparisons
  command lines
  interpolated expressions
  loader or bootstrap sections
- If available, compare with the upstream original to confirm only intended UI text changed.
