# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import itertools

import pytest
import torch
import torch.nn as nn

from torchgeo.models import ChangeMixin, ChangeStar, ChangeStarFarSeg

BACKBONE = ["resnet18", "resnet34", "resnet50", "resnet101", "anynet"]
IN_CHANNELS = [64, 128]
INNNR_CHANNELS = [16, 32, 64]
NC = [1, 2, 4]
SF = [4.0, 8.0, 1.0]


class TestChangeStar:
    @torch.no_grad()  # type: ignore[misc]
    def test_changestar_farseg_classes(self) -> None:
        model = ChangeStarFarSeg(
            classes=4, backbone="resnet50", backbone_pretrained=False
        )
        x = torch.randn(2, 2, 3, 128, 128)
        y = model(x)

        assert y["bi_seg_logit"].shape[2] == 4

    @torch.no_grad()  # type: ignore[misc]
    def test_changestar_farseg_output_size(self) -> None:
        model = ChangeStarFarSeg(
            classes=4, backbone="resnet50", backbone_pretrained=False
        )
        model.eval()
        x = torch.randn(2, 2, 3, 128, 128)
        y = model(x)

        assert y["bi_seg_logit"].shape[3] == 128 and y["bi_seg_logit"].shape[4] == 128
        assert y["change_prob"].shape[2] == 128 and y["change_prob"].shape[3] == 128

        model.train()
        y = model(x)

        assert y["bi_seg_logit"].shape[3] == 128 and y["bi_seg_logit"].shape[4] == 128
        assert y["bi_change_logit"][0].shape[2] == 128
        assert y["bi_change_logit"][0].shape[3] == 128
        assert y["bi_change_logit"][1].shape[2] == 128
        assert y["bi_change_logit"][1].shape[3] == 128

    @torch.no_grad()  # type: ignore[misc]
    @pytest.mark.parametrize("backbone", BACKBONE)
    def test_changestar_farseg_backbone(self, backbone: str) -> None:
        if backbone == "anynet":
            match = "unknown backbone: anynet."
            with pytest.raises(ValueError, match=match):
                ChangeStarFarSeg(
                    classes=4, backbone="anynet", backbone_pretrained=False
                )
        else:
            ChangeStarFarSeg(classes=4, backbone=backbone, backbone_pretrained=False)

    @torch.no_grad()  # type: ignore[misc]
    @pytest.mark.parametrize(
        "inc,innerc,nc,sf", list(itertools.product(IN_CHANNELS, INNNR_CHANNELS, NC, SF))
    )
    def test_changemixin_output_size(self, inc: int, innerc: int, nc: int, sf: float):
        m = ChangeMixin(
            in_channels=inc, inner_channels=innerc, num_convs=nc, scale_factor=sf
        )

        y = m(torch.rand(3, 2, inc // 2, 32, 32))
        assert y[0].shape == y[1].shape
        assert y[0].shape == (3, 1, int(32 * sf), int(32 * sf))

    @torch.no_grad()  # type: ignore[misc]
    def test_changestar(self):
        dense_feature_extractor = nn.Sequential(
            nn.Conv2d(3, 32, 3, 1, 1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(3, 2, 1),
        )

        seg_classifier = nn.Sequential(
            nn.Conv2d(32, 2, 3, 1, 1), nn.UpsamplingBilinear2d(scale_factor=2.0)
        )

        m = ChangeStar(
            dense_feature_extractor,
            seg_classifier,
            ChangeMixin(
                in_channels=32 * 2, inner_channels=16, num_convs=4, scale_factor=2.0
            ),
        )
        m.eval()

        y = m(torch.rand(3, 2, 3, 64, 64))
        assert y["bi_seg_logit"].shape == (3, 2, 3, 64, 64)
        assert y["change_prob"].shape == (3, 1, 64, 64)
