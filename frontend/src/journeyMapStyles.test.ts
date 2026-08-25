import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = [
  'foundations.css',
  'workspace.css',
  'responsive.css',
].map((file) => readFileSync(new URL(`./styles/${file}`, import.meta.url), 'utf8')).join('\n')
const deliveryBoard = readFileSync(new URL('./components/JourneyDeliveryBoard.vue', import.meta.url), 'utf8')

describe('journey map chapter styles', () => {
  it('uses the five-chapter delivery board as the only task list surface', () => {
    expect(deliveryBoard).toContain('v-for="group in groups"')
    expect(deliveryBoard).toContain('journey-delivery__chapter-toggle')
    expect(styles).not.toContain('.journey-stage')
    expect(styles).not.toContain('.map-task')
  })

  it('keeps desktop task metadata in one aligned row', () => {
    expect(deliveryBoard).toContain('.journey-delivery__columns, .journey-delivery__item { display: grid; grid-template-columns: minmax(220px, 1.7fr) minmax(130px, 1fr) minmax(120px, 1fr) 72px 86px;')
  })

  it('switches the same board to stacked task rows on narrow screens', () => {
    expect(deliveryBoard).toContain('@media (max-width: 768px)')
    expect(deliveryBoard).toContain('.journey-delivery__field-label { display: inline;')
  })
})
