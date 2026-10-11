# MOAMU AI Challenge Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python prototype that uses Gemini to design photo-verifiable challenges and judge submitted images against frozen required conditions, with deterministic offline unit tests and opt-in live integration tests.

**Architecture:** Domain models and validation live in a small `moamu_ai` package. Challenge generation and image verification services depend on Protocol-based model ports, while pytest fakes provide deterministic model responses. A Gemini Adapter uses structured outputs for both text and image analysis; image validation and final verdict calculation remain in application code.

**Tech Stack:** Python 3.11+, Pydantic 2.x, Pillow, pytest, google-genai, python-dotenv

**Spec:** `docs/superpowers/specs/2026-10-12-ai-challenge-prototype-design.md`

## Global Constraints

- Do not call external APIs during the default unit-test run; live Gemini tests require `RUN_GEMINI_INTEGRATION=1`.
- Do not read, print, or commit `.env` or API key values.
- Accept goal text only after trimming whitespace and only when its Python string length is 1–20 characters.
- Successful challenge plans contain 2–4 required conditions and exactly 3 shooting guides.
- `DATE_VISIBLE` cannot be a required condition.
- Final verification is `SATISFIED` only when every required condition is `MET`; `NOT_MET` and `UNCERTAIN` map to `UNSATISFIED`.
- Preserve condition-level verdicts, reasons, and evidence even though the external result is binary.
- Accept only valid JPEG, PNG, and WEBP files up to 10MB with both dimensions at least 256 pixels.

## Review Focus

- A `.env` file or API key must never be staged or included in a commit; the repository ignore rules must cover it.
- Korean Unicode goals at exactly 20 characters must pass while 21 characters must fail before the model is called.
- A `SUBSTITUTE` plan must explain both the replacement action and that it does not prove the original goal.
- A verification response with missing, extra, or duplicate condition IDs must fail instead of producing a verdict.
- Corrupt or disguised non-image input must fail before the verification model is called.

---

## File Structure

- `pyproject.toml`: package metadata, runtime dependencies, pytest configuration.
- `.gitignore`: local secrets, virtual environments, caches, build output, and macOS metadata.
- `src/moamu_ai/__init__.py`: public service and schema exports.
- `src/moamu_ai/exceptions.py`: domain-specific validation errors.
- `src/moamu_ai/models.py`: enums and Pydantic input/output models.
- `src/moamu_ai/ports.py`: challenge and verification model Protocols.
- `src/moamu_ai/challenge_service.py`: goal input validation and challenge-plan validation.
- `src/moamu_ai/image_validation.py`: local image file validation.
- `src/moamu_ai/verification_service.py`: condition response validation and final verdict calculation.
- `src/moamu_ai/gemini_adapter.py`: Gemini structured-output calls for challenge generation and image verification.
- `src/moamu_ai/settings.py`: safe environment loading and model configuration.
- `tests/fakes.py`: deterministic fake model ports with call recording.
- `tests/test_models.py`: schema invariants.
- `tests/test_challenge_service.py`: challenge generation behavior.
- `tests/test_image_validation.py`: image file validation.
- `tests/test_verification_service.py`: condition matching and final verdict behavior.
- `tests/test_gemini_adapter.py`: SDK-boundary unit tests with a mocked client.
- `tests/integration/test_gemini_live.py`: opt-in live Gemini smoke tests using generated synthetic data.
- `README.md`: local setup, test commands, examples, and future provider integration boundary.

### Task 1: Secure Python Project Scaffold

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `src/moamu_ai/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Consumes: Python 3.11 or newer.
- Produces: installable `moamu-ai` package and a pytest test path rooted at `tests/`.

- [ ] **Step 1: Add repository safety rules**

Create `.gitignore` entries for `.env`, `.env.*` with `!.env.example`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.coverage`, `dist/`, `build/`, `*.egg-info/`, and `.DS_Store`.

- [ ] **Step 2: Add project metadata**

Create `pyproject.toml` requiring Python `>=3.11`, Pydantic `>=2,<3`, Pillow `>=10,<13`, google-genai, and python-dotenv. Add a `test` optional dependency containing pytest `>=8,<10`. Configure pytest with `testpaths = ["tests"]`, `addopts = "-ra"`, and an `integration` marker.

- [ ] **Step 3: Verify the secret file is ignored**

Run: `git check-ignore -v .env`

Expected: output names `.gitignore` and a matching `.env` rule without printing file contents.

- [ ] **Step 4: Install the package for development**

Run: `python3 -m pip install -e '.[test]'`

Expected: installation succeeds with the official `google-genai` SDK and no OpenAI SDK.

- [ ] **Step 5: Commit**

```bash
git add .gitignore pyproject.toml src/moamu_ai/__init__.py tests/__init__.py
git commit -m "build: scaffold AI prototype"
```

### Task 2: Domain Models and Invariants

**Files:**
- Create: `src/moamu_ai/exceptions.py`
- Create: `src/moamu_ai/models.py`
- Modify: `src/moamu_ai/__init__.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: Pydantic 2.x.
- Produces: `Verifiability`, `ConditionType`, `ConditionVerdict`, `FinalVerdict`, `VerificationCondition`, `ChallengePlan`, `ConditionResult`, and `VerificationResult`.

- [ ] **Step 1: Write failing model-invariant tests**

Add tests asserting:

```python
assert len(valid_plan.required_conditions) == 2
assert len(valid_plan.shooting_guides) == 3
with pytest.raises(ValidationError):
    ChallengePlan(...one_condition...)
with pytest.raises(ValidationError):
    VerificationCondition(type=ConditionType.DATE_VISIBLE, required=True, ...)
with pytest.raises(ValidationError):
    ChallengePlan(verifiability=Verifiability.SUBSTITUTE, substitute_action=None, ...)
```

Also assert rejected states require empty conditions/guides, condition IDs are unique, and successful states require a non-empty challenge name and verification scope.

- [ ] **Step 2: Run model tests to verify they fail**

Run: `pytest tests/test_models.py -v`

Expected: FAIL because domain models do not exist.

- [ ] **Step 3: Implement enums, models, and errors**

Create:

```python
class InvalidGoalError(ValueError): ...
class InvalidChallengePlanError(ValueError): ...
class InvalidImageError(ValueError): ...
class InvalidVerificationResponseError(ValueError): ...
```

Use Pydantic validators to enforce all model invariants from the spec. `ChallengePlan` must represent both successful (`VERIFIABLE`, `SUBSTITUTE`) and unsuccessful (`NOT_VERIFIABLE`, `UNSUPPORTED`, `REJECTED`) outcomes without ambiguous optional fields.

- [ ] **Step 4: Run model tests**

Run: `pytest tests/test_models.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/moamu_ai tests/test_models.py
git commit -m "feat: define AI challenge domain models"
```

### Task 3: Challenge Generation Service and Model Port

**Files:**
- Create: `src/moamu_ai/ports.py`
- Create: `src/moamu_ai/challenge_service.py`
- Modify: `src/moamu_ai/__init__.py`
- Create: `tests/fakes.py`
- Create: `tests/test_challenge_service.py`

**Interfaces:**
- Consumes: `ChallengeModel.generate(goal_text: str) -> Mapping[str, object]` containing an untrusted provider-shaped response.
- Produces: `generate_challenge(goal_text: str, model: ChallengeModel) -> ChallengePlan`.

- [ ] **Step 1: Write failing goal-validation tests**

Add tests showing that empty/whitespace-only and 21-character Korean goals raise `InvalidGoalError`, an exactly 20-character goal reaches the fake once, and rejected inputs never invoke the fake.

- [ ] **Step 2: Write failing response-validation tests**

Add tests for a valid direct plan, a valid substitute plan, and fake model responses that violate the plan schema or contain non-observable required conditions. Assert invalid responses raise `InvalidChallengePlanError`.

- [ ] **Step 3: Run challenge tests to verify they fail**

Run: `pytest tests/test_challenge_service.py -v`

Expected: FAIL because the port and service do not exist.

- [ ] **Step 4: Implement the port, fake, and service**

Define:

```python
class ChallengeModel(Protocol):
    def generate(self, goal_text: str) -> Mapping[str, object]: ...

def generate_challenge(goal_text: str, model: ChallengeModel) -> ChallengePlan: ...
```

Trim input, enforce length before calling the model, call the model once, parse the untrusted mapping into `ChallengePlan`, and translate Pydantic or semantic validation failures into `InvalidChallengePlanError`. Reject required-condition text that claims duration, an entire day, emotion, intent, or other facts not observable in one photograph.

- [ ] **Step 5: Run challenge tests**

Run: `pytest tests/test_challenge_service.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/moamu_ai tests/fakes.py tests/test_challenge_service.py
git commit -m "feat: add challenge generation service"
```

### Task 4: Local Image Validation

**Files:**
- Create: `src/moamu_ai/image_validation.py`
- Create: `tests/test_image_validation.py`

**Interfaces:**
- Consumes: `pathlib.Path` pointing to a local upload candidate.
- Produces: `ValidatedImage(path: Path, format: str, width: int, height: int, size_bytes: int)` or `InvalidImageError`.

- [ ] **Step 1: Write failing image-validation tests**

Generate temporary images with Pillow and assert JPEG, PNG, and WEBP images at 256×256 or larger pass. Assert missing paths, directories, unsupported GIF, a text file named `.jpg`, corrupt bytes, 255-pixel dimensions, and a file over 10MB raise `InvalidImageError`.

- [ ] **Step 2: Run image tests to verify they fail**

Run: `pytest tests/test_image_validation.py -v`

Expected: FAIL because `validate_image` does not exist.

- [ ] **Step 3: Implement image validation**

Define:

```python
def validate_image(image_path: Path) -> ValidatedImage: ...
```

Check path and byte size before opening. Use Pillow `Image.verify()`, reopen to read dimensions, and trust decoded format rather than filename extension.

- [ ] **Step 4: Run image tests**

Run: `pytest tests/test_image_validation.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/moamu_ai/image_validation.py tests/test_image_validation.py
git commit -m "feat: validate challenge proof images"
```

### Task 5: Image Verification Service

**Files:**
- Modify: `src/moamu_ai/ports.py`
- Create: `src/moamu_ai/verification_service.py`
- Modify: `src/moamu_ai/__init__.py`
- Modify: `tests/fakes.py`
- Create: `tests/test_verification_service.py`

**Interfaces:**
- Consumes: `VerificationModel.verify(image: ValidatedImage, conditions: tuple[VerificationCondition, ...]) -> Sequence[Mapping[str, object]]` containing untrusted provider-shaped condition results.
- Produces: `verify_challenge(image_path: Path, required_conditions: Sequence[VerificationCondition], model: VerificationModel) -> VerificationResult`.

- [ ] **Step 1: Write failing final-verdict tests**

Assert all `MET` returns `SATISFIED`; any `NOT_MET` returns `UNSATISFIED` without retry recommendation; any `UNCERTAIN` returns `UNSATISFIED` with `retry_recommended=True`; reasons and evidence remain in the result.

- [ ] **Step 2: Write failing condition-integrity tests**

Assert missing, extra, and duplicate condition IDs raise `InvalidVerificationResponseError`. Assert an invalid image and an empty condition list fail before the fake model is invoked.

- [ ] **Step 3: Run verification tests to verify they fail**

Run: `pytest tests/test_verification_service.py -v`

Expected: FAIL because the verification port and service do not exist.

- [ ] **Step 4: Implement verification orchestration**

Define the `VerificationModel` Protocol and:

```python
def verify_challenge(
    image_path: Path,
    required_conditions: Sequence[VerificationCondition],
    model: VerificationModel,
) -> VerificationResult: ...
```

Validate the image first, require at least two unique required conditions, invoke the model once, compare exact condition-ID sets, preserve input condition order, and calculate the final verdict in application code.

- [ ] **Step 5: Run verification tests**

Run: `pytest tests/test_verification_service.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/moamu_ai tests/fakes.py tests/test_verification_service.py
git commit -m "feat: verify challenge proof conditions"
```

### Task 6: Gemini Provider Adapter and Live Smoke Tests

**Files:**
- Create: `src/moamu_ai/settings.py`
- Create: `src/moamu_ai/gemini_adapter.py`
- Modify: `src/moamu_ai/__init__.py`
- Create: `tests/test_gemini_adapter.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_gemini_live.py`

**Interfaces:**
- Consumes: `GEMINI_API_KEY`, `gemini-3.1-flash-lite`, and the two model ports.
- Produces: `GeminiChallengeModel` and `GeminiVerificationModel`.

- [ ] **Step 1: Write failing settings and Adapter boundary tests**

Test missing-key handling without printing the key, upward `.env` discovery, configured model selection, structured-output schema submission, inline image MIME/data submission, empty responses, invalid JSON, and SDK exceptions. Use a mocked SDK client; no network call is permitted in this test file.

- [ ] **Step 2: Run Adapter unit tests to verify they fail**

Run: `pytest tests/test_gemini_adapter.py -v`

Expected: FAIL because settings and Gemini Adapters do not exist.

- [ ] **Step 3: Implement settings and Gemini Adapters**

Define `load_settings() -> Settings`, `GeminiChallengeModel`, and `GeminiVerificationModel`. Use `google.genai.Client`, `gemini-3.1-flash-lite`, Pydantic-derived JSON Schema, low/minimal thinking, and inline validated image bytes. Wrap configuration, SDK, refusal, empty-output, and parsing failures in domain errors without logging secrets.

- [ ] **Step 4: Add opt-in live smoke tests**

Mark tests with `@pytest.mark.integration` and skip unless `RUN_GEMINI_INTEGRATION=1`. Generate a simple 512×512 image with Pillow, call both public functions through real Gemini Adapters, and assert only schema invariants rather than a brittle exact semantic verdict.

- [ ] **Step 5: Run Adapter unit tests**

Run: `pytest tests/test_gemini_adapter.py -v`

Expected: PASS without network access.

- [ ] **Step 6: Run live Gemini smoke tests**

Run: `RUN_GEMINI_INTEGRATION=1 pytest tests/integration/test_gemini_live.py -v -m integration`

Expected: both live tests PASS and no key value appears in output.

- [ ] **Step 7: Commit**

```bash
git add src/moamu_ai tests/test_gemini_adapter.py tests/integration
git commit -m "feat: integrate Gemini challenge models"
```

### Task 7: Usage Documentation and Full Verification

**Files:**
- Create: `README.md`
- Create: `.env.example`
- Modify: any source or test file only if verification exposes a defect.

**Interfaces:**
- Consumes: public exports from `moamu_ai` and the fake test doubles.
- Produces: reproducible setup and examples without a real secret or network call.

- [ ] **Step 1: Document setup and usage**

Document Python setup, `pip install -e '.[test]'`, offline `pytest`, opt-in Gemini integration tests, both public function signatures, direct and substitute challenge examples, binary verdict mapping, and the Provider Adapter boundary. State that `.env.example` contains names only and that a key exposed in chat or version control must be revoked.

- [ ] **Step 2: Add safe environment template**

Create `.env.example` with empty `GEMINI_API_KEY=` and `OPENAI_API_KEY=` entries only.

- [ ] **Step 3: Run the complete test suite**

Run: `pytest -v`

Expected: all tests PASS.

- [ ] **Step 4: Run repository safety and syntax checks**

Run:

```bash
python3 -m compileall -q src tests
git diff --check
git check-ignore -v .env
git status --short
```

Expected: compilation and diff checks succeed; `.env` is ignored; no secret file is staged.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md .env.example
git commit -m "docs: explain AI prototype usage"
```

### Task 8: Branch Review and Pull Request

**Files:**
- Modify: only files requiring fixes from review.

**Interfaces:**
- Consumes: complete branch diff and test evidence.
- Produces: pushed branch and GitHub pull request with a self-review comment.

- [ ] **Step 1: Review the full diff**

Compare the branch to its base, inspect every changed file, and verify the spec requirements, secret safety, public exports, edge cases, and test coverage. Record findings before making fixes.

- [ ] **Step 2: Fix review findings and rerun verification**

Run: `pytest -v && python3 -m compileall -q src tests && git diff --check`

Expected: all checks pass after any fixes.

- [ ] **Step 3: Push the feature branch**

Run: `git push -u origin feat/ai-challenge-prototype`

Expected: push succeeds using the user's existing Git credentials.

- [ ] **Step 4: Create the pull request**

Use authenticated GitHub CLI or an authenticated GitHub browser session. The PR body must summarize both functions, offline Fake-based unit tests, the opt-in live Gemini Adapter, substitute verification policy, and exact verification commands/results.

- [ ] **Step 5: Add a self-review comment**

Post a PR comment listing reviewed areas, any findings and fixes, tests run, and residual limitations: Gemini-only provider support, no FastAPI route, and no image generation.
