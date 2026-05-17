import type { ComfyApp } from '@comfyorg/comfyui-frontend-types'

declare global {
  // eslint-disable-next-line no-var
  var comfyAPI: { app: { app: ComfyApp } } | undefined
}

const app = globalThis.comfyAPI!.app.app

type PromptCallback = (text: string | null) => void
type ConfirmCallback = () => void

export const $prompt = (
  title: string,
  message: string,
  fn: PromptCallback = () => {}
): void => {
  try {
    app.extensionManager.dialog.prompt({ title, message }).then((text: string) => {
      fn(text)
    }).catch(() => {
      fn(null)
    })
  } catch {
    const text = globalThis.prompt(title, message)
    fn(text)
  }
}

export const $confirm = (
  title: string,
  message: string,
  success: ConfirmCallback = () => {},
  cancel: ConfirmCallback = () => {}
): void => {
  try {
    app.extensionManager.dialog.confirm({ title, message }).then((value: boolean) => {
      if (value) success()
      else cancel()
    })
  } catch {
    success()
  }
}

export const $success = (title: string, message: string, life = 3000): void => {
  try {
    app.extensionManager.toast.add({
      severity: 'success',
      summary: title,
      detail: message,
      life
    })
  } catch {
    globalThis.alert(title)
  }
}

export const $error = (title: string, message: string, life = 3000): void => {
  try {
    app.extensionManager.toast.add({
      severity: 'error',
      summary: title,
      detail: message,
      life
    })
  } catch {
    globalThis.alert(title)
  }
}

export const $warning = (title: string, message: string, life = 3000): void => {
  try {
    app.extensionManager.toast.add({
      severity: 'warn',
      summary: title,
      detail: message,
      life
    })
  } catch {
    globalThis.alert(title)
  }
}