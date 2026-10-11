# D replay image storage

`mapper_recipe_d/run_d.py` defaults to `--replay-storage tiered_fifo` for the
legacy sampling policy. The temporal retention experiment retains its prior
storage implementation. Explicit `--replay-storage legacy` restores the
historical bounded-membership D; `full_ram` retains every observation using the
historical RAM/dense-cache/KF-residency implementation. Use `full_ram` versus
`tiered_fifo` to isolate physical storage at identical logical membership.

The FIFO adapter preserves D's 3:3:6 selection, ERVS, no repeated images within
one selection group, one Adam update per image, κ=16 admission credit, temporal
gap candidate selection, losses, initialization and geometry. Logical membership
and candidate metadata grow with arrivals; no candidate expires and no admitted
image is retired. Frontend buffers are untouched. This is a mapping-only benchmark
using its established reference-pose contract, not a strict sensor-only result.

Defaults: 512 GPU image bundles, 1,024 RAM bundles, then lossless SSD-backed files
under `OUTPUT/replay_images`. Choose an output on `/ssd/intern`, or provide
`--replay-ssd-directory`. Each bundle holds original uint8 pixels and their exact
float32 normalization. Images are FIFO by arrival irrespective of KF/dense role;
reads do not promote them. One CPU bundle and one GPU training image can be held
as scratch in addition to these limits. Construction temporaries, frontend-owned
images, depth/normal targets, gradient masks and the Gaussian map are excluded.
The current adapter explicitly requires native training resolution; it refuses
an unaccounted resized camera cache. Cameras are checked against the original
pixels before adopting shared storage. Files survive export and are not deleted
by the runner. I/O is buffered: measured SSD reads may hit the OS page cache.

Native `mapper_seconds` retains its historical training-service-only meaning.
`mapper_with_admission_seconds` additionally includes image admission, packet
processing/birth and camera adoption, synchronizing CUDA at those boundaries.
`input_mapping_stream_seconds` measures first RGB admission through the last
completed training call (frontend plus mapping and interleaved I/O/logs/snapshots).
`whole_seconds` includes frontend/startup/export/snapshots. The shared-tape runner's
`mapper_seconds` already includes admission, packet work and online topology;
its exact scope is recorded in runtime.json. Tier counters report host wall time
and logical copied bytes, not isolated CUDA DMA or physical disk-bus bandwidth.

Run `test_tiered_rgb.py` in the VIGS environment for lossless roundtrip and FIFO
checks including zero-sized tiers. `compare.py` uses the established shared causal
frontend tapes, full-input 6N contracts, held-out evaluator, source and causality
audits. `--smoke` forces 16 GPU / 32 RAM entries and SSD replay. `--native` uses
actual D with its frontend. The comparison's `full_ram` control is separate from
the historical `legacy` control because removal of old retention limits is a
logical membership change on sufficiently long sequences.
