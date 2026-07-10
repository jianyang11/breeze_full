# Private Machine-Tool v2 Frozen Development Split

- Inner-train file IDs: `1, 2, 4, 5` for each formal class.
- Inner-validation file ID: `10` for each formal class.
- Formal test file IDs `7, 8` are rejected by the data loader and are not read.
- The split rule was frozen before any v2 LLM request or inner-validation result.
