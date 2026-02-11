import { useEffect, useCallback } from 'react'

export function useKeyboardShortcuts(shortcuts) {
  const handleKeyDown = useCallback((e) => {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
    const cmdKey = isMac ? e.metaKey : e.ctrlKey
    for (const shortcut of shortcuts) {
      const { key, ctrl, shift, action, preventDefault = true } = shortcut
      if (e.key.toLowerCase() === key.toLowerCase() &&
          (ctrl ? cmdKey : !cmdKey) &&
          (shift ? e.shiftKey : !e.shiftKey)) {
        if (preventDefault) e.preventDefault()
        action(e)
        return
      }
    }
  }, [shortcuts])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

export default useKeyboardShortcuts
