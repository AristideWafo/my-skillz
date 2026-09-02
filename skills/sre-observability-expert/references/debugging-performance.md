# Debugging and performance evidence

Read this reference when ordinary logs and service metrics do not explain a failure or performance regression.

## Hypothesis-driven collection

State the question before collecting expensive evidence. Examples:

- Are requests waiting on CPU, I/O, a lock, garbage collection, or a downstream service?
- Is memory growth retained application state, cache growth, native memory, or filesystem cache?
- Is latency caused by DNS, connection establishment, server work, queueing, or retries?

Choose the tool that can distinguish the leading hypotheses with the least impact.

## Risk-bearing tools

Heap dumps, core dumps, packet captures, `strace`, `perf`, debuggers, and profilers can pause processes, consume CPU, fill disks, or capture sensitive data. Before production use:

- prefer a replica or canary when representative;
- estimate output size and overhead;
- bound duration, event count, and path;
- confirm storage permissions and retention;
- define abort criteria;
- obtain required authorization.

## Performance method

1. Establish a baseline and representative workload.
2. Measure latency distribution, throughput, errors, saturation, and queueing together.
3. Attribute time or allocation with suitable telemetry or profiling.
4. Change one meaningful variable.
5. Repeat the same measurement and check for regressions elsewhere.

Do not infer causation from correlation alone. A busy component may be a victim of upstream retries or downstream slowness.

## JVM examples

- Thread dumps help distinguish lock contention, blocked I/O, and runnable CPU work.
- GC logs and heap occupancy trends should precede a large heap dump when they can answer the question.
- Heap dumps may contain credentials and user data; protect them as sensitive artifacts.
- Increasing heap or thread pools can delay failure while worsening downstream saturation. Verify the bottleneck first.

## Done

A performance conclusion is supported by before/after evidence under comparable load, explains the limiting resource or wait, and records tradeoffs in latency, throughput, resource use, and reliability.
