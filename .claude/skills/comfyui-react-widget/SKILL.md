---
name: comfyui-react-widget
description: Create React widgets in ComfyUI custom nodes. Covers createReactWidget wrapping, two-way data binding, render synchronization, extension registration, and component authoring conventions. Use when building new React widgets, debugging rendering issues, or registering custom widget types.
---

# ComfyUI React Widget

This project uses the `createReactWidget` factory function to mount React components as ComfyUI DOM widgets. This document describes how the entire mechanism works, key considerations, and complete examples.

---

## Architecture Overview

```
ComfyUI (LGraphNode)
  └── addDOMWidget(name, type, container, options)
        └── container (HTMLDivElement)
              └── React Root (createRoot)
                    └── <YourWidget value={...} onChange={...} />
```

- **currentValue** — Always stored as a JSON string for ComfyUI serialization/deserialization
- **render()** — Called on every value change, passing the latest props to the React Root
- **getValue / setValue** — ComfyUI calls these hooks to sync node values
- **serializeValue** — Called when ComfyUI builds the API payload, returns currentValue

---

## Core Files

| File | Responsibility |
|------|----------------|
| `src/lib/create-react-widget.ts` | Widget factory, manages React Root, value storage, and ComfyUI two-way binding |
| `src/index.ts` | ComfyUI extension entry point, registers `getCustomWidgets` |
| `src/components/widgets/` | React widget components |

---

## Creating a New Widget: Complete Flow

### 1. Write the React Component

```tsx
// src/components/widgets/MyWidget.tsx
import type { ReactWidgetProps } from '@/lib/create-react-widget'

export interface MyData {
  text: string
  count: number
}

export function MyWidget({ value, onChange }: ReactWidgetProps<MyData>) {
  // Key: derive data from value prop, don't use useState for main data
  const data: MyData = value && typeof value === 'object'
    ? value as MyData
    : { text: '', count: 0 }

  function update(patch: Partial<MyData>) {
    onChange({ ...data, ...patch })
  }

  return (
    <div>
      <Input value={data.text} onChange={e => update({ text: e.target.value })} />
    </div>
  )
}
```

### 2. Export the Component

```ts
// src/components/widgets/index.ts
export { MyWidget } from './MyWidget'
export type { MyData } from './MyWidget'
```

### 3. Register Widget Type in Entry Point

```ts
// src/index.ts
const [{ createReactWidget }, { MyWidget }] = await Promise.all([
  import('@/lib/create-react-widget'),
  import('@/components/widgets'),
])

globalThis.comfyAPI!.app.app.registerExtension({
  name: 'EasyMedia.widgets',

  async setup() {
    addStylesheet(`/${import.meta.env.PROJECT_NAME}/globals.css`)
  },

  getCustomWidgets() {
    return {
      MY_WIDGET: createReactWidget<MyData>(MyWidget, {
        defaultValue: JSON.stringify({ text: '', count: 0 }),
        domWidgetOptions: {
          getMinHeight: () => 80,
        },
      }),
    }
  },
})
```

### 4. Declare Corresponding Input Type in Python Node

```python
# nodes.py — Input type name must match getCustomWidgets key
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "my_data": ("MY_WIDGET", {}),
        }
    }
```

---

## createReactWidget Parameters

```ts
createReactWidget<T>(Component, options?)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `Component` | `React.ComponentType<ReactWidgetProps<T>>` | The React component to render |
| `options.defaultValue` | `string` | Initial JSON string, defaults to `''` |
| `options.height` | `number` | Fixed container height (px), auto-sized if not set |
| `options.domWidgetOptions` | `DOMWidgetOptions` | Passed through to `addDOMWidget`, can override `getMinHeight`, `getMaxHeight`, `hideOnZoom`, etc. |

### ReactWidgetProps\<T\>

```ts
interface ReactWidgetProps<T extends object | string = object> {
  value: T          // Current deserialized value
  onChange: (value: T) => void  // Update value and trigger re-render
  inputName: string // Node input name
  node: any         // LGraphNode instance
  widget: DOMWidget // DOMWidget instance for this widget
  app: ComfyApp     // ComfyApp instance
}
```

#### Receiving widget and node Information

```tsx
import type { ReactWidgetProps } from '@/lib/create-react-widget'
import type { DOMWidget } from '@comfyorg/comfyui-frontend-types'

export function MyWidget({ value, onChange, inputName, node, app, widget }: ReactWidgetProps) {
  // node properties
  const nodeId = node.id           // Node unique ID
  const nodeName = node.name      // Node type name
  const nodeType = node.type      // Node class type

  // widget properties
  const widgetValue = widget.options?.serialize // widget serialization options

  // app access
  // app.ui, app.graph, app.commandMenu, etc.

  return <div>...</div>
}
```

---

## Two-Way Data Binding Mechanism

### Internal Update (User Interacts with Component)

```
User interaction → onChange(newValue)
  → currentValue = JSON.stringify(newValue)   // Persist
  → setDirtyCanvas(true, true)                // Notify ComfyUI canvas to refresh
  → render()                                  // Must call! Pass new props
```

### External Update (ComfyUI Loads Workflow/Undo/Redo)

```
ComfyUI calls setValue(jsonString)
  → currentValue = jsonString
  → render()                                  // Re-render with new value
```

### Serialization (Building API Payload)

```
ComfyUI calls serializeValue()
  → Returns currentValue (JSON string)
```

---

## Key Considerations

### 1. Must Call render() After onChange

This is the most common bug. After `onChange` callback updates `currentValue`, you **must call `render()`** to pass the new value to the component. Otherwise the React component won't re-render (no state change triggers the update).

```ts
// Wrong: missing render(), component doesn't update
onChange: (v: T) => {
  currentValue = JSON.stringify(v)
  comfyNode.setDirtyCanvas(true, true)
}

// Correct
onChange: (v: T) => {
  currentValue = JSON.stringify(v)
  comfyNode.setDirtyCanvas(true, true)
  render()
}
```

### 2. Derive Main Data from value Prop, Don't Use useState

The main data (i.e., data to be serialized to ComfyUI) must be read from the `value` prop, not stored in React state. Reason: ComfyUI may externally update values via `setValue` (loading workflows, undo, etc.), and React must render with new props.

```tsx
// Wrong: storing main data in state, external setValue won't sync
const [items, setItems] = useState(value)

// Correct: derive directly from value
const items = Array.isArray(value) ? value : []
```

`useState` is only for UI temporary state (e.g., draft values in input fields) that doesn't affect serialized data.

### 3. Defensive Parsing of value

When `defaultValue` is an empty string, `parseValue` returns the empty string instead of an empty array/object, so defensive handling is needed in components:

```tsx
const items: MyItem[] = Array.isArray(value) ? value : []
const data: MyData = value && typeof value === 'object' ? value as MyData : { text: '' }
```

### 4. Use Top-Level await + Dynamic Import in Entry Point

`src/index.ts` uses `await Promise.all([...dynamic imports...])` to load modules, ensuring React and widget code are code-split by Bun into separate chunks to avoid bloating the ComfyUI main JS bundle.

```ts
// Dynamic import, triggers Bun code splitting
const [{ createReactWidget }, { MyWidget }] = await Promise.all([
  import('@/lib/create-react-widget'),
  import('@/components/widgets'),
])
```

### 5. getCustomWidgets Key Must Match Python Type Name

The type string in Python `INPUT_TYPES` (e.g., `"MY_WIDGET"`) must exactly match the key in the object returned by `getCustomWidgets()`.

---

## Complete Example Reference

### React Component (`src/components/widgets/ColorPaletteWidget.tsx`)

```tsx
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { uuid } from '@/lib/uuid'
import type { ReactWidgetProps } from '@/lib/create-react-widget'

export interface ColorPreset {
  id: string
  name: string
  hexColor: string
}

export function ColorPaletteWidget({ value, onChange }: ReactWidgetProps<ColorPreset[]>) {
  // Main data derived from value
  const presets: ColorPreset[] = Array.isArray(value) ? value : []
  // UI temporary state can use useState
  const [newName, setNewName] = useState('')

  function addPreset() {
    if (!newName.trim()) return
    onChange([...presets, {
      id: uuid(),
      name: newName.trim(),
      hexColor: '#000000',
    }])
    setNewName('')
  }

  function removePreset(id: string) {
    onChange(presets.filter(preset => preset.id !== id))
  }

  function updatePreset(id: string, patch: Partial<ColorPreset>) {
    onChange(presets.map(preset => preset.id === id ? { ...preset, ...patch } : preset))
  }

  return (
    <div className="flex flex-col gap-2 p-2 text-sm">
      {/* ... JSX ... */}
    </div>
  )
}
```

### Entry Registration (`src/index.ts`)

```ts
const [{ createReactWidget }, { ColorPaletteWidget }] = await Promise.all([
  import('@/lib/create-react-widget'),
  import('@/components/widgets'),
])

globalThis.comfyAPI!.app.app.registerExtension({
  name: 'EasyMedia.widgets',
  async setup() {
    addStylesheet(`/${import.meta.env.PROJECT_NAME}/globals.css`)
  },
  getCustomWidgets() {
    return {
      COLOR_PALETTE: createReactWidget<ColorPreset[]>(ColorPaletteWidget, {
        defaultValue: JSON.stringify([]),
        domWidgetOptions: { getMinHeight: () => 100 },
      }),
    }
  },
})
```

---

## Debugging Checklist

| Symptom | Cause | Solution |
|---------|-------|----------|
| Component doesn't update after user action | `onChange` missing `render()` | Add `render()` at end of `onChange` |
| Shows old data after loading workflow | Main data stored in `useState` | Derive from `value` prop instead |
| Node value always empty | `defaultValue` not set or type name mismatch | Check `createReactWidget` `defaultValue` and Python type name |
| Widget height is 0 | `getMinHeight` not set | Set `getMinHeight` in `domWidgetOptions` |
| Styles not applying | CSS not loaded | Confirm `addStylesheet` is called in `setup()` |

---

## Localization (i18n)

All static text in widget components (labels, titles, placeholders, tooltips, context-menu items, aria-labels) **must** use the localization system instead of hardcoded strings.

### How It Works

The current ComfyUI locale is read from `app?.ui?.settings?.settingsValues?.['Comfy.Locale']` in the top-level widget component and provided via `LocaleContext`. Child components consume it with `useT()`.

Message catalogs live in `frontend/messages/`:

```
frontend/messages/
  en.json   ← English (fallback)
  zh.json   ← Chinese
```

Keys are organized by section (one section per component). Parameterized strings use `{name}` placeholders.

### 1. Add Keys to Both Catalogs

```jsonc
// messages/en.json
{
  "myWidget": {
    "addItem": "Add item",
    "deleteItem": "Delete item",
    "itemLabel": "Item {n}",
    "placeholder": "Enter text…"
  }
}

// messages/zh.json
{
  "myWidget": {
    "addItem": "添加项目",
    "deleteItem": "删除项目",
    "itemLabel": "项目 {n}",
    "placeholder": "请输入文字…"
  }
}
```

### 2. Provide Locale in the Top-Level Widget Component

Only the root `*Widget.tsx` component does this. Pass the raw locale string to `LocaleContext.Provider`:

```tsx
// src/components/widgets/MyWidget.tsx
import { LocaleContext } from '@/lib/i18n'

export function MyWidget({ value, onChange, app }: ReactWidgetProps<MyData>) {
  const locale = app?.ui?.settings?.settingsValues?.['Comfy.Locale']

  return (
    <LocaleContext.Provider value={locale}>
      {/* child components */}
    </LocaleContext.Provider>
  )
}
```

### 3. Consume in Any Child Component

```tsx
// src/components/widgets/timeline/MyTrack.tsx
import { useT } from '@/lib/i18n'

export function MyTrack() {
  const t = useT()

  return (
    <div>
      {/* Simple key */}
      <Button>{t('myWidget.addItem')}</Button>

      {/* With parameter */}
      <span>{t('myWidget.itemLabel', { n: 3 })}</span>
      {/* en → "Item 3"  zh → "项目 3" */}

      {/* Placeholder */}
      <Textarea placeholder={t('myWidget.placeholder')} />

      {/* Aria-label */}
      <button aria-label={t('myWidget.deleteItem')} />
    </div>
  )
}
```

### 4. Common Shared Keys

Keys in the `"common"` section are shared across all components:

| Key | en | zh |
|-----|----|----|
| `common.cancel` | Cancel | 取消 |
| `common.save` | Save | 保存 |
| `common.add` | Add | 添加 |
| `common.delete` | Delete | 删除 |

```tsx
const t = useT()
<Button>{t('common.cancel')}</Button>
```

### Rule

> Every widget component that renders static text **must** call `useT()` and reference a message key.  
> Hardcoded strings in JSX or props are not allowed.

