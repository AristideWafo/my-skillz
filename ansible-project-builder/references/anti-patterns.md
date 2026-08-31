# Ansible review heuristics

Use this list to focus a review. Severity depends on scope and evidence.

| Finding | Why it matters | Preferred response |
|---|---|---|
| Plaintext secret or decrypted artifact in version control | Credential exposure | Stop propagation, assess exposure, rotate if needed, move to approved secret storage |
| Reload or restart before configuration validation | Can interrupt service | Validate the candidate file before notification or disruptive action |
| Imperative command without accurate change/failure conditions | Breaks idempotence and hides failure | Use a suitable module or define tested conditions |
| Unpinned remote role, collection, package, or revision | Uncontrolled change | Apply the project's version and update policy |
| Public input in high-precedence role vars | Callers cannot configure safely | Move to defaults or document intentional immutability |
| Environment values duplicated across unrelated scopes | Effective value becomes unclear | Establish one owner and verify precedence |
| Secret-bearing task without output control | Logs can leak values | Limit output and use `no_log` where necessary |
| Fleet-wide disruptive action without batching | Large blast radius | Choose serial batches and recovery criteria from service capacity |
| `changed_when: false` on a mutating command | Hides state change | Detect the actual change or redesign the operation |
| Check mode presented as proof for unsupported modules | False confidence | State limitations and test in an isolated target |
| New role/layout replacing a coherent existing convention | Unnecessary churn | Preserve the existing pattern unless a concrete defect justifies migration |
| Performance tuning without measurement | Can overload controller or targets | Benchmark a representative run and tune the observed bottleneck |

Do not report style preferences as critical defects. Tie severity to security, correctness, operability, and blast radius.
