# Draw My Life: How Emotions Shape the Way We Draw

Code and extracted features for a study of emotion recognition from drawing dynamics, conducted at the **Socially Assistive Robotics with Artificial Intelligence (SARAI) Lab, Karlsruhe Institute of Technology (KIT)**. The PdF project ran from November 2025 to September 2026.

The broader **Draw My Life** project explores how drawing and storytelling with a social robot can support children's self-disclosure. This repository covers an **exploratory study with adults**, investigating two questions:

1. Can drawing dynamic features predict the assigned emotion condition?
2. Which features contribute most to that prediction?

The repository includes the study application, feature extraction, an aggregated dataset, and the analysis notebooks.

## Repository contents

| Path | Contents |
| --- | --- |
| [`draw_my_life_code/`](draw_my_life_code/) | ROS 2 packages for the tablet interface, robot display, and spoken instructions. |
| [`feature_extraction_code/feature_extract.ipynb`](feature_extraction_code/feature_extract.ipynb) | Extracts drawing features from raw session recordings and images. |
| [`extracted_features/`](extracted_features/) | Aggregated features in CSV and Excel format. |
| [`extracted_features/README.md`](extracted_features/README.md) | Feature descriptions. |
| [`feature_analysis_code/feature_analysis.ipynb`](feature_analysis_code/feature_analysis.ipynb) | Mood checks, feature selection, classification, and feature importance analysis. |
| [`feature_analysis_code/figures/`](feature_analysis_code/figures/) | Saved analysis figures. |

## Study and dataset

The analysed dataset contains **25 adult participants and 75 drawing rounds**. Each participant completed three rounds: one positive condition, one negative condition, and a neutral condition. Participants recalled a personal event, rated their mood, drew the event for up to five minutes, and rated their mood again. Baseline mood was also recorded.

| Emotion condition | Drawing rounds | Three-class label |
| --- | ---: | --- |
| Excitement | 13 | Positive |
| Contentment | 12 | Positive |
| Anger | 12 | Negative |
| Sadness | 13 | Negative |
| Neutral | 25 | Neutral |

The feature tables contain **one row per drawing round**, with:

- **72 pen and interaction features**, covering movement, timing, pressure, tilt, stroke shape, spatial extent, and tool use.
- **16 final-image features**, describing spatial coverage, dispersion, and colour.
- **13 metadata and rating fields**, including participant ID, demographics, condition labels, and self-reported valence and arousal.

Identifiers, demographics, and self-reported mood ratings are excluded from the classifier inputs. Classification targets are the **assigned emotion conditions**.

Raw drawings and pen-event recordings are not included for participant privacy. The public feature tables support the analysis, but cannot be used to regenerate the original features from scratch.

## Run the analysis

The analysis uses the included CSV file. **ROS 2 and robot hardware are not required.**

### 1. Set up Python

From a terminal on Linux or macOS:

```bash
git clone https://github.com/SARAI-Lab-KIT/emotion-study-pdf.git
cd emotion-study-pdf
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install jupyterlab ipykernel numpy pandas scipy matplotlib seaborn scikit-learn networkx
```

If you downloaded the repository as a ZIP, extract it and open a terminal in its root folder instead of cloning it.

### 2. Open the analysis notebook

From the repository root, with the environment activated:

```bash
cd feature_analysis_code
jupyter lab feature_analysis.ipynb
```

Run the cells in order. Keep the notebook's working directory set to `feature_analysis_code/`: it reads `../extracted_features/extracted_features.csv` and saves figures under `figures/`.

The notebook:

1. Summarises the sample and checks changes in self-reported mood.
2. Reduces redundant features using correlations and selects stable feature subsets.
3. Trains logistic regression, linear SVM, random forest, and gradient boosting classifiers for five-class and three-class prediction.
4. Evaluates predictions by leaving out one participant at a time, keeping that participant's three rounds together.
5. Calculates accuracy, ROC-AUC, macro F1, permutation tests, and feature importance.

Permutation tests involve many repeated model fits and can take considerably longer than the other cells. Dependency versions are not pinned, so exact results may vary with the software environment and random seeds. Feature selection precedes the final cross-validation loop; the notebook does not implement fully nested feature selection.

## Extract features from raw recordings

This step requires access to the private study recordings. It is **not necessary** to analyse the included feature table.

Install the additional dependencies in the same Python environment:

```bash
python -m pip install opencv-python openpyxl
```

The extraction code expects these paths relative to the repository root:

```text
data_adults/participants.csv
data_adults/<lowercase-participant-id>/session_0/*.npz
data_adults/<lowercase-participant-id>/session_0/*.json
data_adults/<lowercase-participant-id>/session_0/drawings/*.png
```

From the repository root:

```bash
cd feature_extraction_code
jupyter lab feature_extract.ipynb
```

Run the cells in order with `feature_extraction_code/` as the working directory. The default settings extract full-round features and write `extracted_features.csv` and `extracted_features.xlsx` into `extracted_features/`. Set a different `SUFFIX` before running if you want to preserve the bundled tables.

## Study application

The study used **Ubuntu 24.04 LTS, ROS 2 Jazzy, PixelBot v2, and a Wacom One 13 Touch tablet**. The application consists of three ROS 2 packages:

| Package | Purpose | Run command |
| --- | --- | --- |
| [`pixelbot_tablet`](draw_my_life_code/pixelbot_tablet/) | Mood induction, ratings, drawing interface, and session recording. | `ros2 run pixelbot_tablet draw_node` |
| [`pixelbot_display`](draw_my_life_code/pixelbot_display/) | Animated robot eyes with blinking and gaze movement. | `ros2 run pixelbot_display pixelbot_display_node` |
| [`sarai_tts_playsound`](draw_my_life_code/sarai_tts_playsound/) | Local English/German speech using Piper and Pygame. | `ros2 run sarai_tts_playsound sarai_tts_playsound_node` |

### Configuration before use

This is research software with workstation-specific configuration. Before building or collecting data:

- Place the three packages directly under a ROS workspace's `src/` directory. Start the tablet node from the workspace root because some asset paths are relative to it.
- Provide the ROS message packages and Python dependencies. These include `sarai_msgs`, the manifest-declared `pixelbot_msgs`, Pygame, OpenCV, NumPy, `cv_bridge`, `evdev`, and Piper. The external message packages are not bundled, and package manifests do not list every runtime dependency.
- Add the Piper voice models `en_US-sam-medium.onnx` and `de_DE-thorsten-medium.onnx`, together with their matching `.onnx.json` files, under `sarai_tts_playsound/voice_model/` before building. These files are not bundled.
- Review `DEBUG` and `DISABLE_PRESSURE` in `drawing_app_node.py`; both currently default to `True`. Configure the display indices for your workstation; the tablet currently uses display index `2`.
- For pressure recording, ensure the application can read the Wacom input device and launch with `--ros-args -p pressure_recording:=enabled`.

After installing dependencies, build from the ROS workspace root:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --packages-select pixelbot_tablet pixelbot_display sarai_tts_playsound
source install/setup.bash
```

Run the three nodes in separate terminals, sourcing the ROS installation and workspace in each. Session recordings are saved under `src/pixelbot_tablet/saved_drawings/` in the expected workspace layout.

Package-level READMEs contain additional background, but some instructions describe older versions of the display and speech nodes. The current speech implementation uses **Piper**, and pressure recording is disabled by default.

## Authors and paper

**Tamara Buchler, Junxian Liu, Romain Maure, and Barbara Bruno**  
*Draw My Life: How Emotions Shape the Way We Draw*  
SARAI Lab, Karlsruhe Institute of Technology (KIT).

## Licence

The repository's root [`LICENSE`](LICENSE) contains the GNU General Public License, version 3. Some ROS package metadata declare different licences; consult the package-specific licence files and notices as well.
