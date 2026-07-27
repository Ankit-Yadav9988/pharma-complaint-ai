import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { SEVERITIES, STATUSES, severityTone, statusTone } from '../constants'
import {
  fetchComplaint,
  fetchComplaints,
  fetchStats,
  filterChanged,
} from '../store/registerSlice'
import ComplaintDrawer from './ComplaintDrawer'

const fmtDate = (value) =>
  value ? new Date(value).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

export default function ComplaintRegister() {
  const dispatch = useDispatch()
  const { items, stats, filters, listStatus, selected } = useSelector((s) => s.register)

  useEffect(() => {
    dispatch(fetchStats())
  }, [dispatch])

  useEffect(() => {
    const timer = setTimeout(() => dispatch(fetchComplaints(filters)), 220)
    return () => clearTimeout(timer)
  }, [dispatch, filters])

  const setFilter = (event) =>
    dispatch(filterChanged({ name: event.target.name, value: event.target.value }))

  return (
    <div className="page">
      <div className="stat-row">
        <div className="card stat">
          <div className="k">Total Complaints</div>
          <div className="v">{stats?.total ?? '—'}</div>
        </div>
        <div className="card stat">
          <div className="k">Open Critical</div>
          <div className="v" style={{ color: stats?.open_critical ? '#b91c1c' : '#15803d' }}>
            {stats?.open_critical ?? '—'}
          </div>
        </div>
        <div className="card stat">
          <div className="k">Pending Triage</div>
          <div className="v" style={{ color: '#b45309' }}>
            {stats?.by_status?.['Pending Triage'] ?? 0}
          </div>
        </div>
        <div className="card stat">
          <div className="k">Avg Completeness</div>
          <div className="v">{stats?.avg_completeness != null ? `${stats.avg_completeness}%` : '—'}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h1>Complaint Register</h1>
            <p>All logged complaints with their AI triage outcome</p>
          </div>
        </div>

        <div className="card-body" style={{ paddingBottom: 0 }}>
          <div className="toolbar">
            <input
              name="q"
              value={filters.q}
              onChange={setFilter}
              placeholder="Search by number, customer, product, batch or description…"
            />
            <select name="status" value={filters.status} onChange={setFilter}>
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select name="severity" value={filters.severity} onChange={setFilter}>
              <option value="">All severities</option>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        {listStatus === 'loading' && items.length === 0 ? (
          <div className="empty">
            <span className="spin" /> Loading register…
          </div>
        ) : items.length === 0 ? (
          <div className="empty">
            <span className="icon">📋</span>
            No complaints match your filters yet. Log one from the Intake screen.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="register">
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Customer</th>
                  <th>Product</th>
                  <th>Batch</th>
                  <th>Type</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id} onClick={() => dispatch(fetchComplaint(row.id))}>
                    <td className="mono">{row.complaint_number}</td>
                    <td>{row.customer_name ?? '—'}</td>
                    <td>{row.product_name ?? '—'}</td>
                    <td>{row.batch_number ?? '—'}</td>
                    <td>{row.complaint_type ?? '—'}</td>
                    <td>
                      {row.severity ? (
                        <span className={`badge ${severityTone(row.severity)}`}>{row.severity}</span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>
                      <span className={`badge ${statusTone(row.status)}`}>{row.status}</span>
                    </td>
                    <td>{fmtDate(row.complaint_date ?? row.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && <ComplaintDrawer />}
    </div>
  )
}
