import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const api = read('./api.ts')
const settings = read('./pages/platform/PlatformSettings.vue')

describe('platform AI configuration UI contract', () => {
  it('exposes only the masked configuration metadata to the frontend contract', () => {
    expect(api).toContain('export interface PlatformAIConfig')
    expect(api).toContain('configured: boolean')
    expect(api).toContain('masked_key: string')
    expect(api).toContain('model: string')
    expect(api).toContain('base_url: string')
    expect(api).toContain("api.get<PlatformAIConfig>('platform-ai-config/')")
    expect(api).toContain("api.put<PlatformAIConfig>('platform-ai-config/'")
    expect(api).toContain('model: string; base_url: string')
    expect(api).not.toContain('api_key: string')
    expect(api).not.toContain('encrypted_api_key')
  })

  it('keeps the input one-way and renders the returned mask', () => {
    expect(settings).toContain('getPlatformAIConfig')
    expect(settings).toContain('savePlatformAIConfig')
    expect(settings).toContain('v-model="apiKeyInput"')
    expect(settings).toContain('v-model="modelInput"')
    expect(settings).toContain('v-model="baseUrlInput"')
    expect(settings).toContain('type="password"')
    expect(settings).toContain('autocomplete="new-password"')
    expect(settings).toContain('<el-icon :size="18"')
    expect(settings).toContain('config.masked_key')
    expect(settings).toContain('首次保存后不会再次显示完整 API Key')
    expect(settings).not.toContain('config?.api_key')
    expect(settings).not.toContain('config?.encrypted_api_key')
  })
})
