# ArgLAS
This repository hosts $LAS\_{arg}$, a framework to learn argumentation semantics based on ILASP. This material is associated with the paper *A Unifying Framework for Learning Argumentation Semantics* by Z. Mileva, A. Bikakis, F. A. D’Asaro, M. Law and A. Russo (currently submitted to KR-2024). In the following we briefly describe how to run the several tasks that $LAS\_{arg}$ supports.

## Prerequisites

To run the commands below, one should have [clingo](https://potassco.org) (tested version 5.71) and the [ILASP](https://www.ilasp.com) system (tested version 4.4.0) installed.

## Learning from answer sets

$LAS\_{arg}$ can learn from positive and negative examples as per ILASP's syntax. The folder `LAS_Tasks` contains ILASP encodings of tasks from which it is possible to learn semantics for different types of frameworks (namely, AAF, BAF and VAF).

For instance, if one wants to learn the stable semantics, one can run:

```sh
ILASP --version=4 LAS_Tasks/AAF_ILASP_encodings/stable.las
```

This will learn an axiomatic definition of the stable semantics. For those tasks that require learning heuristics (e.g., in the case of grounded and preferred semantics), one can run `ILASP` using the `--learn-heuristics` flag, as in:

```sh
ILASP --version=4 --learn-heuristics LAS_Tasks/AAF_ILASP_encodings/grounded.las
```

## Inference

For simplicity, we have put the result of the learning task for the Abstract Argumentation Frameworks in the folder `ASP_learned_encodings/AAF_LP_encodings/` so that they can be used for inference out-of-the-box skipping the learning step.

For instance, if one wants to find one stable extensions of the `BA_160_0_2.apx` framework in the `Examples` folder, one can run:

```sh
clingo -n 1 ASP_learned_encodings/AAF_LP_encodings/stable.lp Examples/BA_160_0_2.apx
```

Again, if inference requires the use of heuristics (e.g., in the case of grounded and preferred semantics), one must run `clingo` with the additional flags `----heuristic=Domain --enum=domRec` , as in:

```sh
clingo -n 1 --heuristic=Domain --enum=domRec ASP_learned_encodings/AAF_LP_encodings/grounded.lp Examples/BA_160_0_2.apx
```

## Benchmarking

The script for benchmarking is in the `benchmark` folder. It requires Python 3 for running, as well as standard libraries csv, os, subprocess and time. The user should manually set the variables `input_directory` and `output_file`. The input directory should contain all the argumentation frameworks in `apx` format (as those in the `Examples` folder). The output will be produced as a CSV file. Then, the benchmark script can be run via

```sh
python benchmark/run_benchmark.py
```

## Proofs

The file `proofs.pdf` contains proof of equivalence between some of the learned semantics (those in the `ASP_learned_encodings/AAF_LP_encodings/` folder) and their [ASPARTIX](https://www.dbai.tuwien.ac.at/proj/argumentation/systempage/dung.html) counterparts.
