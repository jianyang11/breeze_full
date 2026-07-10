# Private Machine-Tool File Inventory

This inventory is a zero-API preflight audit. Test files are only listed for
integrity and leakage checks, not for parameter or feature selection.

- CSV files scanned: 21
- Channels expected: ['X', 'Y', 'Z', 'Current']
- Sampling rate: 4000 Hz
- Window/stride: 2048/1024
- Train file IDs: ['1', '2', '4', '5', '10']
- Test file IDs: ['7', '8']
- Files by split: {'train': 15, 'test': 6}
- Total windows: 2223
- Train windows: 1737
- Test windows: 486
- Bad-shape files: 0
- Non-finite files: 0

## Files By Split And Class

| Split | Class | Files |
|---|---|---:|
| test | base_imbalance | 2 |
| test | lead_screw_anomaly | 2 |
| test | normal_machining | 2 |
| train | base_imbalance | 5 |
| train | lead_screw_anomaly | 5 |
| train | normal_machining | 5 |
