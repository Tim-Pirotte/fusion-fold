import os
import argparse
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
from scipy.spatial import distance_matrix
from torch.utils.data import Dataset
import torch

MAPPING = {"A": 0, "G": 1, "C": 2, "U": 3}
VALID_BASES = {"A", "U", "G", "C"}

def strip_suffix(x: str) -> str:
    if "_" in x:
        return "_".join(x.split("_")[:-1])
    return x


def unstack_sequences(sequences: pd.DataFrame) -> pd.DataFrame:
    result = sequences.copy()
    result = result.set_index(["ID", "resname", "resid"])
    result.columns = pd.MultiIndex.from_tuples(
        [tuple(col.split("_")) for col in result.columns],
        names=["", "idx"],
    )
    result = result.stack("idx", future_stack=True).reset_index()
    result = result.replace(-1e18, np.nan)
    result = result.dropna(subset=["x", "y", "z"])
    result["target_id"] = result["ID"].map(strip_suffix) + "_" + result["idx"]
    result.drop(columns=["idx", "ID"], inplace=True)
    result = result.reset_index(drop=True)
    return result[["target_id", "resname", "resid", "x", "y", "z"]]


def encode_sequence(str_seq: pd.Series) -> np.ndarray:
    return str_seq.map(MAPPING).to_numpy(dtype=np.uint8)


def get_distance_std_dev(sequence: pd.DataFrame) -> float:
    coords = sequence[["x", "y", "z"]].values
    dist_map = cdist(coords, coords).astype(np.float32)
    mask = ~np.eye(len(coords), dtype=bool)
    return float(dist_map[mask].std() + 1e-6)


def get_coordinates(coordinates: pd.DataFrame, scale: float, t: float = 0) -> np.ndarray:
    coord_values = coordinates[["x", "y", "z"]].values
    coord_values = coord_values - np.mean(coord_values, axis=0)
    coord_values = (coord_values / scale).astype(np.float32)
    noise = np.random.randn(*coord_values.shape)
    coord_values = np.sqrt(1 - t) * coord_values + np.sqrt(t) * noise
    return coord_values.astype(np.float32)


def get_output_tensor(coordinates: pd.DataFrame) -> np.ndarray:
    coord_values = coordinates[["x", "y", "z"]].values
    position_distances = distance_matrix(coord_values, coord_values)
    return position_distances[np.newaxis, :, :].astype(np.float32)

class RNADataset(Dataset):
    def __init__(self, df: pd.DataFrame, presample: bool, min_t: float, max_t: float):
        self.samples = [group.copy() for _, group in df.groupby("target_id")]
        self.ts = None
        self.min_t = min_t
        self.max_t = max_t
        if presample:
            self.ts = [self._sample_t() for _ in range(len(self.samples))]

        self.std_devs = [get_distance_std_dev(seq) for seq in self.samples]

    def _sample_t(self):
        raw_t = torch.distributions.Beta(2, 1).sample()
        return self.min_t + (raw_t * (self.max_t - self.min_t))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sequence = self.samples[idx]
        t = self.ts[idx] if self.ts else self._sample_t()
        std_dev = self.std_devs[idx]
        coordinates = get_coordinates(sequence, std_dev, float(t))
        sequence_encoding = encode_sequence(sequence["resname"])
        target_tensor = get_output_tensor(sequence)
        return coordinates, sequence_encoding, t, target_tensor, std_dev



def load_and_preprocess(
    train_sequences_dir: str,
    train_labels_dir: str,
    validation_sequences_dir: str,
    output_dir: str,
):
    sequences = pd.read_csv(os.path.join(train_sequences_dir, "train_sequences.v2.csv"))
    labels = pd.read_csv(os.path.join(train_labels_dir, "train_labels.v2.csv"))
    test_sequences = pd.read_csv(os.path.join(validation_sequences_dir, "validation_sequences.csv"))

    lengths = sequences["sequence"].str.len()
    sequences = sequences[lengths <= 1024]

    duplicate_sequences = test_sequences.merge(
        sequences,
        on="sequence",
        suffixes=("_test", "_train"),
    )
    labels["target_id"] = labels["ID"].map(strip_suffix)

    labels = labels[~labels["target_id"].isin(duplicate_sequences["target_id_train"])]
    sequences = sequences[~sequences["sequence"].isin(test_sequences["sequence"])]

    df = labels[labels["target_id"].isin(sequences["target_id"])]
    processed_data = unstack_sequences(df)

    invalid = processed_data[~processed_data["resname"].isin(VALID_BASES)]["target_id"].unique()
    processed_data = processed_data[~processed_data["target_id"].isin(invalid)]

    os.makedirs(output_dir, exist_ok=True)
    processed_data.to_parquet(os.path.join(output_dir, "processed_data.parquet"), index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_sequences_dir", type=str, required=True)
    parser.add_argument("--train_labels_dir", type=str, required=True)
    parser.add_argument("--validation_sequences_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, default="./outputs/data")

    args = parser.parse_args()

    load_and_preprocess(
        args.train_sequences_dir,
        args.train_labels_dir,
        args.validation_sequences_dir,
        args.output_dir,
    )
