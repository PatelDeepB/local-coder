"""Unit tests for 10,240-bit HyperVector symbolic operations."""

import numpy as np
import pytest
from local_coder.knowledge.hyper_vector import HyperVector


def test_should_generate_deterministic_bipolar_vector_from_seed() -> None:
    # Arrange & Act
    v1 = HyperVector.from_seed("user_login", dimension=10240)
    v2 = HyperVector.from_seed("user_login", dimension=10240)

    # Assert
    assert v1.dimension == 10240
    assert np.array_equal(v1.data, v2.data)
    assert set(np.unique(v1.data)).issubset({-1, 1})


def test_should_perform_multiplicative_binding_and_unbinding() -> None:
    # Arrange
    role = HyperVector.from_seed("role", dimension=10240)
    user = HyperVector.from_seed("user", dimension=10240)

    # Act: Bound = role * user
    bound = role.bind(user)

    # Assert: Unbinding bound * user == role in bipolar space
    unbound = bound.bind(user)
    similarity = unbound.similarity(role)
    assert similarity > 0.99


def test_should_bundle_vectors_with_majority_voting() -> None:
    # Arrange
    v1 = HyperVector.from_seed("concept_a", dimension=10240)
    v2 = HyperVector.from_seed("concept_b", dimension=10240)
    v3 = HyperVector.from_seed("concept_c", dimension=10240)

    # Act
    bundled = HyperVector.bundle([v1, v2, v3])

    # Assert: Bundled vector should have positive similarity to all constituent vectors
    assert bundled.similarity(v1) > 0.15
    assert bundled.similarity(v2) > 0.15
    assert bundled.similarity(v3) > 0.15
