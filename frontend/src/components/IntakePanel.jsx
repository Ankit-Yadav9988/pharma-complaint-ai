import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api/client'
import { askAssistant, messageAdded, runExtraction } from '../store/intakeSlice'

const SUGGESTIONS = [
  'What is the risk assessment?',
  'What is missing from this record?',
  'Summarise this complaint',
]

export default function IntakePanel() {
  const dispatch = useDispatch()
  const {
    status,
    progress,
    currentNode,
    completedNodes,
    error,
    capabilities,
    messages,
    chatPending,
    analysis,
    rawText,
    filename,
  } = useSelector((s) => s.intake)

  const [dragging, setDragging] = useState(false)
  const [pasted, setPasted] = useState('')
  const [question, setQuestion] = useState('')
  const [samples, setSamples] = useState([])
  const fileInput = useRef(null)
  const chatEnd = useRef(null)

  const busy = status === 'extracting'

  useEffect(() => {
    api.listSamples().then(setSamples).catch(() => setSamples([]))
  }, [])

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages, chatPending])

  const handleFile = (file) => {
    if (!file || busy) return
    dispatch(runExtraction({ file }))
  }

  const onDrop = (event) => {
    event.preventDefault()
    setDragging(false)
    handleFile(event.dataTransfer.files?.[0])
  }

  const onExtractPasted = () => {
    if (pasted.trim().length < 10 || busy) return
    dispatch(runExtraction({ text: pasted, filename: 'pasted-complaint.txt' }))
  }

  const onLoadSample = async (sample) => {
    if (busy) return
    try {
      const { text } = await api.readSample(sample.filename)
      setPasted(text)
      dispatch(runExtraction({ text, filename: sample.filename }))
    } catch (err) {
      dispatch(messageAdded({ role: 'assistant', content: `Could not load that sample: ${err.message}` }))
    }
  }

  const send = (text) => {
    const message = (text ?? question).trim()
    if (!message || chatPending) return
    dispatch(messageAdded({ role: 'user', content: message }))
    dispatch(
      askAssistant({
        message,
        contextText: [analysis?.summary, rawText].filter(Boolean).join('\n\n').slice(0, 6000),
        history: messages.slice(-6).map((m) => ({ role: m.role, content: m.content })),
      }),
    )
    setQuestion('')
  }

  const onChatKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send()
    }
  }

  const formats = capabilities?.supported_formats?.join(', ') ?? 'PDF, DOCX, TXT, EML'

  return (
    <aside className="card assistant">
      <div className="card-head">
        <div>
          <h2>
            <span style={{ color: 'var(--ai-600)' }}>✦</span> AI Complaint Intake Assistant
          </h2>
          <p>Paste, drop or upload a complaint document to auto-fill the form</p>
        </div>
        <span
          className={`badge ${capabilities?.llm_live ? 'badge-ai' : 'badge-neutral'}`}
          style={{ marginLeft: 'auto' }}
        >
          {capabilities?.llm_live ? 'LIVE' : 'OFFLINE'}
        </span>
      </div>

      <div className="assistant-body">
        <div
          className={`dropzone ${dragging ? 'dragging' : ''} ${busy ? 'disabled' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            if (!busy) setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => !busy && fileInput.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && !busy && fileInput.current?.click()}
        >
          <span className="icon">☁</span>
          <strong>Drag &amp; drop complaint document here</strong>
          <span>
            or <span className="link">click to browse</span>
          </span>
          <input
            ref={fileInput}
            type="file"
            hidden
            accept=".pdf,.docx,.txt,.md,.eml"
            onChange={(e) => {
              handleFile(e.target.files?.[0])
              e.target.value = ''
            }}
          />
        </div>

        <div className="divider">OR</div>

        <div className="paste-area">
          <textarea
            value={pasted}
            onChange={(e) => setPasted(e.target.value)}
            placeholder="Paste the complaint email or text here…"
            disabled={busy}
          />
          <button
            type="button"
            className="btn btn-ai btn-sm"
            style={{ marginTop: 8, width: '100%', justifyContent: 'center' }}
            onClick={onExtractPasted}
            disabled={busy || pasted.trim().length < 10}
          >
            {busy ? <span className="spin" /> : '✦'} Extract &amp; Analyse Text
          </button>
        </div>

        <div className="hint info">
          <span>ⓘ</span>
          <div>
            Supported formats: {formats}
            <br />
            Max file size: {capabilities?.max_upload_mb ?? 10} MB
          </div>
        </div>

        {samples.length > 0 && (
          <div>
            <div className="panel-label">Try a sample complaint</div>
            <div className="samples">
              {samples.map((sample) => (
                <button
                  key={sample.filename}
                  type="button"
                  className="chip"
                  disabled={busy}
                  onClick={() => onLoadSample(sample)}
                  title={sample.filename}
                >
                  {sample.title}
                </button>
              ))}
            </div>
          </div>
        )}

        {(busy || status === 'ready') && (
          <div>
            <div className="panel-label">Extraction progress</div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="progress-meta">
              <span>{busy ? currentNode ?? 'Working…' : `Analysis complete${filename ? ` · ${filename}` : ''}`}</span>
              <strong>{progress}%</strong>
            </div>
            {completedNodes.length > 0 && (
              <ul className="node-list">
                {completedNodes.map((node, index) => (
                  <li key={`${node.node}-${index}`}>
                    <span className="tick">✓</span>
                    {node.label}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {error && (
          <div className="hint error">
            <span>!</span>
            <div>{error}</div>
          </div>
        )}

        <div className="chat">
          <div className="panel-label">AI Assistant</div>
          {messages.map((message, index) => (
            <div key={index} className={`bubble ${message.role}`}>
              {message.content}
            </div>
          ))}
          {chatPending && (
            <div className="bubble assistant">
              <span className="spin" /> Thinking…
            </div>
          )}
          {status === 'ready' && !chatPending && (
            <div className="samples">
              {SUGGESTIONS.map((suggestion) => (
                <button key={suggestion} type="button" className="chip" onClick={() => send(suggestion)}>
                  {suggestion}
                </button>
              ))}
            </div>
          )}
          <div ref={chatEnd} />
        </div>
      </div>

      <div className="chat-form">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onChatKeyDown}
          placeholder="Ask me anything about this complaint…"
          rows={1}
        />
        <button
          type="button"
          className="icon-btn"
          onClick={() => send()}
          disabled={chatPending || !question.trim()}
          aria-label="Send message"
        >
          ➤
        </button>
      </div>

      <p className="disclaimer">AI responses may contain errors. Please verify information.</p>
    </aside>
  )
}
