| Category | Method | Reference | aria1253 PSNR↑ / Fl‰↓ | table_06 PSNR↑ / Fl‰↓ | TUM PSNR↑ / Fl‰↓ | TUM GT-front‰↓ | TUM depth acc. %↑ | #G (×base) | Time (×base) |
|---|---|---|---|---|---|---|---|---|---|
| — | Base (no floater handling) | — | 27.01 / 0.26 | 23.66 / 0.03 | 19.90 / 0.20 | 4.87 | 90.6 | 1.00 | 1.00 |
| Map maintenance | MonoGS prune | opacity | 25.79 / 0.00 | 22.97 / 0.00 | 19.51 / 0.05 | 7.19 | 90.2 | 0.24 | 0.85 |
| Depth regularization | DNGaussian | frontend depth | 26.75 / 0.26 | 23.56 / 0.17 | 19.73 / 0.13 | 5.34 | 90.5 | 1.03 | 1.50 |
| Ray statistics | CG-SLAM | own median (two-sided) | 27.14 / 0.13 | 23.56 / 0.01 | 19.86 / 0.07 | 6.02 | 90.6 | 1.10 | 1.15 |
| Sensor free space | GS-SLAM Eq. 9 | frontend depth | 26.33 / 0.11 | 23.26 / 0.03 | 19.72 / 0.09 | 3.49 | 90.6 | 0.59 | 0.92 |
| Detect-and-delete | SparseGS | own depth modes | 24.22 / 0.21 | 21.04 / 0.07 | 17.10 / 0.45 | 1.91 | 87.6 | 0.94 | 1.00 |
| Ours | Consensus Carving | own median (front, persistent) | 27.01 / 0.02 | 23.67 / 0.00 | 19.92 / 0.04 | 4.89 | 90.6 | 1.00 | 1.14 |
