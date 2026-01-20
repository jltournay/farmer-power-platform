# Story 9.7: User Management Dashboard

As a **Platform Administrator**,
I want to view and manage users across all factories,
So that I can support user administration tasks.

## Acceptance Criteria

**AC 9.7.1: User List View**

**Given** I navigate to `/users`
**When** the page loads
**Then** I see a table of all platform users with:
  - Name, email
  - Factory assignment
  - Role (platform_admin, factory_admin, factory_manager, clerk)
  - Last login date
  - Status (Active/Disabled)
**And** I can search by name or email
**And** I can filter by factory, role, status

**AC 9.7.2: User Creation**

**Given** I click "+ Add User"
**When** I complete the form
**Then** I provide: name, email, factory (dropdown), role (dropdown)
**And** user is created in Azure AD B2C
**And** welcome email is sent automatically

**AC 9.7.3: User Editing**

**Given** I click on a user row
**When** the user detail panel opens
**Then** I can edit: role, factory assignment
**And** I can reset password (sends reset email)
**And** I can disable/enable account

## Wireframe: User Management

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  👤 USER MANAGEMENT                                              [+ Add User]   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FILTERS                                                                         │
│  Factory: [All ▼]  Role: [All ▼]  Status: [All ▼]  Search: [🔍            ]    │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  NAME            │ EMAIL                │ FACTORY    │ ROLE      │ STATUS │  │
│  │  ────────────────┼──────────────────────┼────────────┼───────────┼────────│  │
│  │  Joseph Kamau    │ joseph@nyeritea.co.ke│ Nyeri Tea  │ Manager   │ ● Active│  │
│  │  Peter Admin     │ peter@farmerpower.ke │ -          │ Platform  │ ● Active│  │
│  │  Jane Wanjiru    │ jane@karatina.co.ke  │ Karatina   │ Admin     │ ● Active│  │
│  │  Mary Clerk      │ mary@nyeritea.co.ke  │ Nyeri Tea  │ Clerk     │ ○ Disabled│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  Showing 24 users                                      [← Previous] [Next →]    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Technical Notes
- Users stored in Azure AD B2C (not local DB)
- Microsoft Graph API for user operations
- Audit log to MongoDB for compliance

## Dependencies
- Story 9.1a: Platform Admin Application Scaffold
- **Story 0.5.8: Azure AD B2C Configuration (BLOCKING)** - Deferred for production deployment

## Status: Deferred
This story is deferred until Story 0.5.8 (Azure AD B2C Configuration) is completed. User management requires Microsoft Graph API access to Azure AD B2C, which is only available after the B2C tenant is configured.

## Story Points: 5

## Human Validation Gate

**⚠️ MANDATORY: This story requires human validation before acceptance.**

| Validation Type | Requirement |
| --------------- | ----------- |
| **Screen Review with Test Data** | Human must validate UI screens with realistic test data loaded |
| **Checklist** | User list with filters, user creation, role assignment, password reset |
| **Approval** | Story cannot be marked "done" until human signs off |

---
