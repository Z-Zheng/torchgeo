# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
from pathlib import Path
from typing import Generator

import matplotlib.pyplot as plt
import pytest
import torch
from _pytest.monkeypatch import MonkeyPatch
from rasterio.crs import CRS

from torchgeo.datasets import NAIP, BoundingBox, ZipDataset
from torchgeo.transforms import Identity


class TestNAIP:
    @pytest.fixture
    def dataset(self, monkeypatch: Generator[MonkeyPatch, None, None]) -> NAIP:
        monkeypatch.setattr(  # type: ignore[attr-defined]
            plt, "show", lambda *args: None
        )
        root = os.path.join("tests", "data", "naip")
        transforms = Identity()
        return NAIP(root, transforms=transforms)

    def test_getitem(self, dataset: NAIP) -> None:
        x = dataset[dataset.bounds]
        assert isinstance(x, dict)
        assert isinstance(x["crs"], CRS)
        assert isinstance(x["image"], torch.Tensor)

    def test_add(self, dataset: NAIP) -> None:
        ds = dataset + dataset
        assert isinstance(ds, ZipDataset)

    def test_plot(self, dataset: NAIP) -> None:
        query = dataset.bounds
        x = dataset[query]
        dataset.plot(x["image"])

    def test_no_data(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No NAIP data was found in "):
            NAIP(str(tmp_path))

    def test_invalid_query(self, dataset: NAIP) -> None:
        query = BoundingBox(0, 0, 0, 0, 0, 0)
        with pytest.raises(
            IndexError, match="query: .* not found in index with bounds:"
        ):
            dataset[query]
