---
name: comfyui-node-i18n
description: ComfyUI node internationalization - locales structure, nodeDefs.json, settings.json, main.json for translations. Use when adding i18n support to custom nodes.
---

# ComfyUI Node Internationalization (i18n)

ComfyUI supports localization of node names, descriptions, input/output labels, and settings through a structured `locales` directory system.

## Directory Structure

```
your_node_package/
└── locales/
    ├── en/
    │   ├── main.json
    │   ├── nodeDefs.json
    │   └── settings.json (optional)
    ├── zh/
    │   ├── main.json
    │   ├── nodeDefs.json
    │   └── settings.json (optional)
    └── zh-TW/
        └── ...
```

## Translation Files

### nodeDefs.json — Node Definitions

Translate node display names, descriptions, and I/O labels:

```json
{
  "imageBrightness": {
    "display_name": "Localized Node Name",
    "description": "Localized node description text",
    "inputs": {
      "text": {
        "name": "Text Input",
        "tooltip": "Tooltip shown on hover"
      }
    },
    "outputs": {
      "0": {
        "name": "Output Image"
      }
    }
  }
}
```

**Keys:** 
— Notice: key using `node_id` value`"imageBrightness"`not className when className not same as node_id.
- `display_name` — Translated node name in menu
- `description` — Translated tooltip/description
- `inputs.<input_id>.name` — Input label
- `inputs.<input_id>.tooltip` — Input hover tooltip
- `outputs.<index>.name` — Output label (use numeric index, not name)

### main.json — General Translations

Category names, settings categories, and common strings:

```json
{
  "categories": {
    "MyNodes": "My Nodes Category"
  },
  "settingsCategories": {
    "MyExtension": "My Extension Settings"
  }
}
```

### settings.json — Settings Interface

Translate settings UI elements:

```json
{
  "MyExtension_EnableDebug": {
    "name": "Enable Debug Mode",
    "tooltip": "Show debug information in console"
  }
}
```

**Note:** Settings ID uses `_` instead of `.` (e.g., `MyExt.setting` becomes `MyExt_setting`).

## Python Node Structure (V3)

Keep node code in English, translations override display via locales:

```python
from comfy_api.latest import io

class ImageBrightness(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="imageBrightness",
            display_name="Brighten Image",  # overridden by locales/zh/nodeDefs.json
            category="image/adjust",
            description="Adjusts image brightness by a factor",
            inputs=[
                io.Image.Input("image"),
                io.Float.Input("factor", default=1.0, min=0.0, max=3.0),
            ],
            outputs=[io.Image.Output("IMAGE")],
        )

    @classmethod
    def execute(cls, image, factor):
        result = clamp(image * factor, 0.0, 1.0)
        return io.NodeOutput(result)
```

The `display_name` in schema is the fallback; `nodeDefs.json` translations take precedence.

| Code | Language |
|------|----------|
| en | English (fallback) |
| zh | Simplified Chinese |
| zh-TW | Traditional Chinese |
| fr | French |
| ko | Korean |
| ru | Russian |
| es | Spanish |
| ja | Japanese |
| ar | Arabic |

## Example: Complete Setup

### locales/en/nodeDefs.json

```json
{
  "imageBrightness": {
    "display_name": "Brighten Image",
    "description": "Adjusts image brightness by a factor",
    "inputs": {
      "image": {
        "name": "Image",
        "tooltip": "The input image to brighten"
      },
      "factor": {
        "name": "Factor",
        "tooltip": "Brightness multiplier (0.0-3.0)"
      }
    },
    "outputs": {
      "0": {
        "name": "Image"
      }
    }
  }
}
```

### locales/zh/nodeDefs.json

```json
{
  "imageBrightness": {
    "display_name": "图像增强",
    "description": "通过系数调整图像亮度",
    "inputs": {
      "image": {
        "name": "图像",
        "tooltip": "要增强的输入图像"
      },
      "factor": {
        "name": "系数",
        "tooltip": "亮度倍增器 (0.0-3.0)"
      }
    },
    "outputs": {
      "0": {
        "name": "图像"
      }
    }
  }
}
```

### locales/zh/main.json

```json
{
  "categories": {
    "I18n Demo": "国际化演示"
  }
}
```

## Best Practices

1. **Keep code in English** — Node IDs, class names, and logic stay in English
2. **Use fallback first** — Place English translations in `en/` as the fallback
3. **Consistent key naming** — Match keys exactly with Python class names
4. **Output indices not names** — Use `"0"`, `"1"`, etc. for output translations
5. **Settings ID transformation** — Replace `.` with `_` in settings keys
