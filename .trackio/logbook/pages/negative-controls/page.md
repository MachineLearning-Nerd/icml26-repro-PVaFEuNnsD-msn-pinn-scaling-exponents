# Negative controls


---
<!-- trackio-cell
{"type": "markdown", "id": "cell_f80cd5da0ac8", "created_at": "2026-07-19T21:02:20+00:00", "title": "Independent falsifiers"}
-->
# Negative controls

- Frozen exponents fail where trainable exponents recover within 1%.
- A wrong 240-degree angle makes the 270-degree quantization residual nonzero.
- Swapping sine/cosine quantization for mixed BCs is rejected exactly.
- Matched initialization isolates the constraint term from the improved protocol package.
- Repeated bounded structured errors reject the theorem's unstated `N^-1/2` conclusion.
- Eleven naive corner interpretations reject the reported 14.6% baseline.
- A noiseless global oracle resolves every close pair and rejects an absolute Rayleigh-limit interpretation.
- Exact log moments are independently checked by numerical quadrature; autograd is checked by finite differences.


---
<!-- trackio-cell
{"type": "code", "id": "cell_568140029bf7", "created_at": "2026-07-19T21:02:42+00:00", "title": "Run: uv (exit 0)", "command": ["uv", "run", "pytest", "-q"], "exit_code": 0, "duration_s": 2.519}
-->
````bash
$ uv run pytest -q
````

exit 0 · 2.5s


````output
................                                                         [100%]
16 passed in 1.74s

````
