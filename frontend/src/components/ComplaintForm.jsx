import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  COMPLAINT_SOURCES,
  COMPLAINT_TYPES,
  PRIORITIES,
  SEVERITIES,
  UNITS,
  severityTone,
} from '../constants'
import { dismissSaved, fieldChanged, resetForm, saveComplaint } from '../store/intakeSlice'

const AWAITING = ''

function Field({ name, label, children, filled, flash, confidence }) {
  const classes = ['field', filled && 'ai-filled', flash && 'ai-flash'].filter(Boolean).join(' ')
  return (
    <div className={classes}>
      <label htmlFor={name}>
        {label}
        {filled && confidence != null && (
          <span className="conf" title="Model confidence for this field">
            {Math.round(confidence * 100)}%
          </span>
        )}
      </label>
      {children}
    </div>
  )
}

export default function ComplaintForm() {
  const dispatch = useDispatch()
  const { form, analysis, status, saveStatus, saveError, savedComplaint } = useSelector(
    (s) => s.intake,
  )

  // Flash newly-populated fields once, right after an extraction lands.
  const [flashing, setFlashing] = useState(false)
  const previousStatus = useRef(status)
  useEffect(() => {
    if (previousStatus.current !== 'ready' && status === 'ready') {
      setFlashing(true)
      const timer = setTimeout(() => setFlashing(false), 1300)
      return () => clearTimeout(timer)
    }
    previousStatus.current = status
  }, [status])

  const confidence = analysis?.field_confidence ?? {}
  const isFilled = (name) => Boolean(analysis) && form[name] !== '' && form[name] != null

  const set = (event) =>
    dispatch(fieldChanged({ name: event.target.name, value: event.target.value }))

  const props = (name) => ({
    id: name,
    name,
    value: form[name] ?? '',
    onChange: set,
  })

  const fieldProps = (name) => ({
    name,
    filled: isFilled(name),
    flash: flashing && isFilled(name),
    confidence: confidence[name],
  })

  const placeholder = status === 'extracting' ? 'Extracting…' : AWAITING

  const onSave = async (event) => {
    event.preventDefault()
    await dispatch(saveComplaint())
  }

  return (
    <form className="card" onSubmit={onSave}>
      <div className="card-head">
        <div>
          <h1>Log Customer Complaint</h1>
          <p>API &amp; FDF Quality Assurance Module</p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          {form.severity && (
            <span className={`badge ${severityTone(form.severity)}`}>
              <span className="dot" />
              {form.severity}
            </span>
          )}
          <span className="badge badge-warn">Pending Triage</span>
        </div>
      </div>

      {savedComplaint && (
        <div style={{ padding: '12px 20px 0' }}>
          <div className="hint">
            <span>✓</span>
            <div style={{ flex: 1 }}>
              Complaint <strong>{savedComplaint.complaint_number}</strong> saved to the register with
              its full AI analysis.
            </div>
            <button
              type="button"
              className="chip"
              onClick={() => dispatch(dismissSaved())}
              style={{ padding: '2px 8px' }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {saveStatus === 'error' && (
        <div style={{ padding: '12px 20px 0' }}>
          <div className="hint error">
            <span>!</span>
            <div>{saveError}</div>
          </div>
        </div>
      )}

      {/* 1 ---------------------------------------------------------------- */}
      <section className="section">
        <div className="section-title">
          <span className="num">1</span> Origin &amp; Customer Details
        </div>
        <div className="grid-2">
          <Field {...fieldProps('complaint_source')} label="Complaint Source">
            <select {...props('complaint_source')}>
              <option value="">{placeholder}</option>
              {COMPLAINT_SOURCES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
          <Field {...fieldProps('customer_name')} label="Customer Name">
            <input {...props('customer_name')} placeholder={placeholder} />
          </Field>
          <Field {...fieldProps('customer_contact')} label="Customer Contact">
            <input {...props('customer_contact')} placeholder={placeholder} />
          </Field>
        </div>
      </section>

      {/* 2 ---------------------------------------------------------------- */}
      <section className="section">
        <div className="section-title">
          <span className="num">2</span> Product &amp; Batch Identification
        </div>
        <div className="grid-2">
          <Field {...fieldProps('product_name')} label="Product Name">
            <input {...props('product_name')} placeholder={placeholder} />
          </Field>
          <Field {...fieldProps('product_strength')} label="Product Strength / Grade">
            <input {...props('product_strength')} placeholder={placeholder} />
          </Field>
          <Field {...fieldProps('batch_number')} label="Batch / Lot Number">
            <input {...props('batch_number')} placeholder={placeholder} />
          </Field>
          <Field {...fieldProps('manufacturing_date')} label="Manufacturing Date">
            <input type="date" {...props('manufacturing_date')} />
          </Field>
          <Field {...fieldProps('expiry_date')} label="Expiry Date">
            <input type="date" {...props('expiry_date')} />
          </Field>
          <Field {...fieldProps('quantity_affected')} label="Quantity Affected">
            <div className="input-row">
              <input
                type="number"
                step="any"
                min="0"
                {...props('quantity_affected')}
                placeholder={placeholder}
              />
              <select {...props('quantity_unit')} aria-label="Unit">
                {UNITS.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </div>
          </Field>
        </div>
      </section>

      {/* 3 ---------------------------------------------------------------- */}
      <section className="section">
        <div className="section-title">
          <span className="num">3</span> Complaint Details
        </div>
        <div className="grid-2">
          <Field {...fieldProps('complaint_type')} label="Complaint Type">
            <select {...props('complaint_type')}>
              <option value="">{placeholder}</option>
              {COMPLAINT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </Field>
          <Field {...fieldProps('complaint_date')} label="Complaint Date">
            <input type="date" {...props('complaint_date')} />
          </Field>
        </div>
        <Field {...fieldProps('description')} label="Detailed Complaint Description">
          <textarea {...props('description')} rows={5} placeholder={placeholder} />
        </Field>
      </section>

      {/* 4 ---------------------------------------------------------------- */}
      <section className="section">
        <div className="section-title">
          <span className="num">4</span> Initial Assessment &amp; Priority
        </div>
        <div className="grid-2">
          <Field {...fieldProps('severity')} label="Initial Severity">
            <select {...props('severity')}>
              <option value="">{placeholder}</option>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
          <Field {...fieldProps('priority')} label="Priority">
            <select {...props('priority')}>
              <option value="">{placeholder}</option>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </section>

      <div className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={() => dispatch(resetForm())}>
          ↺ Reset Form
        </button>
        <div className="spacer" />
        <button type="submit" className="btn btn-primary" disabled={saveStatus === 'saving'}>
          {saveStatus === 'saving' ? <span className="spin" /> : '⬒'} Save Complaint
        </button>
      </div>
    </form>
  )
}
