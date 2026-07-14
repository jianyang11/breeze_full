"""Training-based 1D synthetic-signal baselines for the closing protocol.

The implementations are intentionally independent of BREEZE's verifier and
recipe machinery.  They learn only from the outer-training windows provided by
the caller, train one unconditional model per class, and produce complete
three-channel windows.  TimeGAN follows its embedding/recovery, supervisor,
and adversarial stages; its embedding/recovery are convolutional so a 2048
sample vibration/current window becomes a 128-step latent sequence.  DDPM uses
the standard forward noising objective and ancestral reverse sampling with a
1D residual denoiser.

Every training stage writes an atomic checkpoint.  Because each epoch and
batch derives its own seed, a resumed run is equivalent to an uninterrupted
run at a stage boundary.
"""

from __future__ import annotations

import math
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Literal

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


DeviceName = Literal["cpu"]


@dataclass(frozen=True)
class TimeGANConfig:
    latent_channels: int = 32
    batch_size: int = 16
    embedding_epochs: int = 80
    supervisor_epochs: int = 80
    joint_epochs: int = 160
    learning_rate: float = 1e-3


@dataclass(frozen=True)
class DDPMConfig:
    hidden_channels: int = 32
    batch_size: int = 16
    epochs: int = 240
    diffusion_steps: int = 50
    learning_rate: float = 2e-4


def _atomic_torch_save(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_path = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(raw_path)
    try:
        torch.save(payload, tmp_path)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _seeded_randn(shape: tuple[int, ...], seed: int, device: torch.device) -> torch.Tensor:
    generator = torch.Generator(device=device).manual_seed(seed)
    return torch.randn(shape, generator=generator, device=device)


def _batch_indices(n: int, batch_size: int, seed: int) -> list[torch.Tensor]:
    generator = torch.Generator().manual_seed(seed)
    permutation = torch.randperm(n, generator=generator)
    return [permutation[start : start + batch_size] for start in range(0, n, batch_size)]


class ConvEmbedder(nn.Module):
    """Map a 2048-sample window to a 128-step latent sequence."""

    def __init__(self, in_channels: int, latent_channels: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_channels, 32, kernel_size=8, stride=4, padding=2),
            nn.GroupNorm(4, 32),
            nn.SiLU(),
            nn.Conv1d(32, latent_channels, kernel_size=8, stride=4, padding=2),
            nn.GroupNorm(4, latent_channels),
            nn.SiLU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ConvRecovery(nn.Module):
    def __init__(self, latent_channels: int, out_channels: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.ConvTranspose1d(latent_channels, 32, kernel_size=8, stride=4, padding=2),
            nn.GroupNorm(4, 32),
            nn.SiLU(),
            nn.ConvTranspose1d(32, out_channels, kernel_size=8, stride=4, padding=2),
        )

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        return self.net(h)


class TemporalGRU(nn.Module):
    def __init__(self, latent_channels: int):
        super().__init__()
        self.gru = nn.GRU(latent_channels, latent_channels, batch_first=True)
        self.proj = nn.Linear(latent_channels, latent_channels)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        # convolutional tensors are (batch, channels, steps); GRU uses steps first.
        seq = h.transpose(1, 2)
        out, _ = self.gru(seq)
        return self.proj(out).transpose(1, 2)


class TemporalDiscriminator(nn.Module):
    def __init__(self, latent_channels: int):
        super().__init__()
        self.gru = nn.GRU(latent_channels, latent_channels, batch_first=True)
        self.head = nn.Linear(latent_channels, 1)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        seq = h.transpose(1, 2)
        out, _ = self.gru(seq)
        return self.head(out).mean(dim=1)


class ConvTimeGAN(nn.Module):
    def __init__(self, channels: int, latent_channels: int):
        super().__init__()
        self.embedder = ConvEmbedder(channels, latent_channels)
        self.recovery = ConvRecovery(latent_channels, channels)
        self.generator = TemporalGRU(latent_channels)
        self.supervisor = TemporalGRU(latent_channels)
        self.discriminator = TemporalDiscriminator(latent_channels)
        self.channels = channels
        self.latent_channels = latent_channels

    def reconstruct(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.embedder(x)
        return self.recovery(h), h

    def synthesize_latent(self, noise: torch.Tensor) -> torch.Tensor:
        return self.supervisor(self.generator(noise))


class TimeGANTrainer:
    def __init__(self, channels: int, length: int, config: TimeGANConfig, seed: int):
        if length != 2048:
            raise ValueError(f"TimeGAN baseline is registered for 2048-sample PU windows, got {length}")
        self.config = config
        self.seed = seed
        self.device = torch.device("cpu")
        torch.manual_seed(seed)
        self.model = ConvTimeGAN(channels, config.latent_channels).to(self.device)
        self.opt_embed = torch.optim.Adam(
            list(self.model.embedder.parameters()) + list(self.model.recovery.parameters()),
            lr=config.learning_rate,
        )
        self.opt_supervisor = torch.optim.Adam(self.model.supervisor.parameters(), lr=config.learning_rate)
        self.opt_generator = torch.optim.Adam(
            list(self.model.generator.parameters()) + list(self.model.supervisor.parameters()),
            lr=config.learning_rate,
        )
        self.opt_discriminator = torch.optim.Adam(self.model.discriminator.parameters(), lr=config.learning_rate)
        self.mean: torch.Tensor | None = None
        self.std: torch.Tensor | None = None
        self.history: list[dict[str, float | int | str]] = []

    def _checkpoint(self, path: Path, stage: str, completed_epoch: int, elapsed_seconds: float) -> None:
        if self.mean is None or self.std is None:
            raise RuntimeError("normalization state is unavailable")
        _atomic_torch_save(
            {
                "algorithm": "conv_timegan",
                "config": asdict(self.config),
                "seed": self.seed,
                "stage": stage,
                "completed_epoch": completed_epoch,
                "elapsed_seconds": elapsed_seconds,
                "model": self.model.state_dict(),
                "opt_embed": self.opt_embed.state_dict(),
                "opt_supervisor": self.opt_supervisor.state_dict(),
                "opt_generator": self.opt_generator.state_dict(),
                "opt_discriminator": self.opt_discriminator.state_dict(),
                "mean": self.mean.cpu(),
                "std": self.std.cpu(),
                "history": self.history,
            },
            path,
        )

    def _restore(self, path: Path) -> tuple[str, int, float]:
        state = torch.load(path, map_location=self.device, weights_only=False)
        if state.get("algorithm") != "conv_timegan" or state.get("config") != asdict(self.config):
            raise RuntimeError(f"checkpoint configuration mismatch: {path}")
        self.model.load_state_dict(state["model"])
        self.opt_embed.load_state_dict(state["opt_embed"])
        self.opt_supervisor.load_state_dict(state["opt_supervisor"])
        self.opt_generator.load_state_dict(state["opt_generator"])
        self.opt_discriminator.load_state_dict(state["opt_discriminator"])
        self.mean = state["mean"].to(self.device)
        self.std = state["std"].to(self.device)
        self.history = list(state.get("history", []))
        return str(state["stage"]), int(state["completed_epoch"]), float(state["elapsed_seconds"])

    def training_history(self) -> list[dict[str, float | int | str]]:
        """Return the complete checkpointed epoch-level optimization record."""
        return [dict(row) for row in self.history]

    def fit(self, x: np.ndarray, checkpoint: Path) -> float:
        if x.ndim != 3:
            raise ValueError(f"expected (windows, channels, samples), got {x.shape}")
        if not np.isfinite(x).all():
            raise ValueError("TimeGAN cannot train on non-finite windows")
        x_tensor = torch.as_tensor(x, dtype=torch.float32, device=self.device)
        stage_order = ("embed", "supervisor", "joint", "complete")
        stage, completed_epoch, elapsed = ("embed", 0, 0.0)
        if checkpoint.exists():
            stage, completed_epoch, elapsed = self._restore(checkpoint)
        else:
            self.mean = x_tensor.mean(dim=(0, 2), keepdim=True)
            self.std = x_tensor.std(dim=(0, 2), keepdim=True).clamp_min(1e-6)
        if self.mean is None or self.std is None:
            raise RuntimeError("missing normalization state")
        xn = (x_tensor - self.mean) / self.std
        if stage == "complete":
            return elapsed
        start_stage = stage_order.index(stage)
        epoch_plan = {
            "embed": self.config.embedding_epochs,
            "supervisor": self.config.supervisor_epochs,
            "joint": self.config.joint_epochs,
        }
        for stage_index in range(start_stage, 3):
            active_stage = stage_order[stage_index]
            first_epoch = completed_epoch if active_stage == stage else 0
            for epoch in range(first_epoch, epoch_plan[active_stage]):
                tic = perf_counter()
                reconstruction_losses: list[float] = []
                supervisor_losses: list[float] = []
                discriminator_losses: list[float] = []
                generator_losses: list[float] = []
                for batch_index, idx in enumerate(
                    _batch_indices(len(xn), self.config.batch_size, self.seed + stage_index * 1_000_000 + epoch)
                ):
                    batch = xn[idx]
                    if active_stage == "embed":
                        rec, _ = self.model.reconstruct(batch)
                        loss = F.mse_loss(rec, batch)
                        if not torch.isfinite(loss):
                            raise FloatingPointError(f"non-finite TimeGAN reconstruction loss at {active_stage} epoch {epoch}")
                        self.opt_embed.zero_grad(set_to_none=True)
                        loss.backward()
                        self.opt_embed.step()
                        reconstruction_losses.append(float(loss.detach().cpu()))
                    elif active_stage == "supervisor":
                        with torch.no_grad():
                            h = self.model.embedder(batch)
                        h_sup = self.model.supervisor(h)
                        loss = F.mse_loss(h_sup[:, :, :-1], h[:, :, 1:])
                        if not torch.isfinite(loss):
                            raise FloatingPointError(f"non-finite TimeGAN supervisor loss at {active_stage} epoch {epoch}")
                        self.opt_supervisor.zero_grad(set_to_none=True)
                        loss.backward()
                        self.opt_supervisor.step()
                        supervisor_losses.append(float(loss.detach().cpu()))
                    else:
                        with torch.no_grad():
                            h_real = self.model.embedder(batch)
                        noise = _seeded_randn(
                            tuple(h_real.shape),
                            self.seed + 2_000_000 + epoch * 10_000 + batch_index,
                            self.device,
                        )
                        h_fake = self.model.synthesize_latent(noise)
                        d_real = self.model.discriminator(h_real.detach())
                        d_fake = self.model.discriminator(h_fake.detach())
                        d_loss = F.binary_cross_entropy_with_logits(d_real, torch.ones_like(d_real))
                        d_loss = d_loss + F.binary_cross_entropy_with_logits(d_fake, torch.zeros_like(d_fake))
                        if not torch.isfinite(d_loss):
                            raise FloatingPointError(f"non-finite TimeGAN discriminator loss at {active_stage} epoch {epoch}")
                        self.opt_discriminator.zero_grad(set_to_none=True)
                        d_loss.backward()
                        self.opt_discriminator.step()

                        h_real = self.model.embedder(batch)
                        h_sup = self.model.supervisor(h_real)
                        d_fake_for_g = self.model.discriminator(h_fake)
                        adversarial = F.binary_cross_entropy_with_logits(d_fake_for_g, torch.ones_like(d_fake_for_g))
                        supervised = F.mse_loss(h_sup[:, :, :-1], h_real[:, :, 1:])
                        generated = self.model.recovery(h_fake)
                        moment = (generated.mean(dim=(0, 2)) - batch.mean(dim=(0, 2))).abs().mean()
                        moment = moment + (generated.std(dim=(0, 2)) - batch.std(dim=(0, 2))).abs().mean()
                        g_loss = adversarial + 100.0 * supervised + 10.0 * moment
                        if not torch.isfinite(g_loss):
                            raise FloatingPointError(f"non-finite TimeGAN generator loss at {active_stage} epoch {epoch}")
                        self.opt_generator.zero_grad(set_to_none=True)
                        g_loss.backward()
                        self.opt_generator.step()

                        rec, _ = self.model.reconstruct(batch)
                        embed_loss = F.mse_loss(rec, batch) + 0.1 * supervised.detach()
                        if not torch.isfinite(embed_loss):
                            raise FloatingPointError(f"non-finite TimeGAN reconstruction loss at {active_stage} epoch {epoch}")
                        self.opt_embed.zero_grad(set_to_none=True)
                        embed_loss.backward()
                        self.opt_embed.step()
                        reconstruction_losses.append(float(embed_loss.detach().cpu()))
                        supervisor_losses.append(float(supervised.detach().cpu()))
                        discriminator_losses.append(float(d_loss.detach().cpu()))
                        generator_losses.append(float(g_loss.detach().cpu()))
                elapsed += perf_counter() - tic
                record: dict[str, float | int | str] = {"stage": active_stage, "epoch": epoch + 1}
                if reconstruction_losses:
                    record["reconstruction_loss"] = float(np.mean(reconstruction_losses))
                if supervisor_losses:
                    record["supervisor_loss"] = float(np.mean(supervisor_losses))
                if discriminator_losses:
                    record["discriminator_loss"] = float(np.mean(discriminator_losses))
                if generator_losses:
                    record["generator_loss"] = float(np.mean(generator_losses))
                self.history.append(record)
                self._checkpoint(checkpoint, active_stage, epoch + 1, elapsed)
            completed_epoch = 0
            stage = active_stage
        self._checkpoint(checkpoint, "complete", 0, elapsed)
        return elapsed

    def sample(self, n: int, sample_seed: int) -> np.ndarray:
        if n <= 0:
            raise ValueError("n must be positive")
        if self.mean is None or self.std is None:
            raise RuntimeError("fit or checkpoint restore is required before sample")
        self.model.eval()
        with torch.no_grad():
            noise = _seeded_randn((n, self.config.latent_channels, 128), sample_seed, self.device)
            generated = self.model.recovery(self.model.synthesize_latent(noise))
            return (generated * self.std + self.mean).cpu().numpy().astype(np.float32)


def _sinusoidal_embedding(t: torch.Tensor, width: int) -> torch.Tensor:
    half = width // 2
    exponent = torch.arange(half, device=t.device, dtype=torch.float32) / max(half - 1, 1)
    frequencies = torch.exp(-math.log(10_000.0) * exponent)
    values = t.float().unsqueeze(1) * frequencies.unsqueeze(0)
    embedding = torch.cat([torch.sin(values), torch.cos(values)], dim=1)
    return embedding if width % 2 == 0 else F.pad(embedding, (0, 1))


class DiffusionResidualBlock(nn.Module):
    def __init__(self, width: int, dilation: int, time_width: int):
        super().__init__()
        self.norm = nn.GroupNorm(4, width)
        self.conv = nn.Conv1d(width, width, kernel_size=3, padding=dilation, dilation=dilation)
        self.time = nn.Sequential(nn.SiLU(), nn.Linear(time_width, width))
        self.out = nn.Conv1d(width, width, kernel_size=3, padding=1)

    def forward(self, x: torch.Tensor, time_embedding: torch.Tensor) -> torch.Tensor:
        h = self.conv(F.silu(self.norm(x))) + self.time(time_embedding).unsqueeze(-1)
        return x + self.out(F.silu(h))


class DDPMDenoiser1D(nn.Module):
    def __init__(self, channels: int, width: int):
        super().__init__()
        self.time_width = width * 2
        self.time_mlp = nn.Sequential(
            nn.Linear(self.time_width, self.time_width),
            nn.SiLU(),
            nn.Linear(self.time_width, self.time_width),
        )
        self.input = nn.Conv1d(channels, width, kernel_size=3, padding=1)
        self.blocks = nn.ModuleList(
            [DiffusionResidualBlock(width, dilation, self.time_width) for dilation in (1, 2, 4, 8, 16, 8, 4, 2)]
        )
        self.output = nn.Sequential(nn.GroupNorm(4, width), nn.SiLU(), nn.Conv1d(width, channels, kernel_size=3, padding=1))

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        te = self.time_mlp(_sinusoidal_embedding(t, self.time_width))
        h = self.input(x)
        for block in self.blocks:
            h = block(h, te)
        return self.output(h)


class DDPMTrainer:
    def __init__(self, channels: int, length: int, config: DDPMConfig, seed: int):
        if length != 2048:
            raise ValueError(f"DDPM baseline is registered for 2048-sample PU windows, got {length}")
        self.config = config
        self.seed = seed
        self.device = torch.device("cpu")
        torch.manual_seed(seed)
        self.model = DDPMDenoiser1D(channels, config.hidden_channels).to(self.device)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=config.learning_rate, weight_decay=1e-4)
        beta = torch.linspace(1e-4, 2e-2, config.diffusion_steps, device=self.device)
        self.beta = beta
        self.alpha = 1.0 - beta
        self.alpha_bar = torch.cumprod(self.alpha, dim=0)
        self.mean: torch.Tensor | None = None
        self.std: torch.Tensor | None = None
        self.history: list[dict[str, float | int | str]] = []

    def _checkpoint(self, path: Path, completed_epoch: int, elapsed_seconds: float) -> None:
        if self.mean is None or self.std is None:
            raise RuntimeError("normalization state is unavailable")
        _atomic_torch_save(
            {
                "algorithm": "ddpm_1d",
                "config": asdict(self.config),
                "seed": self.seed,
                "completed_epoch": completed_epoch,
                "elapsed_seconds": elapsed_seconds,
                "model": self.model.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "mean": self.mean.cpu(),
                "std": self.std.cpu(),
                "history": self.history,
            },
            path,
        )

    def _restore(self, path: Path) -> tuple[int, float]:
        state = torch.load(path, map_location=self.device, weights_only=False)
        if state.get("algorithm") != "ddpm_1d" or state.get("config") != asdict(self.config):
            raise RuntimeError(f"checkpoint configuration mismatch: {path}")
        self.model.load_state_dict(state["model"])
        self.optimizer.load_state_dict(state["optimizer"])
        self.mean = state["mean"].to(self.device)
        self.std = state["std"].to(self.device)
        self.history = list(state.get("history", []))
        return int(state["completed_epoch"]), float(state["elapsed_seconds"])

    def training_history(self) -> list[dict[str, float | int | str]]:
        """Return the complete checkpointed epoch-level optimization record."""
        return [dict(row) for row in self.history]

    def fit(self, x: np.ndarray, checkpoint: Path) -> float:
        if x.ndim != 3:
            raise ValueError(f"expected (windows, channels, samples), got {x.shape}")
        if not np.isfinite(x).all():
            raise ValueError("DDPM cannot train on non-finite windows")
        x_tensor = torch.as_tensor(x, dtype=torch.float32, device=self.device)
        start_epoch, elapsed = 0, 0.0
        if checkpoint.exists():
            start_epoch, elapsed = self._restore(checkpoint)
        else:
            self.mean = x_tensor.mean(dim=(0, 2), keepdim=True)
            self.std = x_tensor.std(dim=(0, 2), keepdim=True).clamp_min(1e-6)
        if self.mean is None or self.std is None:
            raise RuntimeError("missing normalization state")
        xn = (x_tensor - self.mean) / self.std
        for epoch in range(start_epoch, self.config.epochs):
            tic = perf_counter()
            noise_losses: list[float] = []
            for batch_index, idx in enumerate(_batch_indices(len(xn), self.config.batch_size, self.seed + epoch)):
                batch = xn[idx]
                generator = torch.Generator(device=self.device).manual_seed(self.seed + epoch * 10_000 + batch_index)
                t = torch.randint(0, self.config.diffusion_steps, (len(batch),), generator=generator, device=self.device)
                noise = torch.randn(tuple(batch.shape), generator=generator, device=self.device)
                alpha_bar_t = self.alpha_bar[t].view(-1, 1, 1)
                noised = torch.sqrt(alpha_bar_t) * batch + torch.sqrt(1.0 - alpha_bar_t) * noise
                predicted = self.model(noised, t)
                loss = F.mse_loss(predicted, noise)
                if not torch.isfinite(loss):
                    raise FloatingPointError(f"non-finite DDPM noise-prediction loss at epoch {epoch}")
                self.optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()
                noise_losses.append(float(loss.detach().cpu()))
            elapsed += perf_counter() - tic
            self.history.append({"stage": "ddpm", "epoch": epoch + 1, "noise_prediction_mse": float(np.mean(noise_losses))})
            self._checkpoint(checkpoint, epoch + 1, elapsed)
        return elapsed

    def sample(self, n: int, sample_seed: int) -> np.ndarray:
        if n <= 0:
            raise ValueError("n must be positive")
        if self.mean is None or self.std is None:
            raise RuntimeError("fit or checkpoint restore is required before sample")
        self.model.eval()
        with torch.no_grad():
            x = _seeded_randn((n, self.mean.shape[1], 2048), sample_seed, self.device)
            for step in range(self.config.diffusion_steps - 1, -1, -1):
                t = torch.full((n,), step, dtype=torch.long, device=self.device)
                predicted_noise = self.model(x, t)
                alpha = self.alpha[step]
                alpha_bar = self.alpha_bar[step]
                mean = (x - (self.beta[step] / torch.sqrt(1.0 - alpha_bar)) * predicted_noise) / torch.sqrt(alpha)
                if step > 0:
                    x = mean + torch.sqrt(self.beta[step]) * _seeded_randn(tuple(x.shape), sample_seed + step, self.device)
                else:
                    x = mean
            return (x * self.std + self.mean).cpu().numpy().astype(np.float32)


def make_trainer(
    method: str,
    channels: int,
    length: int,
    seed: int,
    timegan_config: TimeGANConfig,
    ddpm_config: DDPMConfig,
) -> TimeGANTrainer | DDPMTrainer:
    if method == "timegan":
        return TimeGANTrainer(channels, length, timegan_config, seed)
    if method == "ddpm":
        return DDPMTrainer(channels, length, ddpm_config, seed)
    raise ValueError(f"unknown trained baseline: {method}")
