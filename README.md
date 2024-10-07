[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/planetx-vfx/tk-desktop-deliveries?include_prereleases)](https://github.com/planetx-vfx/tk-desktop-deliveries) 
[![GitHub issues](https://img.shields.io/github/issues/planetx-vfx/tk-desktop-deliveries)](https://github.com/planetx-vfx/tk-desktop-deliveries/issues) 
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


# ShotGrid Deliveries App <img src="icon_256.png" alt="Icon" height="24"/>

[![Documentation](https://img.shields.io/badge/documentation-blue?style=for-the-badge)](https://github.com/planetx-vfx/tk-desktop-deliveries#readme)
[![Support](https://img.shields.io/badge/support-orange?style=for-the-badge)](https://github.com/planetx-vfx/tk-desktop-deliveries/issues)

App to deliver shots with the correct naming convention.

This app will get all versions with the "Ready for Delivery" status, create slated previews and/or copy the publishes to the delivery folder with the correct naming convention.

## User interface
![delivery_export](https://github.com/nfa-vfxim/tk-desktop-deliveries/assets/63094424/46c7fbab-84c8-401e-8627-eb25b315b313)


## Requirements

| ShotGrid version | Core version | Engine version |
|------------------|--------------|----------------|
| -                | v0.14.28     | -              |

## Configuration

### Templates

| Name                  | Description                                 | Default value | Fields                                                                                           |
|-----------------------|---------------------------------------------|---------------|--------------------------------------------------------------------------------------------------|
| `preview_movie`       | Template of the preview files.              |               | context, *                                                                                       |
| `input_sequence`      | Template to deliver the sequences from.     |               | context, version, SEQ, *                                                                         |
| `delivery_folder`     | Folder to deliver to.                       |               | prj, delivery_date, delivery_version                                                             |
| `delivery_sequence`   | Template to deliver the sequences to.       |               | context, prj, delivery_date, delivery_version, task_name, version, SEQ, *                        |
| `delivery_preview`    | Template to deliver the previews to.        |               | context, prj, delivery_date, delivery_version, task_name, version, delivery_preview_extension, * |
| `csv_submission_form` | Template to deliver the submission form to. |               | prj, delivery_date, delivery_version                                                             |
| `csv_template_folder` | Folder to saves CSV templates.              |               | context, *                                                                                       |


### Lists

| Name                        | Description                                               | Default value |
|-----------------------------|-----------------------------------------------------------|---------------|
| `delivery_preview_outputs`  |                                                           |               |
| `delivery_sequence_outputs` | List of version statuses to match exr render settings to. |               |


### Strings

| Name                               | Description                                                                                | Default value     |
|------------------------------------|--------------------------------------------------------------------------------------------|-------------------|
| `shot_status_field`                | Field to check the shot status with.                                                       | sg_status_list    |
| `version_status_field`             | Field to check the version status with.                                                    | sg_status_list    |
| `delivery_sequence_outputs_field`  | Field to match the delivery sequence output settings with.                                 | sg_submitting_for |
| `shot_delivery_status`             | Status of a shot that will be added to the ready for delivery list.                        | rfd               |
| `version_delivery_status`          | Status of a version that will be added to the ready for delivery list.                     | rfd               |
| `version_delivered_status`         | Status to set the version to if the EXRs (and preview) of the version have been delivered. | dlvr              |
| `version_preview_delivered_status` | Status to set the version to if only a preview of the version has been delivered.          | dlvr              |
| `shot_delivered_status`            | Status to set the shot to if the EXRs of the shot have been delivered.                     | fin               |
| `preview_colorspace_idt`           | Input colorspace of the preview.                                                           | ACES - ACEScg     |
| `preview_colorspace_odt`           | Output colorspace of the preview.                                                          | Output - sRGB     |
| `sg_server_path`                   | ShotGrid server path                                                                       |                   |
| `sg_script_name`                   | ShotGrid script name                                                                       |                   |
| `sg_script_key`                    | ShotGrid script key                                                                        |                   |
| `logo_path_linux`                  | Linux path to the company logo.                                                            |                   |
| `logo_path_mac`                    | Mac path to the company logo.                                                              |                   |
| `logo_path_windows`                | Windows path to the company logo.                                                          |                   |
| `font_path_linux`                  | Linux path to the regular font to use.                                                     |                   |
| `font_bold_path_linux`             | Linux path to the bold font to use.                                                        |                   |
| `font_path_mac`                    | Mac path to the regular font to use.                                                       |                   |
| `font_bold_path_mac`               | Mac path to the bold font to use.                                                          |                   |
| `font_path_windows`                | Windows path to the regular font to use.                                                   |                   |
| `font_bold_path_windows`           | Windows path to the bold font to use.                                                      |                   |
| `nuke_path_linux`                  | Linux path to your Nuke installation for creating slates.                                  |                   |
| `nuke_path_mac`                    | Mac path to your Nuke installation for creating slates.                                    |                   |
| `nuke_path_windows`                | Windows path to your Nuke installation for creating slates.                                |                   |


