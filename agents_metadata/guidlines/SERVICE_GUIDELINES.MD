# Service Guidelines

- Put business logic, orchestration, validation, and domain state transitions in services, not in thin entrypoints such as CLI handlers, notebooks, scripts, or temporary glue code.
- Use services for bounded domain operations and reusable workflow logic.
- Use job modules for executable corpus workflows such as category discovery, article collection, content cleaning, database population, export generation, and scheduled refreshes.
- Use adapters for external systems and infrastructure boundaries such as the MediaWiki API, database access, filesystem exports, HTTP clients, and optional HTML parsing.
- Keep entrypoints thin: parse inputs, construct dependencies, invoke the owning service or job, and shape outputs.
- Validation and data formatting helpers may prepare inputs and outputs, but they should not orchestrate domain workflows that belong in services or jobs.
- When one service needs another, make the dependency explicit through constructor injection, owned fields, or a clear module boundary.
- Service methods should be typed. New non-trivial methods should have clear docstrings describing purpose, inputs, outputs, and raised domain exceptions.
- Keep service methods explicit about the boundary they own. If logic belongs to a more specific component, move it there instead of duplicating wrappers in a broader module.
- Raise domain-specific custom exceptions for expected failures. Preserve more specific downstream exceptions instead of flattening them into generic framework errors.
- Keep logs in services, jobs, and integration adapters for business failures, state transitions, integrations, and recoverable/internal error paths.
- Avoid hidden side effects in unrelated layers. If a module owns a workflow, it should be the clear entry point for that workflow.
- Reuse existing service methods when an appropriate one already exists. If the correct domain method does not exist, add it in the appropriate owning module instead of bypassing the framework structure.
- Design services so they can be composed for alternate crawl configurations, cleaning strategies, storage backends, exports, and corpus-quality checks without rewriting the surrounding flow.
