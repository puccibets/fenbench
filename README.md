# FenBench: Chess Visual Understanding Benchmark

A comprehensive benchmark for evaluating AI models' ability to understand 3D-rendered chess positions through four distinct visual reasoning tasks.

## Overview

FenBench tests computer vision models on chess-related spatial reasoning using photorealistic 3D chessboards. The benchmark consists of 200 tasks across four categories, each designed to evaluate different aspects of chess visual understanding.

## Evaluation Categories

- **Category 1: Piece Identification** - Identify which piece is on a given square
- **Category 2: Square Location** - Find all squares containing a specific piece type  
- **Category 3: Piece Counting** - Count and categorize all pieces on the board
- **Category 4: FEN Generation** - Generate complete board position in FEN notation

## Blender Files
The repository also includes Blender source files for generating additional 3D chessboard renders directly from FEN strings. This allows researchers and developers to easily extend the benchmark with custom positions, test cases, or augmentations tailored to their model’s needs.
