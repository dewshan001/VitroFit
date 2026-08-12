import { useState, useRef, useCallback, useEffect } from 'react';
import './PhotoUploadModal.css';

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif'];
const MAX_MB   = 5;
const MAX_BYTES = MAX_MB * 1024 * 1024;

export default function PhotoUploadModal({ isOpen, onClose, onUpload, uploading, uploadMsg }) {
  const [dragging, setDragging]   = useState(false);
  const [preview,  setPreview]    = useState(null);
  const [file,     setFile]       = useState(null);
  const [error,    setError]      = useState('');
  const [entered,  setEntered]    = useState(false); /* mount animation */
  const inputRef   = useRef(null);
  const overlayRef = useRef(null);

  /* Animate in */
  useEffect(() => {
    if (isOpen) {
      // tiny delay so CSS transition fires
      const t = setTimeout(() => setEntered(true), 10);
      return () => clearTimeout(t);
    } else {
      setEntered(false);
    }
  }, [isOpen]);

  /* Reset when closed */
  useEffect(() => {
    if (!isOpen) {
      setPreview(null);
      setFile(null);
      setError('');
      setDragging(false);
    }
  }, [isOpen]);

  /* ── File validation ── */
  const validateAndSet = useCallback((f) => {
    setError('');
    if (!f) return;
    if (!ACCEPTED.includes(f.type)) {
      setError('Unsupported format. Use JPG, PNG, WebP, GIF, or AVIF.');
      return;
    }
    if (f.size > MAX_BYTES) {
      setError(`File too large. Maximum size is ${MAX_MB} MB.`);
      return;
    }
    setFile(f);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  }, []);

  /* ── Drag events ── */
  const onDragEnter = (e) => { e.preventDefault(); e.stopPropagation(); setDragging(true);  };
  const onDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setDragging(false); };
  const onDragOver  = (e) => { e.preventDefault(); e.stopPropagation(); };
  const onDrop      = (e) => {
    e.preventDefault(); e.stopPropagation();
    setDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) validateAndSet(dropped);
  };

  /* ── Input change ── */
  const onInputChange = (e) => {
    const f = e.target.files?.[0];
    if (f) validateAndSet(f);
    e.target.value = '';
  };

  /* ── Submit ── */
  const handleSubmit = () => {
    if (!file) return;
    onUpload(file);
  };

  /* ── Close on backdrop ── */
  const handleOverlayClick = (e) => {
    if (e.target === overlayRef.current) onClose();
  };

  /* ── Escape key ── */
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={overlayRef}
      className={`pum-overlay ${entered ? 'pum-overlay--in' : ''}`}
      onClick={handleOverlayClick}
      role="dialog"
      aria-modal="true"
      aria-label="Upload profile photo"
    >
      <div className={`pum-modal ${entered ? 'pum-modal--in' : ''}`}>

        {/* ── Header ── */}
        <div className="pum-header">
          <div className="pum-header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <div>
            <h2 className="pum-title">Upload Profile Photo</h2>
            <p className="pum-subtitle">JPG, PNG, WebP, GIF · Max {MAX_MB} MB</p>
          </div>
          <button className="pum-close" onClick={onClose} aria-label="Close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* ── Drop zone ── */}
        <div
          className={`pum-dropzone ${dragging ? 'pum-dropzone--active' : ''} ${preview ? 'pum-dropzone--has-preview' : ''}`}
          onDragEnter={onDragEnter}
          onDragLeave={onDragLeave}
          onDragOver={onDragOver}
          onDrop={onDrop}
          onClick={() => !preview && inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && !preview && inputRef.current?.click()}
        >
          {/* Animated grid lines */}
          <div className="pum-grid-lines" aria-hidden="true">
            {[...Array(6)].map((_, i) => <span key={i} className="pum-grid-v" style={{ left: `${(i+1)*100/7}%` }} />)}
            {[...Array(4)].map((_, i) => <span key={i} className="pum-grid-h" style={{ top: `${(i+1)*100/5}%` }} />)}
          </div>

          {preview ? (
            /* Preview mode */
            <div className="pum-preview-wrap">
              <img src={preview} alt="Preview" className="pum-preview-img" />
              <div className="pum-preview-overlay">
                <button
                  className="pum-preview-change"
                  onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                  Change Photo
                </button>
              </div>
              <div className="pum-preview-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
            </div>
          ) : (
            /* Upload prompt */
            <div className="pum-drop-content">
              <div className={`pum-drop-icon ${dragging ? 'pum-drop-icon--bounce' : ''}`}>
                <svg viewBox="0 0 64 64" fill="none">
                  <circle cx="32" cy="32" r="30" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" className="pum-icon-circle"/>
                  <path d="M32 42V22M22 32l10-10 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                  <rect x="20" y="44" width="24" height="3" rx="1.5" fill="currentColor" opacity="0.4"/>
                </svg>
              </div>
              <p className="pum-drop-title">
                {dragging ? 'Release to upload' : 'Drag & drop your photo here'}
              </p>
              <p className="pum-drop-or">— or —</p>
              <button
                className="pum-browse-btn"
                onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
                type="button"
              >
                Browse Files
              </button>
            </div>
          )}

          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(',')}
            className="pum-hidden-input"
            onChange={onInputChange}
          />
        </div>

        {/* ── URL input ── */}
        <div className="pum-divider"><span>or paste an image URL</span></div>
        <div className="pum-url-row">
          <input
            type="url"
            className="pum-url-input"
            placeholder="https://example.com/photo.jpg"
            onChange={async (e) => {
              const url = e.target.value.trim();
              if (!url) { setPreview(null); setFile(null); return; }
              try { new URL(url); setPreview(url); setFile({ _isUrl: true, url }); } catch {}
            }}
          />
        </div>

        {/* ── Error ── */}
        {error && (
          <div className="pum-error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {error}
          </div>
        )}

        {/* ── Upload result msg ── */}
        {uploadMsg && (
          <div className={`pum-result-msg ${uploadMsg.startsWith('✓') ? 'pum-result-msg--ok' : 'pum-result-msg--err'}`}>
            {uploadMsg}
          </div>
        )}

        {/* ── Footer actions ── */}
        <div className="pum-footer">
          <button className="pum-cancel-btn" onClick={onClose} disabled={uploading}>
            Cancel
          </button>
          <button
            className={`pum-upload-btn ${uploading ? 'pum-upload-btn--loading' : ''}`}
            onClick={handleSubmit}
            disabled={!file || uploading}
          >
            {uploading ? (
              <>
                <span className="pum-btn-spinner" />
                Uploading…
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                Upload Photo
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
}
