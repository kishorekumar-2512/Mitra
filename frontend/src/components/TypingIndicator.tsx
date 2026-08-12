/**
 * TypingIndicator — Three pulsing dots shown while the bot is thinking.
 * Purely visual, no backend dependency.
 */
export function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <div className="dot" />
      <div className="dot" />
      <div className="dot" />
    </div>
  );
}
