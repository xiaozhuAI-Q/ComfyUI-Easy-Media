import { addStylesheet } from "@/lib/add-stylesheet";
import type { ComfyApp } from '@comfyorg/comfyui-frontend-types'
import type { TimelineData } from '@/types/timeline'

declare global {
  // eslint-disable-next-line no-var
  var comfyAPI: { app: { app: ComfyApp } } | undefined
}

const [{ createReactWidget }, { TimelineWidget }, { createDefaultTimelineData }] = await Promise.all([
  import('@/lib/create-react-widget'),
  import('@/components/widgets'),
  import('@/lib/timeline-utils'),
]);

const DEFAULT_TIMELINE_VALUE = JSON.stringify(createDefaultTimelineData())

globalThis.comfyAPI!.app.app.registerExtension({
  name: 'Comfy.EasyMedia.widgets',

  async setup() {
    addStylesheet(`/${import.meta.env.PROJECT_NAME}/globals.css`);
  },

  getCustomWidgets() {
    return {
      TIMELINE: createReactWidget<TimelineData>(TimelineWidget, {
        defaultValue: DEFAULT_TIMELINE_VALUE,
        domWidgetOptions: {
          getMinHeight: () => 180,
        },
      }),
    }
  },
})


