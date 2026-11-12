# AquaWatch - archived optional data-expansion research tools

**Historical research workflow, separate from the current release.** The current AquaWatch release uses **3 reviewed above-water pool CCTV clips** when installed with `-SampleVideos`. Its installation guide is [docs/INSTALL.md](../../docs/INSTALL.md); it does not require this package, a PILOT experiment, or a `D:\httm` folder. The **13 existing / 37 added / 50 total** counts below describe an earlier library experiment, not the current catalog. Drone footage is outside the current pool-CCTV demo scope. Run the optional MOBDrone installer only in the isolated research copy described in Step 7; it changes that copy's active catalog.

This package does NOT combine CURRENT and PILOT checkpoints. It does NOT overwrite existing models. It creates a NEW isolated RESEARCH dataset and NEW checkpoint. Steps 0–6 retain historical **Windows PowerShell** examples using `D:\httm`; adapt that path to your research workspace. These optional training steps require separately prepared datasets and experiment artifacts, which are not bundled with a fresh clone.

## Prerequisites and provenance

- For the archived training workflow, the research app root contains `.venv`, `data/curated/surface_v4`, pretrained `models/base/yolov8s_coco.pt`, and the separately created PILOT directory when used. Normal application setup does not require these research datasets or PILOT artifacts.
- Stable app uses Python 3.12, PyTorch, Ultralytics, Pillow, PyYAML and OpenCV.
- `scripts/download_roboflow.py` is OPTIONAL and requires a Roboflow account/API key with access to the selected dataset export versions. Use its **dry-run** to inspect sources first. NEVER upload an API key or put it in code.
- The new external image labels are uploader-provided labels, NOT independent ground-truth of drowning incidents. Their underlying video copyright has not been independently verified, and duplicate scenes may occur across datasets. The package deliberately labels output **research-only / not for deployment**. Preserve source attribution.
- Source `MOBDrone` provides aerial video of people *simulating* man-overboard scenarios; these videos are not confirmed real drowning incidents or classification ground truth. Keep them OUT of training if using them to illustrate/assess your application.
- Large Roboflow datasets may contain reexports/augmentations of identical original video frames. The script only imports source `train` images, filters labels and near-duplicates, and keeps all original `surface_v4` validation/test **byte-for-byte**.
- The earlier experiment kept 13 AquaWatch clips and added 37 drone videos to reach 50 playable examples. These are historical counts; the installer calculates additions from the isolated copy's actual catalog. Drone videos come from one collection, not independent confirmed drowning events.

## Step 0 - Extract the package to the app tooling directory

The current repository already includes this tool under `tools/AquaWatch_Data_Expansion_v5`; skip extraction after cloning. If using the older standalone archive, unzip it into your research workspace's `tools` directory. Historical example:

```
D:\httm\tools\AquaWatch_Data_Expansion_v5\scripts\
```

PowerShell example (adjust Downloads path if necessary):

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\AquaWatch_Data_Expansion_v5.zip" -DestinationPath D:\httm\tools -Force
cd D:\httm
$tool = 'D:\httm\tools\AquaWatch_Data_Expansion_v5'
```

## Step 1 - Choose new datasets

Read the catalogue: `$tool\catalog\datasets.csv`. Direct two-class import candidates:

- `first368`: a smaller YOLO drowning/swimming dataset.
- `foiaxlc`: 3 classes; the third class is *excluded at IMAGE level* if an image contains that class.
- `se_v1`: similarly requires label/class checks.
- `abdos`: larger 14k two-class project; sample a bounded subset before scaling.
- `university`: another large dataset that may overlap with other sources; optional.

Do **not** directly map person, rescue, pose, or distress labels into drowning. Therefore `swimsecure`, `pool_pose`, `person_water`, `AquaSurVai` are in the catalogue but blocked from automatic direct-class import.

## Step 2 - Export dataset packages, WITHOUT touching AquaWatch virtualenv

Create a separate Python virtualenv for the Roboflow SDK, since dependencies could conflict with the app:

```powershell
py -3.12 -m venv D:\httm\.venv_datasets
D:\httm\.venv_datasets\Scripts\python.exe -m pip install --upgrade pip roboflow
$env:ROBOFLOW_API_KEY = 'YOUR_OWN_KEY_FROM_ROBOFLOW'
& D:\httm\.venv_datasets\Scripts\python.exe "$tool\scripts\download_roboflow.py" --destination D:\httm\data\research\roboflow_exports --ids first368 foiaxlc se_v1 abdos --dry-run
& D:\httm\.venv_datasets\Scripts\python.exe "$tool\scripts\download_roboflow.py" --destination D:\httm\data\research\roboflow_exports --ids first368 foiaxlc se_v1 abdos
Remove-Item Env:\ROBOFLOW_API_KEY
```

These commands assume the Roboflow SDK can access the public version exports. If denied: open each URL from the catalogue while logged in, **download as YOLOv8** (when authorized), then extract each export to:

```
D:\httm\data\research\roboflow_exports\first368\data.yaml
D:\httm\data\research\roboflow_exports\foiaxlc\data.yaml
D:\httm\data\research\roboflow_exports\se_v1\data.yaml
D:\httm\data\research\roboflow_exports\abdos\data.yaml
```

If a dataset has no usable public export, omit it from later `--ids` rather than guessing or fabricating labels. Export folders can contain one nested directory with `data.yaml`; the import script handles this layout.

## Step 3 - Inspect actual labels and camera viewpoints

```powershell
cd D:\httm
$tool = 'D:\httm\tools\AquaWatch_Data_Expansion_v5'
.\.venv\Scripts\python.exe "$tool\scripts\inspect_multisource.py" --sources-root data\research\roboflow_exports --ids first368 foiaxlc se_v1 abdos --output data\reviews\multisource_v5 --per-source 48
explorer data\reviews\multisource_v5
```

Review contact sheets. Red = drowning, blue = swimming, orange text = questionable/unsupported annotation. If source footage is underwater, captions/movie/stock, excessive augmentation, or blatantly mislabeled, **exclude that source** or manually remove those images from the export. The tool is a *spot check*, not 100% automatic approval. Verify source usage rights separately. Do NOT modify frozen `surface_v4`.

## Step 4 - Build a NEW combined training dataset

```powershell
.\.venv\Scripts\python.exe "$tool\scripts\prepare_multisource.py" --base data\curated\surface_v4 --sources-root data\research\roboflow_exports --ids first368 foiaxlc se_v1 abdos --pilot data\research_pilot\lifeguard_v1 --max-per-source 400 --output data\research_expanded\surface_v5_multi
```

`--pilot` is OPTIONAL: remove both `--pilot` and its path if you want to postpone reusing the Lifeguard frames. This is a **DATA** merge only, not a weight merge.

Read the printed counts. The `surface_v4` baseline has 1007 train / 137 val / 169 test images. Each selected source adds up to 400 *eligible* new train images; exact and perceptual duplicates, invalid labels, unsupported classes, and unseen data are skipped. The output contains:

```
data\research_expanded\surface_v5_multi\data.yaml
...\research_record.json
...\research_manifest.json
...\images\train,val,test\
...\labels\train, val,test\
```

If zero new images survived, read the error and inspect the dataset export format/labels. A failed output retains `FAILED.txt`; choose a NEW output name on retry, never overwrite a data version.

## Step 5 - Train a THIRD checkpoint (does not overwrite CURRENT or PILOT)

```powershell
.\.venv\Scripts\python.exe "$tool\scripts\train_multisource.py" --dataset data\research_expanded\surface_v5_multi --model models\base\yolov8s_coco.pt --epochs 30 --imgsz 416 --batch 4 --name multi_v5_experiment_01 --exploratory-unverified
```

New checkpoint:

```
D:\httm\data\training_exploratory\multi_v5_experiment_01\weights\best.pt
```

CURRENT remains `D:\httm\models\finetuned\weights\best.pt` and PILOT remains `D:\httm\data\training_exploratory\lifeguard_pilot_v1\weights\best.pt`.

## Step 6 - Compare all three checkpoints on the SAME frozen 137 validation images

```powershell
.\.venv\Scripts\python.exe "$tool\scripts\evaluate_three_models.py" --dataset data\research_expanded\surface_v5_multi --current models\finetuned\weights\best.pt --pilot data\training_exploratory\lifeguard_pilot_v1\weights\best.pt --candidate data\training_exploratory\multi_v5_experiment_01\weights\best.pt --output data\evaluation_pilot\multi_v5_comparison.json
```

Report contains total mAP and class-level precision, recall and mAP; it does **not** evaluate `test` or deploy anything. Do not conclude that a model is safe for drowning rescue based only on image-level mAP. Check false alerts/hour and event-level labels on independent video, preferably fixed CCTV.

## Step 7 - Optional MOBDrone experiment in a separate research copy

Skip this step for the current pool-CCTV application. MOBDrone contains aerial recordings of simulated man-overboard scenarios. These clips are useful for a separate playback/domain-stress experiment, not as drowning-positive labels or additions to the current CCTV catalog. The historical 13 + 37 = 50 example count is not a promise about the current release.

Create a **new, separate checkout** with its own Python environment and data. Choose an unused directory; keep the existing application and its catalog separate:

```powershell
$researchApp = Join-Path $env:USERPROFILE 'AquaWatch_MOBDrone_Research'
git clone https://github.com/NTDung123/Aquawatch.git "$researchApp"
Set-Location -LiteralPath $researchApp
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\SETUP.ps1 -CpuOnly
$researchTool = Join-Path $researchApp 'tools\AquaWatch_Data_Expansion_v5'
$researchPython = Join-Path $researchApp '.venv\Scripts\python.exe'
$archive = Join-Path $researchApp 'data\research\MOBDrone_videos.zip'
```

This checkout starts without sample videos. The optional installer needs a catalog, so initialize an empty research catalog only if it does not already exist:

```powershell
$researchCatalog = Join-Path $researchApp 'data\video_library.json'
if (-not (Test-Path -LiteralPath $researchCatalog)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $researchCatalog) | Out-Null
    [System.IO.File]::WriteAllText($researchCatalog, '{"sources":[],"videos":[]}', [System.Text.UTF8Encoding]::new($false))
}
```

**Space:** the official ZIP is about 5.5 GB, plus extracted originals and MP4 previews; allow approximately 12–15 GB for this experiment, in addition to its Python environment. Download `MOBDrone_videos.zip` from the official [Zenodo dataset](https://zenodo.org/records/5996890), or use the helper with an explicit destination inside this research copy:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$researchTool\DOWNLOAD_MOBDRONE.ps1" -Destination "$archive"
```

The helper resumes downloads with `curl.exe -C -` and checks the pinned MD5 `250c19fdd6fb0b5aa5fa43e5ad140306`.

Preview the plan first; this command does not edit the catalog:

```powershell
& $researchPython "$researchTool\scripts\install_mobdrone_examples.py" --app-root "$researchApp" --archive "$archive" --target 50 --seconds 40
```

Review the reported existing/new counts. Starting from an empty catalog requires 50 eligible source videos; an existing catalog changes that number. If enough valid sources remain and this research experiment is wanted, install **into this research copy only**:

```powershell
& $researchPython "$researchTool\scripts\install_mobdrone_examples.py" --app-root "$researchApp" --archive "$archive" --target 50 --seconds 40 --install
```

The installer verifies the archive and source videos, preserves existing entries, caches selected full-length originals, creates H.264 previews/posters, and backs up the research catalog as `data/video_library.pre_mobdrone.json`. New entries are `open_water_unlabeled`, not drowning-positive annotations. It does not train or change checkpoints. It refuses an impossible target rather than inventing entries.

Run this separate application on another port:

```powershell
Set-Location -LiteralPath $researchApp
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\RUN.ps1 -Port 8001
```

Open `http://localhost:8001` for the research copy and inspect its library. These optional aerial examples demonstrate playback/inference and domain stress; they are outside the current three-clip pool-CCTV demo and are not evidence of clinically validated drowning detection.

## Future expansion

After reviewing labels and rights, run another export/import build with a fresh version name `surface_v6_multi`, and train a new name `multi_v6_experiment_01`. Never manipulate old audit/manifest files after the run. Never merge model weights without separate experimental testing.

Sources for attribution:

- https://github.com/NTDung123/Aquawatch
- https://zenodo.org/records/5996890
- https://universe.roboflow.com/abdos-workspace-totgi/swimming-drowning-ed3dl
- https://universe.roboflow.com/se-zgnpx/swimming-drowning
- https://universe.roboflow.com/foiaxlc/drownings-test
- https://universe.roboflow.com/first-d0cuw/drowning-detection-g996n-e0osd/dataset/1
