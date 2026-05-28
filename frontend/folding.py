from typing import TypedDict, Iterator
import math
import time
import os

import numpy as np
import torch

_model = None

def get_model():
    global _model

    if _model is None:
        _model = RNAConvModel(
            hidden_size=64, 
            n_nucleotides=4,
            distance_channels=1, 
            relational_embedding_length=8,
            position_encoding_length=8, 
            time_encoding_length=8,
        )
        
        _model.load_state_dict(torch.load(os.path.join('models', 'rna.pt'), map_location=torch.device('cpu')))
        _model.eval()

    return _model

MAPPING = {'A': 0, 'G': 1, 'C': 2, 'U': 3}

def encode_sequence(sequence: str) -> torch.tensor:
    return torch.tensor([MAPPING[n] for n in sequence]).unsqueeze(0)

def distances_to_coords(distances: np.ndarray) -> np.ndarray:
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

    return coords

class FoldingStep(TypedDict):
    fold: int
    step: int
    coords: list[list[float]]

def folding_iterator(sequence: str, folds_to_generate: int, steps_per_fold: int, return_noise: bool) -> Iterator[FoldingStep]:
    model = get_model()

    num_nucleotides = len(sequence)
    seq = encode_sequence(sequence)

    for fold in range(folds_to_generate):
        coords = torch.randn((1, num_nucleotides, 3))
        timesteps = torch.linspace(1.0, 0.0, steps_per_fold + 1)

        with torch.no_grad():
            for step in range(steps_per_fold):
                start_time = time.perf_counter()

                t_curr = timesteps[step]
                t_next = timesteps[step + 1]

                pred = model(coords, seq, t_curr.unsqueeze(0))
                pred_np = pred.squeeze().numpy()

                coords_np = distances_to_coords(pred_np)
                x0_coords = torch.from_numpy(coords_np).float()[None, :, :]
                x0_coords -= x0_coords.mean(dim=1, keepdim=True)
                
                mask = ~np.eye(pred_np.shape[0], dtype=bool)
                std_dev = pred_np[mask].std() + 1e-6

                coords_to_return = x0_coords
                
                if t_next > 0:
                    x0_coords_scaled = x0_coords / std_dev
                    noise = torch.randn_like(x0_coords_scaled)

                    coords = torch.sqrt(1 - t_next) * x0_coords_scaled + torch.sqrt(t_next) * noise

                    if return_noise:
                        coords_to_return = (coords * std_dev)
                else:
                    coords = x0_coords

                yield {
                    'fold': fold,
                    'step': step,
                    'coords': coords_to_return.squeeze(0).tolist()
                }

                duration = time.perf_counter() - start_time

                time.sleep(max(0, 1.6 - duration))

class SinusoidalEncoding(torch.nn.Module):
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
    
class ResBlock(torch.nn.Module):
    def __init__(self, channels, kernel_size=3, dilation=1):
        super().__init__()

        self.conv1 = torch.nn.Conv2d(channels, channels, kernel_size, padding='same', dilation=dilation)
        self.norm1 = torch.nn.GroupNorm(8, channels)
        self.act1  = torch.nn.SiLU(inplace=True)
        self.conv2 = torch.nn.Conv2d(channels, channels, kernel_size, padding='same', dilation=dilation)
        self.norm2 = torch.nn.GroupNorm(8, channels)
        self.act2  = torch.nn.SiLU(inplace=True)

    def forward(self, x):
        residual = x
        
        x = self.conv1(x)
        x = self.norm1(x)
        x = self.act1(x)
        x = self.conv2(x)
        x = self.norm2(x)

        return self.act2(x + residual)

class RNAConvModel(torch.nn.Module):
    def __init__(
            self,  
            hidden_size, 
            n_nucleotides,
            distance_channels, 
            relational_embedding_length,
            position_encoding_length, 
            time_encoding_length, 
    ):
        super().__init__()

        self.n_nucleotides = n_nucleotides
        self.pair_embedding = torch.nn.Embedding(n_nucleotides**2, relational_embedding_length)
        self.time_encoding = SinusoidalEncoding(time_encoding_length)
        self.position_encoding = SinusoidalEncoding(position_encoding_length)

        input_channels = distance_channels + relational_embedding_length + position_encoding_length + time_encoding_length
        
        self.stem = torch.nn.Sequential(
            torch.nn.Conv2d(input_channels, hidden_size, kernel_size=1),
            torch.nn.GroupNorm(8, hidden_size),
            torch.nn.SiLU(inplace=True),
        )

        self.res1 = ResBlock(hidden_size, dilation=1)
        self.res2 = ResBlock(hidden_size, dilation=2)
        self.res3 = ResBlock(hidden_size, dilation=4)
        self.res4 = ResBlock(hidden_size, dilation=8)
        self.res5 = ResBlock(hidden_size, dilation=16)
        self.res6 = ResBlock(hidden_size, dilation=32)

        self.res7 = ResBlock(hidden_size, dilation=1)
        self.res8 = ResBlock(hidden_size, dilation=2)
        self.res9 = ResBlock(hidden_size, dilation=4)
        self.res10 = ResBlock(hidden_size, dilation=8)
        self.res11 = ResBlock(hidden_size, dilation=16)
        self.res12 = ResBlock(hidden_size, dilation=32)

        self.head = torch.nn.Sequential(
            torch.nn.Conv2d(hidden_size, 1, kernel_size=1),
            torch.nn.Softplus(),
        )

    def forward(self, coords, sequence, t):
        b, n, _ = coords.shape
        device = coords.device

        dist_3d = torch.cdist(coords, coords, p=2).unsqueeze(1)

        pos = torch.arange(n, device=device).float()
        dist_seq = torch.abs(pos.unsqueeze(1) - pos.unsqueeze(0)).unsqueeze(0).expand(b, -1, -1)
        pos_enc = self.position_encoding(dist_seq).permute(0, 3, 1, 2)

        t_enc = self.time_encoding(t).view(b, -1, 1, 1).expand(-1, -1, n, n)

        pair_indices = (sequence.unsqueeze(2) * self.n_nucleotides + sequence.unsqueeze(1)).long()
        pairwise_emb = self.pair_embedding(pair_indices).permute(0, 3, 1, 2)

        x = torch.cat([dist_3d, pos_enc, pairwise_emb, t_enc], dim=1)

        x = self.stem(x)

        x = self.res1(x)
        x = self.res2(x)
        x = self.res3(x)
        x = self.res4(x)
        x = self.res5(x)
        x = self.res6(x) 
        x = self.res7(x)
        x = self.res8(x)
        x = self.res9(x)
        x = self.res10(x)
        x = self.res11(x)
        x = self.res12(x)
        
        x = self.head(x)
        
        x = torch.tril(x, diagonal=-1)

        return x + x.transpose(-1, -2)
