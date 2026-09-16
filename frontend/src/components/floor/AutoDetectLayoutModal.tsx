import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import { useFloor } from '../../context/FloorContext'
import { useGlobalPointerDrag, type DragRect } from '../../lib/useGlobalPointerDrag'
import type { CameraLayoutPreview, DraftTable, Floor, TableShape } from '../../types'

const TEAL = '#0e8f9c'
const SELECTED = '#2563eb'
const CANVAS_MAX_W = 660

interface Props {
  floor: Floor
  onClose: () => void
}

/** One draggable/resizable detected box, in display-space pixels. Reuses the
 *  same pointer-drag hook the manual layout editor uses. */
function DraftBox({
  rectDisp,
  label,
  selected,
  onSelect,
  onCommit,
}: {
  rectDisp: DragRect
  label: string
  selected: boolean
  onSelect: () => void
  onCommit: (r: DragRect) => void
}) {
  const [live, setLive] = useState(rectDisp)
  useEffect(() => {
    setLive(rectDisp)
  }, [rectDisp.x, rectDisp.y, rectDisp.width, rectDisp.height])
  const { startMove, startResizeSE } = useGlobalPointerDrag(live, setLive, onCommit, true)

  return (
    <div
      onPointerDown={(e) => {
        e.stopPropagation()
        onSelect()
        startMove(e)
      }}
      style={{
        position: 'absolute',
        left: live.x,
        top: live.y,
        width: live.width,
        height: live.height,
        border: `2px solid ${selected ? SELECTED : TEAL}`,
        background: selected ? 'rgba(37,99,235,0.16)' : 'rgba(14,143,156,0.12)',
        borderRadius: 6,
        cursor: 'move',
        boxSizing: 'border-box',
        zIndex: selected ? 3 : 2,
      }}
    >
      <span
        style={{
          position: 'absolute',
          top: -10,
          left: 3,
          fontSize: 11,
          fontWeight: 700,
          background: selected ? SELECTED : TEAL,
          color: '#fff',
          padding: '1px 6px',
          borderRadius: 4,
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </span>
      <span
        onPointerDown={(e) => {
          e.stopPropagation()
          onSelect()
          startResizeSE(e)
        }}
        style={{
          position: 'absolute',
          right: -6,
          bottom: -6,
          width: 13,
          height: 13,
          borderRadius: 3,
          background: SELECTED,
          border: '2px solid #fff',
          cursor: 'nwse-resize',
        }}
      />
    </div>
  )
}

export function AutoDetectLayoutModal({ floor, onClose }: Props) {
  const { refresh } = useFloor()
  const [step, setStep] = useState<'source' | 'review'>('source')

  const knownCameras = useMemo(() => {
    const seen = new Set<string>()
    const list: string[] = []
    for (const t of floor.tables) {
      if (t.cameraUrl && !seen.has(t.cameraUrl)) {
        seen.add(t.cameraUrl)
        list.push(t.cameraUrl)
      }
    }
    return list
  }, [floor.tables])

  const [cameraUrl, setCameraUrl] = useState(
    knownCameras[0] ?? '/app/camera_uploads/table_t-1.mp4',
  )
  const [detecting, setDetecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [cameras, setCameras] = useState<CameraLayoutPreview[]>([])
  const [drafts, setDrafts] = useState<DraftTable[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [replace, setReplace] = useState(true)
  const [applying, setApplying] = useState(false)

  const scale = Math.min(CANVAS_MAX_W / floor.width, 1)
  const dispW = floor.width * scale
  const dispH = floor.height * scale
  const sectionId = floor.sections[0]?.id ?? ''

  async function handleDetect() {
    const url = cameraUrl.trim()
    if (!url) {
      setError('Enter a camera stream URL or video path first.')
      return
    }
    setDetecting(true)
    setError(null)
    try {
      const result = await api.autoDetectLayout([url])
      setCameras(result.cameras)
      setDrafts(result.draftTables)
      setSelected(result.draftTables.length ? 0 : null)
      setStep('review')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not detect a layout from that camera.')
    } finally {
      setDetecting(false)
    }
  }

  function updateDraft(index: number, patch: Partial<DraftTable>) {
    setDrafts((prev) => prev.map((d, i) => (i === index ? { ...d, ...patch } : d)))
  }

  function deleteDraft(index: number) {
    setDrafts((prev) => prev.filter((_, i) => i !== index))
    setSelected(null)
  }

  function addDraft() {
    const used = new Set(drafts.map((d) => d.number))
    let n = 1
    while (used.has(`T${n}`)) n += 1
    const next: DraftTable = {
      number: `T${n}`,
      capacity: 4,
      type: 'STANDARD',
      shape: 'RECTANGLE',
      sectionId,
      x: floor.width / 2 - 60,
      y: floor.height / 2 - 45,
      width: 120,
      height: 90,
      rotation: 0,
      cameraUrl: cameraUrl.trim() || null,
      roiCoords: null,
      confidence: 0,
    }
    setDrafts((prev) => [...prev, next])
    setSelected(drafts.length)
  }

  async function handleApply() {
    if (!drafts.length) {
      setError('No tables to apply. Add at least one or re-detect.')
      return
    }
    setApplying(true)
    setError(null)
    try {
      await api.applyDetectedLayout(drafts, replace)
      await refresh()
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not apply the layout.')
      setApplying(false)
    }
  }

  const sel = selected != null ? drafts[selected] : null

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal" style={{ maxWidth: step === 'review' ? 760 : 520, width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
          <div>
            <h3 style={{ margin: 0 }}>Auto-Detect Layout from Camera</h3>
            <p className="muted" style={{ margin: '4px 0 0', fontSize: 13 }}>
              {step === 'source'
                ? 'Point at a ceiling camera and detect the tables automatically.'
                : 'Review the detected tables — drag, resize, edit, or delete — then apply.'}
            </p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {step === 'source' && (
          <div>
            <label className="field">
              <span>Camera stream URL or video path</span>
              <input
                className="input"
                value={cameraUrl}
                onChange={(e) => setCameraUrl(e.target.value)}
                placeholder="rtsp://…  or  /app/camera_uploads/floor.mp4"
              />
            </label>
            {knownCameras.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                {knownCameras.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setCameraUrl(c)}
                    style={{
                      fontSize: 12,
                      padding: '4px 10px',
                      borderRadius: 999,
                      border: '1px solid #dbe3ef',
                      background: cameraUrl === c ? '#e6f6f8' : '#fff',
                      color: '#0e6d78',
                      cursor: 'pointer',
                      maxWidth: 260,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={c}
                  >
                    {c}
                  </button>
                ))}
              </div>
            )}
            <p className="muted" style={{ fontSize: 12.5, marginTop: 10 }}>
              We sample several frames and use the trained table model (with a classical fallback)
              to find each table. Nothing is saved until you review and apply.
            </p>
            {error && <p className="form-error" style={{ marginTop: 8 }}>{error}</p>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button type="button" className="btn btn-primary" onClick={handleDetect} disabled={detecting}>
                {detecting ? 'Detecting…' : 'Detect tables'}
              </button>
            </div>
          </div>
        )}

        {step === 'review' && (
          <div>
            <p className="muted" style={{ fontSize: 13, margin: '0 0 10px' }}>
              Detected <strong style={{ color: '#0f172a' }}>{drafts.length}</strong> table{drafts.length === 1 ? '' : 's'}
              {cameras[0] ? <> · method <code>{cameras[0].method}</code></> : null}. Positions are mapped onto the floor canvas.
            </p>

            {/* Interactive canvas — draggable/resizable detected boxes */}
            <div
              onPointerDown={() => setSelected(null)}
              style={{
                position: 'relative',
                width: dispW,
                height: dispH,
                maxWidth: '100%',
                margin: '0 auto',
                background:
                  'repeating-linear-gradient(0deg,#f4f7fb,#f4f7fb 23px,#eef2f8 24px),repeating-linear-gradient(90deg,#f4f7fb,#f4f7fb 23px,#eef2f8 24px)',
                border: '1px solid #dbe3ef',
                borderRadius: 8,
                overflow: 'hidden',
                touchAction: 'none',
              }}
            >
              {drafts.map((d, i) => (
                <DraftBox
                  key={i}
                  label={`${d.number} · ${d.capacity}`}
                  selected={selected === i}
                  rectDisp={{ x: d.x * scale, y: d.y * scale, width: d.width * scale, height: d.height * scale }}
                  onSelect={() => setSelected(i)}
                  onCommit={(r) =>
                    updateDraft(i, {
                      x: Math.round(r.x / scale),
                      y: Math.round(r.y / scale),
                      width: Math.round(r.width / scale),
                      height: Math.round(r.height / scale),
                    })
                  }
                />
              ))}
            </div>

            {/* Selected-table editor */}
            <div style={{ marginTop: 12, display: 'flex', alignItems: 'flex-end', gap: 10, flexWrap: 'wrap' }}>
              {sel ? (
                <>
                  <label className="field" style={{ margin: 0, width: 90 }}>
                    <span>Number</span>
                    <input
                      className="input"
                      value={sel.number}
                      onChange={(e) => updateDraft(selected!, { number: e.target.value })}
                    />
                  </label>
                  <label className="field" style={{ margin: 0, width: 90 }}>
                    <span>Seats</span>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      value={sel.capacity}
                      onChange={(e) => updateDraft(selected!, { capacity: Math.max(1, Number(e.target.value) || 1) })}
                    />
                  </label>
                  <label className="field" style={{ margin: 0, width: 130 }}>
                    <span>Shape</span>
                    <select
                      className="input"
                      value={sel.shape}
                      onChange={(e) => updateDraft(selected!, { shape: e.target.value as TableShape })}
                    >
                      <option value="RECTANGLE">Rectangle</option>
                      <option value="CIRCLE">Circle</option>
                    </select>
                  </label>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => deleteDraft(selected!)}>
                    Delete
                  </button>
                </>
              ) : (
                <p className="muted" style={{ fontSize: 13, margin: 0 }}>Select a box to edit its number, seats, or shape.</p>
              )}
              <button type="button" className="btn btn-secondary btn-sm" style={{ marginLeft: 'auto' }} onClick={addDraft}>
                + Add missed table
              </button>
            </div>

            {/* Camera reference snapshot */}
            {cameras[0]?.previewImage && (
              <details style={{ marginTop: 12 }}>
                <summary style={{ fontSize: 13, color: '#5a6b86', cursor: 'pointer' }}>
                  Show camera snapshot with detections
                </summary>
                <img
                  src={cameras[0].previewImage}
                  alt="Camera detections"
                  style={{ display: 'block', width: '100%', marginTop: 8, borderRadius: 8, border: '1px solid #dbe3ef' }}
                />
              </details>
            )}

            {/* Apply controls */}
            <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                <input type="radio" checked={replace} onChange={() => setReplace(true)} />
                Replace floor
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                <input type="radio" checked={!replace} onChange={() => setReplace(false)} />
                Add to existing
              </label>
            </div>
            {error && <p className="form-error" style={{ marginTop: 8 }}>{error}</p>}
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginTop: 14 }}>
              <button type="button" className="btn btn-ghost" onClick={() => setStep('source')}>← Back</button>
              <button type="button" className="btn btn-primary" onClick={handleApply} disabled={applying}>
                {applying ? 'Applying…' : replace ? `Apply — replace with ${drafts.length}` : `Add ${drafts.length} tables`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
