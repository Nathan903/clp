# Integration Debugging Final Report

## Summary

The clean integration command requested by the user now succeeds:

```bash
cd ~/clp; git clean -Xdf ; task clean ; task tests:integration
```

Final verification run:

- Background task ID: `b459r2isa`
- Output file: `/tmp/claude-1001/-home-nathan-clp/507b0b56-1bbc-4290-99be-ca5b7dc73467/tasks/b459r2isa.output`
- Exit code: `0`
- Core integration tests: `5 passed, 7 deselected`
- Package integration tests: `6 passed, 6 deselected`
- Final package summary:

```text
================== 6 passed, 6 deselected in 72.17s (0:01:12) ==================
```

No manual install actions were performed. I only changed files in the codebase and reran the requested clean integration command.

The fixes were committed separately, one fix per commit, and pushed to:

- Local/current branch: `fix-integration-clean`
- Remote branch: `origin/fix-integration-clean`
- PR creation URL: <https://github.com/Nathan903/clp/pull/new/fix-integration-clean>

The originally requested remote branch name, `origin/fix-integration`, already existed and contained unrelated commit `bb4c2b4b Update CMakeLists.txt`, so I did not overwrite it. Per user choice, I pushed to a different new branch.

## Commits created

```text
9de9dc00 fix(tests): ignore reusable package test ports
ed518e65 fix(package): profile optional compose services
ab5302a6 fix(task): serialize core integration build
```

## Fix 1: Serialize the root `core` Task build

### Commit

```text
ab5302a6 fix(task): serialize core integration build
```

### Kind/category

Build-system race / duplicate Task dependency execution against the same CMake build directory.

### Observed failure symptoms

A clean integration run failed because the required `clg` binary was missing:

```text
RuntimeError: CLP core binaries at /home/nathan/clp/build/core are incomplete. Missing binaries: clg
```

The same run showed duplicate concurrent builds of the same target in the same build directory:

```text
cmake --build "/home/nathan/clp/build/core" --parallel "8" --target="clg"
cmake --build "/home/nathan/clp/build/core" --parallel "8" --target="clg"
```

The concurrent `clg` link failed with GCC LTO/linker errors, including:

```text
lto1: internal compiler error: resolution sub id ... not in object file
lto-wrapper: fatal error: /usr/bin/c++ returned 1 exit status
/usr/bin/ld: error: lto-wrapper failed
collect2: error: ld returned 1 exit status
```

### Root cause

`task tests:integration` reaches the root `core` task through two separate dependency paths in the same Task invocation:

1. `tests:integration:core -> ::core`
2. `tests:integration:package -> ::package -> docker-images:package -> package-build-deps -> core`

Because the root `core` task did not specify `run: "once"`, Task could execute the root `core` task concurrently through these paths. That allowed multiple CMake builds to operate on the same build directory and target at the same time, producing the `clg` link failure and leaving the core binaries incomplete.

### Code fix

Updated `taskfile.yaml`:

```yaml
core:
  run: "once"
  cmds:
    - task: "core-generate"
    - task: "core-build"
```

This ensures the shared root `core` generate/build sequence runs at most once per Task invocation.

### Likely introducing commit

```text
e7acd6918 feat(ci): Add task for package integration tests. (#1664)
```

This commit added the package integration dependency path that created the second route to the root `core` task.

### Verification status

The next repeated clean integration run got past the `clg`/LTO failure, and the core integration tests passed:

```text
5 passed, 7 deselected
```

That run then exposed the next independent issue in Docker Compose package startup.

## Fix 2: Put optional Docker Compose services behind profiles

### Commit

```text
ed518e65 fix(package): profile optional compose services
```

### Kind/category

Docker Compose orchestration/configuration issue for disabled optional services.

### Observed failure symptoms

After the core build race was fixed, package integration tests failed during CLP package startup. The pytest-level failure was:

```text
AssertionError: The 'start-clp.sh' subprocess returned a returncode indicative of failure (1)
```

The package subprocess logs showed Docker Compose failing because an intentionally disabled optional service was still part of the Compose graph:

```text
clp-package-... is missing dependency log-ingestor
2026-07-09T13:49:26.769 ERROR [start_clp] Failed to start CLP.
```

The generated environment had disabled log-ingestor:

```text
CLP_LOG_INGESTOR_ENABLED=0
```

After applying a targeted log-ingestor fix and rerunning the clean integration command, the same class of failure appeared for another optional service:

```text
clp-package-... is missing dependency mcp-server
2026-07-09T14:03:33.426 ERROR [start_clp] Failed to start CLP.
```

The clp-text mode also generated:

```text
CLP_API_SERVER_ENABLED=0
```

so `api-server` had the same optional-service/default-graph risk even though it had not yet surfaced as a separate observed failure.

### Root cause

The optional services were disabled with `deploy.replicas: 0`, but they still remained in Docker Compose's default service graph. When `docker compose up --detach --wait` evaluated the graph, dependencies involving those disabled optional services could make startup fail even though the services were intentionally not configured.

The affected optional services were:

- `log-ingestor`
- `mcp-server`
- `api-server`

### Code fix

Updated `tools/deployment/package/docker-compose-all.yaml` to add service-specific profiles:

```yaml
mcp-server:
  <<: *service_defaults
  profiles: ["mcp-server"]
  hostname: "mcp_server"
```

```yaml
api-server:
  <<: *service_defaults
  profiles: ["api-server"]
  hostname: "api_server"
```

```yaml
log-ingestor:
  <<: *service_defaults
  profiles: ["log-ingestor"]
  hostname: "log_ingestor"
```

Updated `components/clp-package-utils/clp_package_utils/controller.py` so `DockerComposeController.start()` enables each profile only when the corresponding optional component is configured and applicable:

```python
cmd = ["docker", "compose", "--project-name", self._project_name]
if self._clp_config.api_server is not None:
    cmd += ["--profile", "api-server"]
if (
    self._clp_config.log_ingestor is not None
    and StorageType.S3 == self._clp_config.logs_input.type
):
    cmd += ["--profile", "log-ingestor"]
if self._clp_config.mcp_server is not None:
    cmd += ["--profile", "mcp-server"]
cmd += ["--file", self._get_docker_file_name()]
cmd += ["up", "--detach", "--wait"]
```

This removes disabled optional services from the default Compose graph while preserving them when configured.

### Likely introducing commits

- `39398e65 feat(clp-package): Add log-ingestor config interface and Docker Compose orchestration. (#1741)` introduced log-ingestor Compose orchestration.
- `0671077c refactor(deployment): Uses replicas to control and standardize MCP server enablement in Docker Compose (resolves #1620). (#1634)` standardized MCP server enablement through replicas.
- `a6dd50e1 feat(clp-package): Add API Server config interface and Docker Compose orchestration; Set HOME=/tmp during image build in GH workflow. (#1575)` introduced API server Compose orchestration.
- `a6b373c7 feat(webui): Add file listing API; Map logs input dir into the webui service container in the Package Docker Compose project. (#1688)` later added API server replicas control.

### Verification status

The clean integration run after the log-ingestor profile fix no longer failed on `log-ingestor`; it instead exposed the same issue for `mcp-server`. After generalizing the profile fix to `mcp-server` and `api-server`, the final clean integration run passed all package tests:

```text
tests/package_tests/clp_json/test_clp_json.py::test_clp_json_startstop[clp-json] PASSED
tests/package_tests/clp_json/test_clp_json.py::test_clp_json_compression_json_multifile[clp-json] PASSED
tests/package_tests/clp_json/test_clp_json.py::test_clp_json_compression_text_multifile[clp-json] PASSED
tests/package_tests/clp_json/test_clp_json.py::test_clp_json_search[clp-json] PASSED
tests/package_tests/clp_text/test_clp_text.py::test_clp_text_startstop[clp-text] PASSED
tests/package_tests/clp_text/test_clp_text.py::test_clp_text_compression_text_multifile[clp-text] PASSED
```

## Fix 3: Allow reusable TCP ports in the package test availability probe

### Commit

```text
9de9dc00 fix(tests): ignore reusable package test ports
```

### Kind/category

Integration-test environment false positive in package port availability checks.

### Observed failure symptoms

After the Docker Compose optional-service profile fix, the repeated clean integration run got further:

- Core integration tests passed.
- All `clp-json` package tests passed.
- `clp-text` tests failed during fixture setup before package startup.

The failure was:

```text
ValueError: Port '56132' in the desired range ('56000' to '56134' inclusive) is already in use. Choose a different port range for the test environment.
```

The affected tests were:

```text
ERROR tests/package_tests/clp_text/test_clp_text.py::test_clp_text_startstop[clp-text]
ERROR tests/package_tests/clp_text/test_clp_text.py::test_clp_text_compression_text_multifile[clp-text]
```

Post-failure checks found no active listener or CLP package container using that port:

```bash
ss -ltnp 'sport = :56132'
docker ps --format '{{.ID}} {{.Names}} {{.Ports}}' | grep 56132
```

No listener/container was found.

### Root cause

Package integration tests reuse the same configured base port range across package modes. The port availability probe used a plain socket `bind()` without `SO_REUSEADDR`. A port recently used by the previous package mode could therefore be reported unavailable even after the package was stopped and no process was listening.

This was a false positive in the test availability check: the port was reusable, but the check treated it as unavailable.

### Code fix

Updated `integration-tests/tests/utils/port_utils.py`:

```python
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError:
        return False
    return True
```

This matches normal server restart semantics and allows reusable port states while still failing when another active listener owns the address.

### Likely introducing commit

```text
71daa70f feat(integration-tests): Add port range assignment based on a configurable base port to avoid package spin-up failures. (#1662)
```

This commit introduced the port availability checker.

### Verification status

A local syntax check passed:

```bash
python3 -m py_compile integration-tests/tests/utils/port_utils.py
```

The final repeated clean integration command then passed with exit code `0`.

## Incidental issues encountered

### Large output files

The integration output files were too large to read in one pass. I used line counts and targeted reads around the tail/failure sections instead of reading entire logs at once.

### Task list state reset

An initial task list created during the investigation later disappeared from the task tool state. This did not affect the code investigation or fixes.

### Subagent context-window failure

A read-only exploration subagent launched to investigate the missing `clg` failure terminated early with an API/context-window error:

```text
Agent terminated early due to an API error: API Error: 400 Your input exceeds the context window of this model.
```

This did not block progress because the root cause had already been identified manually.

### Git index lock

The first attempt to create the `taskfile.yaml` commit failed because `.git/index.lock` existed:

```text
fatal: Unable to create '/home/nathan/clp/.git/index.lock': File exists.
```

I checked for active git processes and the lock file. On recheck, the lock was gone, and all commits completed successfully.

### Existing remote branch name

When asked to push the commits to a new branch called `fix-integration`, the local branch was created, but push failed because `origin/fix-integration` already existed with unrelated history:

```text
! [rejected] fix-integration -> fix-integration (non-fast-forward)
```

The existing remote branch pointed at:

```text
bb4c2b4b Update CMakeLists.txt
```

I did not force-push over that branch. After the user chose to use a new branch name, I renamed the local branch and pushed to:

```text
fix-integration-clean
```

## Final verification details

Final clean integration command:

```bash
cd /home/nathan/clp; git clean -Xdf ; task clean ; task tests:integration
```

Final output path:

```text
/tmp/claude-1001/-home-nathan-clp/507b0b56-1bbc-4290-99be-ca5b7dc73467/tasks/b459r2isa.output
```

Core test excerpt:

```text
tests/binary_tests/test_identity_transformation.py::test_clp_identity_transform PASSED
tests/binary_tests/test_identity_transformation.py::test_clp_s_identity_transform[directory] PASSED
tests/binary_tests/test_identity_transformation.py::test_clp_s_identity_transform[tar_gz] PASSED
tests/binary_tests/test_log_converter.py::test_log_converter_transform[directory] PASSED
tests/binary_tests/test_log_converter.py::test_log_converter_transform[tar_gz] PASSED

======================= 5 passed, 7 deselected in 0.58s ========================
```

Package test excerpt:

```text
tests/package_tests/clp_json/test_clp_json.py::test_clp_json_startstop[clp-json] PASSED
tests/package_tests/clp_json/test_clp_json.py::test_clp_json_compression_json_multifile[clp-json] PASSED
tests/package_tests/clp_json/test_clp_json.py::test_clp_json_compression_text_multifile[clp-json] PASSED
tests/package_tests/clp_json/test_clp_json.py::test_clp_json_search[clp-json] PASSED
tests/package_tests/clp_text/test_clp_text.py::test_clp_text_startstop[clp-text] PASSED
tests/package_tests/clp_text/test_clp_text.py::test_clp_text_compression_text_multifile[clp-text] PASSED

================== 6 passed, 6 deselected in 72.17s (0:01:12) ==================
```

## Final repository state

The working tree was clean before creating this report. The code fixes are committed on branch `fix-integration-clean` and pushed to `origin/fix-integration-clean`.

This report itself is written to `report.md` as requested.
