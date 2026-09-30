#==============
def get_setup_javascript() -> str:
	"""Share a release-safe visual press state across pointer and keyboard input.

	The theme bootstrap installs these delegated listeners once per document.
	Native activation and grading remain responsible for the actual button action.
	"""
	js = "let pressedButton = null;"
	js += "let keyboardPress = false;"
	js += "function releaseButton() {"
	js += "if (pressedButton) pressedButton.classList.remove('qti-pressed');"
	js += "pressedButton = null;"
	js += "keyboardPress = false;"
	js += "}"
	js += "function practiceButton(event) {"
	js += "return event.target instanceof Element ? event.target.closest('.qti-selftest .qti-btn') : null;"
	js += "}"
	js += "function pressButton(event) {"
	js += "releaseButton();"
	js += "const button = practiceButton(event);"
	js += "if (!button || button.disabled) return;"
	js += "pressedButton = button;"
	js += "keyboardPress = event.type === 'keydown';"
	js += "button.classList.add('qti-pressed');"
	js += "}"
	js += "document.addEventListener('pointerdown', function(event) {"
	js += "if (event.button === 0) pressButton(event);"
	js += "});"
	js += "document.addEventListener('pointerup', releaseButton);"
	js += "document.addEventListener('pointercancel', releaseButton);"
	js += "document.addEventListener('keydown', function(event) {"
	js += "if (![' ', 'Enter'].includes(event.key) || event.isComposing) return;"
	js += "if (event.ctrlKey || event.metaKey || event.altKey) return;"
	js += "pressButton(event);"
	js += "});"
	js += "document.addEventListener('keyup', function(event) {"
	js += "if ([' ', 'Enter'].includes(event.key)) releaseButton();"
	js += "});"
	js += "document.addEventListener('focusout', function(event) {"
	# Safari blurs a focused button on pointerdown; pointerup/cancel owns that release.
	js += "if (keyboardPress && practiceButton(event) === pressedButton) releaseButton();"
	js += "});"
	js += "window.addEventListener('blur', releaseButton);"
	return js
