# R8 Deployment Load Report

This report exercises the R8 deployment service over HTTP. It is a deployment smoke/load audit, not a production load test.

| Workers | Submitted | Accepted | Rejected | Invalid commits | Latency p50/p95 ms | Throughput proposals/min |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 200 | 120 | 80 | 0 | 0.250 / 0.380 | 173746.85 |
| 4 | 200 | 120 | 80 | 0 | 0.822 / 1.307 | 271099.39 |
| 8 | 200 | 120 | 80 | 0 | 1.743 / 3.136 | 257312.64 |
| 16 | 200 | 120 | 80 | 0 | 3.047 / 5.396 | 11784.96 |

Expected safety criterion: invalid commits must remain 0 at every worker setting.
