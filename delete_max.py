import argparse
import logging
import os
import sys
from google.cloud import spanner

os.environ["GOOGLE_CLOUD_SPANNER_METRICS_ENABLED"] = "false"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# This is the approximate internal lock limit for DELETE transactions before hitting resource constraints.
MAX_DELETE_ROWS = 800000

def main():
    parser = argparse.ArgumentParser(description="Spanner Max Delete Limits Test")
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
    
    # Pre-population step
    logger.info(f"Populating {MAX_DELETE_ROWS} rows for the delete test (using multiple transactions)...")
    def insert_chunk(txn, s, e):
        sql = f"INSERT INTO TestTable (Id, Val) SELECT x, 'del_test' FROM UNNEST(GENERATE_ARRAY({s}, {e})) AS x"
        txn.execute_update(sql)

    remaining_population = MAX_DELETE_ROWS
    curr_pop_id = 1
    while remaining_population > 0:
        chunk = min(remaining_population, 40000) # Ensure each insert chunk is under 80k mutations
        end_pop_id = curr_pop_id + chunk - 1
        database.run_in_transaction(insert_chunk, curr_pop_id, end_pop_id)
        curr_pop_id += chunk
        remaining_population -= chunk
        
    logger.info("Population complete. Now testing massive delete...")

    def run_delete(transaction):
        logger.info(f"Attempting to delete {MAX_DELETE_ROWS} rows in a single transaction...")
        remaining = MAX_DELETE_ROWS
        curr_id = 1
        total_deleted = 0
        
        while remaining > 0:
            # We must keep each DELETE statement under the 80k mutation counter
            # We batch them in 75k chunks per statement to bypass the counter limit.
            chunk = min(remaining, 75000)
            end_id = curr_id + chunk - 1
            sql = f"DELETE FROM TestTable WHERE Id >= {curr_id} AND Id <= {end_id}"
            rows = transaction.execute_update(sql)
            total_deleted += rows
            curr_id += chunk
            remaining -= chunk
        
        logger.info(f"DML statements executed. Total rows queued for deletion: {total_deleted}")

    try:
        database.run_in_transaction(run_delete)
        logger.info("Delete transaction committed successfully.")
    except Exception as e:
        logger.error(f"Transaction failed: {e}")

if __name__ == "__main__":
    main()
