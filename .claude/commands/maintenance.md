---
name: maintenance
description: Use when the codebase needs cleanup, organization, documentation updates, or general hygiene - runs comprehensive maintenance using /geminiplan for planning
---

# Codebase Maintenance Skill

This skill performs comprehensive codebase maintenance. Use it periodically or when the codebase feels cluttered.

## MANDATORY WORKFLOW

1. **Use /geminiplan to create the maintenance plan** - Do NOT skip this step
2. Execute the plan in batches with verification between each
3. Commit changes at logical checkpoints

## MAINTENANCE CATEGORIES

### 1. File Cleanup
- [ ] Delete temporary files: `*.log`, `*.tmp`, `*.pyc`, `__pycache__/`
- [ ] Remove old exports/outputs that are no longer needed
- [ ] Clean up duplicate or redundant files
- [ ] Archive stale data files (>30 days old with no references)
- [ ] Remove empty directories

### 2. Code Hygiene
- [ ] Identify and remove dead code (unused functions, imports)
- [ ] Check for TODO/FIXME comments that are done or outdated
- [ ] Remove commented-out code blocks
- [ ] Consolidate duplicate logic

### 3. File Organization
- [ ] Ensure files are in correct directories per project structure
- [ ] Move misplaced files to appropriate locations
- [ ] Verify naming conventions are consistent
- [ ] Check that test files are in tests/ directories

### 4. Documentation Updates
- [ ] Update README.md to reflect current state
- [ ] Sync CLAUDE.md with actual codebase capabilities
- [ ] Update TODO.md (remove done items, add discovered items)
- [ ] Verify docstrings match function behavior
- [ ] Update inline comments if code has changed

### 5. Dependency Audit
- [ ] Check for outdated packages: `pip list --outdated` / `npm outdated`
- [ ] Review unused dependencies
- [ ] Run security audit: `pip-audit` / `npm audit`
- [ ] Sync requirements.txt / package.json with actual imports

### 6. Git Hygiene
- [ ] Check for large uncommitted changes that should be committed
- [ ] Review .gitignore for missing patterns
- [ ] Identify files that shouldn't be tracked
- [ ] List stale local branches that can be deleted

### 7. Configuration Cleanup
- [ ] Check .env files for unused variables
- [ ] Verify config files are up to date
- [ ] Remove deprecated config options
- [ ] Ensure sensitive data isn't hardcoded

### 8. Data/Output Cleanup
- [ ] Remove stale JSON exports in data/ directories
- [ ] Clean up old log files
- [ ] Archive or delete old scraper outputs
- [ ] Verify data files are properly gitignored

### 9. Health Checks
- [ ] Verify database connections are working
- [ ] Test API keys are still valid (don't expose them)
- [ ] Check external service integrations (Gmail, etc.)
- [ ] Verify scheduled tasks/crons are running
- [ ] Test critical endpoints/functions still work

### 10. Performance Audit
- [ ] Identify slow database queries
- [ ] Find large files that could be compressed/archived
- [ ] Check for memory leaks or resource hogs
- [ ] Review inefficient loops or N+1 query patterns
- [ ] Profile slow scripts/functions

### 11. Secrets Scan
- [ ] Scan for accidentally committed credentials
- [ ] Check for hardcoded API keys, passwords, tokens
- [ ] Verify .env files are gitignored
- [ ] Review recent commits for sensitive data leaks
- [ ] Ensure secrets aren't in logs or error messages
```bash
# Quick secrets scan
grep -rn "password\|secret\|api_key\|token" --include="*.py" --include="*.js" . 2>/dev/null | grep -v "\.env\|node_modules\|venv"
```

### 12. Test Coverage
- [ ] Run test suite and note failures
- [ ] Identify untested code paths
- [ ] Check for tests that are skipped or commented out
- [ ] Verify critical functions have test coverage
- [ ] Remove obsolete tests for deleted features

### 13. Error Log Review
- [ ] Summarize recent errors from logs
- [ ] Identify recurring/repeated errors
- [ ] Check for silent failures (errors that don't surface)
- [ ] Review exception handling patterns
- [ ] Document known issues that need fixing

## EXECUTION STEPS

1. **Scan Phase** (read-only)
   ```
   Use /geminiplan with prompt:
   "Perform a comprehensive codebase maintenance audit. Scan for:
   - Temporary/stale files to delete
   - Dead code to remove
   - Documentation that needs updating
   - Dependencies to audit
   - Git hygiene issues
   - Health check failures (DB, APIs, services)
   - Performance issues (slow queries, large files)
   - Secrets/credentials accidentally exposed
   - Test coverage gaps
   - Recurring errors in logs
   Create a prioritized cleanup plan with risk levels."
   ```

2. **Plan Review** - Show user the plan before executing

3. **Execute in Batches:**
   - Batch 1: File cleanup (safe deletions) + Data cleanup
   - Batch 2: Code hygiene + Dead code removal
   - Batch 3: Documentation updates
   - Batch 4: Dependency/config updates
   - Batch 5: Health checks + Performance fixes
   - Batch 6: Security (secrets scan, credential rotation)
   - Batch 7: Test coverage improvements
   - Batch 8: Error resolution (from log review)

4. **Verify** - Run tests after each batch

5. **Commit** - Create descriptive commit after each batch

## SAFETY RULES

- NEVER delete files without showing user first
- NEVER modify code logic during maintenance (cleanup only)
- ALWAYS run tests before and after changes
- CREATE backups before bulk deletions
- ASK before removing anything that might be needed

## QUICK MAINTENANCE (Light Version)

For a quick cleanup without full audit:
```bash
# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Remove temp files
find . -type f -name "*.log" -mtime +7 -delete 2>/dev/null
find . -type f -name "*.tmp" -delete 2>/dev/null

# Show large files that might need attention
find . -type f -size +10M -not -path "./.git/*" 2>/dev/null

# Quick secrets scan
grep -rn "password=\|api_key=\|secret=" --include="*.py" . 2>/dev/null | grep -v venv

# Check for outdated deps
pip list --outdated 2>/dev/null | head -10

# Recent errors in logs
find . -name "*.log" -mtime -1 -exec grep -l "ERROR\|Exception" {} \; 2>/dev/null
```

## RECOMMENDED FREQUENCY

| Frequency | Tasks |
|-----------|-------|
| **Daily** | Error log review (if production) |
| **Weekly** | Quick cleanup (temp files, caches) |
| **Bi-weekly** | Documentation sync, health checks |
| **Monthly** | Full maintenance audit, dependency updates |
| **Quarterly** | Security audit, secrets rotation, test coverage review |
| **After major features** | Dependency audit, code hygiene, performance check |
| **Before releases** | Full test suite, secrets scan, documentation update |

## MAINTENANCE PRIORITY MATRIX

| Issue Type | Priority | Fix Immediately? |
|------------|----------|------------------|
| Exposed secrets | CRITICAL | YES |
| Failing health checks | HIGH | YES |
| Security vulnerabilities | HIGH | Within 24h |
| Failing tests | MEDIUM | Before next commit |
| Outdated dependencies | MEDIUM | Within week |
| Documentation drift | LOW | During maintenance |
| Dead code | LOW | During maintenance |
| Large temp files | LOW | During cleanup |
