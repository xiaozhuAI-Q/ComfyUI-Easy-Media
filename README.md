# ComfyUI Easy Media

<div align="center">
<a href="./README.md"><img src="https://img.shields.io/badge/🇬🇧English-0b8cf5"></a>
<a href="./README_CN.md"><img src="https://img.shields.io/badge/🇨🇳中文简体-e9e9e9"></a>
<br>
</div>

A ComfyUI custom node package for streamlined media loading and video pipeline assembly. Provides intuitive nodes that simplify media resource editing and loading with user-friendly parameters, making it easier to build and configure video processing workflows.

<table>
    <tr>
        <td><pre style="height:150px;"><br>Code is being continuously updated~<br>May your tokens be inexhaustible.</pre></td>
        <td><img src="https://pbs.twimg.com/media/HHvOkkraMAAoT0o?format=jpg&name=medium" height="150"></td>
    </tr>
</table>


## Installation

The code has not yet been added to the registry; currently, only manual installation is supported:

```bash
cd Your_ComfyUI_Path/custom_nodes
git clone https://github.com/yolain/ComfyUI-Easy-Media.git
```

Then restart ComfyUI.

## Example Workflows

After installing, open ComfyUI and find the bundled example workflows in the **Templates** panel on the left sidebar — look for entries under **ComfyUI-Easy-Media**.

## Roadmap 2026

| Date (estimated) | Status                 | Version |
| ---------------- | ---------------------- | ------- |
| May 21-24        | (Improve & Register)   | v1.0.0  |
| May 17-18 🚩     | Pre-release & Debug    | -       |
| May 13-16        | Development            | -       |
| May 11-12        | Architecture Design    | -       |



## Features

### Timeline Editor

> I believe the media timeline editor component is better suited as a standalone module node for greater versatility. This node focuses on media import/editing and timeline-related functionality, providing better support for video pipeline creation across different models.<br>
The editor can be used for single video segment generation (e.g., combined with PromptRelay), as well as segmented generation. Each segment can be combined with different model video pipelines for text-only generation, single image generation, first/last frame generation, multi-frame generation, reference-based generation, etc.

![timelineEditor](https://github.com/user-attachments/assets/5f78a31c-e0e7-4d0e-ba58-e68d78f325ac)

#### Track Types

| Type       | Description                              |
| ---------- | ---------------------------------------- |
| Main Track | Supports multi-segment editing with images and prompts |
| Audio Track | Can load multiple audio segments, merged for final export |

### SaveVideo

![SaveVideo](https://github.com/user-attachments/assets/acf75fae-88ea-450d-8171-cb655bb99420)
> Integrated and enhanced the video saving node from the SaveVideoRGBA node package. Supports video export with customizable output path, filename prefix, frame rate, and other parameters.

### MultiTrack Editor

> Planned...


