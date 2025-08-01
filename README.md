[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/planetx-vfx/tk-desktop-deliveries?include_prereleases)](https://github.com/planetx-vfx/tk-desktop-deliveries) 
[![GitHub issues](https://img.shields.io/github/issues/planetx-vfx/tk-desktop-deliveries)](https://github.com/planetx-vfx/tk-desktop-deliveries/issues) 
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


# ShotGrid Deliveries App <img src="icon_256.png" alt="Icon" height="24"/>

[![Documentation](https://img.shields.io/badge/documentation-blue?style=for-the-badge)](https://github.com/planetx-vfx/tk-desktop-deliveries#readme)
[![Support](https://img.shields.io/badge/support-orange?style=for-the-badge)](https://github.com/planetx-vfx/tk-desktop-deliveries/issues)

App to deliver shots with the correct naming convention.

The **tk-desktop-deliveries** app streamlines the process of delivering shot versions and previews in a ShotGrid
pipeline, ensuring correct file naming, status tracking, and structured output.

## User interface

|                                                 Home                                                  |                                                 Settings                                                  |
|:-----------------------------------------------------------------------------------------------------:|:---------------------------------------------------------------------------------------------------------:|
| ![delivery_app_home](https://github.com/user-attachments/assets/ce7a4d97-6832-4002-87c4-bf9266acf802) | ![delivery_app_settings](https://github.com/user-attachments/assets/bc03fe7a-b96c-4d12-80ed-82ddb85b4de0) |

## ✨ Features

### 🔧 Template-Based Delivery Configuration

Define output locations and naming conventions for input sequences, preview movies, delivery folders, submission forms,
and more using customizable templates.

---

### 🔁 Status Tracking & Automation

#### Status Field Mapping

The app uses configurable ShotGrid field names to determine which fields to read from when evaluating delivery
readiness:

- `shot_status_field`: The Shot field used to check whether a shot is ready for delivery.
- `version_status_field`: The Version field used to check whether a version is ready for delivery.

#### Delivery Readiness

The following status values determine whether an item is considered ready for delivery:

- `shot_delivery_status`: If a shot has this status, it is included for sequence delivery.
- `version_delivery_status`: If a version has this status, it is included for preview delivery.

#### Post-Delivery Status Updates

Once delivery is complete, the app updates ShotGrid statuses to reflect what was delivered:

- `version_delivered_status`: Applied to the Version if a **sequence** was delivered. This takes precedence if both
  sequence and preview were delivered.
- `version_preview_delivered_status`: Applied to the Version if only a **preview** was delivered.
- `shot_delivered_status`: Applied to the Shot once at least one version tied to it has been delivered.

Example configuration:

```yaml
shot_status_field: sg_footage_status
version_status_field: sg_status_list

shot_delivery_status: iarts
version_delivery_status: iarts
version_delivered_status: dlvr
version_preview_delivered_status: dledit
shot_delivered_status: dlvr
```

---

### 🎞️ Sequence & Preview Output Control

#### Preview Output

Configure multiple delivery formats for previews. Each format includes a configurable extension for a Nuke write node,
and the ability to configure your own write settings.

Example:

```yaml
delivery_preview_outputs:
  - name: H.264
    extension: mov
    settings:
      mov64_codec: h264
  - name: ProRes LT
    extension: mov
    settings:
      mov_prores_codec_profile: ProRes 4:2:2 LT 10-bit
```

##### Preview Letterboxing

The app supports adding a **letterbox mask** to preview renders. This can be used to maintain a consistent aspect
ratio (e.g. 2.39:1) and simulate final framing. The letterbox mask can be disabled per preview output.

This feature is controlled by ShotGrid fields on the Project entity:

- `sg_output_preview_enable_mask`: A boolean toggle to enable or disable the letterbox overlay.
- `sg_output_preview_aspect_ratio`: A float value (e.g. `2.39`) defining the **width** of the target aspect ratio. The
  height is assumed to be `1`.

When enabled, a black letterbox will be added to the preview output at a preset opacity to simulate the intended aspect
ratio. This is especially useful for editorial previews and reviews where final framing matters.

> Note: This applies to **preview outputs only**, not sequence deliveries.

Example:

| Field                            | Value  |
|----------------------------------|--------|
| `sg_output_preview_enable_mask`  | `true` |
| `sg_output_preview_aspect_ratio` | `2.39` |

This would render the preview with a black matte letterbox simulating a 2.39:1 frame on a 1.0 aspect base.

> [!WARNING]
> Currently the fields are hardcoded and must exactly match by name. This will be improved upon in the future.

#### EXR Render Output

Match different render settings (e.g., compression types) to version statuses. Great for controlling how files are
exported for review, reference, or final delivery.

When the sequence already matches the configured settings, the files will be symlinked if possible or just copied if
not.

Example:

```yaml
delivery_sequence_outputs:
  - name: DWAA
    extension: exr
    status: WIP
    settings:
      compression: DWAA
  - name: PIZ
    extension: exr
    status: TECH CHECKED
    settings:
      compression: PIZ Wavelet (32 scanlines)
```

The Version field used to determine which output setting applies to each version is defined by
`delivery_sequence_outputs_field`.

```yaml
delivery_sequence_outputs_field: sg_submitting_for
```

#### TCL Support in Output Fields

Text fields in the output `settings` support Nuke TCL expressions for dynamic, scriptable content.

```yaml
delivery_preview_outputs:
  - name: DNxHR SQ
    extension: mxf
    default_enabled: true
    settings:
      mxf_video_codec_knob: Avid DNxHR
      mxf_op_pattern_knob: OP-Atom
      mxf_codec_profile_knob: SQ 4:2:2 8-bit
      mxf_tape_id_knob: "[basename [file rootname [file rootname [value Read1.file]]]]" # Gets the filename without frame number and extension
```

#### Slate Integration

- A **slate is always added** to preview deliveries.
- Optionally add the same slate to the rendered sequence by setting `add_slate_to_sequence: true`.
- The slate includes default fields like **Submitting For** and **Submission Note**, which are mapped via the following
  settings:
    - `submitting_for_field`: controls which ShotGrid field is shown on the slate under "Submitting for"
    - `submission_note_field`: defines which ShotGrid field is used as the "Submission Note" on the slate
- You can define up to 6 extra fields for the slate via `slate_extra_fields`.
    - The slate values support **Nuke TCL** expressions, giving you full control over dynamic values.
        - _The read node for the preview/exr is called `Read1`._
    - The slate extra fields also support inline **ShotGrid templates**.
        - _Note: the fields used in this template must be used by an actual template in `templates.yml`_
    - The slate extra fields also support custom **ShotGrid entity templates**.
        - Uses <...> to wrap a reference to a field on an entity.
        - Supported entities are: `project`, `shot` and `version`.
        - If a field is an array, the first item is used.
- Optional color management settings `preview_colorspace_idt` and `preview_colorspace_odt` can be configured to control
  the preview's input/output colorspace during slate rendering.

Example:

```yaml
add_slate_to_sequence: true

submitting_for_field: sg_submitting_for
submission_note_field: sg_submission_note

slate_extra_fields:
  Director: Steven Spielberg
  Format: '[value width]x[value height], [format "%.2f" [expr (double([value input.width]) / double([value input.height]))]]:1'
  Filename: '{prj}[_{Episode}]_{Sequence}_{Shot}_{task_name}[_{vnd}]_v{version}'
  Lens: '<shot.sg_footage_formats.sg_lens_name>'
```

##### Slate Font Configuration

To customize the look of the slate, you can specify platform-specific paths to the fonts used during rendering.

- The **bold font** is used for field **labels** (e.g. "Submitting For", "Shot Name").
- The **regular font** is used for the corresponding **values**.

You can configure fonts separately for Windows, macOS, and Linux:

```yaml
font_path_windows: X:/Fonts/Inter-Regular.ttf
font_bold_path_windows: X:/Fonts/RobotoSlab-Bold.ttf

font_path_mac: /Volumes/Fonts/Inter-Regular.ttf
font_bold_path_mac: /Volumes/Fonts/RobotoSlab-Bold.ttf

font_path_linux: /mnt/fonts/Inter-Regular.ttf
font_bold_path_linux: /mnt/fonts/RobotoSlab-Bold.ttf
```

> If any font path is left blank for a platform, a default system font will be used.

---

### 📄 CSV Submission & Metadata

On delivery a CSV will be created with the fields specified in the settings.
These values can use expressions by wrapping a field with {}, or you can just add regular text.

#### Fields

The following fields are available in the CSV values:

| Value                         | Description                                                                                                                            |
|-------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| file.name                     | The outputted file name                                                                                                                |
| file.codec / file.compression | The codec (video) or compression (exr) of the outputted file                                                                           |
| file.folder                   | The name of the delivery folder                                                                                                        |
| date.&lt;format&gt;           | &lt;format&gt; is a date format using [Python Date Format Codes](https://www.w3schools.com/python/gloss_python_date_format_codes.asp). |
| project.*                     | A ShotGrid field on the current Project                                                                                                |
| shot.*                        | A ShotGrid field on the Shot                                                                                                           |
| version.                      | A ShotGrid field on the Version                                                                                                        |

#### Save a template

To easily reuse CSV templates, you can save the current configuration using the Save button.
If you use the name `Default`, the saved configuration will be loaded automatically on launch.
Use the `csv_template_folder` template setting to control where CSV form templates are stored and loaded from.

#### Linked Attachment Support

If a file is linked to a Version via a ShotGrid file field, the app can include this in the delivery package:

- The file is either **copied** (if local) or **downloaded** (if it's an uploaded file) into the delivery folder.
- Its filename is then added as a column value in the CSV — but only if the `attachment_field` is referenced in the CSV
  configuration.

Example configuration:

```yaml
attachment_field: sg_attachment
default_csv:
  Attachment: "{version.sg_attachment}"
```

This is useful for including additional review materials (like PDFs, reference images, or any other supplementary
material) as part of your delivery package.

---

### 🧠 Version Field Overrides

- **Custom Field Replacement**: Replace values in ShotGrid fields using `version_overrides`. This is useful for
  injecting vendor-specific data or customizing metadata before delivery.
- **Entity Support**: Overrides can target `Shot`, `Version` and `PublishedFile` entity types.
    - The version number that is used for the version comes from the Published File.

#### Dynamic Field Replacement

Customize fields before delivery using `version_overrides`. This is especially useful when renaming tasks or adjusting
version numbers.

Example:

```yaml
version_overrides:
  - entity_type: PublishedFile
    match: { task.name: v000 }
    replace: { task.name: Comp, version_number: 0 }
```

---

### ♻️ Delivery Override & Merge

The app allows you to **override** an existing delivery or **merge** into a custom delivery path, providing more control
for updates, corrections, or grouped submissions.

#### Override Delivery Version

In the UI, you can manually enter a **delivery version number**, which will replace the automatically incremented
version (e.g. `v001`, `v002`). This allows you to:

- Deliver an update to an existing package using the same version number.
- Re-use the same folder structure for related or grouped shots.

> When you override the version number, existing files in the delivery folder may be overwritten.

#### Custom Delivery Location

You can also specify a **custom delivery folder** path via the GUI. This lets you:

- Deliver to a temporary or external location.
- Merge multiple shot deliveries into a shared folder.
- Redirect output for ad hoc deliveries outside the default template structure.

These overrides are useful in client-review scenarios, late delivery fixes, or special submission rounds that don't
follow the default path/version logic.

> [!WARNING]
> Be cautious when overriding both version and path — the app will not automatically prevent overwriting unless the
> destination is locked externally.

---

### 📊 Error Reporting through Sentry (Optional)

Hook into Sentry for crash/error reporting by providing a DSN URL, helping maintain reliability and trace issues
quickly.


## Requirements

| ShotGrid version | Core version | Engine version |
|------------------|--------------|----------------|
| -                | v0.14.28     | -              |

## Configuration

### Templates

| Name                      | Description                                   | Default value | Fields                                                                                           |
|---------------------------|-----------------------------------------------|---------------|--------------------------------------------------------------------------------------------------|
| `input_shot_preview`      | Template of the shot preview files.           |               | context, *                                                                                       |
| `input_shot_sequence`     | Template to deliver the shot sequences from.  |               | context, version, SEQ, *                                                                         |
| `input_shot_lut`          | Template of the shot LUT files.               |               | context, *                                                                                       |
| `input_asset_preview`     | Template of the asset preview files.          |               | context, *                                                                                       |
| `input_asset_sequence`    | Template to deliver the asset sequences from. |               | context, version, SEQ, *                                                                         |
| `delivery_folder`         | Folder to deliver to.                         |               | prj, delivery_date, delivery_version                                                             |
| `delivery_shot_sequence`  | Template to deliver the shot sequences to.    |               | context, prj, delivery_date, delivery_version, task_name, version, SEQ, *                        |
| `delivery_shot_preview`   | Template to deliver the shot previews to.     |               | context, prj, delivery_date, delivery_version, task_name, version, delivery_preview_extension, * |
| `delivery_shot_lut`       | Template to deliver the shot LUT files to.    |               | context, prj, delivery_date, delivery_version, task_name, version, *                             |
| `delivery_asset_sequence` | Template to deliver the asset sequences to.   |               | context, prj, delivery_date, delivery_version, task_name, version, SEQ, *                        |
| `delivery_asset_preview`  | Template to deliver the asset previews to.    |               | context, prj, delivery_date, delivery_version, task_name, version, delivery_preview_extension, * |
| `csv_submission_form`     | Template to deliver the submission form to.   |               | prj, delivery_date, delivery_version                                                             |
| `csv_template_folder`     | Folder to saves CSV templates.                |               | context, *                                                                                       |


### Lists

| Name                        | Description                                                                         | Default value |
|-----------------------------|-------------------------------------------------------------------------------------|---------------|
| `delivery_preview_outputs`  | List of preview output settings to use.                                             |               |
| `delivery_sequence_outputs` | List of version statuses to match exr render settings to.                           |               |
| `version_overrides`         | List of overrides to replace ShotGrid data with. The keys are ShotGrid field names. |               |


### Dictionaries

| Name                    | Description                                                                                                      | Default value                                                                                                                                                                                                                                 |
|-------------------------|------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `default_csv`           | Dict of default values for the CSV.                                                                              | {'Version Name': '<file.name>', 'Link': '<shot.code>', 'VFX Scope of Work': '<shot.sg_scope_of_work>', 'Vendor': '<project.sg_vendorid>', 'Submitting For': '<version.sg_submitting_for>', 'Submission Note': '<version.sg_submission_note>'} |
| `slate_extra_fields`    | Extra fields to display on the slate. Max 6. You can use Nuke TCL expressions or a ShotGrid Template definition. | {}                                                                                                                                                                                                                                            |
| `footage_format_fields` |                                                                                                                  |                                                                                                                                                                                                                                               |


### Strings

| Name                               | Description                                                                                | Default value            |
|------------------------------------|--------------------------------------------------------------------------------------------|--------------------------|
| `shot_status_field`                | Field to check the shot status with.                                                       | sg_status_list           |
| `version_status_field`             | Field to check the version status with.                                                    | sg_status_list           |
| `vfx_scope_of_work_field`          | Shot field to use on the slate in "VFX Scope Of Work".                                     | sg_scope_of_work         |
| `submitting_for_field`             | Version field to use on the slate in "Submitting for".                                     | sg_submitting_for        |
| `submission_note_field`            | Version field to use on the slate in "Submission note".                                    | sg_submission_note       |
| `short_submission_note_field`      | Version field to use on the preview overlay as submission note.                            | sg_submission_note_short |
| `attachment_field`                 | Field to get the attachment from. Field should be of type File/Link (url).                 | sg_attachment            |
| `delivery_sequence_outputs_field`  | Field to match the delivery sequence output settings with.                                 | sg_submitting_for        |
| `shot_delivery_status`             | Status of a shot that will be added to the ready for delivery list.                        | rfd                      |
| `version_delivery_status`          | Status of a version that will be added to the ready for delivery list.                     | rfd                      |
| `version_delivered_status`         | Status to set the version to if the EXRs (and preview) of the version have been delivered. | dlvr                     |
| `version_preview_delivered_status` | Status to set the version to if only a preview of the version has been delivered.          | dlvr                     |
| `shot_delivered_status`            | Status to set the shot to if the EXRs of the shot have been delivered.                     | fin                      |
| `preview_colorspace_idt`           | Input colorspace of the preview.                                                           | ACES - ACEScg            |
| `preview_colorspace_odt`           | Output colorspace of the preview.                                                          | Output - sRGB            |
| `sequence_colorspace`              | Colorspace of the sequence.                                                                | ACES - ACES2065-1        |
| `footage_format_entity`            | Entity that contains the footage formats.                                                  |                          |
| `shot_footage_formats_field`       | Field that links to the used footage formats on an Shot.                                   | sg_footage_formats       |
| `asset_footage_formats_field`      | Field that links to the used footage formats on an Asset.                                  | sg_footage_formats       |
| `logo_path_linux`                  | Linux path to the company logo.                                                            |                          |
| `logo_path_mac`                    | Mac path to the company logo.                                                              |                          |
| `logo_path_windows`                | Windows path to the company logo.                                                          |                          |
| `font_path_linux`                  | Linux path to the regular font to use.                                                     |                          |
| `font_bold_path_linux`             | Linux path to the bold font to use.                                                        |                          |
| `font_path_mac`                    | Mac path to the regular font to use.                                                       |                          |
| `font_bold_path_mac`               | Mac path to the bold font to use.                                                          |                          |
| `font_path_windows`                | Windows path to the regular font to use.                                                   |                          |
| `font_bold_path_windows`           | Windows path to the bold font to use.                                                      |                          |
| `nuke_path_linux`                  | Linux path to your Nuke installation for creating slates.                                  |                          |
| `nuke_path_mac`                    | Mac path to your Nuke installation for creating slates.                                    |                          |
| `nuke_path_windows`                | Windows path to your Nuke installation for creating slates.                                |                          |
| `sentry_dsn`                       | Sentry DSN Url                                                                             |                          |


### Booleans

| Name                               | Description                                                                | Default value |
|------------------------------------|----------------------------------------------------------------------------|---------------|
| `add_slate_to_sequence`            | If a slate frame should be added before the delivered sequence             | False         |
| `override_preview_submission_note` | If the preview should add a new submission note as an overlay.             | False         |
| `continuous_versioning`            | If the delivery versions should always increment, independent of the date. | False         |


