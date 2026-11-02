# AquaMind security and credential response

## Incident: tracked root environment file

A local root `.env` containing populated application and database credentials was found in the public Git history on 2026-11-03. It has been deleted from the current tracked branch and ignore rules have been added. **Deletion from the current branch does not revoke credentials or remove earlier Git history.** Treat every credential in that file as exposed, including database access, admin credentials, JWT signing material, and application secret keys.

## Required immediate actions (repository owner)

1. Rotate the PostgreSQL role password referenced by the exposed `DATABASE_URL`; update the database connection configuration on every running deployment. Verify whether the database is reachable outside the trusted network.
2. Replace `ADMIN_PASSWORD` (and the existing admin user's actual stored password using the supported user/password-management flow). If reused anywhere, replace those passwords too.
3. Replace `JWT_SECRET_KEY` and `SECRET_KEY` with fresh cryptographically secure independent values. Rotating JWT signing keys invalidates previously signed tokens; require fresh logins and revoke active refresh sessions if the application stores them. Locate all dependent services before rotating.
4. Check any additional tokens, passwords, or credentials referenced by previous versions of `.env`, old commits, deployment files, or logs. Revoke/rotate as applicable.
5. Audit GitHub access and relevant authentication, database, and application logs for unexpected activity. Avoid posting credential values in issues or logs.
6. Arrange **Git history remediation** (e.g. `git-filter-repo` or GitHub's sensitive-data removal guidance). Rewriting history affects collaborators, open PRs, clones, and signed commits; coordinate and back up first. Force-pushing a sanitized history does not revoke leaked credentials and may not remove all cached copies or forks. Follow up with GitHub Support where applicable.
7. Enable repository security features in **Settings → Security & analysis**: secret scanning, push protection (where eligible), Dependabot alerts and security updates; configure branch protection/rulesets and require code review and CI checks for `main`.

## Safe local configuration

Use tracked `.env.example` only as a template. Create `.env` on each deployment or developer machine with unique values. Do not add real secrets to examples, commits, test snapshots, frontend `VITE_*` variables, bug reports, or container images. Files called `*.env` under `backend/deploy/` may contain configuration templates; audit any new non-template secret before committing.

Example secure key generation:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Generate distinct keys separately; do not reuse the exposed ones.

## Validation

```bash
git ls-files .env
git check-ignore -v .env
git status --short
```

The first command should have no output, and the second should identify an ignore rule. **Previously committed environment files remain reachable in Git history until separately remediated.**

## Physical safety

Changing software security controls must not inadvertently energize relays or pumps. Preserve `HARDWARE_ENABLED=false` on development systems, keep physical emergency-stop and fail-safe procedures available, and verify actuator behavior before modifying any live Raspberry Pi deployment.
