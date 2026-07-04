import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { FloorPlanMiniMap } from '../components/floor/FloorPlanMiniMap'
import { useFloor } from '../context/FloorContext'
import type { CameraRoiSuggestion, RectBounds } from '../types'

const MAX_DISPLAY_WIDTH = 720
const DEFAULT_BOX_SIZE = 160
const LASSO_PADDING = 18

interface LassoPoint {
  x: number
  y: number
}

function isUsableAutoRoi(roi: RectBounds, frameWidth: number, frameHeight: number): boolean {
  const areaRatio = (roi.width * roi.height) / (frameWidth * frameHeight)
  if (areaRatio > 0.32) return false
  if (roi.width > frameWidth * 0.78 || roi.height > frameHeight * 0.78) return false
  if (roi.y < frameHeight * 0.06) return false
  if (roi.x <= 4 && roi.y <= 4) return false
  if (roi.x + roi.width >= frameWidth - 4 && roi.y + roi.height >= frameHeight - 4) return false
  return true
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function boundsFromLasso(points: LassoPoint[], width: number, height: number): RectBounds | null {
  if (!points.length) return null
  const minX = Math.min(...points.map((point) => point.x))
  const maxX = Math.max(...points.map((point) => point.x))
  const minY = Math.min(...points.map((point) => point.y))
  const maxY = Math.max(...points.map((point) => point.y))
  const x = clamp(minX - LASSO_PADDING, 0, width)
  const y = clamp(minY - LASSO_PADDING, 0, height)
  const right = clamp(maxX + LASSO_PADDING, x + 40, width)
  const bottom = clamp(maxY + LASSO_PADDING, y + 40, height)
  return {
    x,
    y,
    width: right - x,
    height: bottom - y,
  }
}

function lassoFromRect(rect: RectBounds): LassoPoint[] {
  return [
    { x: rect.x, y: rect.y },
    { x: rect.x + rect.width, y: rect.y },
    { x: rect.x + rect.width, y: rect.y + rect.height },
    { x: rect.x, y: rect.y + rect.height },
  ]
}

export function CameraSetupPage() {
  const { floor, updateTable, refresh } = useFloor()
  const tables = floor?.tables ?? []

  const [selectedTableId, setSelectedTableId] = useState<string | null>(null)
  const selectedTable = tables.find((t) => t.id === selectedTableId) ?? null

  // Camera URL
  const [cameraUrl, setCameraUrl] = useState('')
  const [savingUrl, setSavingUrl] = useState(false)
  const [urlSaved, setUrlSaved] = useState(false)
  const [urlError, setUrlError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Snapshot + ROI
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null)
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null)
  const [displayWidth, setDisplayWidth] = useState(MAX_DISPLAY_WIDTH)
  const [loadingSnapshot, setLoadingSnapshot] = useState(false)
  const [snapshotError, setSnapshotError] = useState<string | null>(null)
  const [autoDetecting, setAutoDetecting] = useState(false)
  const [autoDetectError, setAutoDetectError] = useState<string | null>(null)
  const [autoSuggestion, setAutoSuggestion] = useState<CameraRoiSuggestion | null>(null)
  const [box, setBox] = useState<RectBounds>({ x: 40, y: 40, width: DEFAULT_BOX_SIZE, height: DEFAULT_BOX_SIZE })
  const [lassoPoints, setLassoPoints] = useState<LassoPoint[]>([])
  const [lassoing, setLassoing] = useState(false)
  const [hasDraftRoi, setHasDraftRoi] = useState(false)
  const [savingRoi, setSavingRoi] = useState(false)
  const [roiSaved, setRoiSaved] = useState(false)

  const objectUrlRef = useRef<string | null>(null)
  const imageFrameRef = useRef<HTMLDivElement>(null)
  const boxRef = useRef(box)
  const lassoPointsRef = useRef<LassoPoint[]>([])

  useEffect(() => {
    boxRef.current = box
  }, [box])

  useEffect(() => {
    lassoPointsRef.current = lassoPoints
  }, [lassoPoints])

  // Clean up blob URL on unmount
  useEffect(() => {
    return () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    }
  }, [])

  // When a different table is selected, reset everything
  useEffect(() => {
    setCameraUrl(selectedTable?.cameraUrl ?? '')
    setSnapshotUrl(null)
    setNaturalSize(null)
    setSnapshotError(null)
    setAutoDetectError(null)
    setUrlError(null)
    setUrlSaved(false)
    setRoiSaved(false)
    setUploadedFilename(null)
    setAutoSuggestion(null)
    setLassoPoints([])
    lassoPointsRef.current = []
    setHasDraftRoi(false)
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = null
    }
  }, [selectedTableId])

  async function handleSaveCameraUrl() {
    if (!selectedTable) return
    setSavingUrl(true)
    setUrlError(null)
    setUrlSaved(false)
    try {
      await updateTable(selectedTable.id, { cameraUrl: cameraUrl.trim() || null })
      setUrlSaved(true)
    } catch (e) {
      setUrlError(e instanceof Error ? e.message : 'Could not save camera URL')
    } finally {
      setSavingUrl(false)
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !selectedTable) return
    setUploading(true)
    setUrlError(null)
    setUrlSaved(false)
    setUploadedFilename(null)
    try {
      const result = await api.uploadCameraVideo(selectedTable.id, file)
      setCameraUrl(result.cameraUrl)
      setUploadedFilename(result.filename)
      setUrlSaved(true)
    } catch (err) {
      setUrlError(err instanceof Error ? err.message : 'Could not upload video')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleLoadSnapshot() {
    if (!selectedTable) return
    setLoadingSnapshot(true)
    setSnapshotError(null)
    setRoiSaved(false)
    try {
      const url = await api.getCameraSnapshot(selectedTable.id)
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = url
      setSnapshotUrl(url)
    } catch (e) {
      setSnapshotError(e instanceof Error ? e.message : 'Could not load a snapshot')
    } finally {
      setLoadingSnapshot(false)
    }
  }

  async function handleAutoDetectRoi() {
    if (!selectedTable) return
    setAutoDetecting(true)
    setAutoDetectError(null)
    setRoiSaved(false)
    try {
      const suggestion = await api.autoDetectCameraRoi(selectedTable.id)
      const candidates = suggestion.candidates.filter((candidate) =>
        isUsableAutoRoi(candidate, suggestion.frameWidth, suggestion.frameHeight),
      )
      if (!isUsableAutoRoi(suggestion.roiCoords, suggestion.frameWidth, suggestion.frameHeight) || candidates.length === 0) {
        throw new Error('Auto-detect could not find a reliable table box. Please adjust the ROI manually for this clip.')
      }
      const safeSuggestion = {
        ...suggestion,
        roiCoords: candidates[0],
        candidates,
      }
      setAutoSuggestion(safeSuggestion)
      const scale = displayWidth / safeSuggestion.frameWidth
      const detectedBox = {
        x: safeSuggestion.roiCoords.x * scale,
        y: safeSuggestion.roiCoords.y * scale,
        width: safeSuggestion.roiCoords.width * scale,
        height: safeSuggestion.roiCoords.height * scale,
      }
      boxRef.current = detectedBox
      setBox(detectedBox)
      const detectedLasso = lassoFromRect(detectedBox)
      lassoPointsRef.current = detectedLasso
      setLassoPoints(detectedLasso)
      setHasDraftRoi(true)
      if (!snapshotUrl) {
        await handleLoadSnapshot()
      }
    } catch (e) {
      setAutoDetectError(e instanceof Error ? e.message : 'Could not auto-detect the ROI')
    } finally {
      setAutoDetecting(false)
    }
  }

  function handleImageLoaded(img: HTMLImageElement) {
    const natural = { width: img.naturalWidth, height: img.naturalHeight }
    setNaturalSize(natural)
    const shownWidth = Math.min(MAX_DISPLAY_WIDTH, natural.width)
    setDisplayWidth(shownWidth)
    const scale = shownWidth / natural.width

    if (autoSuggestion) {
      const detectedBox = {
        x: autoSuggestion.roiCoords.x * scale,
        y: autoSuggestion.roiCoords.y * scale,
        width: autoSuggestion.roiCoords.width * scale,
        height: autoSuggestion.roiCoords.height * scale,
      }
      boxRef.current = detectedBox
      setBox(detectedBox)
      const detectedLasso = lassoFromRect(detectedBox)
      lassoPointsRef.current = detectedLasso
      setLassoPoints(detectedLasso)
      setHasDraftRoi(true)
      return
    }

    if (selectedTable?.roiCoords) {
      const savedBox = {
        x: selectedTable.roiCoords.x * scale,
        y: selectedTable.roiCoords.y * scale,
        width: selectedTable.roiCoords.width * scale,
        height: selectedTable.roiCoords.height * scale,
      }
      const savedLasso = lassoFromRect(savedBox)
      boxRef.current = savedBox
      setBox(savedBox)
      setLassoPoints(savedLasso)
      lassoPointsRef.current = savedLasso
      setHasDraftRoi(false)
    } else {
      const defaultBox = {
        x: shownWidth / 2 - DEFAULT_BOX_SIZE / 2,
        y: (shownWidth * (natural.height / natural.width)) / 2 - DEFAULT_BOX_SIZE / 2,
        width: DEFAULT_BOX_SIZE,
        height: DEFAULT_BOX_SIZE,
      }
      boxRef.current = defaultBox
      setBox(defaultBox)
      setLassoPoints([])
      lassoPointsRef.current = []
      setHasDraftRoi(false)
    }
  }

  function applyLassoPoint(clientX: number, clientY: number) {
    const frame = imageFrameRef.current
    if (!frame || !naturalSize) return
    const rect = frame.getBoundingClientRect()
    const frameWidth = rect.width
    const frameHeight = rect.height
    const nextPoint = {
      x: clamp(clientX - rect.left, 0, frameWidth),
      y: clamp(clientY - rect.top, 0, frameHeight),
    }
    setLassoPoints((current) => {
      const previous = current[current.length - 1]
      if (previous && Math.hypot(previous.x - nextPoint.x, previous.y - nextPoint.y) < 8) {
        return current
      }
      const next = [...current, nextPoint]
      lassoPointsRef.current = next
      const nextBounds = boundsFromLasso(next, frameWidth, frameHeight)
      if (nextBounds) {
        boxRef.current = nextBounds
        setBox(nextBounds)
        setHasDraftRoi(true)
      }
      return next
    })
    setRoiSaved(false)
  }

  function handleLassoStart(e: React.PointerEvent<HTMLDivElement>) {
    if (!naturalSize) return
    e.preventDefault()
    e.stopPropagation()
    e.currentTarget.setPointerCapture(e.pointerId)
    setLassoing(true)
    setLassoPoints([])
    lassoPointsRef.current = []
    setHasDraftRoi(false)
    applyLassoPoint(e.clientX, e.clientY)
  }

  function handleLassoMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!lassoing) return
    applyLassoPoint(e.clientX, e.clientY)
  }

  function handleLassoEnd(e: React.PointerEvent<HTMLDivElement>) {
    if (!lassoing) return
    e.currentTarget.releasePointerCapture(e.pointerId)
    setLassoing(false)
  }

  function clearLasso() {
    setLassoPoints([])
    lassoPointsRef.current = []
    setHasDraftRoi(false)
    if (!naturalSize) return
    const defaultBox = {
      x: displayWidth / 2 - DEFAULT_BOX_SIZE / 2,
      y: displayHeight / 2 - DEFAULT_BOX_SIZE / 2,
      width: DEFAULT_BOX_SIZE,
      height: DEFAULT_BOX_SIZE,
    }
    boxRef.current = defaultBox
    setBox(defaultBox)
    setRoiSaved(false)
  }

  async function handleSaveRoi() {
    if (!naturalSize || !selectedTable) return
    if (!hasDraftRoi && lassoPointsRef.current.length === 0) {
      setSnapshotError('Draw a lasso around the table before saving the ROI.')
      return
    }
    const frame = imageFrameRef.current
    const renderedWidth = frame?.getBoundingClientRect().width || displayWidth
    setSavingRoi(true)
    setSnapshotError(null)
    try {
      const scale = naturalSize.width / renderedWidth
      const currentBox = boxRef.current
      const realRoi: RectBounds = {
        x: Math.round(currentBox.x * scale),
        y: Math.round(currentBox.y * scale),
        width: Math.round(currentBox.width * scale),
        height: Math.round(currentBox.height * scale),
      }
      await updateTable(selectedTable.id, { roiCoords: realRoi })
      await refresh()
      setHasDraftRoi(false)
      setRoiSaved(true)
    } catch (e) {
      setSnapshotError(e instanceof Error ? e.message : 'Could not save the ROI')
    } finally {
      setSavingRoi(false)
    }
  }

  const displayHeight = naturalSize ? displayWidth * (naturalSize.height / naturalSize.width) : 0
  const canSaveRoi = Boolean(hasDraftRoi || lassoPoints.length > 0 || autoSuggestion)

  return (
    <div className="camera-setup-page">
      <h2 style={{ margin: '0 0 4px' }}>Camera Setup</h2>
      <p className="muted" style={{ margin: '0 0 24px', fontSize: 14 }}>
        Configure camera streams and lasso regions of interest for each table.
        Only detections inside the saved region will count toward that table.
      </p>

      {/* Table selector */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Select a table
        </label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {tables.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setSelectedTableId(t.id)}
              style={{
                padding: '8px 16px',
                borderRadius: 8,
                border: selectedTableId === t.id ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                background: selectedTableId === t.id ? '#eff6ff' : '#fff',
                fontWeight: selectedTableId === t.id ? 600 : 400,
                cursor: 'pointer',
                fontSize: 14,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              T{t.number}
              {t.cameraUrl && (
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} title="Camera configured" />
              )}
            </button>
          ))}
        </div>
      </div>

      {!selectedTable && (
        <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', border: '2px dashed #e2e8f0', borderRadius: 12 }}>
          Select a table above to configure its camera and ROI
        </div>
      )}

      {selectedTable && (
        <div className="camera-setup-card">
          <div className="camera-setup-layout">
            <div className="camera-setup-main">
              <h3 style={{ margin: '0 0 16px', fontSize: 18 }}>
                Table {selectedTable.number}
                <span style={{ fontSize: 13, fontWeight: 400, color: '#94a3b8', marginLeft: 8 }}>
                  {selectedTable.type} · {selectedTable.shape} · Seats {selectedTable.capacity}
                </span>
              </h3>

              {/* Step 1 — Camera source */}
              <div style={{ marginBottom: 24 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  1. Camera source
                </label>

                {/* Upload option */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleFileUpload}
                    style={{ display: 'none' }}
                    id="camera-upload"
                  />
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                  >
                    {uploading ? 'Uploading…' : 'Upload video file'}
                  </button>
                  {uploadedFilename && (
                    <span style={{ fontSize: 13, color: '#16a34a' }}>
                      Uploaded: {uploadedFilename} ✓
                    </span>
                  )}
                </div>

                {/* URL option */}
                <p style={{ fontSize: 13, color: '#94a3b8', margin: '0 0 6px' }}>Or enter a stream URL / webcam index:</p>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="text"
                    className="input"
                    style={{ flex: 1 }}
                    placeholder="rtsp://... or 0 for webcam"
                    value={cameraUrl}
                    onChange={(e) => { setCameraUrl(e.target.value); setUrlSaved(false) }}
                  />
                  <button type="button" className="btn btn-secondary" onClick={handleSaveCameraUrl} disabled={savingUrl}>
                    {savingUrl ? 'Saving…' : 'Enter'}
                  </button>
                </div>
                {urlError && <p className="form-error">{urlError}</p>}
                {urlSaved && !uploadedFilename && <p style={{ color: '#16a34a', fontSize: 13, marginTop: 4 }}>Camera URL saved ✓</p>}
              </div>

              {/* Step 2 — Snapshot + ROI */}
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  2. Lasso the region of interest
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleLoadSnapshot}
                    disabled={loadingSnapshot}
                  >
                    {loadingSnapshot ? 'Loading…' : snapshotUrl ? 'Reload snapshot' : 'Load snapshot'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleAutoDetectRoi}
                    disabled={autoDetecting}
                  >
                    {autoDetecting ? 'Detecting…' : 'Auto-detect tables'}
                  </button>
                </div>
                {snapshotUrl && naturalSize && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
                    {lassoPoints.length > 0 && (
                      <button type="button" className="btn btn-secondary btn-sm" onClick={clearLasso}>
                        Clear lasso
                      </button>
                    )}
                  </div>
                )}
                {snapshotError && <p className="form-error" style={{ marginTop: 8 }}>{snapshotError}</p>}
                {autoDetectError && <p className="form-error" style={{ marginTop: 8 }}>{autoDetectError}</p>}
                {autoSuggestion && (
                  <p className="muted" style={{ marginTop: 8, fontSize: 13 }}>
                    Auto-detect ran on {autoSuggestion.sampledFrames} frames using {autoSuggestion.method}, confidence {Math.round(autoSuggestion.confidence * 100)}%.
                  </p>
                )}

                {snapshotUrl && (
                  <div
                    ref={imageFrameRef}
                    onPointerDown={handleLassoStart}
                    onPointerMove={handleLassoMove}
                    onPointerUp={handleLassoEnd}
                    onPointerCancel={handleLassoEnd}
                    style={{
                      position: 'relative',
                      marginTop: 12,
                      width: displayWidth,
                      height: displayHeight || undefined,
                      maxWidth: '100%',
                      userSelect: 'none',
                      borderRadius: 8,
                      overflow: 'hidden',
                      border: '1px solid #e2e8f0',
                      touchAction: 'none',
                      cursor: 'crosshair',
                    }}
                  >
                    <img
                      src={snapshotUrl}
                      alt="Camera snapshot"
                      width={displayWidth}
                      style={{ display: 'block', maxWidth: '100%' }}
                      onLoad={(e) => handleImageLoaded(e.currentTarget)}
                    />

                    {lassoPoints.length > 0 && (
                      <svg
                        aria-hidden="true"
                        viewBox={`0 0 ${displayWidth} ${displayHeight}`}
                        style={{
                          position: 'absolute',
                          inset: 0,
                          width: '100%',
                          height: '100%',
                          pointerEvents: 'none',
                        }}
                      >
                        <polygon
                          points={lassoPoints.map((point) => `${point.x},${point.y}`).join(' ')}
                          fill="rgba(34, 197, 94, 0.16)"
                          stroke="none"
                        />
                        <polyline
                          points={lassoPoints.map((point) => `${point.x},${point.y}`).join(' ')}
                          fill="none"
                          stroke="#16a34a"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </div>
                )}

                {snapshotUrl && naturalSize && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
                    <button type="button" className="btn btn-primary" onClick={handleSaveRoi} disabled={savingRoi || !canSaveRoi}>
                      {savingRoi ? 'Saving…' : 'Save ROI'}
                    </button>
                    {roiSaved && <span style={{ color: '#16a34a', fontSize: 13 }}>Saved ✓</span>}
                  </div>
                )}
              </div>
            </div>

            {floor && (
              <FloorPlanMiniMap
                floor={floor}
                selectedTableId={selectedTableId}
                onSelectTable={setSelectedTableId}
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
