# BSD 3-Clause License

# Copyright (c) 2021, Muhammad Asad (masadcv@gmail.com)
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import math
import unittest
from functools import partial, wraps

import numpy as np
import torch
from parameterized import parameterized

# set deterministic seed
torch.manual_seed(15)
np.random.seed(15)

try:
    import FastGeodis
except:
    print(
        "Unable to load FastGeodis for unittests\nMake sure to install using: python setup.py install"
    )
    exit()


def skip_if_no_cuda(obj):
    return unittest.skipUnless(torch.cuda.is_available(), "Skipping CUDA-based tests")(
        obj
    )


def run_cuda_if_available(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if args[1] == "cuda":
            if torch.cuda.is_available():
                return fn(*args, **kwargs)
            else:
                raise unittest.SkipTest("skipping as cuda device not found")
        else:
            return fn(*args, **kwargs)

    return wrapper


def fastgeodis_generalised_geodesic_distance_2d(image, softmask, v, lamb, iter):
    return FastGeodis.generalised_geodesic2d(image, softmask, v, lamb, iter)


def fastgeodis_generalised_geodesic_distance_3d(
    image, softmask, v, lamb, iter, spacing
):
    return FastGeodis.generalised_geodesic3d(image, softmask, spacing, v, lamb, iter)


def fastgeodis_GSF_2d(image, softmask, theta, v, lamb, iter):
    return FastGeodis.GSF2d(image, softmask, theta, v, lamb, iter)


def fastgeodis_GSF_3d(image, softmask, theta, v, lamb, iter, spacing):
    return FastGeodis.GSF3d(image, softmask, theta, spacing, v, lamb, iter)


def get_simple_shape(base_dim, num_dims):
    return [1, 1] + [
        base_dim,
    ] * num_dims


def get_fastgeodis_func(num_dims, spacing=[1.0, 1.0, 1.0]):
    if num_dims == 2:
        return fastgeodis_generalised_geodesic_distance_2d
    elif num_dims == 3:
        return partial(fastgeodis_generalised_geodesic_distance_3d, spacing=spacing)
    else:
        raise ValueError("Unsupported num_dims received: {}".format(num_dims))


def get_GSF_func(num_dims, spacing=[1.0, 1.0, 1.0]):
    if num_dims == 2:
        return fastgeodis_GSF_2d
    elif num_dims == 3:
        return partial(fastgeodis_GSF_3d, spacing=spacing)
    else:
        raise ValueError("Unsupported num_dims received: {}".format(num_dims))


DEVICES_TO_RUN = ["cpu", "cuda"]
CONF_2D = [(dev, 2, bas) for dev in DEVICES_TO_RUN for bas in [32, 128, 256]]
CONF_3D = [(dev, 3, bas) for dev in DEVICES_TO_RUN for bas in [16, 64, 128]]
CONF_ALL = CONF_2D + CONF_3D


class TestFastGeodis(unittest.TestCase):
    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_ill_shape(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_fastgeodis_func(num_dims=num_dims)

        # batch != 1 - unsupported
        image_shape_mod = image_shape.copy()
        mask_shape_mod = mask_shape.copy()
        with self.assertRaises(ValueError):
            mask_shape_mod[0] = 2
            image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
            mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        with self.assertRaises(ValueError):
            image_shape_mod[0] = 2
            image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
            mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        # spatial shape mismatch - unsupported
        image_shape_mod = image_shape.copy()
        mask_shape_mod = mask_shape.copy()
        with self.assertRaises(ValueError):
            image_shape_mod[-1] = 12
            image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
            mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        # 3D shape for 2D functions - unsupported
        image_shape_mod = image_shape.copy()
        mask_shape_mod = mask_shape.copy()
        with self.assertRaises(ValueError):
            image_shape_mod += [128]
            mask_shape_mod += [128]
            image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
            mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_correct_shape(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_fastgeodis_func(num_dims=num_dims)

        # device mismatch for input - unsupported
        image_shape_mod = image_shape.copy()
        mask_shape_mod = mask_shape.copy()
        image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
        mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)

        # should work without any errors
        geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_zeros_input(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_fastgeodis_func(num_dims=num_dims)

        # device mismatch for input - unsupported
        image = torch.zeros(image_shape, dtype=torch.float32).to(device)
        mask = torch.zeros(mask_shape, dtype=torch.float32).to(device)

        # should work without any errors
        geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        # output should be zeros as well
        np.testing.assert_allclose(
            np.zeros(mask_shape, dtype=np.float32), geodesic_dist.cpu().numpy()
        )

    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_mask_ones_input(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_fastgeodis_func(num_dims=num_dims)

        # device mismatch for input - unsupported
        image = torch.zeros(image_shape, dtype=torch.float32).to(device)
        mask = torch.ones(mask_shape, dtype=torch.float32).to(device)

        # should work without any errors
        geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        # output should be ones * v
        np.testing.assert_allclose(
            np.ones(mask_shape, dtype=np.float32) * 1e10, geodesic_dist.cpu().numpy()
        )

    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_euclidean_dist_output(self, device, num_dims, base_dim):
        """
        Explanation:

        Taking euclidean distance with x==0 below:
        x-------------
        |            |
        |            |
        |            |
        |            |
        |            |
        |            |
        --------------

        The max distance in euclidean output will be approx equal to
        distance to furthest corner (x->o) along diagonal shown below:
        x-------------
        | \          |
        |   \        |
        |     \      |
        |       \    |
        |         \  |
        |           \|
        -------------o
        """

        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_fastgeodis_func(num_dims=num_dims)

        # device mismatch for input - unsupported
        image = torch.ones(image_shape, dtype=torch.float32).to(device)
        mask = torch.ones(mask_shape, dtype=torch.float32).to(device)
        mask[0, 0, 0, 0] = 0

        geodesic_dist = geodis_func(image, mask, 1e10, 0.0, 2)
        pred_max_dist = geodesic_dist.cpu().numpy().max()
        exp_max_dist = math.sqrt(num_dims * (base_dim ** 2))
        tolerance = 10 if num_dims == 2 else 100  # more tol needed for 3d approx

        check = exp_max_dist - tolerance < pred_max_dist < exp_max_dist + tolerance
        self.assertTrue(check)

    @parameterized.expand(CONF_3D)
    @run_cuda_if_available
    def test_ill_spacing(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        # device mismatch for input - unsupported
        image = torch.zeros(image_shape, dtype=torch.float32).to(device)
        mask = torch.zeros(mask_shape, dtype=torch.float32).to(device)

        spacing = [1.0, 1.0]
        geodis_func = get_fastgeodis_func(num_dims=num_dims, spacing=spacing)

        with self.assertRaises(ValueError):
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

    @skip_if_no_cuda
    def test_device_mismatch(self):
        device = "cuda"
        base_dim = 128

        for num_dims in [2, 3]:
            # start with a good shape for image and mask
            image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
            mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

            geodis_func = get_fastgeodis_func(num_dims=num_dims)

            # device mismatch for input - unsupported
            image_shape_mod = image_shape.copy()
            mask_shape_mod = mask_shape.copy()
            with self.assertRaises(ValueError):
                image_shape_mod[0] = 1
                mask_shape_mod[0] = 2
                image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
                mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
                geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

class TestFastGeodisSigned(unittest.TestCase):
    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_ill_shape(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_fastgeodis_func(num_dims=num_dims)

        # batch != 1 - unsupported
        image_shape_mod = image_shape.copy()
        mask_shape_mod = mask_shape.copy()
        with self.assertRaises(ValueError):
            mask_shape_mod[0] = 2
            image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
            mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        with self.assertRaises(ValueError):
            image_shape_mod[0] = 2
            image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
            mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        # spatial shape mismatch - unsupported
        image_shape_mod = image_shape.copy()
        mask_shape_mod = mask_shape.copy()
        with self.assertRaises(ValueError):
            image_shape_mod[-1] = 12
            image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
            mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        # 3D shape for 2D functions - unsupported
        image_shape_mod = image_shape.copy()
        mask_shape_mod = mask_shape.copy()
        with self.assertRaises(ValueError):
            image_shape_mod += [128]
            mask_shape_mod += [128]
            image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
            mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_correct_shape(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_fastgeodis_func(num_dims=num_dims)

        # device mismatch for input - unsupported
        image_shape_mod = image_shape.copy()
        mask_shape_mod = mask_shape.copy()
        image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
        mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)

        # should work without any errors
        geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_zeros_input(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_fastgeodis_func(num_dims=num_dims)

        # device mismatch for input - unsupported
        image = torch.zeros(image_shape, dtype=torch.float32).to(device)
        mask = torch.zeros(mask_shape, dtype=torch.float32).to(device)

        # should work without any errors
        geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        # output should be zeros as well
        np.testing.assert_allclose(
            np.zeros(mask_shape, dtype=np.float32), geodesic_dist.cpu().numpy()
        )

    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_mask_ones_input(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_fastgeodis_func(num_dims=num_dims)

        # device mismatch for input - unsupported
        image = torch.zeros(image_shape, dtype=torch.float32).to(device)
        mask = torch.ones(mask_shape, dtype=torch.float32).to(device)

        # should work without any errors
        geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

        # output should be ones * v
        np.testing.assert_allclose(
            np.ones(mask_shape, dtype=np.float32) * 1e10, geodesic_dist.cpu().numpy()
        )

    @parameterized.expand(CONF_3D)
    @run_cuda_if_available
    def test_ill_spacing(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        # device mismatch for input - unsupported
        image = torch.zeros(image_shape, dtype=torch.float32).to(device)
        mask = torch.zeros(mask_shape, dtype=torch.float32).to(device)

        spacing = [1.0, 1.0]
        geodis_func = get_fastgeodis_func(num_dims=num_dims, spacing=spacing)

        with self.assertRaises(ValueError):
            geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)

    @skip_if_no_cuda
    def test_device_mismatch(self):
        device = "cuda"
        base_dim = 128

        for num_dims in [2, 3]:
            # start with a good shape for image and mask
            image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
            mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

            geodis_func = get_fastgeodis_func(num_dims=num_dims)

            # device mismatch for input - unsupported
            image_shape_mod = image_shape.copy()
            mask_shape_mod = mask_shape.copy()
            with self.assertRaises(ValueError):
                image_shape_mod[0] = 1
                mask_shape_mod[0] = 2
                image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
                mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)
                geodesic_dist = geodis_func(image, mask, 1e10, 1.0, 2)


class TestGSF(unittest.TestCase):
    @parameterized.expand(CONF_ALL)
    @run_cuda_if_available
    def test_correct_shape(self, device, num_dims, base_dim):
        print(device)
        print(num_dims)

        # start with a good shape for image and mask
        image_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)
        mask_shape = get_simple_shape(base_dim=base_dim, num_dims=num_dims)

        geodis_func = get_GSF_func(num_dims=num_dims)

        # device mismatch for input - unsupported
        image_shape_mod = image_shape.copy()
        mask_shape_mod = mask_shape.copy()
        image = torch.rand(image_shape_mod, dtype=torch.float32).to(device)
        mask = torch.rand(mask_shape_mod, dtype=torch.float32).to(device)

        # should work without any errors
        geodesic_dist = geodis_func(image, mask, 0.0, 1e10, 1.0, 2)


if __name__ == "__main__":
    unittest.main()
