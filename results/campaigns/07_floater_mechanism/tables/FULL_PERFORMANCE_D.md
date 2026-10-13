
### aria1253 (Aria, MPS pose)

| 카테고리 | 방법 | PSNR ↑ | SSIM ↑ | LPIPS ↓ | Gaussian | floater (export) ↓ | floater (학습 직후) | mapper s |
|---|---|---|---|---|---|---|---|---|
| 기준 | C − carve − FM | 27.39 | 0.884 | 0.224 | 112k | 16 | 197 | 54 |
| 우리 | Consensus Carve + FM (= release C) | 27.41 (+0.01) | 0.884 | 0.224 | 112k | 1 | 78 | 62 |

### TUM fr1_desk (GT pose + Kinect)

| 카테고리 | 방법 | PSNR ↑ | SSIM ↑ | LPIPS ↓ | Gaussian | floater (export) ↓ | floater (학습 직후) | GT floater ↓ | mapper s |
|---|---|---|---|---|---|---|---|---|---|
| 기준 | C − carve − FM | 19.96 | 0.707 | 0.357 | 47k | 5 | 15 | 295 | 23 |
| 우리 | Consensus Carve + FM (= release C) | 19.95 (-0.01) | 0.708 | 0.353 | 47k | 0 | 8 | 289 | 26 |
