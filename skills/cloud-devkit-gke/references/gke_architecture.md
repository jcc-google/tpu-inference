# GKE Architecture for Cloud-Devkit

## JobSet API
Cloud-devkit leverages the `sigs.k8s.io/jobset` API to manage groups of related pods. This is crucial for:
- **TPU Multi-host**: Ensuring all hosts in a topology start together.
- **Client-Server Coordination**: Running a vLLM server and a benchmark client in the same JobSet for easy networking.

## Persistence and Tracking
- **MongoDB**: Every job created is recorded in a MongoDB database (configured in `.cdk.ini`). This tracks the job ID, owner, creation time, and status.
- **Job Syncer**: A background service (`services/job_syncer`) periodically:
  1. Syncs Kubernetes pod status back to MongoDB.
  2. Archives logs to GCS once a job completes or fails.

## Observability
- **Log Archival**: Logs are stored in `gs://cloud-devkit/jobs/<job-id>/logs/`.
- **Trace Generation**: The `tracegen` utility parses archived logs to create Chrome Trace Event JSON files for Perfetto. It looks for specific patterns:
  - `trace-event: name=... ts=... dur=... pid=... tid=...`
  - `rid=...` (Request IDs for timing)
