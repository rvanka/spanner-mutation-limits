# Spanner Mutation Limits Demo

> **🤖 AI Agents & Harnesses:** If you are an AI assistant tasked with running this demo, please read the [HARNESS_INSTRUCTIONS.md](HARNESS_INSTRUCTIONS.md) file first for step-by-step automated execution instructions.

This repository demonstrates the absolute maximum physical transaction limits of Google Cloud Spanner when executing Data Manipulation Language (DML) statements.

Specifically, it demonstrates how the historical `80,000` mutation-limit counter is bypassed when executing multiple partitioned DML statements within a single transaction, forcing Spanner to fall back on its physical hard limits:
1. **100 MB Payload Limit:** Limits large payloads like `INSERT`.
2. **~800,000 Lock Limit:** Limits small payloads like `DELETE` due to memory tracking constraints on the Spanner nodes.

## Prerequisites

1.  Python 3.x installed.
2.  `google-cloud-spanner` library installed:
    ```bash
    pip install google-cloud-spanner
    ```
3.  Authenticated with Google Cloud Application Default Credentials:
    ```bash
    gcloud auth application-default login
    ```

## Usage

These scripts accept the following flags:
*   `--project`: Your Google Cloud Project ID.
*   `--instance`: The Spanner Instance ID to use or create.
*   `--database`: The Spanner Database ID to use (this script will **DROP** the database if it already exists to ensure a clean slate).

### 1. Test Maximum Inserts

The `insert_max.py` script identifies the 100 MB commit payload limit. For the given table schema (`Id INT64, Val STRING(MAX)`), exactly **466,186 rows** (which equals **932,372 mutations** because 2 columns are modified per row) fits perfectly into the 100 MB transaction boundary.

```bash
python3 insert_max.py --project your-project-id --instance your-instance-id --database testdb-insert
```

### 2. Test Maximum Deletes

The `delete_max.py` script bypasses the 80k counter limit but stays under the lock limit by targeting 400,000 rows. Spanner can only buffer and hold row locks for roughly 800,000 rows per transaction before running out of transaction workspace memory.

This script first populates the database and then attempts to delete 400,000 rows in a single transaction across multiple DML statements.

```bash
python3 delete_max.py --project your-project-id --instance your-instance-id --database testdb-delete --rows 400000
```

### 3. Binary Search for Max Deletes

The `binary_search.py` script automates the process of finding the exact physical limit for your specific schema and payload by running a binary search over a range of row counts using `delete_max.py`.

```bash
python3 binary_search.py --project your-project-id --instance your-instance-id --database testdb-delete --min 400000 --max 800000
```

### Note on Commit Stats

Both scripts enable `database.log_commit_stats = True`, so upon successful commit, the total mutation count evaluated directly by the Cloud Spanner backend is explicitly logged to standard output.
