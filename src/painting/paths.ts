export function paintingBaseUrl(paintingId: string): string {
  return `/data/paintings/${paintingId}`
}

export function paintingAssetUrl(paintingId: string, relativePath: string): string {
  const clean = relativePath.replace(/^\//, '')
  return `${paintingBaseUrl(paintingId)}/${clean}`
}
