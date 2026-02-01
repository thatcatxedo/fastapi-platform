import { useState, useRef, useEffect } from 'react'

function DropdownMenu({ trigger, items }) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    function handleEscape(event) {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  const handleItemClick = (item) => {
    if (item.onClick && !item.disabled) {
      item.onClick()
      setIsOpen(false)
    }
  }

  const visibleItems = items.filter(item => item.show !== false)

  return (
    <div className="dropdown" ref={dropdownRef}>
      <button
        className="btn btn-secondary dropdown-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {trigger}
      </button>
      {isOpen && (
        <div className="dropdown-menu">
          {visibleItems.map((item, index) => {
            if (item.type === 'separator') {
              return <div key={index} className="dropdown-separator" />
            }
            return (
              <button
                key={index}
                className={`dropdown-item ${item.danger ? 'dropdown-item-danger' : ''}`}
                onClick={() => handleItemClick(item)}
                disabled={item.disabled}
              >
                {item.label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default DropdownMenu
