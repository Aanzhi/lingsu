import { reactive } from 'vue'
import { getHealth, type RuntimeCapabilities } from '../api'

type RuntimeCapabilityState = RuntimeCapabilities & {
  loaded: boolean
  loading: boolean
}

// The safe default keeps optional resource flows disabled until the server
// explicitly confirms that their backing services are available.
const SAFE_DEFAULTS: RuntimeCapabilities = {
  attachments: false,
  pdf_export: false,
}

export const runtimeCapabilities = {
  state: reactive<RuntimeCapabilityState>({
    ...SAFE_DEFAULTS,
    loaded: false,
    loading: false,
  }),

  async load(force = false) {
    if (this.state.loading || (this.state.loaded && !force)) return
    this.state.loading = true
    try {
      const { data } = await getHealth()
      Object.assign(this.state, SAFE_DEFAULTS, data.capabilities ?? {})
    } catch {
      Object.assign(this.state, SAFE_DEFAULTS)
    } finally {
      this.state.loaded = true
      this.state.loading = false
    }
  },
}
