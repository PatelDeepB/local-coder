"""Hyperdimensional Vector Symbolic Architecture (VSA) for zero-RAM semantic indexing."""

from dataclasses import dataclass
from typing import Sequence
import hashlib
import numpy as np


@dataclass(frozen=True)
class HyperVector:
    """Represents a 10,240-bit bipolar hypervector for symbolic computing."""

    data: np.ndarray  # int8 array with values in {-1, 1}

    @property
    def dimension(self) -> int:
        """Returns the dimensionality of the vector."""
        return int(len(self.data))

    @classmethod
    def from_seed(cls, seed_string: str, dimension: int = 10240) -> "HyperVector":
        """Generates a deterministic pseudo-random bipolar hypervector from text."""
        # Use SHA-256 seed to create reproducible pseudorandom bits
        hasher = hashlib.sha256(seed_string.encode("utf-8")).digest()
        seed_int = int.from_bytes(hasher[:4], "little")
        rng = np.random.RandomState(seed_int)

        # Generate bipolar {-1, 1} array
        raw = rng.choice(np.array([-1, 1], dtype=np.int8), size=dimension)
        return cls(data=raw)

    def bind(self, other: "HyperVector") -> "HyperVector":
        """Performs multiplicative binding (elementwise multiplication / XOR equivalent)."""
        if self.dimension != other.dimension:
            raise ValueError(f"Dimension mismatch: {self.dimension} vs {other.dimension}")
        bound_data = (self.data * other.data).astype(np.int8)
        return HyperVector(data=bound_data)

    def permute(self, shift: int = 1) -> "HyperVector":
        """Applies cyclic permutation (rotation) to encode sequence order and tree depth."""
        rotated = np.roll(self.data, shift)
        return HyperVector(data=rotated)

    @classmethod
    def bundle(cls, vectors: Sequence["HyperVector"]) -> "HyperVector":
        """Performs majority bundling (vector addition followed by sign thresholding)."""
        if not vectors:
            raise ValueError("Cannot bundle an empty sequence of vectors.")
        if len(vectors) == 1:
            return vectors[0]

        dim = vectors[0].dimension
        accumulator = np.zeros(dim, dtype=np.int32)
        for v in vectors:
            accumulator += v.data

        # Threshold using majority voting
        signs = np.sign(accumulator)
        signs[signs == 0] = 1
        return cls(data=signs.astype(np.int8))

    def similarity(self, other: "HyperVector") -> float:
        """Computes normalized cosine similarity (equivalent to Hamming distance)."""
        if self.dimension != other.dimension:
            raise ValueError("Dimension mismatch.")
        dot_product = float(np.dot(self.data.astype(np.float32), other.data.astype(np.float32)))
        return dot_product / float(self.dimension)
