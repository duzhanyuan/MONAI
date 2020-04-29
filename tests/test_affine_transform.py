# Copyright 2020 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import numpy as np
import torch
from parameterized import parameterized

from monai.networks.layers import AffineTransform
from monai.networks.utils import normalize_transform, to_norm_affine

TEST_NORM_CASES = [
    [(4, 5), True, [[[0.5, 0, -1], [0, 0.666667, -1], [0, 0, 1]]]],
    [(2, 4, 5), True, [[[0.5, 0., 0., -1.], [0., 0.6666667, 0., -1.], [0., 0., 2., -1.], [0., 0., 0., 1.]]]],
    [(4, 5), False, [[[0.4, 0., -0.8], [0., 0.5, -0.75], [0., 0., 1.]]]],
    [(2, 4, 5), False, [[[0.4, 0., 0., -0.8], [0., 0.5, 0., -0.75], [0., 0., 1., -0.5], [0., 0., 0., 1.]]]],
]

TEST_TO_NORM_AFFINE_CASES = [
    [[[[1, 0, 0], [0, 1, 0], [0, 0, 1]]], (4, 6), (5, 3), True,
     [[[0.4, 0., -0.6], [0., 1.3333334, 0.33333337], [0., 0., 1.]]]],
    [[[[1, 0, 0], [0, 1, 0], [0, 0, 1]]], (4, 6), (5, 3), False, [[[0.5, 0., -0.5], [0., 1.25, 0.25], [0., 0., 1.]]]],
    [[[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]], (2, 4, 6), (3, 5, 3), True,
     [[[0.4, 0., 0., -0.6], [0., 1.3333334, 0., 0.33333337], [0., 0., 2., 1.], [0., 0., 0., 1.]]]],
    [[[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]], (2, 4, 6), (3, 5, 3), False,
     [[[0.5, 0., 0., -0.5], [0., 1.25, 0., 0.25], [0., 0., 1.5, 0.5], [0., 0., 0., 1.]]]],
]

TEST_ILL_TO_NORM_AFFINE_CASES = [
    [[[[1, 0, 0], [0, 1, 0], [0, 0, 1]]], (3, 4, 6), (3, 5, 3), False],
    [[[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]], (4, 6), (3, 5, 3), True],
    [[[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]], (4, 6), (3, 5, 3), True],
]


class TestNormTransform(unittest.TestCase):

    @parameterized.expand(TEST_NORM_CASES)
    def test_norm_xform(self, input_shape, align_corners, expected):
        norm = normalize_transform(input_shape,
                                   device=torch.device('cpu:0'),
                                   dtype=torch.float32,
                                   align_corners=align_corners)
        norm = norm.detach().cpu().numpy()
        np.testing.assert_allclose(norm, expected, atol=1e-6)
        if torch.cuda.is_available():
            norm = normalize_transform(input_shape,
                                       device=torch.device('cuda:0'),
                                       dtype=torch.float32,
                                       align_corners=align_corners)
            norm = norm.detach().cpu().numpy()
            np.testing.assert_allclose(norm, expected, atol=1e-4)


class TestToNormAffine(unittest.TestCase):

    @parameterized.expand(TEST_TO_NORM_AFFINE_CASES)
    def test_to_norm_affine(self, affine, src_size, dst_size, align_corners, expected):
        affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
        new_affine = to_norm_affine(affine, src_size, dst_size, align_corners)
        new_affine = new_affine.detach().cpu().numpy()
        np.testing.assert_allclose(new_affine, expected, atol=1e-6)

        if torch.cuda.is_available():
            affine = torch.as_tensor(affine, device=torch.device('cuda:0'), dtype=torch.float32)
            new_affine = to_norm_affine(affine, src_size, dst_size, align_corners)
            new_affine = new_affine.detach().cpu().numpy()
            np.testing.assert_allclose(new_affine, expected, atol=1e-4)

    @parameterized.expand(TEST_ILL_TO_NORM_AFFINE_CASES)
    def test_to_norm_affine_ill(self, affine, src_size, dst_size, align_corners):
        with self.assertRaises(ValueError):
            to_norm_affine(affine, src_size, dst_size, align_corners)
        with self.assertRaises(ValueError):
            affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
            to_norm_affine(affine, src_size, dst_size, align_corners)


class TestAffineTransform(unittest.TestCase):

    def test_affine_shift(self):
        affine = [[1, 0, 0], [0, 1, -1]]
        image = torch.as_tensor([[[[4, 1, 3, 2], [7, 6, 8, 5], [3, 5, 3, 6]]]])
        out = AffineTransform(affine)(image)
        out = out.detach().cpu().numpy()
        expected = [[[[0, 4, 1, 3], [0, 7, 6, 8], [0, 3, 5, 3]]]]
        np.testing.assert_allclose(out, expected, atol=1e-5)

    def test_affine_shift_1(self):
        affine = [[1, 0, -1], [0, 1, -1]]
        image = torch.as_tensor([[[[4, 1, 3, 2], [7, 6, 8, 5], [3, 5, 3, 6]]]])
        out = AffineTransform(affine)(image)
        out = out.detach().cpu().numpy()
        expected = [[[[0, 0, 0, 0], [0, 4, 1, 3], [0, 7, 6, 8]]]]
        np.testing.assert_allclose(out, expected, atol=1e-5)

    def test_affine_shift_2(self):
        affine = [[1, 0, -1], [0, 1, 0]]
        image = torch.as_tensor([[[[4, 1, 3, 2], [7, 6, 8, 5], [3, 5, 3, 6]]]])
        out = AffineTransform(affine)(image)
        out = out.detach().cpu().numpy()
        expected = [[[[0, 0, 0, 0], [4, 1, 3, 2], [7, 6, 8, 5]]]]
        np.testing.assert_allclose(out, expected, atol=1e-5)

    def test_zoom(self):
        affine = [[1, 0, 0], [0, 2, 0]]
        image = torch.arange(1, 13).view(1, 1, 3, 4).to(device=torch.device('cpu:0'))
        out = AffineTransform(affine, (3, 2))(image)
        expected = [[[[1, 3], [5, 7], [9, 11]]]]
        np.testing.assert_allclose(out, expected, atol=1e-5)

    def test_zoom_1(self):
        affine = [[2, 0, 0], [0, 1, 0]]
        image = torch.arange(1, 13).view(1, 1, 3, 4).to(device=torch.device('cpu:0'))
        out = AffineTransform(affine, (1, 4))(image)
        expected = [[[[1, 2, 3, 4]]]]
        np.testing.assert_allclose(out, expected, atol=1e-5)

    def test_zoom_2(self):
        affine = [[2, 0, 0], [0, 2, 0]]
        image = torch.arange(1, 13).view(1, 1, 3, 4).to(device=torch.device('cpu:0'))
        out = AffineTransform(affine, (1, 2))(image)
        expected = [[[[1, 3]]]]
        np.testing.assert_allclose(out, expected, atol=1e-5)

    def test_affine_transform_minimum(self):
        t = np.pi / 3
        affine = [[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]]
        affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
        image = torch.arange(24).view(1, 1, 4, 6).to(device=torch.device('cpu:0'))
        out = AffineTransform(affine)(image)
        out = out.detach().cpu().numpy()
        expected = [[[[0.0, 0.06698727, 0., 0., 0., 0.], [3.8660254, 0.86602557, 0., 0., 0., 0.],
                      [7.732051, 3.035899, 0.73205125, 0., 0., 0.], [11.598076, 6.901923, 2.7631402, 0., 0., 0.]]]]
        np.testing.assert_allclose(out, expected, atol=1e-5)

    def test_affine_transform_2d(self):
        t = np.pi / 3
        affine = [[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]]
        affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
        image = torch.arange(24).view(1, 1, 4, 6).to(device=torch.device('cpu:0'))
        out = AffineTransform(affine, (3, 4), padding_mode='border', align_corners=True, mode='bilinear')(image)
        out = out.detach().cpu().numpy()
        expected = [[[[7.1525574e-07, 4.9999994e-01, 1.0000000e+00, 1.4999999e+00],
                      [3.8660259e+00, 1.3660253e+00, 1.8660252e+00, 2.3660252e+00],
                      [7.7320518e+00, 3.0358994e+00, 2.7320509e+00, 3.2320507e+00]]]]
        np.testing.assert_allclose(out, expected, atol=1e-5)

        if torch.cuda.is_available():
            affine = torch.as_tensor(affine, device=torch.device('cuda:0'), dtype=torch.float32)
            image = torch.arange(24).view(1, 1, 4, 6).to(device=torch.device('cuda:0'))
            xform = AffineTransform(affine, (3, 4), padding_mode='border', align_corners=True, mode='bilinear')
            out = xform(image)
            out = out.detach().cpu().numpy()
            expected = [[[[7.1525574e-07, 4.9999994e-01, 1.0000000e+00, 1.4999999e+00],
                          [3.8660259e+00, 1.3660253e+00, 1.8660252e+00, 2.3660252e+00],
                          [7.7320518e+00, 3.0358994e+00, 2.7320509e+00, 3.2320507e+00]]]]
            np.testing.assert_allclose(out, expected, atol=1e-4)

    def test_affine_transform_3d(self):
        t = np.pi / 3
        affine = [[1, 0, 0, 0], [0., np.cos(t), -np.sin(t), 0], [0, np.sin(t), np.cos(t), 0], [0, 0, 0, 1]]
        affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
        image = torch.arange(48).view(2, 1, 4, 2, 3).to(device=torch.device('cpu:0'))
        xform = AffineTransform(affine, (3, 4, 2), padding_mode='border', align_corners=False, mode='bilinear')
        out = xform(image)
        out = out.detach().cpu().numpy()
        expected = [[[[[0.00000006, 0.5000001], [2.3660254, 1.3660254], [4.732051, 2.4019241], [5., 3.9019237]],
                      [[6., 6.5], [8.366026, 7.3660254], [10.732051, 8.401924], [11., 9.901924]],
                      [[12., 12.5], [14.366026, 13.366025], [16.732052, 14.401924], [17., 15.901923]]]],
                    [[[[24., 24.5], [26.366024, 25.366024], [28.732052, 26.401924], [29., 27.901924]],
                      [[30., 30.5], [32.366028, 31.366026], [34.732048, 32.401924], [35., 33.901924]],
                      [[36., 36.5], [38.366024, 37.366024], [40.73205, 38.401924], [41., 39.901924]]]]]
        np.testing.assert_allclose(out, expected, atol=1e-4)

        if torch.cuda.is_available():
            affine = torch.as_tensor(affine, device=torch.device('cuda:0'), dtype=torch.float32)
            image = torch.arange(48).view(2, 1, 4, 2, 3).to(device=torch.device('cuda:0'))
            xform = AffineTransform(affine, (3, 4, 2), padding_mode='border', align_corners=False, mode='bilinear')
            out = xform(image)
            out = out.detach().cpu().numpy()
            expected = [[[[[0.00000006, 0.5000001], [2.3660254, 1.3660254], [4.732051, 2.4019241], [5., 3.9019237]],
                          [[6., 6.5], [8.366026, 7.3660254], [10.732051, 8.401924], [11., 9.901924]],
                          [[12., 12.5], [14.366026, 13.366025], [16.732052, 14.401924], [17., 15.901923]]]],
                        [[[[24., 24.5], [26.366024, 25.366024], [28.732052, 26.401924], [29., 27.901924]],
                          [[30., 30.5], [32.366028, 31.366026], [34.732048, 32.401924], [35., 33.901924]],
                          [[36., 36.5], [38.366024, 37.366024], [40.73205, 38.401924], [41., 39.901924]]]]]
            np.testing.assert_allclose(out, expected, atol=1e-4)

    def test_ill_affine_transform(self):
        with self.assertRaises(ValueError):  # shape not sequence
            t = np.pi / 3
            affine = [[1, 0, 0, 0], [0., np.cos(t), -np.sin(t), 0], [0, np.sin(t), np.cos(t), 0], [0, 0, 0, 1]]
            affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
            xform = AffineTransform(affine, range(3, 4), padding_mode='border', align_corners=False, mode='bilinear')

        with self.assertRaises(ValueError):  # image too small
            t = np.pi / 3
            affine = [[1, 0, 0, 0], [0., np.cos(t), -np.sin(t), 0], [0, np.sin(t), np.cos(t), 0], [0, 0, 0, 1]]
            affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
            xform = AffineTransform(affine, (3, 4, 2), padding_mode='border', align_corners=False, mode='bilinear')
            xform([1, 2, 3])

        with self.assertRaises(ValueError):  # output shape too small
            t = np.pi / 3
            affine = [[1, 0, 0, 0], [0., np.cos(t), -np.sin(t), 0], [0, np.sin(t), np.cos(t), 0], [0, 0, 0, 1]]
            affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
            image = torch.arange(48).view(2, 1, 4, 2, 3).to(device=torch.device('cpu:0'))
            xform = AffineTransform(affine, (3, 4), padding_mode='border', align_corners=False, mode='bilinear')
            xform(image)

        with self.assertRaises(ValueError):  # incorrect affine
            t = np.pi / 3
            affine = [[1, 0, 0, 0], [0., np.cos(t), -np.sin(t), 0], [0, np.sin(t), np.cos(t), 0], [0, 0, 0, 1]]
            affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
            affine = affine.unsqueeze(0).unsqueeze(0)
            image = torch.arange(48).view(2, 1, 4, 2, 3).to(device=torch.device('cpu:0'))
            xform = AffineTransform(affine, (2, 3, 4), padding_mode='border', align_corners=False, mode='bilinear')

        with self.assertRaises(ValueError):  # batch doesn't match
            t = np.pi / 3
            affine = [[1, 0, 0, 0], [0., np.cos(t), -np.sin(t), 0], [0, np.sin(t), np.cos(t), 0], [0, 0, 0, 1]]
            affine = torch.as_tensor(affine, device=torch.device('cpu:0'), dtype=torch.float32)
            affine = affine.unsqueeze(0)
            affine = affine.repeat(3, 1, 1)
            image = torch.arange(48).view(2, 1, 4, 2, 3).to(device=torch.device('cpu:0'))
            xform = AffineTransform(affine, (2, 3, 4), padding_mode='border', align_corners=False, mode='bilinear')
            xform(image)

        with self.assertRaises(ValueError):  # wrong affine
            affine = [[1, 0, 0, 0], [0, 0, 0, 1]]
            xform = AffineTransform(affine, (2, 3, 4), padding_mode='border', align_corners=False, mode='bilinear')

    def test_forward_2d(self):
        x = torch.rand(2, 1, 4, 4)
        theta = torch.Tensor([[[0, -1, 0], [1, 0, 0]]]).repeat(2, 1, 1)
        grid = torch.nn.functional.affine_grid(theta, x.size(), align_corners=False)
        expected = torch.nn.functional.grid_sample(x, grid, align_corners=False)
        expected = expected.detach().cpu().numpy()

        actual = AffineTransform(theta, normalized=True, reverse_indexing=False)(x)
        actual = actual.detach().cpu().numpy()
        np.testing.assert_allclose(actual, expected)
        np.testing.assert_allclose(list(theta.shape), [2, 2, 3])

        theta = torch.Tensor([[0, -1, 0], [1, 0, 0]])
        actual = AffineTransform(theta, normalized=True, reverse_indexing=False)(x)
        actual = actual.detach().cpu().numpy()
        np.testing.assert_allclose(actual, expected)
        np.testing.assert_allclose(list(theta.shape), [2, 3])

        theta = torch.Tensor([[[0, -1, 0], [1, 0, 0]]])
        actual = AffineTransform(theta, normalized=True, reverse_indexing=False)(x)
        actual = actual.detach().cpu().numpy()
        np.testing.assert_allclose(actual, expected)
        np.testing.assert_allclose(list(theta.shape), [1, 2, 3])

    def test_forward_3d(self):
        x = torch.rand(2, 1, 4, 4, 4)
        theta = torch.Tensor([[[0, 0, -1, 0], [1, 0, 0, 0], [0, 0, 1, 0]]]).repeat(2, 1, 1)
        grid = torch.nn.functional.affine_grid(theta, x.size(), align_corners=False)
        expected = torch.nn.functional.grid_sample(x, grid, align_corners=False)
        expected = expected.detach().cpu().numpy()

        actual = AffineTransform(theta, normalized=True, reverse_indexing=False)(x)
        actual = actual.detach().cpu().numpy()
        np.testing.assert_allclose(actual, expected)
        np.testing.assert_allclose(list(theta.shape), [2, 3, 4])

        theta = torch.Tensor([[0, 0, -1, 0], [1, 0, 0, 0], [0, 0, 1, 0]])
        actual = AffineTransform(theta, normalized=True, reverse_indexing=False)(x)
        actual = actual.detach().cpu().numpy()
        np.testing.assert_allclose(actual, expected)
        np.testing.assert_allclose(list(theta.shape), [3, 4])

        theta = torch.Tensor([[[0, 0, -1, 0], [1, 0, 0, 0], [0, 0, 1, 0]]])
        actual = AffineTransform(theta, normalized=True, reverse_indexing=False)(x)
        actual = actual.detach().cpu().numpy()
        np.testing.assert_allclose(actual, expected)
        np.testing.assert_allclose(list(theta.shape), [1, 3, 4])


if __name__ == '__main__':
    unittest.main()
