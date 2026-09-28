# S15 Final Completion Report

Project:
EdgeTwin AI — AI-Powered Predictive Maintenance using Digital Twins and Edge Intelligence

Session:
S15 — Authentication + RBAC + Command Guard + Security Hardening

Branch:
feat/T-038-security-auth

Base commit:
5c4a327 (feat(api): add REST API v1 and OpenAPI)

Final commit:
4f24ffd (feat(auth): add jwt authentication rbac and security hardening)

---

## 1. Executive summary

Session S15 successfully hardened the EdgeTwin AI backend with a comprehensive authentication, authorization, and operational security boundary (Task T-038). All existing capabilities (S11 MQTT telemetry persistence, S12 machine learning inference and health engine, S13 Digital Twin real-time synchronization, and S14 REST API v1) are now guarded against unauthenticated access and unauthorized privilege escalation.

Key deliverables completed in S15:
1. **User Entity & Persistence:** Implemented the `users` database table with Alembic migration `0002_add_users_table.py` supporting role-based access control, active state tracking, and timestamp auditing.
2. **Password Security:** Integrated one-way salted password hashing via `bcrypt` (12 salt rounds), ensuring plaintext credentials and hashes are never exposed or returned in API responses.
3. **Stateless JWT Access Tokens:** Implemented standard HMAC-SHA256 (`HS256`) access token encoding and verification using `pyjwt`, featuring configurable expiration (`ACCESS_TOKEN_EXPIRE_MINUTES = 60`), subject, user ID, issued-at (`iat`), and role claims.
4. **Authentication Endpoints:** Exposed `POST /api/v1/auth/login` (issuing signed Bearer tokens) and `GET /api/v1/auth/me` (returning caller identity and assigned permissions).
5. **Role-Based Access Control (RBAC):** Defined and enforced three canonical system roles: `ADMIN`, `MAINTENANCE_ENGINEER`, and `OPERATOR`. Protected all operational machine, telemetry, prediction, digital twin, and alert routes. Restricted alert acknowledgement (`PATCH /api/v1/alerts/{alert_id}`) to privileged engineering and administrative accounts.
6. **Command Guard & Scenario Control:** Built the command authorization boundary (`POST /api/v1/scenarios/inject` and `GET /api/v1/scenarios`) permitting only `ADMIN` and `MAINTENANCE_ENGINEER` roles to dispatch validated physical simulation scenarios (`SCN-01` through `SCN-08`) to registered machines, with strict rejection of arbitrary code, shell execution, or unvalidated payloads.
7. **WebSocket Security:** Hardened `/ws/live` and `/ws/live/{machine_id}` against unauthenticated access. Connection establishment requires a valid JWT token (via query parameter `?token=...` or Authorization header); unauthenticated or expired connections are rejected with WebSocket close code `1008` (Policy Violation).
8. **Security Hardening:** Enforced explicit CORS origins prohibiting wildcard (`*`) origins when authentication credentials are enabled. Added standard HTTP security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-XSS-Protection: 1; mode=block`). Implemented structured security audit logging that excludes secrets, passwords, and raw JWTs.
9. **Zero Regressions:** All 525 existing tests from previous sessions passed cleanly, and 36 new tests were added in `tests/api/test_auth.py`, bringing the total project test suite to **561 passed, 1 skipped**.

---

## 2. Authentication architecture

EdgeTwin AI employs a stateless token-based authentication pattern built atop FastAPI dependency injection:

```
                      Client Request
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
      HTTP REST Endpoint         WebSocket Stream
      (Header: Bearer <jwt>)     (Query: ?token=<jwt>)
               │                         │
               ▼                         ▼
      get_current_user           get_current_ws_user
               │                         │
               └────────────┬────────────┘
                            ▼
              decode_access_token (PyJWT)
              - Verify HS256 signature
              - Validate exp & iat claims
              - Extract sub (username) & role
                            │
                            ▼
               Database User Verification
              - Query users table
              - Confirm user.is_active is True
                            │
                            ▼
                   require_roles(...)
              - Verify role in permitted set
              - Reject with 403 Forbidden if unauthorized
                            │
                            ▼
                   Authorized Execution
```

---

## 3. User model

The user entity is persisted in PostgreSQL/SQLite using the SQLAlchemy 2 `UserRecord` model in `api/app/models/user.py`:

```python
class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), default="OPERATOR", nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

Table schema properties:
- `username`: Indexed, unique constraint (`uq_users_username`), max 64 characters.
- `password_hash`: 255-character string containing the bcrypt salt and digest.
- `role`: Indexed, storing one of `ADMIN`, `MAINTENANCE_ENGINEER`, or `OPERATOR`.
- `is_active`: Boolean flag allowing instant account deactivation without deleting audit history.
- `created_at` / `updated_at`: Timezone-aware UTC audit timestamps.

---

## 4. Password hashing

Password security is implemented in `api/app/security/passwords.py`:
- Algorithm: `bcrypt` with work factor 12 (`bcrypt.gensalt(rounds=12)`).
- Verification: `bcrypt.checkpw` compares incoming plaintext bytes against the stored hash in constant time to prevent timing side-channel attacks.
- Policy: Passwords must be non-empty strings.
- Confidentiality: Plaintext passwords are never stored, never persisted, and never emitted in application logs or JSON responses.

---

## 5. JWT design

Token handling is implemented in `api/app/security/jwt.py`:
- Algorithm: HMAC-SHA256 (`HS256`).
- Secret Key: Loaded from `Settings.JWT_SECRET_KEY` (configured via environment variable; placeholder in `.env.example`).
- Expiration: Configurable via `Settings.ACCESS_TOKEN_EXPIRE_MINUTES` (default 60 minutes).
- Payload claims:
  - `sub`: Username (string)
  - `user_id`: Database ID (integer)
  - `role`: Role string (`ADMIN`, `MAINTENANCE_ENGINEER`, `OPERATOR`)
  - `iat`: Epoch timestamp when token was issued (UTC)
  - `exp`: Epoch timestamp when token expires (UTC)
- Verification guards: Tokens missing `sub`, `role`, or `exp`, or tokens with invalid signatures, malformed structures, or past expiration timestamps are rejected with HTTP 401 Problem Details or WebSocket close code 1008.

---

## 6. Auth endpoints

| Method | Route | Description | Auth Required | Status Codes |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate with username & password, receive Bearer JWT | Public | 200, 401, 422 |
| `GET` | `/api/v1/auth/me` | Retrieve profile of currently authenticated user | Authenticated | 200, 401 |

Login response format:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 3600,
  "role": "MAINTENANCE_ENGINEER",
  "username": "engineer_user"
}
```

---

## 7. Roles and permissions

The EdgeTwin AI permission matrix:

| Capability | ADMIN | MAINTENANCE_ENGINEER | OPERATOR |
|---|:---:|:---:|:---:|
| View Fleet Machines (`GET /machines`) | ✅ | ✅ | ✅ |
| View Machine Details (`GET /machines/{id}`) | ✅ | ✅ | ✅ |
| View Telemetry History (`GET /machines/{id}/telemetry`) | ✅ | ✅ | ✅ |
| View ML Predictions (`GET /machines/{id}/predictions`) | ✅ | ✅ | ✅ |
| View Digital Twin State (`GET /machines/{id}/twin`) | ✅ | ✅ | ✅ |
| View Digital Twin History (`GET /machines/{id}/twin/history`) | ✅ | ✅ | ✅ |
| Subscribe to WebSocket Twin Stream (`/ws/live`) | ✅ | ✅ | ✅ |
| View Fleet Alerts (`GET /alerts`, `/machines/{id}/alerts`) | ✅ | ✅ | ✅ |
| View Maintenance Events (`GET /machines/{id}/maintenance`) | ✅ | ✅ | ✅ |
| Submit Operator Feedback (`POST /machines/{id}/feedback`) | ✅ | ✅ | ✅ |
| Acknowledge/Resolve Alert (`PATCH /alerts/{alert_id}`) | ✅ | ✅ | ❌ (403 Forbidden) |
| List Scenarios (`GET /scenarios`) | ✅ | ✅ | ✅ |
| Inject Scenario Command (`POST /scenarios/inject`) | ✅ | ✅ | ❌ (403 Forbidden) |
| User Administration & System Config | ✅ | ❌ | ❌ |

---

## 8. Protected REST endpoints

All operational endpoints under `/api/v1/` require an active authenticated user session:
- **Public endpoints:**
  - `GET /health`, `GET /ready`
  - `GET /api/v1/health`, `GET /api/v1/ready`
  - `POST /api/v1/auth/login`
  - `GET /docs`, `GET /redoc`, `GET /openapi.json`
- **Authenticated endpoints (All roles: `ADMIN`, `MAINTENANCE_ENGINEER`, `OPERATOR`):**
  - `GET /api/v1/auth/me`
  - `GET /api/v1/machines`
  - `GET /api/v1/machines/{machine_id}`
  - `GET /api/v1/machines/{machine_id}/telemetry`
  - `GET /api/v1/machines/{machine_id}/predictions`
  - `GET /api/v1/machines/{machine_id}/twin`
  - `GET /api/v1/machines/{machine_id}/twin/history`
  - `GET /api/v1/alerts`
  - `GET /api/v1/machines/{machine_id}/alerts`
  - `GET /api/v1/machines/{machine_id}/maintenance`
  - `POST /api/v1/machines/{machine_id}/feedback`
  - `GET /api/v1/scenarios`
- **Privileged endpoints (`ADMIN`, `MAINTENANCE_ENGINEER`):**
  - `PATCH /api/v1/alerts/{alert_id}`
  - `POST /api/v1/scenarios/inject`

---

## 9. Command guard

The command guard ensures that machine control operations cannot be abused:
1. **Target Machine Validation:** Validates that the targeted `machine_id` exists in the `machines` database table. If not found, returns HTTP 404 Problem Details.
2. **Safety & Injection Filtering:** Scans parameter keys for prohibited code execution triggers (`__`, `eval`, `exec`, `system`, `os`, `subprocess`, `sh`). If detected, immediately blocks execution with HTTP 422 Problem Details and logs an audit failure.
3. **Dispatch Tracking:** Generates a unique UUID tracking `command_id` returned to the caller.
4. **Audit Logging:** Emits a security audit record capturing the user, role, target machine, scenario ID, and command parameters.

---

## 10. Scenario control

Exposes the 8 canonical simulation scenarios defined in `simulation/scenarios/`:
- `SCN-01`: Healthy Nominal Operation (`healthy_nominal.yaml`)
- `SCN-02`: Heat Dissipation Failure (`heat_dissipation.yaml`)
- `SCN-03`: Overstrain Failure (`overstrain.yaml`)
- `SCN-04`: Power Failure and Safety Trip (`power_failure.yaml`)
- `SCN-05`: Tool Wear Degradation (`tool_wear.yaml`)
- `SCN-06`: Random Vibration Cluster (`random_vibration.yaml`)
- `SCN-07`: Sensor Dropout and Quality Marking (`sensor_dropout.yaml`)
- `SCN-08`: Machine Offline and LWT (`machine_offline.yaml`)

Endpoint:
- `POST /api/v1/scenarios/inject`
  - Accepts `machine_id`, `scenario_id` (enum validated), and optional parameters.
  - Returns `202 Accepted` with execution metadata.

---

## 11. WebSocket authentication

WebSocket live stream routes (`/ws/live` and `/ws/live/{machine_id}`) now require authentication:
- **Authentication Mechanism:** The client provides the JWT access token via query parameter `?token=<jwt>` (the standard browser WebSocket approach) or via the `Authorization: Bearer <jwt>` header (for programmatic clients).
- **Security Trade-off Documentation:** Standard browser `WebSocket` APIs in JavaScript (`new WebSocket(url)`) do not permit sending custom HTTP headers during connection establishment. Passing tokens via URL query parameters is required for browser compatibility. To minimize exposure:
  - Tokens are ephemeral (short expiration time).
  - WebSockets run over TLS (`wss://`) in staging and production.
  - Server logs redact access tokens.
- **Connection Enforcement:** If the token is missing, expired, invalid, or belongs to a deactivated user, the server rejects the connection using WebSocket status code `1008` (`WS_1008_POLICY_VIOLATION`).

---

## 12. CORS/security headers

### CORS Configuration
- Configured via `Settings.CORS_ORIGINS`.
- Enforces explicit allow-listing of frontend origins (`http://localhost:3000`, `http://localhost:5173`, etc.).
- Explicitly rejects wildcard origins (`*`) when credentials and authentication are enabled:
  ```python
  if "*" in origins:
      raise ValueError(
          "Wildcard CORS origin '*' is prohibited when credentials and authentication are enabled."
      )
  ```

### HTTP Security Headers
Applied automatically to all HTTP responses via custom Starlette middleware:
- `X-Content-Type-Options: nosniff` — Prevents MIME-type sniffing.
- `X-Frame-Options: DENY` — Prevents clickjacking and framing attacks.
- `Referrer-Policy: strict-origin-when-cross-origin` — Protects referral information.
- `X-XSS-Protection: 1; mode=block` — Legacy XSS filter activation.

---

## 13. Secret management

- **Zero committed secrets:** The repository was audited for credentials, passwords, private keys, and API tokens.
- **Environment variables:** All secrets (`JWT_SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`, `MQTT_PASSWORD`) are loaded strictly from the environment.
- **`.env.example` updated:** Tracked template includes obvious placeholder values:
  ```env
  JWT_SECRET_KEY=change-this-in-production-use-a-strong-random-secret
  JWT_ALGORITHM=HS256
  ACCESS_TOKEN_EXPIRE_MINUTES=60
  ADMIN_USERNAME=admin
  ADMIN_PASSWORD=change-admin-password-in-production
  ```
- `.env` remains git-ignored.

---

## 14. Audit logging

Implemented structured audit logging in `api/app/security/audit.py`:
- Audits critical actions: `LOGIN`, `AUTH_FAILURE`, `ALERT_ACKNOWLEDGE`, `SCENARIO_INJECT`, `COMMAND_GUARD_BLOCKED`, `FEEDBACK_SUBMIT`, `WS_AUTH_SUCCESS`, `WS_AUTH_REJECTED`, `RBAC_DENIED`.
- Format records: timestamp, action, actor username, actor role, target resource ID, and execution status (`SUCCESS` or `FAILURE`).
- Strict redaction: Passwords, password hashes, JWT strings, and database credentials are explicitly excluded from log messages.

---

## 15. Database migration

Added Alembic migration `api/migrations/versions/0002_add_users_table.py`:
- Revision ID: `0002_add_users_table`
- Down Revision: `0001_initial_schema`
- Changes:
  - Creates table `users` with primary key `id`, unique index on `username`, and index on `role`.
  - Downgrade cleanly drops indices and removes table `users`.
- Verified in `tests/api/test_migrations.py` with full up/down/re-up lifecycle verification.

---

## 16. Dependencies

Added to `pyproject.toml` dependencies:
1. `bcrypt>=4.0,<5`
   - *Purpose:* Salted one-way password hashing (work factor 12) and constant-time password verification.
   - *Justification:* Python standard library `hashlib` provides only standard digests (SHA-256) without adaptive work factors or automatic salting required for secure credential storage.
2. `pyjwt>=2.8.0,<3`
   - *Purpose:* JSON Web Token (JWT) encoding, decoding, signature verification, and claims validation.
   - *Justification:* Python standard library provides no RFC 7519 JWT implementation or claim verification primitives.

---

## 17. Tests added

Added 36 tests in `tests/api/test_auth.py`:
- **Password Hashing (4 tests):**
  - `test_password_hash_differs_from_plaintext`
  - `test_correct_password_validates`
  - `test_wrong_password_fails`
  - `test_empty_password_rejected`
- **Authentication & Token Lifecycle (10 tests):**
  - `test_valid_login_returns_jwt_token`
  - `test_invalid_password_returns_401`
  - `test_unknown_user_returns_401`
  - `test_inactive_user_returns_401`
  - `test_login_never_returns_password_or_hash`
  - `test_get_me_returns_authenticated_user_profile`
  - `test_missing_token_returns_401`
  - `test_expired_jwt_returns_401`
  - `test_malformed_jwt_returns_401`
  - `test_invalid_signature_returns_401`
- **Role-Based Access Control (6 tests):**
  - `test_admin_allowed_on_privileged_alert_patch`
  - `test_maintenance_engineer_allowed_on_alert_patch`
  - `test_operator_forbidden_from_alert_patch_403`
  - `test_operator_allowed_on_read_endpoints`
  - `test_operator_allowed_to_submit_feedback`
  - `test_unauthenticated_request_to_machines_returns_401`
- **Command Guard & Scenarios (7 tests):**
  - `test_list_scenarios_authenticated`
  - `test_inject_scenario_admin_success`
  - `test_inject_scenario_engineer_success`
  - `test_inject_scenario_operator_forbidden_403`
  - `test_inject_scenario_invalid_machine_404`
  - `test_inject_scenario_invalid_scenario_id_422`
  - `test_inject_scenario_arbitrary_code_command_rejected_422`
- **WebSocket Authentication (6 tests):**
  - `test_ws_unauthenticated_connection_rejected`
  - `test_ws_valid_token_accepted`
  - `test_ws_valid_token_single_machine_accepted`
  - `test_ws_invalid_token_rejected`
  - `test_ws_expired_token_rejected`
  - `test_ws_inactive_user_rejected`
- **Security Hardening (3 tests):**
  - `test_security_headers_present`
  - `test_cors_disallows_wildcard_with_credentials`
  - `test_password_and_jwt_not_in_audit_logs`

---

## 18. Full test result

Executed the complete pytest suite via `.\.venv\Scripts\pytest.exe`:
```
561 passed, 1 skipped, 41 warnings in 221.67s (0:03:41)
```
- Baseline before S15: 525 passed, 1 skipped
- Tests after S15: 561 passed, 1 skipped (36 new security tests)
- Regressions: 0

---

## 19. Ruff

Ran `.\.venv\Scripts\ruff.exe check .`:
```
All checks passed!
```
Zero lint warnings or errors.

---

## 20. Black

Ran `.\.venv\Scripts\black.exe --check .`:
```
All done! ✨ 🍰 ✨
125 files would be left unchanged.
```
All files formatted according to the project's 100-character line length configuration.

---

## 21. Security verification

- Audited repository for hardcoded secrets: none found.
- Plaintext passwords: never persisted or returned.
- JWT token leakage: excluded from audit logs and exception messages.
- Permissive CORS: wildcard prohibited when credentials enabled.
- Authorization: server-side dependency enforcement across all operational REST and WebSocket routes.
- Command safety: arbitrary command and shell execution rejected.
- SQL injection: all queries parameterized via SQLAlchemy Core and ORM.

---

## 22. Held-out test verification

- The held-out test data directory `data/test/` was **never opened, never modified, never evaluated against, and never used for retraining**.
- ML model weights, thresholds ($t^* = 0.16$), and calibration parameters remain 100% frozen.

---

## 23. Regression verification

- Telemetry MQTT ingestion and database persistence: verified functional.
- ML inference, health engine, and alert persistence: verified functional.
- Digital Twin real-time state calculation: verified functional.
- S14 REST API v1 endpoints: verified functional with authenticated test client.
- Database migrations: verified with up/down test.

---

## 24. Known limitations

- **Refresh Tokens:** Access tokens are short-lived Bearer tokens without automatic refresh token rotation. Token refreshing will be implemented if required by frontend requirements.
- **External OAuth/OIDC:** Authentication is local and self-contained; integration with enterprise Identity Providers (Okta, Keycloak, Azure AD) is out of scope for the current phase.
- **In-Memory Rate Limiting:** Advanced distributed rate limiting (e.g. via Redis) is omitted in favor of lightweight application-level protection.

---

## 25. Scope confirmation

Explicitly confirming:
- S16 firmware work was **NOT** implemented in this session.
- S18 Wokwi/backend E2E was **NOT** implemented in this session.
- Frontend was **NOT** implemented.
- MLOps drift/retraining pipeline was **NOT** implemented.
- ML models and parameters were **NOT** modified.

---

## 26. Next session

**S16 — ESP32 Firmware v1 Integration & Verification**
- Tasks: T-041 / T-042 ESP32 firmware integration, sensor simulation mapping, telemetry contract compliance, and edge trip logic verification.
