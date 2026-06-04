import os
import math
import argparse

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.checkpoint import checkpoint
from torch.utils.data import DataLoader
<<<<<<< HEAD
from scipy.spatial.distance import cdist
from scipy.spatial import distance_matrix
=======
>>>>>>> 2e15c95 (Add Azure ML pipeline)

from utils import (
    EarlyStopping,
    create_run_dir,
    display_save_metrics,
    distances_to_coords,
    align_points,
    save_checkpoint,
    save_loss_curve,
    tm_score,
)
<<<<<<< HEAD

torch.manual_seed(42)
np.random.seed(42)

MAPPING = {"A": 0, "G": 1, "C": 2, "U": 3}


def encode_sequence(str_seq):
    return str_seq.map(MAPPING).to_numpy(dtype=np.uint8)


def get_distance_std_dev(sequence):
=======
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# ──────────────────────────────────────────────
# Dataset (inlined from dataprep)
# ──────────────────────────────────────────────

MAPPING = {"A": 0, "G": 1, "C": 2, "U": 3}

def encode_sequence(str_seq):
    return str_seq.map(MAPPING).to_numpy(dtype=np.uint8)

def get_distance_std_dev(sequence):
    from scipy.spatial.distance import cdist
>>>>>>> 2e15c95 (Add Azure ML pipeline)
    coords = sequence[["x", "y", "z"]].values
    dist_map = cdist(coords, coords).astype(np.float32)
    mask = ~np.eye(len(coords), dtype=bool)
    return float(dist_map[mask].std() + 1e-6)

<<<<<<< HEAD

def get_coordinates(coordinates, scale, t=0):
=======
def get_coordinates(coordinates, scale, t=0):
    from scipy.spatial import distance_matrix as dm
>>>>>>> 2e15c95 (Add Azure ML pipeline)
    coord_values = coordinates[["x", "y", "z"]].values
    coord_values = coord_values - np.mean(coord_values, axis=0)
    coord_values = (coord_values / scale).astype(np.float32)
    noise = np.random.randn(*coord_values.shape)
    coord_values = np.sqrt(1 - t) * coord_values + np.sqrt(t) * noise
    return coord_values.astype(np.float32)

<<<<<<< HEAD

def get_output_tensor(coordinates):
    coord_values = coordinates[["x", "y", "z"]].values
    position_distances = distance_matrix(coord_values, coord_values)
    return position_distances[np.newaxis, :, :].astype(np.float32)


=======
def get_output_tensor(coordinates):
    from scipy.spatial import distance_matrix as dm
    coord_values = coordinates[["x", "y", "z"]].values
    position_distances = dm(coord_values, coord_values)
    return position_distances[np.newaxis, :, :].astype(np.float32)

>>>>>>> 2e15c95 (Add Azure ML pipeline)
class RNADataset(torch.utils.data.Dataset):
    def __init__(self, df, presample, min_t, max_t):
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
        X = get_coordinates(sequence, std_dev, float(t))
        S = encode_sequence(sequence["resname"])
        Y = get_output_tensor(sequence)
        return X, S, t, Y, std_dev
<<<<<<< HEAD


=======
torch.manual_seed(42)
np.random.seed(42)


# ──────────────────────────────────────────────
# Model
# ──────────────────────────────────────────────

>>>>>>> 2e15c95 (Add Azure ML pipeline)
class ResBlock(nn.Module):
    def __init__(self, channels: int, kernel_size: int = 3, dilation: int = 1):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size, padding="same", dilation=dilation)
        self.norm1 = nn.GroupNorm(8, channels)
        self.act1 = nn.SiLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size, padding="same", dilation=dilation)
        self.norm2 = nn.GroupNorm(8, channels)
        self.act2 = nn.SiLU(inplace=True)

    def forward(self, x):
        residual = x
        x = self.conv1(x)
        x = self.norm1(x)
        x = self.act1(x)
        x = self.conv2(x)
        x = self.norm2(x)
        return self.act2(x + residual)


class SinusoidalEncoding(nn.Module):
    def __init__(self, embedding_dim: int):
        super().__init__()
        self.embedding_dim = embedding_dim

    def forward(self, x):
        device = x.device
        half_dim = self.embedding_dim // 2
        freqs = torch.exp(
            -torch.arange(0, half_dim, device=device) * (math.log(10000.0) / (half_dim - 1))
        )
        args = x.unsqueeze(-1) * freqs
        return torch.cat([torch.sin(args), torch.cos(args)], dim=-1)


class RNAConvModel(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        n_nucleotides: int,
        distance_channels: int,
        relational_embedding_length: int,
        position_encoding_length: int,
        time_encoding_length: int,
    ):
        super().__init__()
        self.n_nucleotides = n_nucleotides
        self.pair_embedding = nn.Embedding(n_nucleotides ** 2, relational_embedding_length)
        self.time_encoding = SinusoidalEncoding(time_encoding_length)
        self.position_encoding = SinusoidalEncoding(position_encoding_length)

        input_channels = (
            distance_channels
            + relational_embedding_length
            + position_encoding_length
            + time_encoding_length
        )

        self.stem = nn.Sequential(
            nn.Conv2d(input_channels, hidden_size, kernel_size=1),
            nn.GroupNorm(8, hidden_size),
            nn.SiLU(inplace=True),
        )

        self.res1  = ResBlock(hidden_size, dilation=1)
        self.res2  = ResBlock(hidden_size, dilation=2)
        self.res3  = ResBlock(hidden_size, dilation=4)
        self.res4  = ResBlock(hidden_size, dilation=8)
        self.res5  = ResBlock(hidden_size, dilation=16)
        self.res6  = ResBlock(hidden_size, dilation=32)
        self.res7  = ResBlock(hidden_size, dilation=1)
        self.res8  = ResBlock(hidden_size, dilation=2)
        self.res9  = ResBlock(hidden_size, dilation=4)
        self.res10 = ResBlock(hidden_size, dilation=8)
        self.res11 = ResBlock(hidden_size, dilation=16)
        self.res12 = ResBlock(hidden_size, dilation=32)

        self.head = nn.Sequential(
            nn.Conv2d(hidden_size, 1, kernel_size=1),
            nn.Softplus(),
        )

    def forward(self, coords, sequence, t):
        b, n, _ = coords.shape
        device = coords.device

        dist_3d = torch.cdist(coords, coords, p=2).unsqueeze(1)
<<<<<<< HEAD
        pos = torch.arange(n, device=device).float()
        dist_seq = torch.abs(pos.unsqueeze(1) - pos.unsqueeze(0)).unsqueeze(0).expand(b, -1, -1)
        pos_enc = self.position_encoding(dist_seq).permute(0, 3, 1, 2)
        t_enc = self.time_encoding(t).view(b, -1, 1, 1).expand(-1, -1, n, n)
=======

        pos = torch.arange(n, device=device).float()
        dist_seq = torch.abs(pos.unsqueeze(1) - pos.unsqueeze(0)).unsqueeze(0).expand(b, -1, -1)
        pos_enc = self.position_encoding(dist_seq).permute(0, 3, 1, 2)

        t_enc = self.time_encoding(t).view(b, -1, 1, 1).expand(-1, -1, n, n)

>>>>>>> 2e15c95 (Add Azure ML pipeline)
        pair_indices = (sequence.unsqueeze(2) * self.n_nucleotides + sequence.unsqueeze(1)).long()
        pairwise_emb = self.pair_embedding(pair_indices).permute(0, 3, 1, 2)

        x = torch.cat([dist_3d, pos_enc, pairwise_emb, t_enc], dim=1)
        del coords, sequence, dist_3d, pos, dist_seq, pos_enc, t_enc, pair_indices, pairwise_emb

        x = self.stem(x)

        def group_1(h):
            return self.res3(self.res2(self.res1(h)))

        def group_2(h):
            return self.res6(self.res5(self.res4(h)))

        def group_3(h):
            return self.res9(self.res8(self.res7(h)))

        def group_4(h):
            return self.res12(self.res11(self.res10(h)))

        x = checkpoint(group_1, x, use_reentrant=False)
        x = checkpoint(group_2, x, use_reentrant=False)
        x = checkpoint(group_3, x, use_reentrant=False)
        x = checkpoint(group_4, x, use_reentrant=False)

        x = self.head(x)
        x = torch.tril(x, diagonal=-1)
        return x + x.transpose(-1, -2)


<<<<<<< HEAD
=======
# ──────────────────────────────────────────────
# Training / validation loops
# ──────────────────────────────────────────────

>>>>>>> 2e15c95 (Add Azure ML pipeline)
def run_train_epoch(model, loader, loss_fn, optimizer, device):
    metrics = {"loss_sum": 0.0, "sample_count": 0.0}
    model.train()

    with torch.enable_grad():
        for i, (x, s, t, y, std_dev) in enumerate(loader, start=1):
            x, s, t, y, std_dev = (
                x.to(device), s.to(device), t.to(device), y.to(device), std_dev.to(device)
            )
<<<<<<< HEAD
            prediction = model(x, s, t)
            loss = loss_fn(prediction, y, std_dev)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            metrics["loss_sum"] += loss.item() * len(y)
            metrics["sample_count"] += len(y)
=======

            prediction = model(x, s, t)
            loss = loss_fn(prediction, y, std_dev)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            metrics["loss_sum"] += loss.item() * len(y)
            metrics["sample_count"] += len(y)

>>>>>>> 2e15c95 (Add Azure ML pipeline)
            if i % 10 == 0:
                print(f"Train progress: {i}/{len(loader)} ({i / len(loader) * 100:.1f}%)", end="\r")

    return metrics


def run_validation_epoch(model, loader, loss_fn, device):
    metrics = {
        "loss_sum": 0.0,
        "sample_count": 0.0,
        "tm_score_sum": 0.0,
        "invalidity_score_sum": 0.0,
        "samples": [],
    }
    model.eval()

    with torch.no_grad():
        for i, (x, s, t, y, std_dev) in enumerate(loader, start=1):
            x, s, t, y, std_dev = (
                x.to(device), s.to(device), t.to(device), y.to(device), std_dev.to(device)
            )
<<<<<<< HEAD
            prediction = model(x, s, t)
            loss = loss_fn(prediction, y, std_dev)
            metrics["loss_sum"] += loss.item() * len(y)
            metrics["sample_count"] += len(y)
            coords_pred, invalidity_score = distances_to_coords(prediction[0, 0].float().cpu().numpy())
            coords_y, _ = distances_to_coords(y[0, 0].cpu().numpy())
            metrics["invalidity_score_sum"] += invalidity_score
            val_tm = tm_score(coords_y, coords_pred)
            metrics["tm_score_sum"] += val_tm
            if i <= 3:
                metrics["samples"].append((align_points(coords_y, coords_pred), coords_y, val_tm))
=======

            prediction = model(x, s, t)
            loss = loss_fn(prediction, y, std_dev)

            metrics["loss_sum"] += loss.item() * len(y)
            metrics["sample_count"] += len(y)

            coords_pred, invalidity_score = distances_to_coords(prediction[0, 0].float().cpu().numpy())
            coords_y, _ = distances_to_coords(y[0, 0].cpu().numpy())

            metrics["invalidity_score_sum"] += invalidity_score
            val_tm = tm_score(coords_y, coords_pred)
            metrics["tm_score_sum"] += val_tm

            if i <= 3:
                metrics["samples"].append((align_points(coords_y, coords_pred), coords_y, val_tm))

>>>>>>> 2e15c95 (Add Azure ML pipeline)
            if i % 10 == 0:
                print(f"Val progress: {i}/{len(loader)} ({i / len(loader) * 100:.1f}%)", end="\r")

    return metrics


<<<<<<< HEAD
def main(args):
    device = torch.device("cpu")

=======
# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main(args):
    pass  # removed: float32 matmul precision (CPU only)
    device = torch.device("cpu")
    print(f"Using device: {device}")

    # Load splits
>>>>>>> 2e15c95 (Add Azure ML pipeline)
    train_df = pd.read_parquet(args.train_path)
    val_df = pd.read_parquet(args.val_path)

    train_dataset = RNADataset(train_df, presample=False, min_t=0, max_t=1)
    val_dataset = RNADataset(val_df, presample=True, min_t=0, max_t=1)

    train_loader = DataLoader(
        train_dataset, batch_size=1, shuffle=True,
        pin_memory=False, num_workers=2, prefetch_factor=4, persistent_workers=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=1, shuffle=False,
        pin_memory=False, num_workers=2, prefetch_factor=4, persistent_workers=True,
    )

<<<<<<< HEAD
=======
    # Model
>>>>>>> 2e15c95 (Add Azure ML pipeline)
    model = RNAConvModel(
        hidden_size=64,
        n_nucleotides=4,
        distance_channels=1,
        relational_embedding_length=8,
        position_encoding_length=8,
        time_encoding_length=8,
    ).to(device)

    optimizer = optim.AdamW(model.parameters(), lr=0.004, weight_decay=0.01)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)
    loss_fn = lambda p, y, s: nn.L1Loss()(p, y) / s.squeeze()
    early_stopping = EarlyStopping(patience=40, delta=0, max_run_time=60 * 60 * 9)

    start_epoch = 1

<<<<<<< HEAD
    if args.checkpoint_path and os.path.isfile(args.checkpoint_path):
=======
    # Optional checkpoint resume
    if args.checkpoint_path and os.path.isfile(args.checkpoint_path):
        print(f"Resuming from checkpoint: {args.checkpoint_path}")
>>>>>>> 2e15c95 (Add Azure ML pipeline)
        ckpt = torch.load(args.checkpoint_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        start_epoch = ckpt["epoch"] + 1

    run_dir = create_run_dir(args.experiment_name, base_dir=args.output_dir)
    metrics = {"training": [], "validation": []}

    for epoch in range(start_epoch, args.epochs + 1):
        print(f"\n--- Epoch {epoch}/{args.epochs} ---")
<<<<<<< HEAD
        metrics["training"].append(run_train_epoch(model, train_loader, loss_fn, optimizer, device))
        metrics["validation"].append(run_validation_epoch(model, val_loader, loss_fn, device))
        metrics["training"][-1]["learning_rate"] = optimizer.param_groups[0]["lr"]
        scheduler.step()
        save_checkpoint(model, optimizer, scheduler, epoch, os.path.join(run_dir, "checkpoint.pt"))
        display_save_metrics(run_dir, epoch, metrics)
        val_loss = metrics["validation"][-1]["loss_sum"] / metrics["validation"][-1]["sample_count"]
        early_stopping(val_loss, model)
=======

        metrics["training"].append(run_train_epoch(model, train_loader, loss_fn, optimizer, device))
        metrics["validation"].append(run_validation_epoch(model, val_loader, loss_fn, device))

        metrics["training"][-1]["learning_rate"] = optimizer.param_groups[0]["lr"]
        scheduler.step()

        save_checkpoint(model, optimizer, scheduler, epoch, os.path.join(run_dir, "checkpoint.pt"))
        display_save_metrics(run_dir, epoch, metrics)

        val_loss = metrics["validation"][-1]["loss_sum"] / metrics["validation"][-1]["sample_count"]
        early_stopping(val_loss, model)

>>>>>>> 2e15c95 (Add Azure ML pipeline)
        if early_stopping.early_stop:
            print(f"Stopping early: {early_stopping.reason}")
            break

    save_loss_curve(run_dir, metrics)
    torch.save(early_stopping.best_model_state, os.path.join(run_dir, "best_model.pt"))
<<<<<<< HEAD
=======
    print(f"\nTraining complete. Outputs saved to {run_dir}")
>>>>>>> 2e15c95 (Add Azure ML pipeline)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
<<<<<<< HEAD
    parser.add_argument("--train_path", type=str, required=True)
    parser.add_argument("--val_path", type=str, required=True)
    parser.add_argument("--experiment_name", type=str, default="rna_experiment")
    parser.add_argument("--epochs", type=int, default=350)
    parser.add_argument("--checkpoint_path", type=str, default=None)
    parser.add_argument("--output_dir", type=str, default="./outputs")
=======
    parser.add_argument("--train_path", type=str, required=True, help="Path to train.parquet")
    parser.add_argument("--val_path", type=str, required=True, help="Path to val.parquet")
    parser.add_argument("--experiment_name", type=str, default="rna_experiment")
    parser.add_argument("--epochs", type=int, default=350)
    parser.add_argument("--checkpoint_path", type=str, default=None, help="Optional path to resume from")
    parser.add_argument("--output_dir", type=str, default="./outputs", help="Output directory for Azure ML")
>>>>>>> 2e15c95 (Add Azure ML pipeline)
    args = parser.parse_args()

    main(args)