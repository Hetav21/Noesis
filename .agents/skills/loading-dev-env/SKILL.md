---
name: loading-dev-env
description: Loads and manages development environment configurations, toolchain paths, and local variables from direnv, .envrc, and Nix flakes in a workspace. Use when environment variables or CLI tools are missing, when direnv is not active or blocked, or when running commands in non-interactive subshells that require the project environment.
---

# Loading Development Environment

A generic guide for loading and managing development environments, toolchains, and environment variables configured via `direnv`, `.envrc`, or Nix flakes.

## When to Use This Skill

Activate this skill when:
- Commands fail with missing environment variables or unauthenticated API errors.
- A non-interactive subshell (such as an automated agent script or `bash -c ...`) does not inherit the interactive `direnv` shell hook.
- `.envrc` was created or modified and requires re-authorization.
- Diagnosing environment loading failures (`direnv: error`, `direnv: blocked`).

---

## 1. How direnv Works in Subshells

In interactive terminal sessions, `direnv` hooks into the shell prompt to export variables automatically upon entering a directory.

However, **non-interactive subshells** (commands run via agents, child processes, or scripts) do not trigger interactive shell hooks. Therefore, the subshell must explicitly load the exported environment.

---

## 2. Loading Patterns

### Pattern A: Robust Subshell Evaluation (Recommended)
When executing shell commands that depend on `.envrc` variables:

```bash
eval "$(direnv export bash 2>/dev/null)" || eval "$(grep '^export ' .envrc 2>/dev/null || true)"
```

- If `direnv` is installed and authorized, `direnv export bash` safely exports the full computed environment (including layout, Nix paths, and variables).
- If `direnv` is not authorized or not installed, the fallback safely extracts and exports literal `export KEY="VALUE"` lines from `.envrc` without failing on direnv-specific directives (such as `use flake` or `dotenv`).

### Pattern B: Authorizing New or Modified Files
Whenever `.envrc` is created or its contents change, `direnv` blocks execution until explicitly approved:

```bash
direnv allow
```

To verify the approval status:
```bash
direnv status
```

### Pattern C: Combined with Nix Flakes (If Applicable)
If `.envrc` uses `use flake`, you can enter or execute within the declared development shell directly:

```bash
nix develop -c <command>
```

---

## 3. Security & Git Hygiene

1. **Keep Secrets Local**:
   - `.envrc` typically contains private tokens, API keys, and connection strings.
   - It **must always remain Git-ignored**.
   - Verify it is ignored before staging:
     ```bash
     git check-ignore -v .envrc
     ```

2. **Template Pattern (`.envrc.example`)**:
   - Provide a checked-in template (e.g. `.envrc.example`) with dummy values and documentation.
   - Developers and agents copy `.envrc.example` to `.envrc` and populate real values locally.
