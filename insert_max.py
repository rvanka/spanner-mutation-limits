import argparse
import logging
import os
import sys
from google.cloud import spanner

os.environ["GOOGLE_CLOUD_SPANNER_METRICS_ENABLED"] = "false"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# This is the exact physical limit threshold (100MB) for this specific table schema
MAX_INSERT_ROWS = 466186 

def main():
    parser = argparse.ArgumentParser(description="Spanner Max Insert Limits Test")
    parser.add_argument("--project", required=True, help="Google Cloud Project ID")
    parser.add_argument("--instance", required=True, help="Spanner Instance ID")
    parser.add_argument("--database", required=True, help="Spanner Database ID")
    args = parser.parse_args()

    client = spanner.Client(project=args.project, disable_builtin_metrics=True)
    instance = client.instance(args.instance)
    
    if not instance.exists():
        logger.info(f"Instance {args.instance} does not exist. Creating...")
        instance.configuration_name = f"{client.project_name}/instanceConfigs/regional-us-central1"
        instance.display_name = "Spanner Limits Test"
        instance.node_count = 1
        op = instance.create()
        op.result(1200)
        logger.info("Instance created.")
    
    database = instance.database(args.database, ddl_statements=[
        "CREATE TABLE TestTable (Id INT64 NOT NULL, Val STRING(MAX)) PRIMARY KEY (Id)"
    ])
    if database.exists():
        logger.info(f"Database {args.database} already exists. Dropping for a clean slate...")
        database.drop()
        logger.info("Database dropped.")
        
    logger.info(f"Creating database {args.database}...")
    op = database.create()
    op.result(120)
    logger.info("Database created.")
    
    database.log_commit_stats = True
    
    def run_insert(transaction):
        logger.info(f"Attempting to insert {MAX_INSERT_ROWS} rows in a single transaction...")
        remaining = MAX_INSERT_ROWS
        curr_id = 1
        total_inserted = 0
        
        while remaining > 0:
            # We must keep each DML statement under the 80k mutation counter (40k rows * 2 columns)
            # We batch them in 35k chunks per statement to bypass the counter limit.
            chunk = min(remaining, 35000)
            end_id = curr_id + chunk - 1
            sql = f"INSERT INTO TestTable (Id, Val) SELECT x, 'limit_test' FROM UNNEST(GENERATE_ARRAY({curr_id}, {end_id})) AS x"
            rows = transaction.execute_update(sql)
            total_inserted += rows
            curr_id += chunk
            remaining -= chunk
        
        logger.info(f"DML statements executed. Total rows queued for commit: {total_inserted}")

    try:
        database.run_in_transaction(run_insert)
        logger.info("Transaction committed successfully.")
    except Exception as e:
        logger.error(f"Transaction failed: {e}")

if __name__ == "__main__":
    main()
