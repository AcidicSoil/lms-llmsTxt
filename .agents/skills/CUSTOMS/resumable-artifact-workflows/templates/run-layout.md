# Run Layout Template

```text
runs/<workflow>_<timestamp>/
├── artifacts/
│   └── <item-slug>/
│       ├── scan_status.json
│       ├── output.*
│       ├── logs/
│       │   ├── commands.log
│       │   ├── stdout.log
│       │   └── stderr.log
│       └── snapshots/
│           ├── 01_initial.txt
│           ├── 02_stage_verified.txt
│           └── 99_failure_terminal_snapshot.txt
├── checkpoints/
│   └── workflow.tsv
└── run-summary.json
```

Keep the run root stable across resume attempts when the checkpoint already references artifacts from that run.
