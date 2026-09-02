# Container security decisions

Last reviewed: 2026-08-31. Verify current scanner advisories and runtime documentation before changing security tooling.

## Build boundary

- Keep credentials out of `ARG`, `ENV`, copied files, logs, and final layers.
- Use BuildKit secret or SSH mounts for authenticated build steps and confirm later stages cannot access them.
- Restrict build context with `.dockerignore`, but do not rely on ignore rules as the only protection for credentials stored in the repository.
- Verify downloaded artifacts with signatures or checksums from an independent trusted source.

## Supply chain

- Prefer maintained upstream images and an approved registry.
- Pin digests where immutable provenance is required.
- Generate and retain an SBOM when policy or incident response benefits from it.
- Scan the final image, not only dependency manifests or an intermediate tag.
- Sign and verify artifacts when the trust model includes admission or promotion checks.

A clean scan is not proof of safety, and a signed image is not proof that the build inputs were trustworthy.

## Runtime boundary

Apply controls supported by the workload:

- non-root UID/GID;
- minimal Linux capabilities;
- no privileged mode or host namespaces without a demonstrated need;
- read-only root filesystem with explicit writable mounts;
- seccomp/AppArmor/SELinux policy;
- CPU, memory, process, and storage limits;
- network exposure limited to required peers;
- secret delivery outside the image.

Document exceptions with the operation that requires them and the narrower alternatives considered.

## Vulnerability policy

Define blockers from risk, not severity labels alone. Consider exploitability, reachability, environment exposure, fixed versions, compensating controls, and exception expiry. Ensure scanner failures cannot be confused with a clean result.

## Incident considerations

Container scanners and third-party CI actions are themselves supply-chain dependencies. Pin reviewed revisions, follow their advisories, and rotate accessible credentials if compromised code may have executed.

## Validation

Inspect image configuration and history, verify the effective UID and capabilities, run with target restrictions, scan the immutable digest, and test required writes and network access. Record any control that must be enforced by the orchestrator rather than the image.
