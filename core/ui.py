import html

# --- PREMIUM PALETTE ---
# Using high-contrast emojis and clean MarkdownV2 structure
GOLD_SHIELD = "🛡️"
GOLD_STAR = "🌟"
BLUE_DIAMOND = "🔹"
CYAN_DOT = "💠"
SEPARATOR = "────────────────────────────────"

def escape_md(text):
    """Escapes special characters for Telegram MarkdownV2."""
    if not text: return ""
    # Characters that need escaping in MarkdownV2: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)

def format_premium_card(title, content, footer="Slancio Algo Executive"):
    """
    Generates a premium, high-end card layout using MarkdownV2.
    Note: Title and Content should be pre-escaped if they contain special chars, 
    or use the bold/italic markers carefully.
    """
    card = (
        f"{GOLD_SHIELD} *{title}*\n"
        f"{SEPARATOR}\n\n"
        f"{content}\n\n"
        f"{SEPARATOR}\n"
        f"{GOLD_STAR} _{footer}_"
    )
    return card

def format_signal_card(instrument, side, entry, sl, targets, accuracy="94%"):
    """Specific formatter for trading signals."""
    target_str = "\n".join([f"🎯 *T{i+1}:* {t}" for i, t in enumerate(targets)])
    content = (
        f"📊 *TERMINAL:* `{instrument}`\n"
        f"⚡ *ACTION:* {side}\n"
        f"{SEPARATOR}\n"
        f"💰 *ENTRY:* `{entry}`\n"
        f"🛑 *STOP LOSS:* `{sl}`\n\n"
        f"{target_str}\n"
        f"{SEPARATOR}\n"
        f"🛡️ *ACCURACY:* {accuracy}"
    )
    return format_premium_card("NEW SIGNAL", content)
