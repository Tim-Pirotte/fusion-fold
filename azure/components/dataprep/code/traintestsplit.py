import os
import argparse
import pandas as pd
from sklearn.model_selection import train_test_split


def split_data(
    processed_data_path: str,
    output_dir: str,
    test_size: float = 0.1,
    random_state: int = 42,
):
    print(f"Loading processed data from {processed_data_path}...")
    X = pd.read_parquet(processed_data_path)

    unique_ids = X["target_id"].unique()
    print(f"Total sequences: {len(unique_ids)}")

    train_ids, val_ids = train_test_split(unique_ids, test_size=test_size, random_state=random_state)

    train = X[X["target_id"].isin(train_ids)]
    val = X[X["target_id"].isin(val_ids)]

    print(f"Train sequences: {len(train_ids)}, Val sequences: {len(val_ids)}")

    os.makedirs(output_dir, exist_ok=True)

    train_path = os.path.join(output_dir, "train.parquet")
    val_path = os.path.join(output_dir, "val.parquet")

    train.to_parquet(train_path, index=False)
    val.to_parquet(val_path, index=False)

    print(f"Saved train split to {train_path}")
    print(f"Saved val split to {val_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--processed_data_path",
        type=str,
        required=True,
        help="Path to processed_data.parquet",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./outputs/splits",
        help="Where to save train/val splits",
    )
    parser.add_argument("--test_size", type=float, default=0.1)
    parser.add_argument("--random_state", type=int, default=42)
    args = parser.parse_args()

    split_data(args.processed_data_path, args.output_dir, args.test_size, args.random_state)
