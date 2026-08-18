export interface ChunkUploadFile {
  name: string
  type: string
  size: number
  slice(start: number, end: number): Blob
}

export function shouldUseChunkUpload(files: Array<Pick<ChunkUploadFile, 'size'>>, threshold: number) {
  return files.some((file) => file.size >= threshold)
}

export async function sha256(blob: Blob) {
  const digest = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer())
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

export async function uploadFileInChunks(
  file: ChunkUploadFile,
  options: {
    chunkSize: number
    uploadedParts: number[]
    uploadPart(index: number, blob: Blob, sha256: string): Promise<void>
    complete(): Promise<{ attachment_id: number }>
    onProgress?(percent: number): void
    retries?: number
  },
) {
  const partCount = Math.ceil(file.size / options.chunkSize)
  const uploaded = new Set(options.uploadedParts)
  const reportProgress = () => options.onProgress?.(Math.round(uploaded.size / partCount * 100))
  reportProgress()
  for (let index = 0; index < partCount; index += 1) {
    if (uploaded.has(index)) continue
    const chunk = file.slice(index * options.chunkSize, Math.min(file.size, (index + 1) * options.chunkSize))
    const digest = await sha256(chunk)
    let lastError: unknown
    for (let attempt = 0; attempt <= (options.retries ?? 2); attempt += 1) {
      try {
        await options.uploadPart(index, chunk, digest)
        lastError = undefined
        break
      } catch (error) {
        lastError = error
      }
    }
    if (lastError) throw lastError
    uploaded.add(index)
    reportProgress()
  }
  return options.complete()
}
