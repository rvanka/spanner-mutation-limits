import subprocess
import argparse

def test_rows(rows, project, instance, database):
    print(f"Testing {rows} rows...")
    
    cmd = [
        "./venv/bin/python3", "delete_max.py", 
        "--project", project, 
        "--instance", instance, 
        "--database", database,
        "--rows", str(rows)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if "Delete transaction committed successfully." in result.stdout:
        print(f"Success for {rows}")
        return True
    else:
        print(f"Failed for {rows}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Binary Search Spanner Delete Limits")
    parser.add_argument("--project", required=True, help="Google Cloud Project ID")
    parser.add_argument("--instance", required=True, help="Spanner Instance ID")
    parser.add_argument("--database", required=True, help="Spanner Database ID")
    parser.add_argument("--min", type=int, default=400000, help="Minimum rows")
    parser.add_argument("--max", type=int, default=800000, help="Maximum rows")
    args = parser.parse_args()

    low = args.min
    high = args.max
    best = low

    while low <= high:
        mid = (low + high) // 2
        # To save time, we round to nearest 10k
        mid = (mid // 10000) * 10000
        if test_rows(mid, args.project, args.instance, args.database):
            best = mid
            low = mid + 10000
        else:
            high = mid - 10000

    print(f"Max successful rows: {best}")

if __name__ == "__main__":
    main()
