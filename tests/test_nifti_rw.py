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

import os
import tempfile
import unittest

import nibabel as nib
import numpy as np
from parameterized import parameterized

from monai.data import write_nifti
from monai.transforms import LoadNifti, Orientation, Spacing
from tests.utils import make_nifti_image

TEST_IMAGE = np.arange(24).reshape((2, 4, 3))
TEST_AFFINE = np.array([[-5.3, 0., 0., 102.01], [0., 0.52, 2.17, -7.50], [-0., 1.98, -0.26, -23.12], [0., 0., 0., 1.]])

TEST_CASES = [
    [TEST_IMAGE, TEST_AFFINE,
     dict(as_closest_canonical=True, image_only=False),
     np.arange(24).reshape((2, 4, 3))],
    [
        TEST_IMAGE, TEST_AFFINE,
        dict(as_closest_canonical=True, image_only=True),
        np.array([[[12., 15., 18., 21.], [13., 16., 19., 22.], [14., 17., 20., 23.]],
                  [[0., 3., 6., 9.], [1., 4., 7., 10.], [2., 5., 8., 11.]]])
    ],
    [TEST_IMAGE, TEST_AFFINE,
     dict(as_closest_canonical=False, image_only=True),
     np.arange(24).reshape((2, 4, 3))],
    [TEST_IMAGE, TEST_AFFINE,
     dict(as_closest_canonical=False, image_only=False),
     np.arange(24).reshape((2, 4, 3))],
    [TEST_IMAGE, None,
     dict(as_closest_canonical=False, image_only=False),
     np.arange(24).reshape((2, 4, 3))],
]


class TestNiftiLoadRead(unittest.TestCase):

    @parameterized.expand(TEST_CASES)
    def test_orientation(self, array, affine, reader_param, expected):
        test_image = make_nifti_image(array, affine)

        # read test cases
        loader = LoadNifti(**reader_param)
        load_result = loader(test_image)
        if isinstance(load_result, tuple):
            data_array, header = load_result
        else:
            data_array = load_result
            header = None
        if os.path.exists(test_image):
            os.remove(test_image)

        # write test cases
        if header is not None:
            write_nifti(data_array, test_image, header['affine'], header.get('original_affine', None))
        elif affine is not None:
            write_nifti(data_array, test_image, affine)
        else:
            write_nifti(data_array, test_image)
        saved = nib.load(test_image)
        saved_affine = saved.affine
        saved_data = saved.get_fdata()
        if os.path.exists(test_image):
            os.remove(test_image)

        if affine is not None:
            np.testing.assert_allclose(saved_affine, affine)
        np.testing.assert_allclose(saved_data, expected)

    def test_consistency(self):
        np.set_printoptions(suppress=True, precision=3)
        test_image = make_nifti_image(np.arange(64).reshape(1, 8, 8), np.diag([1.5, 1.5, 1.5, 1]))
        data, header = LoadNifti(as_closest_canonical=False)(test_image)
        data, original_affine, new_affine = Spacing([0.8, 0.8, 0.8])(data[None], header['affine'], interp_order='nearest')
        data, _, new_affine = Orientation('ILP')(data, new_affine)
        if os.path.exists(test_image):
            os.remove(test_image)
        write_nifti(data[0], test_image, new_affine, original_affine, interp_order=0, mode='reflect')
        saved = nib.load(test_image)
        saved_data = saved.get_fdata()
        np.testing.assert_allclose(saved_data, np.arange(64).reshape(1, 8, 8), atol=1e-7)
        if os.path.exists(test_image):
            os.remove(test_image)
        write_nifti(data[0], test_image, new_affine, original_affine, interp_order=0, mode='reflect', output_shape=(1, 8, 8))
        saved = nib.load(test_image)
        saved_data = saved.get_fdata()
        np.testing.assert_allclose(saved_data, np.arange(64).reshape(1, 8, 8), atol=1e-7)
        if os.path.exists(test_image):
            os.remove(test_image)

    def test_write_1d(self):
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(5).reshape(-1)
            write_nifti(img, image_name, affine=np.diag([1, 1, 1]), target_affine=np.diag([1.4, 2., 1]))
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), [0, 1, 3, 0])
            np.testing.assert_allclose(out.affine, np.diag([1.4, 1, 1, 1]))
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(5).reshape(-1)
            write_nifti(img, image_name, affine=[[1]], target_affine=[[1.4]])
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), [0, 1, 3, 0])
            np.testing.assert_allclose(out.affine, np.diag([1.4, 1, 1, 1]))
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(5).reshape(-1)
            write_nifti(img, image_name, affine=np.diag([1.5, 1.5, 1.5]), target_affine=np.diag([1.5, 1.5, 1.5]))
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), np.arange(5).reshape(-1))
            np.testing.assert_allclose(out.affine, np.diag([1.5, 1, 1, 1]))

    def test_write_2d(self):
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(6).reshape((2, 3))
            write_nifti(img, image_name, affine=np.diag([1]), target_affine=np.diag([1.4]))
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), [[0, 1, 2], [0, 0, 0]])
            np.testing.assert_allclose(out.affine, np.diag([1.4, 1, 1, 1]))
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(5).reshape((1, 5))
            write_nifti(img, image_name, affine=np.diag([1, 1, 1, 3, 3]), target_affine=np.diag([1.4, 2., 1, 3, 5]))
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), [[0, 2, 4]])
            np.testing.assert_allclose(out.affine, np.diag([1.4, 2, 1, 1]))

    def test_write_3d(self):
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(6).reshape((1, 2, 3))
            write_nifti(img, image_name, affine=np.diag([1]), target_affine=np.diag([1.4]))
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), [[[0, 1, 2], [3, 4, 5]]])
            np.testing.assert_allclose(out.affine, np.diag([1.4, 1, 1, 1]))
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(5).reshape((1, 1, 5))
            write_nifti(img, image_name, affine=np.diag([1, 1, 1, 3, 3]), target_affine=np.diag([1.4, 2., 2, 3, 5]))
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), [[[0, 2, 4]]])
            np.testing.assert_allclose(out.affine, np.diag([1.4, 2, 2, 1]))

    def test_write_4d(self):
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(6).reshape((1, 1, 3, 2))
            write_nifti(img, image_name, affine=np.diag([1.4, 1]), target_affine=np.diag([1, 1.4, 1]))
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), [[[[0, 1], [2, 3], [4, 5]]]])
            np.testing.assert_allclose(out.affine, np.diag([1, 1.4, 1, 1]))
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(5).reshape((1, 1, 5, 1))
            write_nifti(img, image_name, affine=np.diag([1, 1, 1, 3, 3]), target_affine=np.diag([1.4, 2., 2, 3, 5]))
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), [[[[0], [2], [4]]]])
            np.testing.assert_allclose(out.affine, np.diag([1.4, 2, 2, 1]))

    def test_write_5d(self):
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(12).reshape((1, 1, 3, 2, 2))
            write_nifti(img, image_name, affine=np.diag([1]), target_affine=np.diag([1.4]))
            out = nib.load(image_name)
            np.testing.assert_allclose(
                out.get_fdata(), np.array([[[[[0., 1.], [2., 3.]], [[4., 5.], [6., 7.]], [[8., 9.], [10., 11.]]]]]))
            np.testing.assert_allclose(out.affine, np.diag([1.4, 1, 1, 1]))
        with tempfile.TemporaryDirectory() as out_dir:
            image_name = os.path.join(out_dir, 'test.nii.gz')
            img = np.arange(10).reshape((1, 1, 5, 1, 2))
            write_nifti(img, image_name, affine=np.diag([1, 1, 1, 3, 3]), target_affine=np.diag([1.4, 2., 2, 3, 5]))
            out = nib.load(image_name)
            np.testing.assert_allclose(out.get_fdata(), np.array([[[[[0., 1.]], [[4., 5.]], [[8., 9.]]]]]))
            np.testing.assert_allclose(out.affine, np.diag([1.4, 2, 2, 1]))


if __name__ == '__main__':
    unittest.main()
