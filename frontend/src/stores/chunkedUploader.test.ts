import { describe, expect, it, vi } from 'vitest'

import { shouldUseChunkUpload, uploadFileInChunks } from './chunkedUploader'

function fakeFile(content: string) {
  const bytes = new TextEncoder().encode(content)
  return {
    name: 'evidence.bin', type: 'application/octet-stream', size: bytes.length,
    slice(start: number, end: number) { return new Blob([bytes.slice(start, end)]) },
  }
}

describe('chunked uploader', () => {
  it('uses chunk sessions when any selected file reaches the threshold', () => {
    expect(shouldUseChunkUpload([{ size: 7 }, { size: 10 }], 10)).toBe(true)
    expect(shouldUseChunkUpload([{ size: 7 }, { size: 9 }], 10)).toBe(false)
  })

  it('skips server-confirmed parts and reports monotonic progress', async () => {
    const uploadPart = vi.fn().mockResolvedValue(undefined)
    const progress: number[] = []
    const complete = vi.fn().mockResolvedValue({ attachment_id: 9 })

    const result = await uploadFileInChunks(fakeFile('abcdefghij'), {
      chunkSize: 4,
      uploadedParts: [0],
      uploadPart,
      complete,
      onProgress(value) { progress.push(value) },
    })

    expect(uploadPart.mock.calls.map(([index]) => index)).toEqual([1, 2])
    expect(progress).toEqual([33, 67, 100])
    expect(complete).toHaveBeenCalledOnce()
    expect(result).toEqual({ attachment_id: 9 })
  })

  it('retries a transient part failure without reuploading completed parts', async () => {
    const uploadPart = vi.fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValue(undefined)

    await uploadFileInChunks(fakeFile('abcd'), {
      chunkSize: 4, uploadedParts: [], uploadPart,
      complete: async () => ({ attachment_id: 1 }),
      retries: 1,
    })

    expect(uploadPart).toHaveBeenCalledTimes(2)
  })
})
