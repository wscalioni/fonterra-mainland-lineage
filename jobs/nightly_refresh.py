"""Placeholder — replaced in Task 14."""
import argparse

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--warehouse-id", required=True)
    p.add_argument("--working-schema", required=True)
    args = p.parse_args()
    print(f"placeholder: warehouse={args.warehouse_id} schema={args.working_schema}")
