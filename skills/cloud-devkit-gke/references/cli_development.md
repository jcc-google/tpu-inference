# CLI Development and Testing

## Rebuilding the CLI
The CLI is written in Go. To apply changes:

```bash
cd ~/cloud-devkit
# Set PATH to include go if necessary
export PATH=$PATH:/usr/local/go/bin 
make build-cli
sudo cp bin/cdk /usr/local/bin/cdk
```

## Local vs. Remote Workflow
1. **Local Changes**: Make changes on your local machine, commit, and push to a feature branch.
2. **Sync on VM**:
   ```bash
   ssh cdk-vm
   cd ~/cloud-devkit
   git pull origin <branch>
   make build-cli
   sudo cp bin/cdk /usr/local/bin/cdk
   ```
3. **Template Variables**: The CLI automatically injects `{{ .HOME }}` and `{{ .USER }}` into recipes for portability.

## Testing
- **Job Listing**: `cdk job list` (shows Running and Other sections). Use `-a` for all including Deleted.
- **Job Creation**: `cdk job create <recipe-name> [KEY=VAL...]`
- **Log Inspection**: `cdk job log <job-id>`
- **Output Sync**: `cdk job sync-outputs <job-id>` (downloads from GCS to `~/cloud-devkit-data/`).
- **Trace Generation**: `cdk job trace <job-id>` (requires synced logs).
