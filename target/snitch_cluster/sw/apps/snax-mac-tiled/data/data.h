// Copyright 2023 KU Leuven
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0
//
// Josse Van Delm <jvandelm@esat.kuleuven.be>

uint32_t VEC_LEN = 20;
uint32_t A[] = {99, 67, 39, 26, 62, 14, 17, 18, 54, 16,
                44, 9,  26, 85, 72, 66, 95, 65, 43, 84};
uint32_t B[] = {86, 10, 14, 11, 38, 41, 94, 82, 97, 25,
                96, 71, 44, 59, 93, 38, 57, 21, 84, 29};
uint32_t OUT[] = {8514, 670, 546,  286,  2356, 574,  1598, 1476, 5238, 400,
                  4224, 639, 1144, 5015, 6696, 2508, 5415, 1365, 3612, 2436};

// empty placeholder in L3 for sending back data
uint32_t OUT_TEST[] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                       0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
