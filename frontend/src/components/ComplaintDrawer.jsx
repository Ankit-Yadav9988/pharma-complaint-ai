import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api/client'
import { STATUSES, severityTone, statusTone } from '../constants'
import {
  fetchComplaint,
  fetchStats,
  removeComplaint,
  selectionCleared,
  updateStatus,
} from '../store/registerSlice'
import AIInsights from './AIInsights'

const fmt = (value) => (value == null || value === '' ? '—' : String(value))

export default function ComplaintDrawer() {
  const dispatch = useDispatch()
  const { selected } = useSelector((s) => s.register)
  const [reanalysing, setReanalysing] = useState(false)

  if (!selected) return null

  const analysis = selected.latest_analysis

  const close = () => dispatch(selectionCleared())

  const onStatusChange = async (event) => {
    await dispatch(updateStatus({ id: selected.id, status: event.target.value }))
    dispatch(fetchStats())
  }

  const onReanalyse = async () => {
    setReanalysing(true)
    try {
      await api.reanalyze(selected.id)
      await dispatch(fetchComplaint(selected.id))
    } finally {
      setReanalysing(false)
    }
  }

  const onDelete = async () => {
    await dispatch(removeComplaint(selected.id))
    dispatch(fetchStats())
  }

  return (
    <div className="drawer-backdrop" onClick={close}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{selected.complaint_number}</h2>
            <p>
              {fmt(selected.product_name)}
              {selected.batch_number ? ` · Batch ${selected.batch_number}` : ''}
            </p>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
            {selected.severity && (
              <span className={`badge ${severityTone(selected.severity)}`}>{selected.severity}</span>
            )}
            <span className={`badge ${statusTone(selected.status)}`}>{selected.status}</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={close}>
              ✕
            </button>
          </div>
        </div>

        <div className="drawer-content">
          <div className="card">
            <div className="card-body">
              <div className="kv-grid">
                {[
                  ['Complaint Source', selected.complaint_source],
                  ['Customer', selected.customer_name],
                  ['Contact', selected.customer_contact],
                  ['Product', selected.product_name],
                  ['Strength / Grade', selected.product_strength],
                  ['Batch / Lot', selected.batch_number],
                  ['Manufactured', selected.manufacturing_date],
                  ['Expiry', selected.expiry_date],
                  [
                    'Quantity Affected',
                    selected.quantity_affected != null
                      ? `${selected.quantity_affected} ${selected.quantity_unit ?? ''}`.trim()
                      : null,
                  ],
                  ['Complaint Type', selected.complaint_type],
                  ['Complaint Date', selected.complaint_date],
                  ['Priority', selected.priority],
                ].map(([key, value]) => (
                  <div className="kv" key={key}>
                    <div className="k">{key}</div>
                    <div className="v">{fmt(value)}</div>
                  </div>
                ))}
              </div>

              {selected.description && (
                <div style={{ marginTop: 16 }}>
                  <div className="k" style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--ink-500)' }}>
                    Description
                  </div>
                  <p style={{ margin: '4px 0 0', lineHeight: 1.6 }}>{selected.description}</p>
                </div>
              )}
            </div>

            <div className="form-actions">
              <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--ink-700)' }}>
                Status
              </label>
              <select
                value={selected.status}
                onChange={onStatusChange}
                style={{
                  font: 'inherit',
                  fontSize: 13,
                  padding: '6px 9px',
                  border: '1px solid var(--ink-300)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <div className="spacer" />
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={onReanalyse}
                disabled={reanalysing}
              >
                {reanalysing ? <span className="spin" /> : '✦'} Re-run AI analysis
              </button>
              <button type="button" className="btn btn-danger btn-sm" onClick={onDelete}>
                Delete
              </button>
            </div>
          </div>

          {analysis ? (
            <AIInsights analysis={analysis} />
          ) : (
            <div className="card">
              <div className="empty">
                No AI analysis stored for this complaint. Use “Re-run AI analysis” to generate one.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
