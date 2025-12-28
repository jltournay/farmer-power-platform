# ADR-003: Identity & Access Management

**Status:** Accepted
**Date:** 2025-12-26
**Deciders:** Winston (Architect), Jeanlouistournay
**Related Stories:** Story 0.5.6 (BFF Service Setup), Platform Admin UI (User Management)

## Context

The Farmer Power Platform requires identity and access management for multiple user types across 4 frontend applications:

| Application | User Types | Auth Requirements |
|-------------|------------|-------------------|
| factory-portal | Factory Manager, Factory Owner, Factory Admin | Multi-tenant (factory isolation) |
| platform-admin | Platform Administrator | Internal only, super-admin |
| regulator | Tea Board of Kenya officials | Government isolation, read-only aggregates |
| registration-kiosk | Registration Clerks | Long-lived sessions, offline capability |

### Requirements from Epics

- **NFR26**: OAuth2/OpenID Connect authentication
- **NFR27**: RBAC roles: Admin, FactoryManager, FactoryViewer, Regulator
- **Story 3.1**: OAuth2 token validation via Azure AD B2C
- **NFR23**: Kenya Data Protection Act 2019 compliance

### Key Questions to Answer

1. Where does user data live?
2. How are users associated with factories?
3. How are roles and permissions structured?
4. How is the Regulator (TBK) isolated from factory data?
5. How do registration clerks authenticate on kiosk devices?

## Decision

### Identity Provider: Azure AD B2C

**Selected:** Azure Active Directory B2C as the identity provider.

| Factor | Azure AD B2C | Auth0 | Keycloak |
|--------|--------------|-------|----------|
| Cost at scale | Included in Azure | Per-MAU pricing | Self-hosted cost |
| Azure integration | Native | Requires config | Requires config |
| Custom claims | Yes (custom policies) | Yes | Yes |
| B2B federation | Built-in | Add-on | Complex |
| Kenya compliance | Azure Africa regions | US/EU only | Self-hosted option |
| Offline tokens | Refresh tokens | Refresh tokens | Refresh tokens |

**Rationale:**
- Platform already uses Azure (Blob Storage, AKS, CosmosDB)
- Azure Africa (South Africa) region for data residency
- B2B federation for Regulator (TBK) government identity
- No additional vendor, unified billing

### Azure AD B2C Pricing

Azure AD B2C uses **Monthly Active Users (MAU)** pricing:

| Tier | MAUs | Cost |
|------|------|------|
| **Free** | First 50,000 MAUs/month | $0 |
| **Premium P1** | 50,001+ | ~$0.00325 per MAU |
| **Premium P2** | 50,001+ (advanced features) | ~$0.01625 per MAU |

**What counts as a MAU?** A user who authenticates at least once in a calendar month.

**Farmer Power Platform Cost Estimate:**

| User Type | Estimated Count | Monthly Cost |
|-----------|-----------------|--------------|
| Factory Managers | ~100 | Free tier |
| Factory Owners | ~100 | Free tier |
| Factory Admins | ~100 | Free tier |
| Registration Clerks | ~500 | Free tier |
| Platform Admins | ~10 | Free tier |
| Regulators | ~50 | Free tier |
| **Total** | **~860 users** | **$0** |

At Kenya scale (100 factories), we're well within the 50K free tier.

### User Account Types

**Users do NOT need a Microsoft account.** Azure AD B2C supports multiple account types:

| Account Type | Description | Used For |
|--------------|-------------|----------|
| **Local Account** | Email + password stored in B2C | Factory staff, clerks (primary) |
| **B2B Guest** | Federated from external Azure AD | Regulator (TBK government) |
| **Social Identity** | Google, Facebook, etc. | Not used |

**Example local account:**
```
Email: joseph@kerichoFactory.co.ke  (any email domain, not Microsoft)
Password: stored securely in Azure AD B2C
MFA: SMS or Authenticator app
```

### User Creation Flow

Self-service sign-up is **disabled**. Users are created by administrators:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADMIN-CREATED USER FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Admin creates user (Platform Admin UI or Factory Owner)    │
│     ┌────────────────────────────────────────┐                  │
│     │ POST to Microsoft Graph API            │                  │
│     │ {                                      │                  │
│     │   "email": "joseph@kericho.co.ke",     │                  │
│     │   "displayName": "Joseph Mwangi",      │                  │
│     │   "role": "factory_manager",           │                  │
│     │   "factory_id": "KEN-fac-001"          │                  │
│     │ }                                      │                  │
│     └────────────────────────────────────────┘                  │
│                         │                                       │
│                         ▼                                       │
│  2. Azure AD B2C creates local account                          │
│     - Generates temporary password OR password-less invite      │
│     - Stores custom attributes (role, factory_id)               │
│                         │                                       │
│                         ▼                                       │
│  3. Welcome email sent to user                                  │
│     "Welcome to Farmer Power - Click to set your password"      │
│                         │                                       │
│                         ▼                                       │
│  4. User clicks link, sets password, configures MFA             │
│                         │                                       │
│                         ▼                                       │
│  5. User can now sign in to their assigned application          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Who can create users:**

| Creator | Can Create Roles | Scope |
|---------|------------------|-------|
| Platform Admin | All roles | Any factory |
| Factory Owner | factory_manager, factory_admin, factory_viewer, registration_clerk | Own factory only |

### Tenant Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     AZURE AD B2C TENANT                                  │
│                   (farmerpower.onmicrosoft.com)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    USER FLOWS                                    │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │                                                                  │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │
│  │  │ Factory      │  │ Platform     │  │ Regulator            │  │    │
│  │  │ Sign-In      │  │ Admin        │  │ (B2B Federation)     │  │    │
│  │  │              │  │ Sign-In      │  │                      │  │    │
│  │  │ Email/Pass   │  │              │  │ TBK Azure AD tenant  │  │    │
│  │  │ + MFA        │  │ Email/Pass   │  │ federated via        │  │    │
│  │  │              │  │ + MFA        │  │ B2B invite           │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │
│  │                                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │ Kiosk Sign-In (Device Code Flow)                         │   │    │
│  │  │ - Clerk logs in once per shift                           │   │    │
│  │  │ - Long-lived refresh token (8 hours)                     │   │    │
│  │  │ - Offline capability via cached token                    │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### User Model

Users are stored in **Azure AD B2C directory** with custom attributes. No separate User collection in MongoDB.

```yaml
# Azure AD B2C User Object (extended schema)
user:
  # ═══════════════════════════════════════════════════════════════════
  # STANDARD CLAIMS (Azure AD B2C built-in)
  # ═══════════════════════════════════════════════════════════════════
  objectId: "uuid"                    # Azure AD object ID (sub claim)
  displayName: "Joseph Mwangi"
  givenName: "Joseph"
  surname: "Mwangi"
  email: "joseph@kerichoFactory.co.ke"
  mobilePhone: "+254712345678"
  accountEnabled: true

  # ═══════════════════════════════════════════════════════════════════
  # CUSTOM ATTRIBUTES (extension_<app-id>_<attribute>)
  # ═══════════════════════════════════════════════════════════════════
  extension_farmerpower_role: "factory_manager"     # Primary role
  extension_farmerpower_factory_id: "KEN-fac-001"   # Factory assignment
  extension_farmerpower_factory_ids: ["KEN-fac-001", "KEN-fac-002"]  # Multi-factory (owners)
  extension_farmerpower_collection_point_id: "KEN-cp-001"  # For clerks
  extension_farmerpower_region_ids: ["nandi", "kericho"]   # For regulators (scope)
```

### Role Definitions

| Role | Code | Scope | Description |
|------|------|-------|-------------|
| **Platform Admin** | `platform_admin` | Global | Farmer Power internal team, full system access |
| **Factory Owner** | `factory_owner` | Factory(s) | Business owner, ROI dashboards, can have multiple factories |
| **Factory Manager** | `factory_manager` | Factory | Quality manager (Joseph), daily operations |
| **Factory Admin** | `factory_admin` | Factory | Factory settings, SMS templates, payment policies |
| **Factory Viewer** | `factory_viewer` | Factory | Read-only access to factory data |
| **Registration Clerk** | `registration_clerk` | Collection Point | Farmer registration at kiosk |
| **Regulator** | `regulator` | Region(s) | Tea Board of Kenya, aggregated read-only data |

### Role Hierarchy

```
platform_admin
    │
    ├── factory_owner (can do everything factory_manager can)
    │       │
    │       ├── factory_manager (can do everything factory_viewer can)
    │       │       │
    │       │       └── factory_viewer (read-only)
    │       │
    │       └── factory_admin (settings only, not operations)
    │
    └── registration_clerk (isolated to registration)

regulator (completely separate, no hierarchy with factory roles)
```

### Permission Matrix

| Resource | platform_admin | factory_owner | factory_manager | factory_admin | factory_viewer | registration_clerk | regulator |
|----------|----------------|---------------|-----------------|---------------|----------------|-------------------|-----------|
| **Farmers (own factory)** | CRUD | Read | Read | Read | Read | Create | - |
| **Farmers (all)** | CRUD | - | - | - | - | - | Aggregates |
| **Quality Events** | CRUD | Read | Read | Read | Read | - | Aggregates |
| **Diagnoses** | CRUD | Read | Read | Read | Read | - | Aggregates |
| **Action Plans** | CRUD | Read | Read | Read | Read | - | - |
| **SMS Templates** | CRUD | Read | Read | CRUD | Read | - | - |
| **Payment Policies** | CRUD | CRUD | Read | CRUD | Read | - | - |
| **Factory Settings** | CRUD | CRUD | Read | CRUD | Read | - | - |
| **User Management** | CRUD | Create (own factory) | - | - | - | - | - |
| **System Config** | CRUD | - | - | - | - | - | - |
| **National Stats** | Read | - | - | - | - | - | Read |
| **Regional Stats** | Read | Own factory | Own factory | Own factory | Own factory | - | Own regions |

### JWT Token Claims

```json
{
  "iss": "https://farmerpower.b2clogin.com/...",
  "sub": "12345678-1234-1234-1234-123456789012",
  "aud": "farmer-power-api",
  "exp": 1703612400,
  "iat": 1703608800,

  "name": "Joseph Mwangi",
  "email": "joseph@kerichoFactory.co.ke",

  "extension_farmerpower_role": "factory_manager",
  "extension_farmerpower_factory_id": "KEN-fac-001",
  "extension_farmerpower_factory_ids": ["KEN-fac-001"],
  "extension_farmerpower_collection_point_id": null,
  "extension_farmerpower_region_ids": null,

  "roles": ["factory_manager"],
  "permissions": [
    "farmers:read",
    "quality_events:read",
    "diagnoses:read",
    "action_plans:read",
    "sms_templates:read",
    "payment_policies:read"
  ]
}
```

### BFF Authorization Flow

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  React   │     │   Azure AD   │     │     BFF     │     │   Backend    │
│   App    │     │     B2C      │     │  (FastAPI)  │     │   Services   │
└────┬─────┘     └──────┬───────┘     └──────┬──────┘     └──────┬───────┘
     │                  │                    │                   │
     │  1. Login        │                    │                   │
     │─────────────────▶│                    │                   │
     │                  │                    │                   │
     │  2. JWT Token    │                    │                   │
     │◀─────────────────│                    │                   │
     │                  │                    │                   │
     │  3. API Request (Bearer token)        │                   │
     │──────────────────────────────────────▶│                   │
     │                  │                    │                   │
     │                  │  4. Validate JWT   │                   │
     │                  │◀───────────────────│                   │
     │                  │                    │                   │
     │                  │  5. Token valid +  │                   │
     │                  │     claims         │                   │
     │                  │───────────────────▶│                   │
     │                  │                    │                   │
     │                  │                    │  6. Check permission
     │                  │                    │  (role + factory_id)
     │                  │                    │                   │
     │                  │                    │  7. gRPC call with
     │                  │                    │  factory_id filter
     │                  │                    │──────────────────▶│
     │                  │                    │                   │
     │                  │                    │  8. Filtered data │
     │                  │                    │◀──────────────────│
     │                  │                    │                   │
     │  9. Response     │                    │                   │
     │◀──────────────────────────────────────│                   │
     │                  │                    │                   │
```

### BFF Authorization Middleware

```python
# bff/src/bff/api/auth.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import List, Optional

class TokenClaims(BaseModel):
    sub: str  # User ID (Azure AD object ID)
    email: str
    name: str
    role: str
    factory_id: Optional[str] = None
    factory_ids: List[str] = []
    collection_point_id: Optional[str] = None
    region_ids: List[str] = []
    permissions: List[str] = []

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> TokenClaims:
    """Validate JWT and extract claims."""
    try:
        # Validate with Azure AD B2C public keys
        payload = await validate_azure_token(credentials.credentials)
        return TokenClaims(
            sub=payload["sub"],
            email=payload.get("email", ""),
            name=payload.get("name", ""),
            role=payload.get("extension_farmerpower_role", ""),
            factory_id=payload.get("extension_farmerpower_factory_id"),
            factory_ids=payload.get("extension_farmerpower_factory_ids", []),
            collection_point_id=payload.get("extension_farmerpower_collection_point_id"),
            region_ids=payload.get("extension_farmerpower_region_ids", []),
            permissions=payload.get("permissions", []),
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_permission(permission: str):
    """Decorator to check permission."""
    async def checker(user: TokenClaims = Depends(get_current_user)):
        if permission not in user.permissions and user.role != "platform_admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

def require_factory_access(factory_id_param: str = "factory_id"):
    """Ensure user has access to the requested factory."""
    async def checker(
        user: TokenClaims = Depends(get_current_user),
        factory_id: str = None
    ):
        if user.role == "platform_admin":
            return user  # Platform admins can access all

        if user.role == "regulator":
            raise HTTPException(status_code=403, detail="Regulators cannot access factory data")

        # Check factory access
        allowed_factories = user.factory_ids or ([user.factory_id] if user.factory_id else [])
        if factory_id not in allowed_factories:
            raise HTTPException(status_code=403, detail="No access to this factory")

        return user
    return checker
```

### User Management in Platform Admin

Platform Admin UI provides user management screens:

```yaml
# User Management Operations
operations:
  # Factory Owner can:
  - invite_factory_user:
      roles: [factory_manager, factory_admin, factory_viewer, registration_clerk]
      scope: own_factory_only

  # Platform Admin can:
  - create_any_user:
      roles: [all]
      scope: global

  - assign_factory:
      description: "Link user to factory"

  - manage_regulator:
      description: "Invite TBK users via B2B"
```

### Regulator Isolation (B2B Federation)

Tea Board of Kenya users authenticate via their own Azure AD tenant:

```yaml
regulator_federation:
  type: azure_ad_b2b

  # TBK has their own Azure AD tenant
  tbk_tenant: teaboardkenya.go.ke

  # Users are invited as B2B guests
  invitation_flow:
    - Platform Admin sends B2B invitation to TBK email
    - TBK user accepts, authenticates with their own credentials
    - User appears in Farmer Power tenant as guest
    - Custom attributes assigned (role=regulator, region_ids=[...])

  # Data isolation
  isolation:
    - Regulator users can ONLY access aggregated statistics
    - No individual farmer PII exposed
    - No factory-level operational data
    - Region-scoped queries only
```

### Registration Kiosk Authentication

```yaml
kiosk_auth:
  flow: device_code_flow

  # Clerk authentication
  login:
    - Clerk opens kiosk app
    - App displays device code
    - Clerk enters code at login.farmerpower.co.ke on their phone
    - Clerk authenticates with email/password + MFA
    - Kiosk receives tokens

  # Token management
  tokens:
    access_token_lifetime: 1 hour
    refresh_token_lifetime: 8 hours  # Full shift
    offline_access: true

  # Offline capability
  offline:
    - Tokens cached in secure storage (encrypted)
    - Registrations queued locally
    - Sync when back online
    - Token refresh attempted on reconnect
```

### Frontend Auth Library

Shared authentication library for all 4 frontend apps:

```
libs/
└── auth/                          # @fp/auth
    ├── src/
    │   ├── AuthProvider.tsx       # React context provider
    │   ├── useAuth.ts             # Hook: login, logout, user
    │   ├── usePermission.ts       # Hook: check permissions
    │   ├── ProtectedRoute.tsx     # Route guard component
    │   ├── config.ts              # Azure AD B2C config
    │   └── types.ts               # TokenClaims, User types
    ├── package.json               # @fp/auth
    └── tsconfig.json
```

**Usage:**

```typescript
// In any frontend app
import { AuthProvider, useAuth, ProtectedRoute, usePermission } from '@fp/auth';

function App() {
  return (
    <AuthProvider config={azureConfig}>
      <Routes>
        <Route path="/command-center" element={
          <ProtectedRoute roles={['factory_manager', 'factory_owner']}>
            <CommandCenter />
          </ProtectedRoute>
        } />
      </Routes>
    </AuthProvider>
  );
}

function SomeComponent() {
  const { user, logout } = useAuth();
  const canEditTemplates = usePermission('sms_templates:write');

  return (
    <div>
      <p>Welcome, {user.name}</p>
      {canEditTemplates && <EditButton />}
    </div>
  );
}
```

## Consequences

### Positive

- **Single identity provider** - No separate user database to sync
- **Factory isolation** - Users only see their factory's data
- **Regulator isolation** - B2B federation keeps TBK completely separate
- **Offline kiosk** - Device code flow enables long sessions
- **Standard claims** - Permissions in JWT, no database lookup per request
- **Shared auth library** - Consistent auth across all 4 apps

### Negative

- **Azure lock-in** - Tied to Azure AD B2C
- **Custom attributes limit** - Max 15 custom attributes per user
- **B2B complexity** - Regulator federation requires coordination with TBK IT
- **Token size** - Permissions in token increases JWT size

### Mitigations

| Risk | Mitigation |
|------|------------|
| Azure lock-in | Standard OIDC, could migrate to another provider |
| Custom attribute limit | Use JSON encoding for complex data if needed |
| B2B coordination | Start with manual user creation, add federation later |
| Token size | Use role-based permissions (resolve at BFF), not enumerate all |

## Repository Structure Update

Add to `libs/`:

```
libs/
├── fp-common/           # Python
├── fp-proto/            # Python
├── fp-testing/          # Python
├── ui-components/       # React (from ADR-002)
└── auth/                # React: Shared auth library (NEW)
    ├── package.json     # @fp/auth
    └── src/
        ├── AuthProvider.tsx
        ├── useAuth.ts
        ├── usePermission.ts
        ├── ProtectedRoute.tsx
        └── types.ts
```

## Azure AD B2C Configuration

### Custom Policies Required

1. **Sign-in policy** - Email/password + MFA
2. **Sign-up policy** - Disabled (admin-only user creation)
3. **Password reset** - Self-service
4. **Profile edit** - Limited (name, phone only)
5. **B2B invitation** - For regulator federation

### API Permissions

```yaml
api_permissions:
  - name: farmer-power-api
    scopes:
      - farmers.read
      - farmers.write
      - quality.read
      - quality.write
      - settings.read
      - settings.write
      - admin.full
```

## References

- [Azure AD B2C Documentation](https://docs.microsoft.com/en-us/azure/active-directory-b2c/)
- [Azure AD B2B Federation](https://docs.microsoft.com/en-us/azure/active-directory/external-identities/)
- NFR26: OAuth2/OpenID Connect authentication
- NFR27: RBAC roles
- Story 0.5.6: BFF Service Setup
- ADR-002: Frontend Architecture (4 apps requiring auth)
