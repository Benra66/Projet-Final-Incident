# Role and incident access policy

The public homepage is Benson's CV. Sign-in is linked from the site menu. After login, the incident register is scoped by the signed-in user's Django permissions.

| Capability | Reporter | Analyst | Application administrator |
|---|---|---|---|
| Create an incident | Yes | Yes | Yes |
| View own incidents | Yes | Yes | Yes |
| View incidents assigned to them | No | Yes | Yes |
| View every incident | No | No | Yes |
| Comment on an incident they can view | Yes | Yes | Yes |
| Change status/severity | No | Assigned incidents only | Yes |
| Assign an analyst | No | No | Yes |
| Delete an incident | No | No | Yes |
| Django `/admin/` | No | No | Yes, when marked `is_staff` |

Object access is enforced in the queryset used by both list and detail/update/delete views. A reporter who guesses another report's URL receives 404. Delete requires Django's `delete_incident` permission and a CSRF-protected POST. Template controls are convenience only; the server checks permissions independently.

## Roles

`configure_incident_roles` creates three Django Groups and assigns model permissions. Existing users can be assigned after `migrate`:

```bash
python manage.py configure_incident_roles --reporter-username Nazairefabsimple --admin-username Nazairefabadmin
```

An analyst should have an account first, then be assigned with `--analyst-username`. Application administrators are staff for the Django admin site, but are not superusers; their access is limited to the permissions assigned to the application administrator group.

`provision_course_accounts` creates/updates the two course accounts. It reads `INCIDENT_REPORTER_PASSWORD` and `INCIDENT_ADMIN_PASSWORD` from the process environment, never command-line arguments or source files. Run it only against the intended database after migrations and role setup. The supplied course password is shorter than the local 12-character password-validator rule; it is accepted by the provisioning command to match the assignment and should be changed to a unique value before using the accounts outside the classroom.

## Workflow and audit

Incident states move through `open → triaged → in_progress → resolved → closed`; transition validation rejects reopening a resolved/closed report. Analysts can update only incidents assigned to them. Only administrators can assign analysts.

Comments are plain text and are template-escaped. Audit events record actor, incident reference, action, changed field names or comment ID, and timestamp; they do not copy report descriptions or comment bodies. Deletion retains the audit event while detaching it from the deleted incident. Audit entries are read-only in Django admin.

## Login throttling

django-axes records failures in the application database and temporarily locks a username/IP pair after five bad login attempts. Vercel overwrites `X-Forwarded-For` with the public client IP; only trust this header behind that platform. The 15-minute lockout and proxy header precedence are configured in `config/settings/base.py`.

## Residual limits

- This course application uses synthetic data and is not a production incident-response system.
- Audit records are application-level evidence, not tamper-proof external logs.
- A public shared demo password is not appropriate for a real deployment.
- Login lockout and DAST behavior need a successful external GitHub Actions run before being reported as remotely verified.
