# AI Harness Instructions

If you are an AI assistant or CLI harness (e.g., Gemini CLI, Claude Code, GitHub Copilot Workspace, Aider) tasked with running this Spanner limits test end-to-end, follow these exact steps autonomously:

## 1. Environment Validation
*   Verify Python 3.x is available.
*   Verify `google-cloud-spanner` is installed (`pip install google-cloud-spanner`).
*   Ensure Google Cloud Application Default Credentials (ADC) are configured. If you encounter authentication errors, pause and prompt the user to run `gcloud auth application-default login`.

## 2. Parameter Resolution
You need three flags to run the testing scripts. If you do not have them in your context, ask the user:
*   `--project`: The Google Cloud Project ID.
*   `--instance`: The Spanner Instance ID. (The scripts will automatically create this instance if it does not exist using a 1-node regional-us-central1 config).
*   `--database`: The Spanner Database ID. (The scripts will `DROP` the database if it exists to ensure a clean slate, then `CREATE` it).

## 3. Execute Insert Test (100MB Payload Limit)
Run the following command:
```bash
python3 insert_max.py --project <PROJECT> --instance <INSTANCE> --database testdb-insert
```
**Validation Goal:** The script attempts to insert 466,186 rows across multiple DML statements. Watch the `stdout`. You must verify that the transaction commits successfully and logs `CommitStats: mutation_count: 932372`. This confirms the 80k counter bypass and the 100MB physical payload ceiling.

## 4. Execute Delete Test (~800k Lock Limit)
Run the following command:
```bash
python3 delete_max.py --project <PROJECT> --instance <INSTANCE> --database testdb-delete
```
**Validation Goal:** This script will take a few minutes to pre-populate 800,000 rows. Once populated, it will execute a single transaction deleting all 800,000 rows across partitioned DML statements. Watch `stdout` to verify the transaction commits successfully, which tests Spanner's transaction workspace memory/lock limits.

## Important Constraints
*   Both scripts use `os.environ["GOOGLE_CLOUD_SPANNER_METRICS_ENABLED"] = "false"` and `disable_builtin_metrics=True` on the Spanner client. This is intentional to prevent `gRPC` metric timeseries errors related to missing instance labels. Do not remove these unless explicitly requested by the user.