// BSD 3-Clause License

// Copyright (c) 2021, Muhammad Asad (masadcv@gmail.com)
// All rights reserved.

// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:

// 1. Redistributions of source code must retain the above copyright notice, this
//    list of conditions and the following disclaimer.

// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.

// 3. Neither the name of the copyright holder nor the names of its
//    contributors may be used to endorse or promote products derived from
//    this software without specific prior written permission.

// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
// FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
// OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#include <torch/extension.h>
#include <vector>
// #include <iostream>
#ifdef _OPENMP
#include <omp.h>
#endif

// void print_shape(torch::Tensor data)
// {
//     auto num_dims = data.dim();
//     std::cout << "Shape: (";
//     for (int dim = 0; dim < num_dims; dim++)
//     {
//         std::cout << data.size(dim);
//         if (dim != num_dims - 1)
//         {
//             std::cout << ", ";
//         }
//         else
//         {
//             std::cout << ")" << std::endl;
//         }
//     }
// }

float l1distance(const float &in1, const float &in2)
{
    return std::abs(in1 - in2);
}


float l1distance(const float *in1, const float *in2, int size)
{
    float ret_sum = 0.0;
    for (int c_i = 0; c_i < size; c_i++)
    {
        ret_sum += abs(in1[c_i] - in2[c_i]);
    }
    return ret_sum;
}

float l1distance(const std::vector<float> &in1, const std::vector<float> &in2, int size)
{
    float ret_sum = 0.0;
    for (int c_i = 0; c_i < size; c_i++)
    {
        ret_sum += abs(in1[c_i] - in2[c_i]);
    }
    return ret_sum;
}

// float l2distance(const float *in1, const float *in2, int size)
// {
//     float ret_sum = 0.0;
//     for (int c_i = 0; c_i < size; c_i++)
//     {
//         ret_sum += (in1[c_i] - in2[c_i]) * (in1[c_i] - in2[c_i]);
//     }
//     return std::sqrt(ret_sum);
// }


void geodesic_updown_pass_cpu(const torch::Tensor &image, torch::Tensor &distance, const float &l_grad,  const float &l_eucl)
{
    // batch, channel, height, width
    const int channel = image.size(1);
    const int height = image.size(2);
    const int width = image.size(3);

    auto image_ptr = image.accessor<float, 4>();
    auto distance_ptr = distance.accessor<float, 4>();
    // constexpr float local_dist[] = {sqrt(float(2.)), float(1.), sqrt(float(2.))};
    const float local_dist[] = {sqrt(float(2.)), float(1.), sqrt(float(2.))};

    std::vector<float> pval_v(channel);
    std::vector<float> qval_v(channel);

    // top-down
    for (int h = 1; h < height; h++)
    {
        // use openmp to parallelise the loop over width
        #ifdef _OPENMP
            #pragma omp parallel for
        #endif
        for (int w = 0; w < width; w++)
        {
            float pval;
            if (channel == 1)
            {
                pval = image_ptr[0][0][h][w];
            }
            else
            {
                for (int c_i = 0; c_i < channel; c_i++)
                {
                    pval_v[c_i] = image_ptr[0][c_i][h][w];
                }
            }
            float new_dist = distance_ptr[0][0][h][w];

            for (int w_i = 0; w_i < 3; w_i++)
            {
                const int w_ind = w + w_i - 1;
                if (w_ind < 0 || w_ind >= width)
                    continue;

                float l_dist;
                if (channel == 1)
                {
                    l_dist = l1distance(pval, image_ptr[0][0][h - 1][w_ind]);
                }
                else
                {
                    for (int c_i = 0; c_i < channel; c_i++)
                    {
                        qval_v[c_i] = image_ptr[0][c_i][h - 1][w_ind];
                    }
                    l_dist = l1distance(pval_v, qval_v, channel);
                }
                const float cur_dist = distance_ptr[0][0][h - 1][w_ind] + l_eucl * local_dist[w_i] + l_grad * l_dist;
                new_dist = std::min(new_dist, cur_dist);
            }
            distance_ptr[0][0][h][w] = new_dist;
        }
    }

    // bottom-up
    for (int h = height - 2; h >= 0; h--)
    {
        // use openmp to parallelise the loop over width
        #ifdef _OPENMP
            #pragma omp parallel for
        #endif
        for (int w = 0; w < width; w++)
        {
            float pval;
            if (channel == 1)
            {
                pval = image_ptr[0][0][h][w];
            }
            else
            {
                for (int c_i = 0; c_i < channel; c_i++)
                {
                    pval_v[c_i] = image_ptr[0][c_i][h][w];
                }
            }
            float new_dist = distance_ptr[0][0][h][w];

            for (int w_i = 0; w_i < 3; w_i++)
            {
                const int w_ind = w + w_i - 1;
                if (w_ind < 0 || w_ind >= width)
                    continue;

                float l_dist;
                if (channel == 1)
                {
                    l_dist = l1distance(pval, image_ptr[0][0][h + 1][w_ind]);
                }
                else
                {
                    for (int c_i = 0; c_i < channel; c_i++)
                    {
                        qval_v[c_i] = image_ptr[0][c_i][h + 1][w_ind];
                    }
                    l_dist = l1distance(pval_v, qval_v, channel);
                }
                const float cur_dist = distance_ptr[0][0][h + 1][w_ind] + l_eucl * local_dist[w_i] + l_grad * l_dist;
                new_dist = std::min(new_dist, cur_dist);
            }
            distance_ptr[0][0][h][w] = new_dist;
        }
    }
}

torch::Tensor generalised_geodesic2d_cpu(torch::Tensor &image, const torch::Tensor &mask, const float &v, const float &l_grad, const float &l_eucl, const int &iterations)
{
    torch::Tensor distance = v * mask.clone();

    // iteratively run the distance transform
    for (int itr = 0; itr < iterations; itr++)
    {
        image = image.contiguous();
        distance = distance.contiguous();

        // top-bottom - width*, height
        geodesic_updown_pass_cpu(image, distance, l_grad, l_eucl);

        // left-right - height*, width
        image = image.transpose(2, 3);
        distance = distance.transpose(2, 3);

        image = image.contiguous();
        distance = distance.contiguous();
        geodesic_updown_pass_cpu(image, distance, l_grad, l_eucl);
        
        // tranpose back to original - width, height
        image = image.transpose(2, 3);
        distance = distance.transpose(2, 3);

        // * indicates the current direction of pass
    }

    return distance;
}

void geodesic_frontback_pass_cpu(const torch::Tensor &image, torch::Tensor &distance, const std::vector<float> &spacing, const float &l_grad, const float &l_eucl)
{
    // batch, channel, depth, height, width
    const int channel = image.size(1);
    const int depth = image.size(2);
    const int height = image.size(3);
    const int width = image.size(4);

    auto image_ptr = image.accessor<float, 5>();
    auto distance_ptr = distance.accessor<float, 5>();

    float local_dist[3*3];
    for (int h_i = 0; h_i < 3; h_i++)
    {
        for (int w_i = 0; w_i < 3; w_i++)
        {
            float ld = spacing[0];
            ld += float(std::abs(h_i-1)) * spacing[1];
            ld += float(std::abs(w_i-1)) * spacing[2];

            local_dist[h_i * 3 + w_i] = ld;
        }
    }

    std::vector<float> pval_v(channel);
    std::vector<float> qval_v(channel);

    // front-back
    for (int z = 1; z < depth; z++)
    {
        // use openmp to parallelise the loops over height and width
        #ifdef _OPENMP
            #pragma omp parallel for collapse(2)
        #endif
        for (int h = 0; h < height; h++)
        {
            for (int w = 0; w < width; w++)
            {
                float pval;
                if (channel == 1)
                {
                    pval = image_ptr[0][0][z][h][w];
                }
                else
                {
                    for (int c_i = 0; c_i < channel; c_i++)
                    {
                        pval_v[c_i] = image_ptr[0][c_i][z][h][w];
                    }
                }
                float new_dist = distance_ptr[0][0][z][h][w];

                for (int h_i = 0; h_i < 3; h_i++)
                {
                    for (int w_i = 0; w_i < 3; w_i++)
                    {
                        const int h_ind = h + h_i - 1;
                        const int w_ind = w + w_i - 1;

                        if (w_ind < 0 || w_ind >= width || h_ind < 0 || h_ind >= height)
                            continue;

                        float l_dist;
                        if (channel == 1)
                        {
                            l_dist = std::abs(pval - image_ptr[0][0][z - 1][h_ind][w_ind]);
                        }
                        else
                        {
                            for (int c_i = 0; c_i < channel; c_i++)
                            {
                                qval_v[c_i] = image_ptr[0][c_i][z - 1][h_ind][w_ind];
                            }
                            l_dist = l1distance(pval_v, qval_v, channel);
                        }
                        const float cur_dist = distance_ptr[0][0][z - 1][h_ind][w_ind] + l_eucl * local_dist[h_i * 3 + w_i]  + l_grad * l_dist;
                        new_dist = std::min(new_dist, cur_dist);
                    }
                }
                distance_ptr[0][0][z][h][w] = new_dist;
            }
        }
    }

    // back-front
    for (int z = depth - 2; z >= 0; z--)
    {
        // use openmp to parallelise the loops over height and width
        #ifdef _OPENMP
            #pragma omp parallel for collapse(2)
        #endif
        for (int h = 0; h < height; h++)
        {
            for (int w = 0; w < width; w++)
            {
                float pval;
                if (channel == 1)
                {
                    pval = image_ptr[0][0][z][h][w];
                }
                else
                {
                    for (int c_i = 0; c_i < channel; c_i++)
                    {
                        pval_v[c_i] = image_ptr[0][c_i][z][h][w];
                    }
                }
                float new_dist = distance_ptr[0][0][z][h][w];

                for (int h_i = 0; h_i < 3; h_i++)
                {
                    for (int w_i = 0; w_i < 3; w_i++)
                    {
                        const int h_ind = h + h_i - 1;
                        const int w_ind = w + w_i - 1;

                        if (w_ind < 0 || w_ind >= width || h_ind < 0 || h_ind >= height)
                            continue;

                        float l_dist;
                        if (channel == 1)
                        {
                            l_dist = std::abs(pval - image_ptr[0][0][z + 1][h_ind][w_ind]);
                        }
                        else
                        {
                            for (int c_i = 0; c_i < channel; c_i++)
                            {
                                qval_v[c_i] = image_ptr[0][c_i][z + 1][h_ind][w_ind];
                            }
                            l_dist = l1distance(pval_v, qval_v, channel);
                        }
                        const float cur_dist = distance_ptr[0][0][z + 1][h_ind][w_ind] + l_eucl * local_dist[h_i * 3 + w_i] + l_grad * l_dist;
                        new_dist = std::min(new_dist, cur_dist);
                    }
                }
                distance_ptr[0][0][z][h][w] = new_dist;
            }
        }
    }
}

torch::Tensor generalised_geodesic3d_cpu(torch::Tensor &image, const torch::Tensor &mask, const std::vector<float> &spacing, const float &v, const float &l_grad, const float &l_eucl, const int &iterations)
{
    torch::Tensor distance = v * mask.clone();

    // iteratively run the distance transform
    for (int itr = 0; itr < iterations; itr++)
    {
        image = image.contiguous();
        distance = distance.contiguous();

        // front-back - depth*, height, width
        geodesic_frontback_pass_cpu(image, distance, spacing, l_grad, l_eucl);

        // top-bottom - height*, depth, width
        image = torch::transpose(image, 3, 2);
        distance = torch::transpose(distance, 3, 2);
        
        image = image.contiguous();
        distance = distance.contiguous();
        geodesic_frontback_pass_cpu(image, distance, {spacing[1], spacing[0], spacing[2]}, l_grad, l_eucl);
        
        // transpose back to original depth, height, width
        image = torch::transpose(image, 3, 2);
        distance = torch::transpose(distance, 3, 2);
        
        // left-right - width*, height, depth
        image = torch::transpose(image, 4, 2);
        distance = torch::transpose(distance, 4, 2);
        
        image = image.contiguous();
        distance = distance.contiguous();
        geodesic_frontback_pass_cpu(image, distance, {spacing[2], spacing[1], spacing[0]}, l_grad, l_eucl);
        
        // transpose back to original depth, height, width
        image = torch::transpose(image, 4, 2);
        distance = torch::transpose(distance, 4, 2);

        // * indicates the current direction of pass
    }

    return distance;
}