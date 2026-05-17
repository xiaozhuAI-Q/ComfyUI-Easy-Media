import path from 'path'
import { fileURLToPath } from 'url'

// This file lives in frontend/; one level up is the project root.
// Use import.meta.url (Node-compatible) instead of import.meta.dir (Bun-only).
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const customNodeClass = path.basename(path.resolve(__dirname, '..')).toLowerCase()

export default {
  important: `.${customNodeClass}`,
  variants:{
    extend: {
      opacity: ['active'],
    },
  }
};

