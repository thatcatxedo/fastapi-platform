import { useEffect, useRef } from 'react'

export default function ConfirmModal({
  isOpen,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmStyle = 'primary', // 'primary', 'danger'
  onConfirm,
  onCancel,
  loading = false
}) {
  const confirmButtonRef = useRef(null)

  useEffect(() => {
    if (isOpen) {
      // Focus the confirm button when modal opens
      confirmButtonRef.current?.focus()
      
      // Handle escape key
      const handleEscape = (e) => {
        if (e.key === 'Escape' && !loading) {
          onCancel()
        }
      }
      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen, onCancel, loading])

  if (!isOpen) return null

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget && !loading) {
      onCancel()
    }
  }

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-content" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <h2 id="modal-title" className="modal-title">{title}</h2>
        <p className="modal-message">{message}</p>
        <div className="modal-actions">
          <button 
            className="btn btn-secondary" 
            onClick={onCancel}
            disabled={loading}
          >
            {cancelText}
          </button>
          <button 
            ref={confirmButtonRef}
            className={`btn btn-${confirmStyle}`}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Processing...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
