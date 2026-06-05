import os
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.lines import Line2D
from datetime import datetime

import torch

def distances_to_coords(distances: np.ndarray) -> tuple[np.ndarray, float]:
    n = distances.shape[0]
    j = np.eye(n) - np.ones((n, n)) / n
    b = -0.5 * j @ (distances ** 2) @ j
    eigvals, eigvecs = np.linalg.eigh(b)
    idx = np.argsort(eigvals)[::-1]
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]

    v = eigvecs[:, :3]
    l = np.diag(np.sqrt(np.maximum(eigvals[:3], 0)))
    coords = v @ l

    neg_mass: float = np.sum(np.abs(eigvals[eigvals < 0]))
    pos_mass: float = np.sum(eigvals[eigvals > 0])
    invalidity_score = neg_mass / (pos_mass + 1e-12)

    return coords, invalidity_score


def align_points(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    centroid_a = a.mean(axis=0)
    centroid_b = b.mean(axis=0)
    aa = a - centroid_a
    bb = b - centroid_b

    h = aa.T @ bb
    u, _, vt = np.linalg.svd(h)
    r = vt.T @ u.T

    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T

    return (bb @ r) + centroid_a


def d0_scaling(l):
    if l >= 30:
        return 0.6 * np.sqrt(l - 0.5) - 2.5

    bins = [
        (12, 0.3),
        (16, 0.4),
        (20, 0.5),
        (24, 0.6),
        (30, 0.7),
    ]
    for threshold, val in bins:
        if l < threshold:
            return val

    return bins[-1][1]


def tm_score(a: np.ndarray, b: np.ndarray) -> float:
    b_aligned = align_points(a, b)
    l_ref = len(a)
    d0 = d0_scaling(l_ref)
    dists = np.linalg.norm(a - b_aligned, axis=1)
    return np.sum(1 / (1 + (dists / d0) ** 2)) / l_ref

def create_run_dir(experiment_name: str, base_dir: str = "outputs") -> str:
    run_dir = os.path.join(
        base_dir,
        f"{experiment_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}",
    )
    os.makedirs(run_dir, exist_ok=True)

    with open(os.path.join(run_dir, "summary.csv"), "w", encoding="utf-8") as f:
        f.write(
            "Epoch,Learning rate,Average training loss,Average validation loss,"
            "Estimated average validation TM-score,Average validation validity score\n"
        )

    return run_dir


def save_checkpoint(model, optimizer, scheduler, epoch: int, filepath: str):
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
        },
        filepath,
    )

def display_save_metrics(run_dir: str, epoch: int, metrics: dict):
    lr = metrics["training"][-1]["learning_rate"]
    train_loss = (
        metrics["training"][-1]["loss_sum"] / metrics["training"][-1]["sample_count"]
    )
    val_loss = (
        metrics["validation"][-1]["loss_sum"] / metrics["validation"][-1]["sample_count"]
    )
    val_tm = (
        metrics["validation"][-1]["tm_score_sum"] / metrics["validation"][-1]["sample_count"]
    )
    val_inv = (
        metrics["validation"][-1]["invalidity_score_sum"]
        / metrics["validation"][-1]["sample_count"]
    )

    with open(os.path.join(run_dir, "summary.csv"), "a", encoding="utf-8") as f:
        f.write(f"{epoch},{lr},{train_loss},{val_loss},{val_tm},{val_inv}\n")

    print(f"Epoch {epoch}:")
    print(
        f"   - Avg train loss: {train_loss:.4f}\n"
        f"   - Avg val loss:   {val_loss:.4f}\n"
        f"   - Est. avg val TM-score: {val_tm:.4f}\n"
        f"   - Avg val invalidity score: {val_inv}\n"
    )

    plot_validation_samples(run_dir, metrics["validation"][-1]["samples"], epoch)


def save_loss_curve(run_dir: str, metrics: dict):
    train_losses = [m["loss_sum"] / m["sample_count"] for m in metrics["training"]]
    val_losses = [m["loss_sum"] / m["sample_count"] for m in metrics["validation"]]

    _, ax = plt.subplots()
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.plot(range(1, len(train_losses) + 1), train_losses, label="Training loss")
    ax.plot(range(1, len(val_losses) + 1), val_losses, label="Validation loss")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("Loss curve")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(run_dir, "loss_curve.png"))


def plot_points(
    points: pd.DataFrame,
    ax,
    title: str = "",
    tm_score_val: float = 0,
    limit: bool = False,
):
    unique_ids = points["id"].unique()
    base_maps = ["Reds", "Blues", "Greens", "Oranges", "Purples", "Greys"]

    ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z", labelpad=-1)

    legend_handles = []
    for i, pid in enumerate(unique_ids):
        subset = points[points["id"] == pid]
        cmap = plt.get_cmap(base_maps[i % len(base_maps)])
        ax.scatter(
            subset["x"],
            subset["y"],
            subset["z"],
            cmap=cmap,
            c=subset["x"] + subset["y"] + subset["z"],
            s=8,
        )
        handle = Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=cmap(0.6),
            markersize=8,
            label=pid,
        )
        legend_handles.append(handle)
    ax.legend(handles=legend_handles, loc="lower left", fontsize=8)
    if limit:
        ax.set_xlim(-15, 15)
        ax.set_ylim(-15, 15)
        ax.set_zlim(-15, 15)

    ax.text2D(
        0.05,
        0.95,
        f"TM-score: {tm_score_val:.4f}",
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
    )


def plot_validation_samples(run_dir: str, plot_samples: list, epoch: int):
    fig = plt.figure(figsize=(18, 4))
    for col, (coords_pred, coords_y, sample_tm) in enumerate(plot_samples):
        ax = fig.add_subplot(1, 3, col + 1, projection="3d")
        df_pred = pd.DataFrame(coords_pred, columns=["x", "y", "z"])
        df_pred["id"] = "Prediction"
        df_y = pd.DataFrame(coords_y, columns=["x", "y", "z"])
        df_y["id"] = "Actual"
        combined = pd.concat([df_pred, df_y], ignore_index=True)
        plot_points(
            combined,
            ax=ax,
            title=f"Sample {col + 1}",
            tm_score_val=sample_tm,
            limit=True,
        )

    plt.tight_layout()
    plt.savefig(os.path.join(run_dir, f"epoch_{epoch}_val_plots.png"))

class EarlyStopping:
    def __init__(self, patience: int = 5, delta: float = 0, max_run_time: int = 60 * 60 * 24):
        self.end_time = time.time() + max_run_time
        self.patience = patience
        self.delta = delta
        self.best_score = None
        self.early_stop = False
        self.reason = None
        self.counter = 0
        self.best_model_state = None

    def __call__(self, val_loss: float, model):
        score = -val_loss

        if self.best_score is not None and score < self.best_score + self.delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
                self.reason = "No more improvements"
        else:
            self.best_score = score
            self.best_model_state = model.state_dict()
            self.counter = 0

        if time.time() > self.end_time:
            self.early_stop = True
            self.reason = "Time limit reached"
