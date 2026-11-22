# V3 Final Acceptance Demo

> Status: FINAL_VIDEO_COMPLETE / SCREENSHOT_CAPTURE_COMPLETE (10/10)
> Run ID: `v3-20261120-1613818-01`
> Tested code commit: `161381887e421a121cd2878fcbf397d42a8ac818`

These scripts are intended to be copied to:

```text
evidence/v3/v3-20261120-1613818-01/17-final-demo/commands/
```

Run them in order from the V3 worktree:

```powershell
.\17-final-demo\commands\01-baseline.ps1
.\17-final-demo\commands\02-corpus.ps1
.\17-final-demo\commands\03-v1-demo.ps1
.\17-final-demo\commands\04-v2-demo.ps1
.\17-final-demo\commands\05-tests-replay.ps1
.\17-final-demo\commands\06-live-prompt.ps1
.\17-final-demo\commands\07-limitations.ps1
.\17-final-demo\commands\08-content-safety.ps1
.\17-final-demo\commands\09-static-coverage.ps1
```

The scripts:

- set UTF-8 for Python;
- write new demo artifacts under `17-final-demo`;
- read existing replay, mutation, coverage and live semantic evidence;
- do not call the live model again;
- do not print API keys or credentials.

Final artifacts:

- `video demo.mp4` - final project demo video with burned-in captions;
- `screenshots/01-environment.png` through `screenshots/10-gates-limitations.png`;
- `V3-Demo-Script.md`;
- `V3-Demo-Screenshots.md`.

The timestamped `v1-normal-*.audit.jsonl` and `v1-invalid-*.audit.jsonl` files from the final capture are authoritative. Older untimestamped audit files are retained as prior capture artifacts.

`V3-Final-Acceptance-Video-Script.md` is retained only as superseded planning material; the final deliverables are `video demo.mp4` and the 10 screenshots.
